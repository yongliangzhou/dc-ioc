"""演练管理端点 (阶段三 A)。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.crud import drill as crud
from app.crud import drill_record as rec
from app.services import dc_aggregator as agg
from app.schemas.drill import DrillCreate, DrillUpdate
from app.schemas.drill_record import DrillRecordCreate, DrillRecordUpdate

logger = logging.getLogger("ops.drill")
router = APIRouter()


@router.get("", response_model=dict)
def list_drill(db: Session = Depends(get_db), kw: str = Query("", alias="kw"),
               type: str = Query("", alias="type")):
    """演练总览 (B3): 依据真实专业域类别生成建议演练, 合并 DB 计划。"""
    plan = agg.drill_plan(db)
    kw = (kw or "").strip()
    type_ = (type or "").strip()
    plans = plan["plans"]
    if kw:
        plans = [p for p in plans if kw in (p.get("name", "") + p.get("code", ""))]
    if type_:
        plans = [p for p in plans if p.get("type") == type_]
    return {"stats": plan["stats"], "plans": plans}


@router.get("/records", response_model=dict)
def list_drill_records(db: Session = Depends(get_db),
                       planId: int = Query(None, alias="planId")):
    """演练记录列表 (真实数据, 支持按 planId 过滤)。"""
    records = rec.list_records(db, plan_id=planId)
    return {"records": records, "total": rec.count(db, plan_id=planId)}


@router.post("/records", response_model=dict,
             dependencies=[Depends(require_role("admin", "operator"))])
def create_drill_record(payload: DrillRecordCreate, db: Session = Depends(get_db)):
    return rec.create(db, payload.model_dump(exclude_none=True))


@router.get("/records/{rid}", response_model=dict)
def get_drill_record(rid: int, db: Session = Depends(get_db)):
    obj = rec.get(db, rid)
    if not obj:
        raise HTTPException(status_code=404, detail="演练记录不存在")
    return obj


@router.put("/records/{rid}", response_model=dict,
            dependencies=[Depends(require_role("admin", "operator"))])
def update_drill_record(rid: int, payload: DrillRecordUpdate, db: Session = Depends(get_db)):
    obj = rec.update(db, rid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="演练记录不存在")
    return obj


@router.delete("/records/{rid}", status_code=204,
               dependencies=[Depends(require_role("admin", "operator"))])
def delete_drill_record(rid: int, db: Session = Depends(get_db)):
    if not rec.delete(db, rid):
        raise HTTPException(status_code=404, detail="演练记录不存在")


@router.get("/{rid}", response_model=dict)
def get_drill(rid: int, db: Session = Depends(get_db)):
    obj = crud.get(db, rid)
    if not obj:
        raise HTTPException(status_code=404, detail="演练计划不存在")
    return crud._to_dict(obj)


@router.post("", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def create_drill(payload: DrillCreate, db: Session = Depends(get_db)):
    return crud.create(db, payload.model_dump(exclude_none=True))


@router.put("/{rid}", response_model=dict, dependencies=[Depends(require_role("admin", "operator"))])
def update_drill(rid: int, payload: DrillUpdate, db: Session = Depends(get_db)):
    obj = crud.update(db, rid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="演练计划不存在")
    return obj


@router.delete("/{rid}", status_code=204, dependencies=[Depends(require_role("admin", "operator"))])
def delete_drill(rid: int, db: Session = Depends(get_db)):
    if not crud.delete(db, rid):
        raise HTTPException(status_code=404, detail="演练计划不存在")
