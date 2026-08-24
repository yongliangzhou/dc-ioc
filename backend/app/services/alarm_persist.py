"""告警落库处理器: 作为 alarm_engine 的 notify handler, 将新告警写入 alarm_event 表。

仅在告警"非收敛" (新触发) 时由 alarm_engine.evaluate 回调, 避免重复写入。
"""
import logging
import uuid

from app.db.session import SessionLocal
from app.models.alarm import AlarmEvent

logger = logging.getLogger("alarm_persist")


def persist_alarm_event(alarm: dict) -> None:
    """alarm_engine notify handler: 将一条新告警落库。"""
    if not alarm:
        return
    db = None
    try:
        db = SessionLocal()
        evt = AlarmEvent(
            id=uuid.uuid4().hex,
            rule_id=alarm.get("rule", "") or "",
            rule_name=alarm.get("desc", "") or "",
            metric=alarm.get("metric_name", "") or "",
            sys=alarm.get("system", "") or "",
            lv=alarm.get("level", "") or "info",
            desc=alarm.get("desc", "") or "",
            value=alarm.get("value"),
            threshold=alarm.get("threshold"),
            unit=alarm.get("unit"),
            state="active",
            device_id=alarm.get("device_id"),
            category=alarm.get("category"),
            domain=alarm.get("domain"),
        )
        db.add(evt)
        db.commit()
    except Exception:
        logger.exception("告警落库失败: %s", alarm.get("rule"))
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        if db is not None:
            db.close()
