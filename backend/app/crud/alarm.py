"""告警事件 CRUD + 统计 (对齐前端 /api/alarm-history 契约)。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alarm import AlarmEvent

logger = logging.getLogger(__name__)


def _parse_ts(ts: Optional[str]):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception as e:
        logger.debug("时间戳参数解析失败, 已忽略该过滤条件: %s", e)
        return None


def list_alarms(
    db: Session,
    *,
    sys: Optional[str] = None,
    lv: Optional[str] = None,
    state: Optional[str] = None,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    q = db.query(AlarmEvent)
    if sys:
        q = q.filter(AlarmEvent.sys == sys)
    if lv:
        q = q.filter(AlarmEvent.lv == lv)
    if state:
        q = q.filter(AlarmEvent.state == state)
    f_ts = _parse_ts(from_)
    if f_ts:
        q = q.filter(AlarmEvent.triggered_at >= f_ts)
    t_ts = _parse_ts(to)
    if t_ts:
        q = q.filter(AlarmEvent.triggered_at <= t_ts)
    total = q.count()
    items = (
        q.order_by(AlarmEvent.triggered_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def get_alarm(db: Session, alarm_id: str) -> Optional[AlarmEvent]:
    return db.query(AlarmEvent).filter(AlarmEvent.id == alarm_id).first()


def ack_alarm(db: Session, alarm_id: str, by: str, note: Optional[str] = None) -> Optional[AlarmEvent]:
    a = get_alarm(db, alarm_id)
    if not a or a.state not in ("active", "suppressed"):
        return a
    a.state = "acknowledged"
    a.acknowledged_at = datetime.utcnow()
    a.acknowledged_by = by
    if note:
        a.note = (a.note or "") + f"[ack] {note}\n"
    db.commit()
    db.refresh(a)
    return a


def resolve_alarm(
    db: Session, alarm_id: str, by: str, note: Optional[str] = None, auto: bool = False
) -> Optional[AlarmEvent]:
    a = get_alarm(db, alarm_id)
    if not a or a.state == "resolved":
        return a
    a.state = "resolved"
    a.resolved_at = datetime.utcnow()
    a.resolved_by = by
    a.auto_resolved = auto
    if note:
        a.note = (a.note or "") + f"[resolve] {note}\n"
    db.commit()
    db.refresh(a)
    return a


def alarm_stats(db: Session) -> dict:
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    total24h = db.query(AlarmEvent).filter(AlarmEvent.triggered_at >= since).count()
    active24h = db.query(AlarmEvent).filter(
        AlarmEvent.triggered_at >= since, AlarmEvent.state.in_(["active", "suppressed"])
    ).count()
    resolved24h = db.query(AlarmEvent).filter(
        AlarmEvent.triggered_at >= since, AlarmEvent.state == "resolved"
    ).count()

    acked = (
        db.query(AlarmEvent)
        .filter(AlarmEvent.acknowledged_at.isnot(None), AlarmEvent.acknowledged_at >= since)
        .all()
    )
    mtta = 0
    if acked:
        diffs = [
            (a.acknowledged_at - a.triggered_at).total_seconds() / 60.0
            for a in acked
            if a.acknowledged_at and a.triggered_at
        ]
        if diffs:
            mtta = round(sum(diffs) / len(diffs))

    resolved = (
        db.query(AlarmEvent)
        .filter(AlarmEvent.resolved_at.isnot(None), AlarmEvent.resolved_at >= since)
        .all()
    )
    mttr = 0
    if resolved:
        diffs = [
            (r.resolved_at - r.triggered_at).total_seconds() / 60.0
            for r in resolved
            if r.resolved_at and r.triggered_at
        ]
        if diffs:
            mttr = round(sum(diffs) / len(diffs))

    by_sys_rows = (
        db.query(AlarmEvent.sys, func.count(AlarmEvent.id))
        .filter(AlarmEvent.triggered_at >= since)
        .group_by(AlarmEvent.sys)
        .all()
    )
    by_system = {s: c for s, c in by_sys_rows}

    by_lv_rows = (
        db.query(AlarmEvent.lv, func.count(AlarmEvent.id))
        .filter(AlarmEvent.triggered_at >= since)
        .group_by(AlarmEvent.lv)
        .all()
    )
    by_level = {"crit": 0, "warn": 0, "info": 0}
    for lv, c in by_lv_rows:
        if lv in by_level:
            by_level[lv] = c

    return {
        "total24h": total24h,
        "active24h": active24h,
        "resolved24h": resolved24h,
        "mttaMin": mtta,
        "mttrMin": mttr,
        "bySystem": by_system,
        "byLevel": by_level,
    }
