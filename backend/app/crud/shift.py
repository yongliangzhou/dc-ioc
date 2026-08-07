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


def count_handover(db: Session, shift_date: str = "", status: str = "") -> int:
    q = db.query(ShiftHandover)
    if shift_date:
        q = q.filter(ShiftHandover.shift_date == shift_date)
    if status:
        q = q.filter(ShiftHandover.status == status)
    return q.scalar() or 0


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


# ===== 交接班 CRUD =====
from app.models.shift import ShiftHandover


def _to_handover_dict(r: ShiftHandover) -> dict:
    return {
        "id": r.id,
        "shiftDate": r.shift_date or "",
        "shiftType": r.shift_type or "day",
        "fromUser": r.from_user or "",
        "toUser": r.to_user or "",
        "items": r.items or "[]",
        "note": r.note or "",
        "status": r.status or "pending",
        "createdAt": r.created_at,
        "updatedAt": r.updated_at,
    }


def list_handovers(db: Session, shift_date: str = "", status: str = "",
                   limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(ShiftHandover)
    if shift_date:
        q = q.filter(ShiftHandover.shift_date == shift_date)
    if status:
        q = q.filter(ShiftHandover.status == status)
    q = q.order_by(ShiftHandover.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_handover_dict(r) for r in rows]


def get_handover(db: Session, hid: int):
    return db.query(ShiftHandover).filter(ShiftHandover.id == hid).first()


def create_handover(db: Session, *, data: dict) -> dict:
    row = ShiftHandover(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_handover_dict(row)


def update_handover(db: Session, hid: int, *, data: dict) -> Optional[dict]:
    row = get_handover(db, hid)
    if not row:
        return None
    for k, v in data.items():
        if k in ("id", "created_at"):
            continue
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_handover_dict(row)


def delete_handover(db: Session, hid: int) -> bool:
    row = get_handover(db, hid)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
