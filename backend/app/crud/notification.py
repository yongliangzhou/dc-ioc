"""统一告警触达中心 CRUD (通道配置 + 发送记录)。"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select

from app.models.notification import NotificationChannel, NotificationRecord

_LEVEL_RANK = {"info": 0, "warn": 1, "crit": 2}


def level_rank(level: str) -> int:
    return _LEVEL_RANK.get((level or "").lower(), 0)


def level_at_least(level: str, min_level: str) -> bool:
    """级别路由判定: level ≥ min_level 才投递。"""
    return level_rank(level) >= level_rank(min_level)


# ------------------------------------------------------------------ #
# 通道配置
# ------------------------------------------------------------------ #
def list_channels(db, enabled_only: bool = False) -> list[dict]:
    stmt = select(NotificationChannel).order_by(NotificationChannel.id.asc())
    if enabled_only:
        stmt = stmt.where(NotificationChannel.enabled.is_(True))
    return [c.to_dict() for c in db.scalars(stmt).all()]


def get_channel(db, cid: int) -> Optional[dict]:
    obj = db.get(NotificationChannel, cid)
    return obj.to_dict() if obj else None


def create_channel(db, data: dict, user: str = "system") -> dict:
    obj = NotificationChannel(
        type=data.get("type") or "custom",
        name=data.get("name") or "未命名通道",
        url=data.get("url") or "",
        min_level=data.get("minLevel") or "crit",
        quiet_start=data.get("quietStart"),
        quiet_end=data.get("quietEnd"),
        enabled=bool(data.get("enabled", True)),
        updated_by=user,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def update_channel(db, cid: int, data: dict, user: str = "system") -> Optional[dict]:
    obj = db.get(NotificationChannel, cid)
    if obj is None:
        return None
    alias = {"minLevel": "min_level", "quietStart": "quiet_start", "quietEnd": "quiet_end"}
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


def delete_channel(db, cid: int) -> bool:
    obj = db.get(NotificationChannel, cid)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True


# ------------------------------------------------------------------ #
# 发送记录
# ------------------------------------------------------------------ #
def create_record(db, data: dict) -> dict:
    obj = NotificationRecord(
        alarm_id=data.get("alarm_id"),
        channel_id=data.get("channel_id"),
        channel_name=data.get("channel_name") or "",
        level=data.get("level") or "info",
        title=(data.get("title") or "")[:255],
        status=data.get("status") or "sent",
        error=data.get("error"),
        retry_count=data.get("retry_count") or 0,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def is_duplicated(db, alarm_id: Optional[str], channel_id: int, within_minutes: int = 10) -> bool:
    """同告警 + 同通道在时间窗内已成功投递过 → 去重。

    只对带 alarm_id 的告警生效 (测试发送/手工消息不去重)。
    """
    if not alarm_id:
        return False
    since = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    stmt = (
        select(func.count())
        .select_from(NotificationRecord)
        .where(
            NotificationRecord.alarm_id == alarm_id,
            NotificationRecord.channel_id == channel_id,
            NotificationRecord.status == "sent",
            NotificationRecord.created_at >= since,
        )
    )
    return (db.scalar(stmt) or 0) > 0


def list_records(
    db,
    page: int = 1,
    page_size: int = 50,
    level: Optional[str] = None,
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
):
    stmt = select(NotificationRecord)
    if level:
        stmt = stmt.where(NotificationRecord.level == level)
    if channel_id:
        stmt = stmt.where(NotificationRecord.channel_id == channel_id)
    if status:
        stmt = stmt.where(NotificationRecord.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(NotificationRecord.created_at.desc(), NotificationRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }
