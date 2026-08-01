"""值班排班 CRUD (2.3)。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.shift import ShiftSchedule


def list_items(
    db: Session,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 60,
    offset: int = 0,
) -> list[dict]:
    q = db.query(ShiftSchedule)
    if start:
        q = q.filter(ShiftSchedule.date >= start)
    if end:
        q = q.filter(ShiftSchedule.date <= end)
    q = q.order_by(ShiftSchedule.date.asc(), ShiftSchedule.shift.asc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, item_id: int) -> Optional[dict]:
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == item_id).first()
    return _to_dict(row) if row else None


def create(db: Session, *, data: dict) -> dict:
    row = ShiftSchedule(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def update(db: Session, item_id: int, *, data: dict) -> Optional[dict]:
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == item_id).first()
    if not row:
        return None
    for k, v in data.items():
        if k in ("id", "created_at"):
            continue
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def delete(db: Session, item_id: int) -> bool:
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == item_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def count(db: Session) -> int:
    return db.query(ShiftSchedule).count()


def _to_dict(r: ShiftSchedule) -> dict:
    return {
        "id": r.id,
        "date": r.date,
        "shift": r.shift,
        "members": r.members or [],
        "leader": r.leader or "",
        "note": r.note or "",
        "createdAt": r.created_at,
        "updatedAt": r.updated_at,
    }
