"""告警处理反馈 / 经验沉淀模型 (批次B · 反馈持久化)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class AlarmFeedback(Base):
    __tablename__ = "alarm_feedback"

    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(String(64), index=True, default="")   # 告警标识(实时id 或 evt-...)
    system = Column(String(64), default="")                 # 告警系统/专业
    result = Column(String(32), default="")                 # 已处理修复/误报/转工单/持续观察
    note = Column(Text, default="")                         # 根因/排查步骤/修复方案
    operator = Column(String(64), default="")               # 处理人
    created_at = Column(String(32), default=_now)
