"""演练计划 CRUD (阶段三 A)。

说明: 前端以 camelCase 提交, 模型以 snake_case 存储, 故统一用 _to_snake 转换。
返回统一转成 camelCase dict 供前端直接使用。
"""
from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.drill import DrillPlan


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def _to_dict(r: DrillPlan) -> dict:
    return {
        "id": r.id, "code": r.code, "name": r.name, "type": r.type,
        "date": r.date, "state": r.state, "result": r.result,
    }


def count(db: Session, kw: str = "", dtype: str = "") -> int:
    q = db.query(func.count(DrillPlan.id))
    if kw:
        like = f"%{kw}%"
        q = q.filter(DrillPlan.name.ilike(like) | DrillPlan.code.ilike(like))
    if dtype:
        q = q.filter(DrillPlan.type == dtype)
    return q.scalar() or 0


def list_plans(db: Session, kw: str = "", dtype: str = "",
               limit: int = 50, offset: int = 0) -> list[dict]:
    q = db.query(DrillPlan)
    if kw:
        like = f"%{kw}%"
        q = q.filter(DrillPlan.name.ilike(like) | DrillPlan.code.ilike(like))
    if dtype:
        q = q.filter(DrillPlan.type == dtype)
    q = q.order_by(DrillPlan.date.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, rid: int) -> Optional[DrillPlan]:
    return db.query(DrillPlan).filter(DrillPlan.id == rid).first()


def create(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    name = data.get("name") or "未命名演练"
    cnt = db.query(func.count(DrillPlan.id)).scalar() or 0
    if not data.get("code"):
        data["code"] = f"DR-{cnt + 1:03d}"
    obj = DrillPlan(**data)
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


def stats(db: Session) -> dict:
    total = db.query(func.count(DrillPlan.id)).scalar() or 0
    done = db.query(func.count(DrillPlan.id)).filter(DrillPlan.state == "已完成").scalar() or 0
    passed = db.query(func.count(DrillPlan.id)).filter(DrillPlan.result == "通过").scalar() or 0
    today = datetime.date.today().strftime("%Y-%m-%d")
    upcoming = (
        db.query(DrillPlan)
        .filter(DrillPlan.date >= today, DrillPlan.state != "已完成")
        .order_by(DrillPlan.date.asc())
        .first()
    )
    nxt = f"{upcoming.date} {upcoming.name}" if upcoming else "—"
    return {"year": total, "done": done, "pass": passed, "next": nxt}
