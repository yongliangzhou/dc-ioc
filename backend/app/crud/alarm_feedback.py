"""告警处理反馈 CRUD (批次B)。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.alarm_feedback import AlarmFeedback


def create(db: Session, *, data: dict) -> dict:
    obj = AlarmFeedback(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def list_by_alarm(db: Session, alarm_id: str) -> list[dict]:
    rows = (
        db.query(AlarmFeedback)
        .filter(AlarmFeedback.alarm_id == alarm_id)
        .order_by(AlarmFeedback.id.desc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def _to_dict(r: AlarmFeedback) -> dict:
    return {
        "id": r.id,
        "alarmId": r.alarm_id or "",
        "system": r.system or "",
        "result": r.result or "",
        "note": r.note or "",
        "operator": r.operator or "",
        "createdAt": r.created_at or "",
    }
