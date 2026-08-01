"""运维工单 CRUD + 统计 (对齐前端 /api/ops/tickets 契约)。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ticket import Ticket

_SLA_BY_LV = {"crit": "1h", "warn": "4h", "info": "8h"}
_PROGRESS_BY_STATE = {"open": 0, "doing": 20, "pending": 80, "done": 100}


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


def list_tickets(
    db: Session,
    *,
    state: Optional[str] = None,
    sys: Optional[str] = None,
    lv: Optional[str] = None,
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
