"""运维工单 DTO (对齐前端 Ticket / TicketCenter)。"""
from __future__ import annotations

from typing import List, Optional

from app.schemas.common import CamelModel


class TicketOut(CamelModel):
    id: str
    title: str
    sys: str
    lv: str
    state: str
    owner: str
    created: str
    created_by: str = ""
    updated_at: str = ""
    sla: str = ""
    due_at: Optional[str] = None
    progress: int = 0
    source: str = "manual"
    source_alarm_id: Optional[str] = None
    description: Optional[str] = None
    logs: List[dict] = []


class TicketCreateRequest(CamelModel):
    title: Optional[str] = None
    sys: Optional[str] = None
    lv: Optional[str] = None
    owner: Optional[str] = None
    sla: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = "manual"
    source_alarm_id: Optional[str] = None


class TicketUpdateRequest(CamelModel):
    title: Optional[str] = None
    sys: Optional[str] = None
    lv: Optional[str] = None
    owner: Optional[str] = None
    sla: Optional[str] = None
    progress: Optional[int] = None
    description: Optional[str] = None


class TicketTransitionRequest(CamelModel):
    state: str
    operator: str
    note: Optional[str] = None


class TicketCenterOut(CamelModel):
    stats: dict = {}
    list: List[TicketOut] = []
