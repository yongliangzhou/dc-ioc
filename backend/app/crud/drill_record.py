"""(演练记录 CRUD (阶段三 A · 运维作业-演练管理)。

前端以 camelCase 提交, 模型以 snake_case 存储, 故统一用 _to_snake 转换。
返回统一转成 camelCase dict 供前端直接使用。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.drill_record import DrillRecord


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def _to_dict(r: DrillRecord) -> dict:
    return {
        "id": r.id,
        "planId": r.plan_id,
        "planCode": r.plan_code,
        "planName": r.plan_name,
        "executedBy": r.executed_by,
        "startedAt": r.started_at,
        "completedAt": r.completed_at,
        "score": r.score,
        "result": r.result,
        "notes": r.notes,
    }


def count(db: Session, plan_id: Optional[int] = None) -> int:
    q = db.query(func.count(DrillRecord.id))
    if plan_id is not None:
        q = q.filter(DrillRecord.plan_id == plan_id)
    return q.scalar() or 0


def list_records(db: Session, plan_id: Optional[int] = None,
                 limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(DrillRecord)
    if plan_id is not None:
        q = q.filter(DrillRecord.plan_id == plan_id)
    q = q.order_by(DrillRecord.started_at.desc(), DrillRecord.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, rid: int) -> Optional[DrillRecord]:
    return db.query(DrillRecord).filter(DrillRecord.id == rid).first()


def create(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    obj = DrillRecord(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def update(db: Session, rid: int, data: dict) -> Optional[dict]:
    obj = get(db, rid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def delete(db: Session, rid: int) -> bool:
    obj = get(db, rid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
