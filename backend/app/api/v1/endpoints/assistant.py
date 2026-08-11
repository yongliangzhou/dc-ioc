"""AI 运维助手接口：基于知识库检索的处置问答。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.assistant import AssistantAskReq, AssistantAskResp, AssistantStatusResp
from app.schemas.assistant_feedback import AssistantFeedbackCreate
from app.crud import assistant_feedback as fb_crud
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
    """一键自查大模型接入状态：配置 / 可达性 / Key 有效性 / 模型是否存在，并附带 Dify RAG 层状态。"""
    data = assistant_service.check_llm_status()
    data["dify"] = assistant_service.check_dify_status()
    return data


@router.post("/feedback", summary="提交问答反馈(满意度/纠错)")
def submit_feedback(
    payload: AssistantFeedbackCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """用户对 AI 回答的反馈：点赞/点踩/纠错, 用于持续优化检索与知识库。"""
    data = payload.model_dump()
    data["user"] = _user.username
    return {"ok": True, "id": fb_crud.create(db, data=data)["id"]}


@router.get("/feedback", summary="反馈记录(最近)")
def list_feedback(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return {"total": fb_crud.stats(db)["total"], "items": fb_crud.list_recent(db)}
