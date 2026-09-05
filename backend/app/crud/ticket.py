"""运维工单 CRUD + 统计 (对齐前端 /api/ops/tickets 契约)。

5.5.2 业务规则引擎:
  - 工单状态机: 只允许合法状态流转, 非法跳转显式拒绝 (避免 done -> open 等回退)。
  - SLA 计算: 由 created + sla 时限推导 due_at, 并判定是否超时。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ticket import Ticket

_SLA_BY_LV = {"crit": "1h", "warn": "4h", "info": "8h"}

# 合法状态流转 (状态机)。key=当前态, value=允许到达的下一态集合。
# 任意态 -> done(已关闭终态); done 不可再流转。
_TRANSITIONS: dict[str, set[str]] = {
    "open": {"doing", "pending", "done"},
    "doing": {"pending", "open", "done"},
    "pending": {"doing", "done"},
    "done": set(),  # 终态, 不允许任何流转
}

_PROGRESS_BY_STATE = {"open": 0, "doing": 20, "pending": 80, "done": 100}

# SLA 时限文本 -> 分钟, 用于推导 due_at 与超时判定
_SLA_MINUTES = {"15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240, "8h": 480, "24h": 1440}


def _parse_sla_minutes(sla: Optional[str]) -> int:
    if not sla:
        return _SLA_MINUTES["8h"]
    return _SLA_MINUTES.get(sla, _SLA_MINUTES["8h"])


def compute_due_at(created: str, sla: Optional[str]) -> Optional[str]:
    """由创建时间与 SLA 时限推导应完成时间 (ISO)。"""
    if not created:
        return None
    try:
        base = datetime.fromisoformat(created)
    except ValueError:
        return None
    return (base + timedelta(minutes=_parse_sla_minutes(sla))).isoformat(timespec="seconds")


def is_overdue(t: Ticket) -> bool:
    """未关闭且已超过 due_at 即视为超时 (终态 done 不计超时)。"""
    if t.state == "done" or not t.due_at:
        return False
    try:
        due = datetime.fromisoformat(t.due_at)
    except ValueError:
        return False
    return datetime.now() > due


def validate_transition(current: str, target: str) -> bool:
    """业务规则: 校验状态流转是否合法。"""
    if current == target:
        return True
    allowed = _TRANSITIONS.get(current, set())
    return target in allowed


def transition_error(current: str, target: str) -> str:
    """生成非法流转的可读错误信息。"""
    if current == "done":
        return f"工单已处于终态 done, 不可再流转到 {target}"
    allowed = sorted(_TRANSITIONS.get(current, set())) or ["(无可用流转)"]
    return f"非法状态流转: {current} -> {target}; 允许: {', '.join(allowed)}"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _gen_id(db: Session) -> str:
    d = datetime.now()
    ymd = f"{d.year % 100:02d}{d.month:02d}{d.day:02d}"
    cnt = db.query(Ticket).filter(Ticket.id.like(f"WO-{ymd}-%")).count() + 1
    return f"WO-{ymd}-{cnt:03d}"


def create_ticket(
    db: Session,
    *,
    title: str,
    sys: str,
    lv: str,
    owner: str,
    sla: Optional[str] = None,
    description: Optional[str] = None,
    source: str = "manual",
    source_alarm_id: Optional[str] = None,
    operator: str = "system",
) -> Ticket:
    now = _now_iso()
    t = Ticket(
        id=_gen_id(db),
        title=title,
        sys=sys,
        lv=lv,
        state="open",
        owner=owner,
        created=now,
        created_by=operator,
        updated_at=now,
        sla=sla or _SLA_BY_LV.get(lv, "8h"),
        due_at=compute_due_at(now, sla or _SLA_BY_LV.get(lv, "8h")),
        progress=0,
        source=source,
        source_alarm_id=source_alarm_id,
        description=description or "",
        logs=[{
            "ts": now,
            "operator": operator,
            "action": "create",
            "from": None,
            "to": "open",
            "note": description or "",
        }],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def find_open_by_alarm(db: Session, alarm_id: str) -> Optional[Ticket]:
    """按 source_alarm_id 查未关单工单 (告警自动建单的幂等判定)。"""
    return (
        db.query(Ticket)
        .filter(
            Ticket.source_alarm_id == alarm_id,
            Ticket.state.notin_(("done", "resolved", "closed")),
        )
        .order_by(Ticket.created.desc())
        .first()
    )


def list_tickets(
    db: Session,
    *,
    state: Optional[str] = None,
    sys: Optional[str] = None,
    lv: Optional[str] = None,
    source_alarm_id: Optional[str] = None,
    page: int = 1,
    limit: int = 200,
):
    q = db.query(Ticket)
    if state:
        q = q.filter(Ticket.state == state)
    if sys:
        q = q.filter(Ticket.sys == sys)
    if lv:
        q = q.filter(Ticket.lv == lv)
    if source_alarm_id:
        q = q.filter(Ticket.source_alarm_id == source_alarm_id)
    total = q.count()
    items = (
        q.order_by(Ticket.created.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def get_ticket(db: Session, ticket_id: str) -> Optional[Ticket]:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def update_ticket(db: Session, ticket_id: str, patch: dict) -> Optional[Ticket]:
    t = get_ticket(db, ticket_id)
    if not t:
        return None
    now = _now_iso()
    changed = False
    for k, v in patch.items():
        if v is None:
            continue
        if getattr(t, k) != v:
            setattr(t, k, v)
            changed = True
    if changed:
        t.updated_at = now
        t.logs = (t.logs or []) + [{
            "ts": now,
            "operator": "system",
            "action": "update",
            "from": t.state,
            "to": t.state,
            "note": "字段更新",
        }]
        db.commit()
        db.refresh(t)
    return t


def transition_ticket(
    db: Session, ticket_id: str, state: str, operator: str, note: Optional[str] = None
) -> Optional[Ticket]:
    t = get_ticket(db, ticket_id)
    if not t or t.state == state:
        return t
    # 5.5.2 业务规则: 非法状态流转显式拒绝 (由调用方转换为 400)
    if not validate_transition(t.state, state):
        raise ValueError(transition_error(t.state, state))
    old = t.state
    now = _now_iso()
    t.state = state
    t.updated_at = now
    if state in _PROGRESS_BY_STATE:
        t.progress = _PROGRESS_BY_STATE[state]
    t.logs = (t.logs or []) + [{
        "ts": now,
        "operator": operator,
        "action": "transition",
        "from": old,
        "to": state,
        "note": note or "",
    }]
    db.commit()
    db.refresh(t)
    return t


def delete_ticket(db: Session, ticket_id: str) -> bool:
    t = get_ticket(db, ticket_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


def ticket_stats(db: Session) -> dict:
    rows = db.query(Ticket.state, func.count(Ticket.id)).group_by(Ticket.state).all()
    s = {"open": 0, "doing": 0, "pending": 0, "done": 0}
    for st, c in rows:
        if st in s:
            s[st] = c
    return s
