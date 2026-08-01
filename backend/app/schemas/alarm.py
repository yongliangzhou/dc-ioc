"""告警事件 DTO (对齐前端 AlarmEvent / AlarmHistoryResponse)。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.common import CamelModel


class AlarmEventOut(CamelModel):
    id: str
    rule_id: str = ""
    rule_name: str = ""
    metric: str = ""
    sys: str = ""
    lv: str = "info"
    desc: str = ""
    value: Optional[float] = None
    threshold: Optional[float] = None
    unit: Optional[str] = None
    state: str = "active"
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    note: Optional[str] = None
    auto_resolved: bool = False
    escalation_count: int = 0
    device_id: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None


class AlarmActionRequest(CamelModel):
    """确认 / 处置请求 (ack / resolve)。"""
    by: str
    note: Optional[str] = None


class AlarmHistoryResponse(CamelModel):
    items: list[AlarmEventOut] = []
    total: int = 0
    page: int = 1
    limit: int = 20
    stats: dict = {}
