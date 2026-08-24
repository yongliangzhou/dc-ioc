"""物模型 CRUD (phase: thing-model)。

- list: 按 model_key/name/category/domain 模糊过滤
- get: 含嵌套 items
- create: 事务内批量写入 items (cascade 由 FK ondelete 保证一致)
- update: 全量替换 items (先删后插, 简单且幂等)
- delete: 级联删除 items
返回 camelCase dict 供前端直接使用。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.thing_model import ThingModel, ThingModelItem


def _item_to_dict(it: ThingModelItem) -> dict:
    return {
        "id": it.id,
        "thingModelId": it.thing_model_id,
        "itemType": it.item_type,
        "identifier": it.identifier,
        "name": it.name,
        "dataType": it.data_type,
        "unit": it.unit,
        "desc": it.desc,
        "extra": it.extra or {},
    }


def _to_dict(m: ThingModel) -> dict:
    items = (
        m.items
        if getattr(m, "items", None) is not None
        else []  # 未 eagerload 时为空, 调用方按需 query
    )
    return {
        "id": m.id,
        "modelKey": m.model_key,
        "name": m.name,
        "category": m.category,
        "domain": m.domain,
        "protocol": m.protocol,
        "vendor": m.vendor,
        "description": m.description,
        "items": [_item_to_dict(i) for i in items],
        "createdAt": m.created_at,
        "updatedAt": m.updated_at,
    }


def count(db: Session, kw: str = "", category: str = "", domain: str = "") -> int:
    q = db.query(func.count(ThingModel.id))
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            ThingModel.model_key.ilike(like)
            | ThingModel.name.ilike(like)
        )
    if category:
        q = q.filter(ThingModel.category == category)
    if domain:
        q = q.filter(ThingModel.domain == domain)
    return q.scalar() or 0


def list_models(
    db: Session, kw: str = "", category: str = "", domain: str = "",
    limit: int = 100, offset: int = 0,
) -> list[dict]:
    q = db.query(ThingModel)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            ThingModel.model_key.ilike(like) | ThingModel.name.ilike(like)
        )
    if category:
        q = q.filter(ThingModel.category == category)
    if domain:
        q = q.filter(ThingModel.domain == domain)
    q = q.order_by(ThingModel.model_key.asc())
    rows = q.offset(offset).limit(limit).all()
    # 显式加载 items 保证返回完整
    result: list[dict] = []
    for m in rows:
        items = (
            db.query(ThingModelItem)
            .filter(ThingModelItem.thing_model_id == m.id)
            .order_by(ThingModelItem.id.asc())
            .all()
        )
        m.items = items  # type: ignore[attr-defined]
        result.append(_to_dict(m))
    return result


def get(db: Session, mid: int) -> Optional[dict]:
    m = db.query(ThingModel).filter(ThingModel.id == mid).first()
    if not m:
        return None
    items = (
        db.query(ThingModelItem)
        .filter(ThingModelItem.thing_model_id == m.id)
        .order_by(ThingModelItem.id.asc())
        .all()
    )
    m.items = items  # type: ignore[attr-defined]
    return _to_dict(m)


def get_by_key(db: Session, model_key: str) -> Optional[dict]:
    m = db.query(ThingModel).filter(ThingModel.model_key == model_key).first()
    if not m:
        return None
    items = (
        db.query(ThingModelItem)
        .filter(ThingModelItem.thing_model_id == m.id)
        .order_by(ThingModelItem.id.asc())
        .all()
    )
    m.items = items  # type: ignore[attr-defined]
    return _to_dict(m)


def create(db: Session, data: dict) -> dict:
    """data 来自 ThingModelCreate.model_dump(); items 为子项列表。"""
    items_in = data.pop("items", []) or []
    m = ThingModel(**data)
    db.add(m)
    db.flush()  # 拿到 m.id 供子项 FK
    for it in items_in:
        db.add(ThingModelItem(thing_model_id=m.id, **it))
    db.commit()
    db.refresh(m)
    return get(db, m.id)  # type: ignore[return-value]


def update(db: Session, mid: int, data: dict) -> Optional[dict]:
    m = db.query(ThingModel).filter(ThingModel.id == mid).first()
    if not m:
        return None
    # 若含 items 全量替换 (先删后插)
    items_in = data.pop("items", None)
    for k, v in data.items():
        if v is not None and hasattr(m, k):
            setattr(m, k, v)
    if items_in is not None:
        db.query(ThingModelItem).filter(
            ThingModelItem.thing_model_id == m.id
        ).delete()
        for it in items_in:
            db.add(ThingModelItem(thing_model_id=m.id, **it))
    db.commit()
    db.refresh(m)
    return get(db, m.id)  # type: ignore[return-value]


def delete(db: Session, mid: int) -> bool:
    m = db.query(ThingModel).filter(ThingModel.id == mid).first()
    if not m:
        return False
    db.query(ThingModelItem).filter(
        ThingModelItem.thing_model_id == m.id
    ).delete()
    db.delete(m)
    db.commit()
    return True
