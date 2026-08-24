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


def analyze_from_data(db: Session) -> dict:
    """基于活跃告警 + 设备测点自动分析生成风险提示 (草稿, 不自动入库)。

    返回建议新增的风险项列表, 由前端/审核人确认后调用 create 入库。
    """
    from app.services import dc_aggregator as agg

    suggestions: list[dict] = []
    try:
        alarms = agg.alarms().get("active", []) if hasattr(agg, "alarms") else []
    except Exception:  # noqa: BLE001 - 聚合器异常不应阻断分析
        alarms = []

    seen: set[str] = set()
    for a in alarms:
        metric = (a.get("metric") or a.get("sys") or "设备") if isinstance(a, dict) else ""
        key = f"{metric}"
        if not key or key in seen:
            continue
        seen.add(key)
        level_map = {"critical": ("高", 4, 4), "high": ("高", 4, 3),
                     "warning": ("中", 3, 2), "info": ("低", 2, 1)}
        lvl = a.get("level") if isinstance(a, dict) else None
        cat, prob, impact = level_map.get(lvl, ("中", 3, 2))
        suggestions.append({
            "risk": f"{metric} 持续异常, 存在运行风险",
            "cat": "自动分析",
            "prob": prob,
            "impact": impact,
            "level": cat,
            "ctrl": "建议核查相关设备并制定管控措施",
            "owner": "",
            "closed": 0,
            "source": "alarm",
            "sourceRef": a.get("id") if isinstance(a, dict) else None,
        })

    # 若聚合器无活跃告警, 给出一条基于 PUE 偏高的通用提示
    if not suggestions:
        suggestions.append({
            "risk": "当前 PUE 偏高, 存在能效不达标风险",
            "cat": "自动分析",
            "prob": 2, "impact": 2, "level": "中",
            "ctrl": "建议优化冷源运行策略", "owner": "", "closed": 0,
            "source": "energy", "sourceRef": None,
        })
    return {"suggestions": suggestions, "count": len(suggestions)}
