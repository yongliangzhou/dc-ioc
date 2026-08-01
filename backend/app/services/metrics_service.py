"""运营 SLA / 统计服务。

聚合工单与告警的运营指标:
- 工单: 响应时长 (创建 -> 首次进入 doing)、解决时长 (创建 -> done)、SLA 按时率
- 告警: 收敛率 (已确认/已解决 / 总数)、平均确认时长 (MTTA)、平均解决时长 (MTTR)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.alarm import list_alarms as _list_alarms
from app.crud.ticket import list_tickets as _list_tickets
from app.models.alarm import AlarmEvent

logger = logging.getLogger("metrics_service")

_SLA_RE = re.compile(r"(\d+)\s*([hHdDmM])")


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    # 兼容 "YYYY-MM-DD HH:MM:SS"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except (ValueError, TypeError):
            continue
    return None


def _sla_to_minutes(sla: Optional[str]) -> Optional[int]:
    """将 '1h' / '4h' / '8h' / '1d' 解析为分钟, 无法解析返回 None。"""
    if not sla:
        return None
    m = _SLA_RE.search(str(sla))
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    return n * (1 if unit == "m" else 60 if unit == "h" else 1440)


def _first_log_ts(logs: list[dict], to_state: str) -> Optional[datetime]:
    """取日志中首次进入某状态的时刻。"""
    best: Optional[datetime] = None
    for lg in logs or []:
        if lg.get("to") == to_state:
            ts = _parse_dt(lg.get("ts"))
            if ts and (best is None or ts < best):
                best = ts
    return best


def compute_ticket_sla(db: Session) -> dict:
    """工单 SLA 指标。"""
    tickets, _total = _list_tickets(db)
    total = len(tickets)
    open_ = doing = pending = done = 0
    resp_mins: list[float] = []
    res_mins: list[float] = []
    breach = 0
    done_total = 0

    for t in tickets:
        state = getattr(t, "state", "open") or "open"
        if state == "open":
            open_ += 1
        elif state == "doing":
            doing += 1
        elif state == "pending":
            pending += 1
        elif state == "done":
            done_total += 1
            done += 1

        created = _parse_dt(getattr(t, "created", None))
        logs = getattr(t, "logs", None) or []
        target = _sla_to_minutes(getattr(t, "sla", None))

        resp_ts = _first_log_ts(logs, "doing")
        if created and resp_ts:
            resp_mins.append((resp_ts - created).total_seconds() / 60.0)

        res_ts = _first_log_ts(logs, "done")
        if created and res_ts:
            mins = (res_ts - created).total_seconds() / 60.0
            res_mins.append(mins)
            if target is not None and mins > target:
                breach += 1

    def _avg(xs: list[float]) -> Optional[float]:
        return round(sum(xs) / len(xs), 1) if xs else None

    on_time_rate = None
    if done_total:
        on_time_rate = round((done_total - breach) / done_total * 100, 1)

    return {
        "total": total,
        "open": open_,
        "doing": doing,
        "pending": pending,
        "done": done,
        "avgResponseMin": _avg(resp_mins),
        "avgResolveMin": _avg(res_mins),
        "slaTargetMin": _sla_to_minutes("4h"),  # 默认 SLA 基线
        "breach": breach,
        "onTimeRate": on_time_rate,
    }


def compute_alarm_sla(db: Session) -> dict:
    """告警 SLA 指标 (基于 alarm_event 表)。"""
    total = db.query(func.count(AlarmEvent.id)).scalar() or 0
    active = db.query(func.count(AlarmEvent.id)).filter(AlarmEvent.state == "active").scalar() or 0
    acked = db.query(func.count(AlarmEvent.id)).filter(AlarmEvent.state == "acked").scalar() or 0
    resolved = db.query(func.count(AlarmEvent.id)).filter(AlarmEvent.state == "resolved").scalar() or 0

    handled = acked + resolved
    convergence_rate = round(handled / total * 100, 1) if total else None

    mtta_vals: list[float] = []
    mttr_vals: list[float] = []
    for ev in db.query(
        AlarmEvent.triggered_at, AlarmEvent.acknowledged_at, AlarmEvent.resolved_at
    ).all():
        trig = _parse_dt(ev.triggered_at)
        if trig and ev.acknowledged_at:
            ack = _parse_dt(ev.acknowledged_at)
            if ack:
                mtta_vals.append((ack - trig).total_seconds() / 60.0)
        if trig and ev.resolved_at:
            res = _parse_dt(ev.resolved_at)
            if res:
                mttr_vals.append((res - trig).total_seconds() / 60.0)

    def _avg(xs: list[float]) -> Optional[float]:
        return round(sum(xs) / len(xs), 1) if xs else None

    return {
        "total": total,
        "active": active,
        "acked": acked,
        "resolved": resolved,
        "convergenceRate": convergence_rate,
        "mttaMin": _avg(mtta_vals),
        "mttrMin": _avg(mttr_vals),
    }


def get_sla_metrics(db: Session) -> dict:
    """汇总运营 SLA 指标。"""
    return {
        "tickets": compute_ticket_sla(db),
        "alarms": compute_alarm_sla(db),
        "generatedAt": datetime.now().isoformat(),
    }
