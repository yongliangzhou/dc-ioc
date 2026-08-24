"""巡检管理端点 (阶段三 A)。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.crud import inspection as crud
from app.services import dc_aggregator as agg
from app.schemas.inspection import RouteCreate, RouteUpdate, FindingCreate, FindingUpdate

logger = logging.getLogger("ops.inspection")
router = APIRouter()


@router.get("", response_model=dict)
def list_inspection(db: Session = Depends(get_db)):
    """巡检总览 (B3): 真实 external_devices 为巡检对象, 合并用户自建路线。"""
    return agg.inspection_plan(db)


# ---------- 路线 ----------
@router.get("/routes", response_model=list)
def list_routes(db: Session = Depends(get_db)):
    return crud.list_routes(db)


@router.post("/routes", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def create_route(payload: RouteCreate, db: Session = Depends(get_db)):
    return crud.create_route(db, payload.model_dump(exclude_none=True))


@router.put("/routes/{rid}", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def update_route(rid: int, payload: RouteUpdate, db: Session = Depends(get_db)):
    obj = crud.update_route(db, rid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="巡检路线不存在")
    return obj


@router.delete("/routes/{rid}", status_code=204, dependencies=[Depends(require_role("admin", "operator"))])
def delete_route(rid: int, db: Session = Depends(get_db)):
    if not crud.delete_route(db, rid):
        raise HTTPException(status_code=404, detail="巡检路线不存在")


# ---------- 发现 ----------
@router.get("/findings", response_model=list)
def list_findings(db: Session = Depends(get_db)):
    return crud.list_findings(db)


@router.get("/findings/{fid}", response_model=dict)
def get_finding(fid: int, db: Session = Depends(get_db)):
    obj = crud.get_finding(db, fid)
    if not obj:
        raise HTTPException(status_code=404, detail="巡检发现不存在")
    return crud._finding_dict(obj)


@router.post("/findings", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def create_finding(payload: FindingCreate, db: Session = Depends(get_db)):
    return crud.create_finding(db, payload.model_dump(exclude_none=True))


@router.put("/findings/{fid}", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def update_finding(fid: int, payload: FindingUpdate, db: Session = Depends(get_db)):
    obj = crud.update_finding(db, fid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="巡检发现不存在")
    return obj


@router.delete("/findings/{fid}", status_code=204, dependencies=[Depends(require_role("admin", "operator"))])
def delete_finding(fid: int, db: Session = Depends(get_db)):
    if not crud.delete_finding(db, fid):
        raise HTTPException(status_code=404, detail="巡检发现不存在")
