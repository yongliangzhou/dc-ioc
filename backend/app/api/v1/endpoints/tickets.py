"""运维工单 API: 对齐前端 /api/ops/tickets 契约 (工单后端化 2.2)。

  - getTickets        -> GET    /api/ops/tickets
  - createTicket      -> POST   /api/ops/tickets
  - getTicket         -> GET    /api/ops/tickets/{id}
  - updateTicket      -> PUT    /api/ops/tickets/{id}
  - transitionTicket  -> PATCH  /api/ops/tickets/{id}/state
  - deleteTicket      -> DELETE /api/ops/tickets/{id}
  - createTicketFromAlarm -> POST /api/ops/tickets/from-alarm/{alarmId}
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.crud import alarm as alarm_crud
from app.models.user import User
from app.crud import ticket as ticket_crud
from app.services import alarm_engine
from app.schemas.ticket import (
    TicketCenterOut,
    TicketCreateRequest,
    TicketOut,
    TicketTransitionRequest,
    TicketUpdateRequest,
)

logger = logging.getLogger("api.tickets")

router = APIRouter(prefix="/ops/tickets", tags=["tickets"])


@router.get("", response_model=TicketCenterOut)
def list_tickets(
    state: str | None = None,
    sys: str | None = None,
    lv: str | None = None,
    page: int = 1,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    items, _ = ticket_crud.list_tickets(db, state=state, sys=sys, lv=lv, page=page, limit=limit)
    stats = ticket_crud.ticket_stats(db)
    return TicketCenterOut(stats=stats, list=[TicketOut.model_validate(t) for t in items])


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(
    req: TicketCreateRequest,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    if not req.title or not req.sys or not req.lv or not req.owner:
        raise HTTPException(status_code=422, detail="title/sys/lv/owner 为必填项")
    t = ticket_crud.create_ticket(
        db,
        title=req.title,
        sys=req.sys,
        lv=req.lv,
        owner=req.owner,
        sla=req.sla,
        description=req.description,
        source=req.source or "manual",
        source_alarm_id=req.source_alarm_id,
    )
    return t


@router.post("/from-alarm/{alarm_id}", response_model=TicketOut, status_code=201)
def create_from_alarm(
    alarm_id: str,
    req: TicketCreateRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    """一键将告警转为工单 (对齐 createTicketFromAlarm)。

    [B1] 兼容真实联动告警引擎 (alarm_engine 内存态, 不在 AlarmEvent 表):
    优先查历史库, 查不到则回退到活跃告警引擎; 转单同时将告警标记为已确认 (关联)。
    """
    alarm = alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        eng = next(
            (a for a in alarm_engine.get_active_alarms() if a.get("alarm_id") == alarm_id),
            None,
        )
        if eng:
            from datetime import datetime

            from types import SimpleNamespace

            cat = eng.get("category", "")
            sys_name = {
                "chiller": "暖通空调", "crac": "暖通空调", "acunit": "暖通空调",
                "liquid": "液冷系统", "ups": "供配电", "pdudevice": "供配电",
                "hv": "供配电", "lv": "供配电", "genset": "供配电",
                "battery": "储能系统", "fuel": "燃油系统", "WaterSystem": "给排水",
            }.get(cat, cat)
            alarm = SimpleNamespace(
                id=alarm_id,
                lv=eng.get("level", "warn"),
                sys=sys_name,
                desc=f"{eng.get('device_id', '')} · {eng.get('metric_name', '')} 越限（{eng.get('value')}{eng.get('unit', '')}）",
                triggered_at=datetime.fromtimestamp(eng.get("ts", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                state=eng.get("ack_state", "待确认"),
            )
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    # [B1] 转单即标记告警已关联 (确认态), 写穿引擎状态机
    try:
        alarm_engine.ack_alarm(alarm_id)
    except Exception as e:  # noqa: BLE001
        logger.debug("转工单关联告警失败: %s", e)
    data = (req or TicketCreateRequest()).model_dump()
    sla = data.get("sla") or {"crit": "1h", "warn": "4h", "info": "8h"}.get(alarm.lv, "8h")
    title = data.get("title") or f"[告警转工单] {alarm.desc}"
    description = data.get("description") or (
        f"来源系统: {alarm.sys}\n"
        f"告警内容: {alarm.desc}\n"
        f"触发时间: {alarm.triggered_at}\n"
        f"严重级别: {alarm.lv}\n"
        f"原始状态: {alarm.state}"
    )
    t = ticket_crud.create_ticket(
        db,
        title=title,
        sys=data.get("sys") or alarm.sys,
        lv=data.get("lv") or alarm.lv,
        owner=data.get("owner") or "待分配",
        sla=sla,
        description=description,
        source="alarm",
        source_alarm_id=alarm.id,
    )
    return t


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    t = ticket_crud.get_ticket(db, ticket_id)
    if t is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    return t


@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: str,
    req: TicketUpdateRequest,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    t = ticket_crud.update_ticket(db, ticket_id, req.model_dump(exclude_unset=True))
    if t is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    return t


@router.patch("/{ticket_id}/state", response_model=TicketOut)
def transition_ticket(
    ticket_id: str,
    req: TicketTransitionRequest,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    t = ticket_crud.get_ticket(db, ticket_id)
    if t is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    source_alarm_id = t.source_alarm_id
    ticket_crud.transition_ticket(db, ticket_id, req.state, req.operator, req.note)
    # [B1] 关单联动: 工单进入终态时解析其关联的活跃告警 (写穿引擎状态机)
    if req.state in ("done", "resolved", "closed") and source_alarm_id:
        try:
            alarm_engine.resolve_alarm(source_alarm_id)
        except Exception as e:  # noqa: BLE001
            logger.debug("工单关单联动解析告警失败: %s", e)
    t = ticket_crud.get_ticket(db, ticket_id)
    return t


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    ok = ticket_crud.delete_ticket(db, ticket_id)
    if not ok:
        raise HTTPException(status_code=404, detail="工单不存在")
    return None
