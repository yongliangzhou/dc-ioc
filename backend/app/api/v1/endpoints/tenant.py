"""租户管理端点 (阶段三 A · 资源运营-租户管理)。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.crud import tenant as crud
from app.schemas.tenant import TenantCreate, TenantUpdate

logger = logging.getLogger("ops.tenant")
router = APIRouter()


@router.get("", response_model=dict)
def list_tenants(db: Session = Depends(get_db),
                 kw: str = Query("", alias="kw"),
                 status: str = Query("", alias="status")):
    """租户列表 (真实数据, 支持关键字/状态过滤)。"""
    kw = (kw or "").strip()
    status_ = (status or "").strip()
    tenants = crud.list_tenants(db, kw=kw, status=status_)
    return {"total": crud.count(db, kw=kw, status=status_), "tenants": tenants}


@router.get("/stats", response_model=dict)
def tenant_stats(db: Session = Depends(get_db)):
    """租户级统计汇总 (顶部统计卡真实聚合)。"""
    return crud.stats(db)


@router.get("/{tid}", response_model=dict)
def get_tenant(tid: int, db: Session = Depends(get_db)):
    obj = crud.get(db, tid)
    if not obj:
        raise HTTPException(status_code=404, detail="租户不存在")
    return crud._to_dict(obj)


@router.post("", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    return crud.create(db, payload.model_dump(exclude_none=True))


@router.put("/{tid}", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def update_tenant(tid: int, payload: TenantUpdate, db: Session = Depends(get_db)):
    obj = crud.update(db, tid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="租户不存在")
    return obj


@router.delete("/{tid}", status_code=204,
               dependencies=[Depends(require_role("admin", "operator"))])
def delete_tenant(tid: int, db: Session = Depends(get_db)):
    if not crud.delete(db, tid):
        raise HTTPException(status_code=404, detail="租户不存在")
