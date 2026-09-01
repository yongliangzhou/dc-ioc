"""巡检 CRUD (阶段三 A): 路线 / 发现 / 机器人配置。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.inspection import InspectionRoute, InspectionFinding, InspectionRobot


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


# ---------- 路线 ----------
def _route_dict(r: InspectionRoute) -> dict:
    return {
        "id": r.id, "code": r.code, "name": r.name or "", "description": r.description or "",
        "freq": r.freq, "frequency": r.freq, "items": r.items,
        "last": r.last, "next": r.next, "state": r.state, "status": r.state,
    }


def route_count(db: Session) -> int:
    return db.query(func.count(InspectionRoute.id)).scalar() or 0


def list_routes(db: Session, limit: int = 100) -> list[dict]:
    rows = db.query(InspectionRoute).order_by(InspectionRoute.id.asc()).limit(limit).all()
    return [_route_dict(r) for r in rows]


def get_route(db: Session, rid: int) -> Optional[InspectionRoute]:
    return db.query(InspectionRoute).filter(InspectionRoute.id == rid).first()


def create_route(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    cnt = db.query(func.count(InspectionRoute.id)).scalar() or 0
    if not data.get("code"):
        data["code"] = f"RT-{cnt + 1:03d}"
    obj = InspectionRoute(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _route_dict(obj)


def update_route(db: Session, rid: int, data: dict) -> Optional[dict]:
    obj = get_route(db, rid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _route_dict(obj)


def delete_route(db: Session, rid: int) -> bool:
    obj = get_route(db, rid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ---------- 发现 ----------
def _finding_dict(f: InspectionFinding) -> dict:
    return {
        "id": f.id, "route": f.route, "item": f.item,
        "ts": f.ts, "lv": f.lv, "action": f.action,
    }


def finding_count(db: Session) -> int:
    return db.query(func.count(InspectionFinding.id)).scalar() or 0


def list_findings(db: Session, limit: int = 100) -> list[dict]:
    rows = db.query(InspectionFinding).order_by(InspectionFinding.id.desc()).limit(limit).all()
    return [_finding_dict(f) for f in rows]


def get_finding(db: Session, fid: int) -> Optional[InspectionFinding]:
    return db.query(InspectionFinding).filter(InspectionFinding.id == fid).first()


def create_finding(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    obj = InspectionFinding(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _finding_dict(obj)


def update_finding(db: Session, fid: int, data: dict) -> Optional[dict]:
    obj = get_finding(db, fid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _finding_dict(obj)


def delete_finding(db: Session, fid: int) -> bool:
    obj = get_finding(db, fid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ---------- 机器人配置 ----------
def robot_row(db: Session) -> InspectionRobot:
    row = db.query(InspectionRobot).first()
    if row is None:
        row = InspectionRobot()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def robot_state(db: Session) -> dict:
    row = robot_row(db)
    findings = finding_count(db)
    return {
        "units": row.units, "running": row.running,
        "coverage": row.coverage, "findings": findings,
    }


def aggregate(db: Session) -> dict:
    routes = list_routes(db)
    findings = list_findings(db)
    plan = len(routes)
    active = sum(1 for r in routes if r.get("state") == "active")
    abnormal = len(findings)
    rate = round(active / plan * 100) if plan else 0
    return {
        "today": {"plan": plan, "done": active, "active": active, "abnormal": abnormal, "rate": rate},
        "robot": robot_state(db),
        "routes": routes,
        "findings": findings,
    }
