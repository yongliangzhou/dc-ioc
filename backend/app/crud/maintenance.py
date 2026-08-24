"""(维保记录 CRUD (阶段三 A · 运维作业-维保管理)。

维保计划当前由聚合器动态生成, 这里仅持久化"维保记录" (实际执行情况),
关联计划编号 (plan_code) 而非外键, 以兼容动态计划。
前端以 camelCase 提交, 模型以 snake_case 存储, 故统一用 _to_snake 转换。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import maintenance as maintenance_mod


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def _to_dict(r) -> dict:
    return {
        "id": r.id,
        "planCode": r.plan_code,
        "planName": r.plan_name,
        "equipmentCode": r.equipment_code,
        "maintainedBy": getattr(r, "maintained_by", ""),
        "startedAt": r.started_at,
        "completedAt": r.completed_at,
        "status": r.status,
        "result": r.result,
        "actionDescription": r.action_description,
        "notes": r.notes,
    }


# ===== 维保计划 CRUD (批次补强) =====
def _to_plan_dict(r) -> dict:
    return {
        "id": r.id,
        "code": r.code or "",
        "name": r.name or "",
        "equipmentCode": r.equipment_code or "",
        "description": r.description or "",
        "frequency": r.frequency or "monthly",
        "nextDueDate": r.next_due_date or "",
        "status": r.status or "active",
        "owner": r.owner or "",
        "createdAt": r.created_at or "",
    }


def count_plans(db: Session, status: str = "") -> int:
    q = db.query(func.count(maintenance_mod.MaintenancePlan.id))
    if status:
        q = q.filter(maintenance_mod.MaintenancePlan.status == status)
    return q.scalar() or 0


def list_plans(db: Session, status: str = "",
               limit: int = 200, offset: int = 0) -> list[dict]:
    q = db.query(maintenance_mod.MaintenancePlan)
    if status:
        q = q.filter(maintenance_mod.MaintenancePlan.status == status)
    q = q.order_by(maintenance_mod.MaintenancePlan.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_plan_dict(r) for r in rows]


def get_plan(db: Session, pid: int):
    return db.query(maintenance_mod.MaintenancePlan).filter(
        maintenance_mod.MaintenancePlan.id == pid).first()


def create_plan(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    obj = maintenance_mod.MaintenancePlan(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_plan_dict(obj)


def update_plan(db: Session, pid: int, data: dict) -> Optional[dict]:
    obj = get_plan(db, pid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _to_plan_dict(obj)


def delete_plan(db: Session, pid: int) -> bool:
    obj = get_plan(db, pid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ===== 维保记录 CRUD =====
def count(db: Session, plan_code: str = "") -> int:
    q = db.query(func.count(maintenance_mod.MaintenanceRecord.id))
    if plan_code:
        q = q.filter(maintenance_mod.MaintenanceRecord.plan_code == plan_code)
    return q.scalar() or 0


def list_records(db: Session, plan_code: str = "",
                 limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(maintenance_mod.MaintenanceRecord)
    if plan_code:
        q = q.filter(maintenance_mod.MaintenanceRecord.plan_code == plan_code)
    q = q.order_by(maintenance_mod.MaintenanceRecord.completed_at.desc(),
                   maintenance_mod.MaintenanceRecord.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, rid: int):
    return db.query(maintenance_mod.MaintenanceRecord).filter(
        maintenance_mod.MaintenanceRecord.id == rid).first()


def create(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    obj = maintenance_mod.MaintenanceRecord(**data)
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
