"""故障影响分析接口: 候选故障源 + 影响分析 + 历史存档会签。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.crud import fault_impact as fi_crud
from app.schemas import fault_impact as fi_schema

router = APIRouter()


class HistorySaveReq(BaseModel):
    title: str = ""
    faultIds: list[int] = []
    severity: str = "low"
    summary: dict = {}
    businesses: list = []
    mitigations: list = []
    signers: list = []
    pushed: bool = False
    createdBy: str = ""


class SignReq(BaseModel):
    signer: str


@router.get("/fault-impact/sources", summary="候选故障源 (真实拓扑节点 + 易故障提示)")
def fault_sources() -> fi_schema.FaultSourceList:
    return fi_crud.list_sources()


@router.post("/fault-impact/analyze", summary="故障影响分析 (沿真实拓扑 BFS 传播)")
def fault_analyze(req: fi_schema.FaultImpactReq) -> fi_schema.FaultImpactResp:
    return fi_crud.analyze(req.faultIds, req.scope)


@router.get("/fault-impact/history", summary="影响分析报告历史列表 (存档 + 会签)")
def history_list(db: Session = Depends(get_db), limit: int = Query(50, alias="limit")):
    return fi_crud.list_history(db, limit=limit)


@router.get("/fault-impact/history/{hid}", summary="报告详情")
def history_detail(hid: int, db: Session = Depends(get_db)):
    obj = fi_crud.get_history(db, hid)
    if not obj:
        raise HTTPException(status_code=404, detail="报告不存在")
    return obj


@router.post("/fault-impact/history", summary="保存影响分析报告 (存档)",
             dependencies=[Depends(require_role("admin", "operator"))])
def history_save(payload: HistorySaveReq, db: Session = Depends(get_db)):
    return fi_crud.save_history(db, payload.model_dump())


@router.post("/fault-impact/history/{hid}/sign", summary="报告会签 (追加会签人)",
             dependencies=[Depends(require_role("admin", "operator"))])
def history_sign(hid: int, payload: SignReq, db: Session = Depends(get_db)):
    obj = fi_crud.sign_history(db, hid, payload.signer)
    if not obj:
        raise HTTPException(status_code=404, detail="报告不存在")
    return obj
