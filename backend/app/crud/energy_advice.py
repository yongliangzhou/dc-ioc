"""电量节能建议采纳 CRUD (批次C)。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.energy_advice import EnergyAdviceAdopt


def create(db: Session, *, data: dict) -> dict:
    obj = EnergyAdviceAdopt(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def list_recent(db: Session, action: Optional[str] = None, limit: int = 50) -> list[dict]:
    q = db.query(EnergyAdviceAdopt)
    if action:
        q = q.filter(EnergyAdviceAdopt.action == action)
    rows = q.order_by(EnergyAdviceAdopt.id.desc()).limit(limit).all()
    return [_to_dict(r) for r in rows]


def stats(db: Session) -> dict:
    total = db.query(EnergyAdviceAdopt).count()
    adopted = db.query(EnergyAdviceAdopt).filter(EnergyAdviceAdopt.action == "adopt").count()
    ignored = db.query(EnergyAdviceAdopt).filter(EnergyAdviceAdopt.action == "ignore").count()
    rows = db.query(EnergyAdviceAdopt).filter(EnergyAdviceAdopt.action == "adopt").all()
    saving_kw = sum(float(r.saving_kw or 0) for r in rows)
    return {"total": total, "adopted": adopted, "ignored": ignored, "adoptedSavingKw": round(saving_kw, 1)}


def _to_dict(r: EnergyAdviceAdopt) -> dict:
    return {
        "id": r.id,
        "suggestionId": r.suggestion_id or "",
        "title": r.title or "",
        "priority": r.priority or "",
        "savingKw": float(r.saving_kw or 0),
        "savingPct": float(r.saving_pct or 0),
        "detail": r.detail or "",
        "basis": r.basis or "",
        "action": r.action or "",
        "note": r.note or "",
        "pueCurrent": float(r.pue_current or 0),
        "pueTarget": float(r.pue_target or 0),
        "user": r.user or "",
        "createdAt": r.created_at or "",
    }
