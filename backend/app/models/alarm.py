"""告警事件持久化模型 (告警全生命周期记录)。

对齐前端 AlarmEvent: 规则触发 -> active -> acknowledged -> resolved/suppressed。
表名使用 `alarm_event`, 与原生成期占位表 `alarm` 解耦, 避免迁移冲突。
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AlarmEvent(Base):
    __tablename__ = "alarm_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    rule_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    rule_name: Mapped[str] = mapped_column(String(128), default="")
    metric: Mapped[str] = mapped_column(String(128), default="")
    sys: Mapped[str] = mapped_column(String(64), default="", index=True)
    lv: Mapped[str] = mapped_column(String(16), default="info", index=True)
    desc: Mapped[str] = mapped_column(String(512), default="")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="active", index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_count: Mapped[int] = mapped_column(Integer, default=0)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
