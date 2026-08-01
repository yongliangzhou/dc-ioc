"""运维工单持久化模型 (对齐前端 Ticket)。

工单号形如 `WO-YYMMDD-NNN`; 生命周期: open -> doing -> pending -> done。
logs 为 JSON 数组, 每个元素 { ts, operator, action, from, to, note }。
"""
from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Ticket(Base):
    __tablename__ = "ticket"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # WO-YYMMDD-NNN
    title: Mapped[str] = mapped_column(String(256))
    sys: Mapped[str] = mapped_column(String(64), default="", index=True)
    lv: Mapped[str] = mapped_column(String(16), default="info", index=True)
    state: Mapped[str] = mapped_column(String(32), default="open", index=True)
    owner: Mapped[str] = mapped_column(String(64), default="待分配")
    created: Mapped[str] = mapped_column(String(32), default="")        # ISO 字符串
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[str] = mapped_column(String(32), default="")
    sla: Mapped[str] = mapped_column(String(32), default="")
    due_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    source_alarm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    logs: Mapped[list] = mapped_column(JSON, default=list)
