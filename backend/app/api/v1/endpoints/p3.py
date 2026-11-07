"""阶段三端点: IPAM / 自动发现 / 采购盘点 / 自定义字段。

5 个独立 APIRouter, 由 `api/v1/router.py` 挂载:
  /api/ipam, /api/ops/discovery, /api/ops/procurement,
  /api/ops/stocktake, /api/ops/custom-fields

写操作统一 require_role("admin", "operator"); 扫描受 DISCOVERY_ENABLED 开关控制。
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user, require_role
from app.crud import p3 as crud
from app.db.session import SessionLocal
from app.models import p3 as m
from app.schemas import p3 as s
from app.services import p3_services as svc

logger = logging.getLogger(__name__)
_rw = [Depends(require_role("admin", "operator"))]

ipam_router = APIRouter(tags=["ipam"])
discovery_router = APIRouter(tags=["discovery"])
procurement_router = APIRouter(tags=["procurement"])
stocktake_router = APIRouter(tags=["stocktake"])
custom_field_router = APIRouter(tags=["custom-fields"])


def _session():
    return SessionLocal()


def _conflict(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------ #
# IPAM
# ------------------------------------------------------------------ #
@ipam_router.get("/vlans", summary="VLAN 列表")
def list_vlans(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.list_rows(db, m.IpVlan, limit=500)
    finally:
        db.close()


@ipam_router.post("/vlans", summary="新建 VLAN", dependencies=_rw)
def create_vlan(body: s.VlanIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.create_row(db, m.IpVlan, body.model_dump(), unique_field="vlan_id")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@ipam_router.delete("/vlans/{row_id}", summary="删除 VLAN", dependencies=_rw)
def delete_vlan(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.IpVlan, row_id):
            raise HTTPException(status_code=404, detail="VLAN 不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


@ipam_router.get("/subnets", summary="子网列表 (含利用率)")
def list_subnets(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.subnet_views(db)
    finally:
        db.close()


@ipam_router.post("/subnets", summary="新建子网", dependencies=_rw)
def create_subnet(body: s.SubnetIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.create_row(db, m.IpSubnet, body.model_dump(), unique_field="cidr")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@ipam_router.get("/subnets/{row_id}/next-available", summary="查询下一个可用 IP")
def subnet_next(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        subnet = crud.get_row(db, m.IpSubnet, row_id)
        if subnet is None:
            raise HTTPException(status_code=404, detail="子网不存在")
        used = crud.used_addresses(db, subnet_id=row_id)
        return {"address": svc.next_available(subnet.cidr, used)}
    finally:
        db.close()


@ipam_router.post("/subnets/{row_id}/allocate", summary="分配下一个可用 IP", dependencies=_rw)
def allocate(row_id: int, device_ci: str = Query(""), _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.allocate_next(db, row_id, device_ci)
    except (crud.P3Conflict, svc.ValidationError) as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@ipam_router.delete("/subnets/{row_id}", summary="删除子网", dependencies=_rw)
def delete_subnet(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.IpSubnet, row_id):
            raise HTTPException(status_code=404, detail="子网不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


@ipam_router.get("/addresses", summary="IP 地址列表")
def list_addresses(
    subnet_id: int | None = Query(None),
    status: str | None = Query(None),
    _user=Depends(get_current_user),
):
    db = _session()
    try:
        return crud.list_rows(db, m.IpAddress, where={"subnet_id": subnet_id, "status": status}, limit=500)
    finally:
        db.close()


@ipam_router.post("/addresses", summary="登记 IP 地址", dependencies=_rw)
def create_address(body: s.AddressIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.create_row(db, m.IpAddress, body.model_dump(), unique_field="address")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@ipam_router.delete("/addresses/{row_id}", summary="删除 IP 地址", dependencies=_rw)
def delete_address(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.IpAddress, row_id):
            raise HTTPException(status_code=404, detail="IP 记录不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


@ipam_router.get("/stats", summary="IPAM 汇总")
def ipam_stats(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.ipam_stats(db)
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 自动发现
# ------------------------------------------------------------------ #
def _discovery_enabled() -> bool:
    # 默认关闭 (安全), 生产按需显式开启; 仍强制私网段 + /24 上限
    return os.getenv("DISCOVERY_ENABLED", "false").strip().lower() == "true"


@discovery_router.get("/candidates", summary="待确认区候选列表")
def list_candidates(status: str | None = Query(None), _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.list_rows(db, m.DiscoveryCandidate, where={"status": status}, limit=500)
    finally:
        db.close()


@discovery_router.post("/scan", summary="网段 TCP 探测 (仅写待确认区)", dependencies=_rw)
async def scan(body: s.ScanIn, _user=Depends(get_current_user)):
    if not _discovery_enabled():
        raise HTTPException(status_code=403, detail="自动发现未启用: 设置 DISCOVERY_ENABLED=true")
    try:
        scanned = await svc.scan_subnet(body.cidr, body.ports, body.concurrency)
    except svc.ValidationError as exc:
        raise _bad_request(exc) from exc
    db = _session()
    try:
        return {"scanned": len(scanned), **crud.upsert_candidates(db, scanned), "candidates": scanned}
    except Exception as exc:  # noqa: BLE001 - 扫描结果落库失败要显式报错并留痕
        logger.exception("扫描候选落库失败: %s", exc)
        raise HTTPException(status_code=500, detail="扫描结果落库失败") from exc
    finally:
        db.close()


@discovery_router.post("/candidates/{row_id}/confirm", summary="确认候选 (写入 matched_ci)", dependencies=_rw)
def confirm_candidate(row_id: int, body: s.CandidateDecision, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.decide_candidate(db, row_id, "confirm", body.matched_ci)
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@discovery_router.post("/candidates/{row_id}/reject", summary="忽略候选", dependencies=_rw)
def reject_candidate(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.decide_candidate(db, row_id, "reject")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@discovery_router.delete("/candidates/{row_id}", summary="清理候选", dependencies=_rw)
def delete_candidate(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.DiscoveryCandidate, row_id):
            raise HTTPException(status_code=404, detail="候选不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 采购合同 / 盘点
# ------------------------------------------------------------------ #
@procurement_router.get("/orders", summary="采购合同列表")
def list_orders(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.list_rows(db, m.PurchaseOrder, limit=500)
    finally:
        db.close()


@procurement_router.post("/orders", summary="新建采购合同", dependencies=_rw)
def create_order(body: s.OrderIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.create_row(db, m.PurchaseOrder, body.model_dump(), unique_field="order_no")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@procurement_router.delete("/orders/{row_id}", summary="删除采购合同", dependencies=_rw)
def delete_order(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.PurchaseOrder, row_id):
            raise HTTPException(status_code=404, detail="合同不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


@procurement_router.get("/expiring", summary="N 天内保修/合同到期清单")
def expiring_orders(days: int = Query(30, ge=1, le=365), _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.expiring(db, days)
    finally:
        db.close()


@stocktake_router.get("/tasks", summary="盘点任务列表")
def list_tasks(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.list_rows(db, m.StocktakeTask, limit=500)
    finally:
        db.close()


@stocktake_router.post("/tasks", summary="新建盘点任务", dependencies=_rw)
def create_task(body: s.TaskIn, user=Depends(get_current_user)):
    db = _session()
    try:
        payload = body.model_dump()
        payload["created_by"] = getattr(user, "username", "system")
        payload["started_at"] = svc.now_str()
        return crud.create_row(db, m.StocktakeTask, payload)
    finally:
        db.close()


@stocktake_router.get("/tasks/{task_id}/items", summary="盘点明细")
def list_items(task_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.list_rows(db, m.StocktakeItem, where={"task_id": task_id}, limit=500)
    finally:
        db.close()


@stocktake_router.post("/tasks/{task_id}/items", summary="登记盘点结果", dependencies=_rw)
def add_item(task_id: int, body: s.ItemIn, user=Depends(get_current_user)):
    db = _session()
    try:
        payload = body.model_dump()
        payload["task_id"] = task_id
        payload["confirmed_by"] = getattr(user, "username", "system")
        payload["confirmed_at"] = svc.now_str()
        return crud.create_row(db, m.StocktakeItem, payload)
    finally:
        db.close()


@stocktake_router.get("/tasks/{task_id}/report", summary="盘点差异报告")
def task_report(
    task_id: int,
    expected_cis: str = Query("", description="逗号分隔的期望资产 CI 列表"),
    _user=Depends(get_current_user),
):
    db = _session()
    try:
        expected = [x.strip() for x in expected_cis.split(",") if x.strip()] or None
        return crud.stocktake_report(db, task_id, expected)
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 自定义字段
# ------------------------------------------------------------------ #
@custom_field_router.get("", summary="自定义字段定义列表")
def list_custom_fields(_user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.custom_defs(db)
    finally:
        db.close()


@custom_field_router.post("", summary="新增字段定义", dependencies=_rw)
def create_custom_field(body: s.CustomFieldIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.create_row(db, m.CustomFieldDef, body.model_dump(), unique_field="key")
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@custom_field_router.delete("/{row_id}", summary="删除字段定义", dependencies=_rw)
def delete_custom_field(row_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        if not crud.delete_row(db, m.CustomFieldDef, row_id):
            raise HTTPException(status_code=404, detail="字段定义不存在")
        return {"deleted": True, "id": row_id}
    finally:
        db.close()


@custom_field_router.get("/values/{equipment_id}", summary="读取设备自定义字段值")
def get_custom_values(equipment_id: int, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.read_custom_values(db, equipment_id)
    except crud.P3Conflict as exc:
        raise _conflict(exc) from exc
    finally:
        db.close()


@custom_field_router.put("/values/{equipment_id}", summary="保存设备自定义字段值", dependencies=_rw)
def put_custom_values(equipment_id: int, body: s.CustomValuesIn, _user=Depends(get_current_user)):
    db = _session()
    try:
        return crud.write_custom_values(db, equipment_id, body.values)
    except (crud.P3Conflict, svc.ValidationError) as exc:
        raise _bad_request(exc) from exc
    finally:
        db.close()
