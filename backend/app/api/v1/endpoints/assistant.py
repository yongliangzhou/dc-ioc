"""AI 运维助手接口：基于知识库检索的处置问答。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.assistant import AssistantAskReq, AssistantAskResp, AssistantStatusResp
from app.services import assistant_service

router = APIRouter(prefix="/ops/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantAskResp)
def ask_assistant(
    payload: AssistantAskReq,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """接收运维人员描述的现场情况，基于知识库返回处置建议。"""
    ctx = payload.context.model_dump() if payload.context else None
    return assistant_service.answer(db, payload.question, ctx)


@router.get("/status", response_model=AssistantStatusResp)
def assistant_status(_user=Depends(get_current_user)):
    """一键自查大模型接入状态：配置 / 可达性 / Key 有效性 / 模型是否存在。"""
    return assistant_service.check_llm_status()
