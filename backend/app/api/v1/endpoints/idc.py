"""数据中心管理 API (phase: datacenter)。

- GET    /api/idc             列表 (按 region/status 过滤)
- GET    /api/idc/{id}        详情
- POST   /api/idc             新建 (首个中心自动设为当前)
- PUT    /api/idc/{id}        更新
- DELETE /api/idc/{id}        删除 (删当前则自动下移)
- GET    /api/idc/current     当前默认中心
- PUT    /api/idc/current     切换当前中心 (全局生效)
- GET    /api/idc/compare     跨中心对比指标
- GET    /api/idc/alarms      跨中心统一告警汇总

读接口鉴权; 写接口 (建/改/删/切换) 要求 admin 角色。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import idc as idc_crud
from app.models.user import User
from app.schemas.idc import (
    IdcBatchDeleteIn,
    IdcBatchDeleteOut,
    IdcCreate,
    IdcOpLogsOut,
    IdcOut,
    IdcServicesOut,
    IdcToggleStatusOut,
    IdcUpdate,
)

router = APIRouter(tags=["idc"])


@router.get("", response_model=list[IdcOut], summary="数据中心列表")
def list_idcs(
    region: str = Query("", description="按地域过滤"),
    status: str = Query("", description="按状态过滤 运营/建设/下线"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    return idc_crud.list_idcs(db, region=region, status=status, limit=limit, offset=offset)


@router.get("/current", summary="当前默认数据中心")
def current_idc(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    row = idc_crud.get_current(db)
    if not row:
        raise HTTPException(status_code=404, detail="尚未配置任何数据中心")
    return row


@router.put("/current", summary="切换当前数据中心")
def set_current_idc(
    cid: int = Query(..., description="目标数据中心 id"),
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    row = idc_crud.set_current(db, cid)
    if not row:
        raise HTTPException(status_code=404, detail="数据中心不存在")
    return row


@router.get("/compare", summary="跨中心对比指标")
def compare_idcs(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    return idc_crud.compare(db)


@router.get("/alarms", summary="跨中心统一告警汇总")
def unified_alarms(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    return idc_crud.unified_alarms(db)


@router.get("/op-logs", response_model=IdcOpLogsOut, summary="操作日志")
def op_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    return {"total": idc_crud.list_op_logs(limit=limit).__len__(),
            "items": idc_crud.list_op_logs(limit=limit)}


@router.post("/batch-delete", response_model=IdcBatchDeleteOut, summary="批量删除数据中心")
def batch_delete_idcs(
    payload: IdcBatchDeleteIn,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    return idc_crud.batch_delete(db, payload.ids)


@router.put("/{cid}/toggle-status", response_model=IdcToggleStatusOut, summary="启用/停用切换")
def toggle_status_idc(
    cid: int,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    row = idc_crud.toggle_status(db, cid)
    if not row:
        raise HTTPException(status_code=404, detail="数据中心不存在")
    return row


@router.get("/{cid}/services", response_model=IdcServicesOut, summary="关联服务")
def services_idc(cid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    row = idc_crud.related_services(db, cid)
    if not row:
        raise HTTPException(status_code=404, detail="数据中心不存在")
    return row


@router.get("/{cid}", response_model=IdcOut, summary="数据中心详情")
def get_idc(cid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    row = idc_crud.get(db, cid)
    if not row:
        raise HTTPException(status_code=404, detail="数据中心不存在")
    return row


@router.post("", response_model=IdcOut, status_code=201, summary="新建数据中心")
def create_idc(
    payload: IdcCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    try:
        row = idc_crud.create(db, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    idc_crud.add_op_log("create", f"数据中心 #{row['id']} {row['name']}")
    return row


@router.put("/{cid}", response_model=IdcOut, summary="更新数据中心")
def update_idc(
    cid: int,
    payload: IdcUpdate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        row = idc_crud.update(db, cid, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not row:
        raise HTTPException(status_code=404, detail="数据中心不存在")
    idc_crud.add_op_log("update", f"数据中心 #{cid} {row['name']}")
    return row


@router.delete("/{cid}", status_code=204, summary="删除数据中心")
def delete_idc(
    cid: int,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    if not idc_crud.delete(db, cid):
        raise HTTPException(status_code=404, detail="数据中心不存在")
