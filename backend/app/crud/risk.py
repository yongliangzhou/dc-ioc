"""风险项 CRUD (阶段三 A)。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.risk import RiskItem


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def _level(prob: int, impact: int) -> str:
    score = (prob or 1) * (impact or 1)
    if score >= 12:
        return "高"
    if score >= 6:
        return "中"
    return "低"


def _to_dict(r: RiskItem) -> dict:
    return {
        "id": r.id, "code": r.code, "risk": r.risk, "cat": r.cat,
        "prob": r.prob, "impact": r.impact, "level": r.level,
        "ctrl": r.ctrl, "owner": r.owner, "closed": r.closed,
    }


def count(db: Session, kw: str = "", cat: str = "") -> int:
    q = db.query(func.count(RiskItem.id))
    if kw:
        like = f"%{kw}%"
        q = q.filter(RiskItem.risk.ilike(like) | RiskItem.code.ilike(like))
    if cat:
        q = q.filter(RiskItem.cat == cat)
    return q.scalar() or 0


def list_items(db: Session, kw: str = "", cat: str = "",
               limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(RiskItem)
    if kw:
        like = f"%{kw}%"
        q = q.filter(RiskItem.risk.ilike(like) | RiskItem.code.ilike(like))
    if cat:
        q = q.filter(RiskItem.cat == cat)
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, rid: int) -> Optional[RiskItem]:
    return db.query(RiskItem).filter(RiskItem.id == rid).first()


def create(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    cnt = db.query(func.count(RiskItem.id)).scalar() or 0
    if not data.get("code"):
        data["code"] = f"R-{cnt + 1:03d}"
    data["level"] = _level(data.get("prob", 2), data.get("impact", 2))
    obj = RiskItem(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def update(db: Session, rid: int, data: dict) -> Optional[dict]:
    obj = get(db, rid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    # 概率/影响变化时重算等级
    if "prob" in data or "impact" in data:
        prob = data.get("prob", obj.prob)
        impact = data.get("impact", obj.impact)
        data["level"] = _level(prob, impact)
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
    high = db.query(func.count(RiskItem.id)).filter(RiskItem.level == "高").scalar() or 0
    mid = db.query(func.count(RiskItem.id)).filter(RiskItem.level == "中").scalar() or 0
    low = db.query(func.count(RiskItem.id)).filter(RiskItem.level == "低").scalar() or 0
    closed = db.query(func.count(RiskItem.id)).filter(RiskItem.closed == 1).scalar() or 0
    return {"high": high, "mid": mid, "low": low, "closed": closed}
