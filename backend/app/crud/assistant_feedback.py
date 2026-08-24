"""AI 运维助手反馈 CRUD (批次B)。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.assistant_feedback import AssistantFeedback


def create(db: Session, *, data: dict) -> dict:
    obj = AssistantFeedback(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def list_recent(db: Session, limit: int = 50) -> list[dict]:
    rows = db.query(AssistantFeedback).order_by(AssistantFeedback.id.desc()).limit(limit).all()
    return [_to_dict(r) for r in rows]


def stats(db: Session) -> dict:
    total = db.query(AssistantFeedback).count()
    up = db.query(AssistantFeedback).filter(AssistantFeedback.rating == "up").count()
    down = db.query(AssistantFeedback).filter(AssistantFeedback.rating == "down").count()
    corrected = db.query(AssistantFeedback).filter(AssistantFeedback.correction != "").count()
    return {"total": total, "up": up, "down": down, "corrected": corrected}


def _to_dict(r: AssistantFeedback) -> dict:
    return {
        "id": r.id,
        "question": r.question or "",
        "answer": r.answer or "",
        "rating": r.rating or "",
        "correction": r.correction or "",
        "note": r.note or "",
        "grounded": r.grounded or "",
        "model": r.model or "",
        "user": r.user or "",
        "createdAt": r.created_at or "",
    }
