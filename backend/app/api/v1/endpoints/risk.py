"""风险管理端点 (阶段三 A)。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.crud import risk as crud
from app.schemas.risk import RiskCreate, RiskUpdate

logger = logging.getLogger("ops.risk")
router = APIRouter()


@router.get("", response_model=dict)
def list_risk(db: Session = Depends(get_db), kw: str = Query("", alias="kw"),
              cat: str = Query("", alias="cat")):
    """风险矩阵: 统计 + 风险项列表。"""
    items = crud.list_items(db, kw=kw, cat=cat)
    return {"stats": crud.stats(db), "matrix": items}


@router.get("/{rid}", response_model=dict)
def get_risk(rid: int, db: Session = Depends(get_db)):
    obj = crud.get(db, rid)
    if not obj:
        raise HTTPException(status_code=404, detail="风险项不存在")
    return crud._to_dict(obj)


@router.post("", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def create_risk(payload: RiskCreate, db: Session = Depends(get_db)):
    return crud.create(db, payload.model_dump(exclude_none=True))


@router.put("/{rid}", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def update_risk(rid: int, payload: RiskUpdate, db: Session = Depends(get_db)):
    obj = crud.update(db, rid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="风险项不存在")
    return obj


@router.delete("/{rid}", status_code=204, dependencies=[Depends(require_role("admin", "operator"))])
def delete_risk(rid: int, db: Session = Depends(get_db)):
    if not crud.delete(db, rid):
        raise HTTPException(status_code=404, detail="风险项不存在")
