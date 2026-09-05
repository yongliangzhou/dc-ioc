"""统一图形编辑入口 CRUD (图形场景配置 + 加油记录)。"""
from typing import Optional

from sqlalchemy import select


# ------------------------------------------------------------------ #
# 图形场景配置 (graphic_config)
# ------------------------------------------------------------------ #
def get_config(db, kind: str):
    """读取某图形的场景覆盖层, 不存在时返回空场景 (前端据此回退到页面默认渲染)。"""
    from app.models.graphic_config import GraphicConfig

    obj = db.get(GraphicConfig, kind)
    if obj is None:
        return None
    return obj.to_dict()


def save_config(db, kind: str, title: Optional[str], payload: dict, user: str = "system"):
    """写入/更新某图形的场景覆盖层 (按 kind 幂等 upsert)。"""
    from app.models.graphic_config import GraphicConfig

    obj = db.get(GraphicConfig, kind)
    if obj is None:
        obj = GraphicConfig(kind=kind, title=title or "", payload=payload, updated_by=user)
        db.add(obj)
    else:
        if title is not None:
            obj.title = title
        obj.payload = payload
        obj.updated_by = user
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def delete_config(db, kind: str) -> bool:
    """删除某图形的场景覆盖层, 页面回到默认渲染。"""
    from app.models.graphic_config import GraphicConfig

    obj = db.get(GraphicConfig, kind)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True


def list_configs(db):
    from app.models.graphic_config import GraphicConfig

    rows = db.scalars(select(GraphicConfig).order_by(GraphicConfig.updated_at.desc())).all()
    return [r.to_dict() for r in rows]


# ------------------------------------------------------------------ #
# 加油记录 (refuel_record)
# ------------------------------------------------------------------ #
def list_refuels(db, limit: int = 200):
    from app.models.refuel_record import RefuelRecord

    stmt = select(RefuelRecord).order_by(RefuelRecord.date.desc(), RefuelRecord.id.desc())
    rows = db.scalars(stmt.limit(limit)).all()
    return [r.to_dict() for r in rows]


def get_refuel_by_no(db, no: str):
    """按记录编号查重 (no 是业务唯一键)。"""
    from app.models.refuel_record import RefuelRecord

    return db.scalar(select(RefuelRecord).where(RefuelRecord.no == no))


def create_refuel(db, data: dict, user: str = "system"):
    from app.models.refuel_record import RefuelRecord

    obj = RefuelRecord(
        no=data.get("no"),
        date=data.get("date"),
        tank=data.get("tank") or "",
        amount=data.get("amount") or 0,
        before_pct=data.get("before"),
        after_pct=data.get("after"),
        vendor=data.get("vendor") or "",
        grade=data.get("grade") or "",
        qc=data.get("qc") or "",
        operator=data.get("operator") or "",
        status=data.get("status") or "已完成",
        note=data.get("note") or "",
        created_by=user,
        updated_by=user,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def update_refuel(db, rid: int, data: dict, user: str = "system"):
    from app.models.refuel_record import RefuelRecord

    obj = db.get(RefuelRecord, rid)
    if obj is None:
        return None
    # 驼峰 (前端) → 下划线 (列) 的字段名映射
    alias = {"before": "before_pct", "after": "after_pct"}
    for k, v in data.items():
        if v is None:
            continue
        col = alias.get(k, k)
        if hasattr(obj, col):
            setattr(obj, col, v)
    obj.updated_by = user
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def delete_refuel(db, rid: int) -> bool:
    from app.models.refuel_record import RefuelRecord

    obj = db.get(RefuelRecord, rid)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
