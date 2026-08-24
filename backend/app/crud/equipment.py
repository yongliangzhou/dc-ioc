"""设备台账 CRUD (数据访问层, 供真实数据库使用)。

注: 前端独立开发阶段 API 由 services.dc_ioc_data 提供 Mock 数据; 本模块为
数据库落地后的真实查询实现, 接口签名保持一致, 便于后续平滑切换。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.equipment import Equipment


def list_equipment(
    db: Session,
    *,
    domain: Optional[str] = None,
    category: Optional[str] = None,
    room_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Equipment]:
    q = db.query(Equipment)
    if domain:
        q = q.filter(Equipment.domain == domain)
    if category:
        q = q.filter(Equipment.category == category)
    if status:
        q = q.filter(Equipment.status == status)
    if room_code:
        from app.models.room import Room

        q = q.join(Room, Room.id == Equipment.room_id).filter(Room.code == room_code)
    return q.order_by(Equipment.id).offset(skip).limit(limit).all()


def get_equipment(db: Session, equipment_id: int) -> Equipment | None:
    return db.query(Equipment).filter(Equipment.id == equipment_id).first()


def count_equipment(db: Session, domain: Optional[str] = None) -> int:
    q = db.query(Equipment)
    if domain:
        q = q.filter(Equipment.domain == domain)
    return q.count()
