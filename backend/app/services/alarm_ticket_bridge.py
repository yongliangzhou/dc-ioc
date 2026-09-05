"""告警 → 工单自动桥。

订阅 alarm_engine 的 notify_handler 机制: 级别达阈值 (默认 crit) 的告警
自动创建工单 (Ticket.source="auto-alarm", source_alarm_id=告警ID)。

- 幂等: 同一 alarm_id 已存在未关单工单时跳过 (重启/重放安全)。
- 双向联动: 工单进入终态 (done/resolved/closed) 时由 tickets 端点回写
  resolve_alarm (既有 [B1] 逻辑, 见 endpoints/tickets.py transition_ticket)。
- 升级覆盖: warn 持续超阈值升级为 crit 会再次 _notify, 由同一 handler 补建单。
- 配置开关: ALARM_AUTO_TICKET_ENABLED / ALARM_AUTO_TICKET_MIN_LEVEL。

与 endpoints/tickets.py 的 /from-alarm 一键转单保持同一套系统映射与 SLA 规则。
"""
import logging

from app.core.config import settings

logger = logging.getLogger("alarm.ticket")

_LEVEL_RANK = {"info": 0, "warn": 1, "crit": 2}

# 与 endpoints/tickets.py create_from_alarm 的 sys 映射保持一致
_SYS_MAP = {
    "chiller": "暖通空调", "crac": "暖通空调", "acunit": "暖通空调",
    "liquid": "液冷系统", "ups": "供配电", "pdudevice": "供配电",
    "hv": "供配电", "lv": "供配电", "genset": "供配电",
    "battery": "储能系统", "fuel": "燃油系统", "WaterSystem": "给排水",
}
_SLA_BY_LEVEL = {"crit": "1h", "warn": "4h", "info": "8h"}
_TICKET_CLOSED_STATES = ("done", "resolved", "closed")


def _rank(level: str) -> int:
    return _LEVEL_RANK.get((level or "").lower(), 0)


def auto_ticket_handler(alarm: dict) -> None:
    """notify_handler 入口: 达阈值告警自动建单 (幂等)。"""
    if not settings.ALARM_AUTO_TICKET_ENABLED:
        return
    level = (alarm.get("level") or "info").lower()
    min_level = (settings.ALARM_AUTO_TICKET_MIN_LEVEL or "crit").lower()
    if _rank(level) < _rank(min_level):
        return
    alarm_id = alarm.get("alarm_id") or ""
    if not alarm_id:
        return

    from app.crud import ticket as ticket_crud
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        # 幂等: 该告警已有未关单工单则跳过 (升级重放 / 引擎重启重放安全)
        if ticket_crud.find_open_by_alarm(db, alarm_id) is not None:
            return
        device = alarm.get("device_id", "?")
        metric = alarm.get("metric_name", "?")
        cat = alarm.get("category", "")
        t = ticket_crud.create_ticket(
            db,
            title=f"[自动工单] {device} {metric} 越限（{alarm.get('value')}{alarm.get('unit', '')}）",
            sys=_SYS_MAP.get(cat, cat or "未知系统"),
            lv=level,
            owner="待分配",
            sla=_SLA_BY_LEVEL.get(level, "8h"),
            description=(
                f"来源: 告警自动建单 (级别 ≥ {min_level})\n"
                f"告警ID: {alarm_id}\n"
                f"设备: {device}\n"
                f"测点: {metric} = {alarm.get('value')}{alarm.get('unit', '')}\n"
                f"规则: {alarm.get('rule_id', '-')}"
            ),
            source="auto-alarm",
            source_alarm_id=alarm_id,
            operator="alarm-bridge",
        )
        logger.info("告警 %s 已自动建单 %s (level=%s)", alarm_id, t.id, level)
        # 自动建单即视为已关联确认 (与 /from-alarm 行为一致)
        try:
            from app.services import alarm_engine

            alarm_engine.ack_alarm(alarm_id)
        except Exception as e:  # noqa: BLE001
            logger.debug("自动建单关联告警确认失败: %s", e)
    except Exception as e:  # noqa: BLE001  # 建单失败不影响告警主链路
        logger.warning("告警自动建单失败 (%s): %s", alarm_id, e)
    finally:
        db.close()


def register_alarm_ticket_bridge() -> None:
    """由 lifespan 调用, 注册 'auto-ticket' handler (仅一次语义由调用方保证)。"""
    from app.services import alarm_engine

    alarm_engine.register_notify_handler("auto-ticket", auto_ticket_handler)
    logger.info(
        "告警自动建单桥已注册 (enabled=%s, min_level=%s)",
        settings.ALARM_AUTO_TICKET_ENABLED,
        settings.ALARM_AUTO_TICKET_MIN_LEVEL,
    )
