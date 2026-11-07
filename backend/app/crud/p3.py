"""阶段三数据访问层: 通用 CRUD + 各域业务操作。"""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import p3 as m
from app.services import p3_services as svc

logger = logging.getLogger(__name__)


class P3Conflict(ValueError):
    """唯一约束冲突 / 状态机非法流转。"""


def to_dict(row) -> dict:
    """按表列白名单序列化 (时间转 ISO, 不直接透出 ORM 对象)。"""
    out = {}
    for col in row.__table__.columns:
        value = getattr(row, col.name, None)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        out[col.name] = value
    return out


def create_row(db: Session, model, payload: dict, unique_field: str | None = None) -> dict:
    if unique_field and payload.get(unique_field) is not None:
        existing = db.scalar(
            select(model).where(getattr(model, unique_field) == payload[unique_field])
        )
        if existing is not None:
            raise P3Conflict(f"{unique_field}={payload[unique_field]} 已存在")
    row = model(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_dict(row)


def list_rows(
    db: Session,
    model,
    where: dict | None = None,
    limit: int = 200,
    offset: int = 0,
    order_desc: bool = True,
) -> list[dict]:
    stmt = select(model)
    for key, value in (where or {}).items():
        if value is not None and hasattr(model, key):
            stmt = stmt.where(getattr(model, key) == value)
    col = model.id
    stmt = stmt.order_by(col.desc() if order_desc else col.asc()).limit(min(limit, 500)).offset(offset)
    return [to_dict(r) for r in db.scalars(stmt).all()]


def get_row(db: Session, model, row_id: int):
    return db.get(model, row_id)


def delete_row(db: Session, model, row_id: int) -> bool:
    row = db.get(model, row_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


# ------------------------------------------------------------------ #
# IPAM
# ------------------------------------------------------------------ #
def used_addresses(db: Session, subnet_id: int | None = None, cidr: str | None = None) -> list[str]:
    stmt = select(IpAddressAlias)
    if subnet_id is not None:
        stmt = stmt.where(IpAddressAlias.subnet_id == subnet_id)
    return [r.address for r in db.scalars(stmt).all()]


IpAddressAlias = m.IpAddress  # 保持 select() 可读性的别名


def subnet_views(db: Session) -> list[dict]:
    out = []
    for row in list_rows(db, m.IpSubnet):
        used = used_addresses(db, subnet_id=row["id"])
        out.append({**row, **svc.subnet_stats(row["cidr"], used)})
    return out


def allocate_next(db: Session, subnet_id: int, device_ci: str = "") -> dict:
    subnet = get_row(db, m.IpSubnet, subnet_id)
    if subnet is None:
        raise P3Conflict("子网不存在")
    used = used_addresses(db, subnet_id=subnet_id)
    ip = svc.next_available(subnet["cidr"] if isinstance(subnet, dict) else subnet.cidr, used)
    if ip is None:
        raise P3Conflict("该子网已无可分配地址")
    return create_row(db, m.IpAddress, {
        "address": ip,
        "subnet_id": subnet_id,
        "status": "allocated",
        "device_ci": device_ci,
        "note": "auto-allocated",
    }, unique_field="address")


def ipam_stats(db: Session) -> dict:
    vlans = list_rows(db, m.IpVlan, limit=500)
    subnets = subnet_views(db)
    addresses = list_rows(db, m.IpAddress, limit=500)
    return {
        "vlans": len(vlans),
        "subnets": len(subnets),
        "addresses": len(addresses),
        "allocated": sum(1 for a in addresses if a["status"] == "allocated"),
        "avg_utilization_pct": round(
            sum(s["utilization_pct"] for s in subnets) / len(subnets), 2
        ) if subnets else 0.0,
    }


# ------------------------------------------------------------------ #
# 自动发现 (待确认区)
# ------------------------------------------------------------------ #
def upsert_candidates(db: Session, scanned: list[dict]) -> dict:
    """扫描结果只写待确认区; 已存在的 IP 仅更新 last_seen / open_ports。"""
    created = updated = 0
    now = svc.now_str()
    for item in scanned:
        ip = item["ip"]
        row = db.scalar(select(m.DiscoveryCandidate).where(m.DiscoveryCandidate.ip == ip))
        if row is None:
            db.add(m.DiscoveryCandidate(
                ip=ip,
                hostname=item.get("hostname") or "",
                mac=item.get("mac") or "",
                open_ports=item.get("open_ports") or [],
                source="tcp-probe",
                status="pending",
                first_seen=now,
                last_seen=now,
            ))
            created += 1
        else:
            row.last_seen = now
            row.open_ports = item.get("open_ports") or []
            if row.status == "rejected":
                row.status = "pending"  # 重新发现后回到待确认, 但仍需人工确认
            updated += 1
    db.commit()
    return {"created": created, "updated": updated, "total": created + updated}


def decide_candidate(db: Session, candidate_id: int, action: str, matched_ci: str = "") -> dict:
    row = db.get(m.DiscoveryCandidate, candidate_id)
    if row is None:
        raise P3Conflict("候选不存在")
    if row.status != "pending":
        raise P3Conflict(f"候选已处于 {row.status} 状态, 不可重复处理")
    if action not in ("confirm", "reject"):
        raise P3Conflict("非法操作")
    row.status = "confirmed" if action == "confirm" else "rejected"
    if action == "confirm":
        row.matched_ci = matched_ci or f"external:{row.ip}"
    row.last_seen = svc.now_str()
    db.commit()
    db.refresh(row)
    return to_dict(row)


# ------------------------------------------------------------------ #
# 采购 / 盘点
# ------------------------------------------------------------------ #
def expiring(db: Session, days: int = 30) -> list[dict]:
    return svc.expiring_orders(list_rows(db, m.PurchaseOrder, limit=500), days)


def stocktake_report(db: Session, task_id: int, expected_cis: list[str] | None = None) -> dict:
    task = db.get(m.StocktakeTask, task_id)
    if task is None:
        raise P3Conflict("盘点任务不存在")
    items = list_rows(db, m.StocktakeItem, where={"task_id": task_id}, limit=500)
    expected = expected_cis if expected_cis is not None else [
        i["asset_ci"] for i in items if i["result"] != "unexpected"
    ]
    return {
        "task": to_dict(task),
        **svc.stocktake_report(items, expected),
    }


# ------------------------------------------------------------------ #
# 自定义字段
# ------------------------------------------------------------------ #
def custom_defs(db: Session) -> list[dict]:
    return list_rows(db, m.CustomFieldDef, limit=500, order_desc=False)


def read_custom_values(db: Session, equipment_id: int) -> dict:
    from app.models.equipment import Equipment

    row = db.get(Equipment, equipment_id)
    if row is None:
        raise P3Conflict("设备不存在")
    return {"equipment_id": equipment_id, "values": dict(getattr(row, "custom_attributes", None) or {})}


def write_custom_values(db: Session, equipment_id: int, values: dict) -> dict:
    from app.models.equipment import Equipment

    row = db.get(Equipment, equipment_id)
    if row is None:
        raise P3Conflict("设备不存在")
    normalized = svc.validate_custom_values(custom_defs(db), values)
    row.custom_attributes = normalized
    db.commit()
    return {"equipment_id": equipment_id, "values": normalized}
