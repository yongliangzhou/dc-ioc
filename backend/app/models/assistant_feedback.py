"""AI 运维助手问答反馈模型 (批次B · 反馈闭环)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class AssistantFeedback(Base):
    __tablename__ = "assistant_feedback"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, default="")            # 用户提问
    answer = Column(Text, default="")              # AI 回答(摘要)
    rating = Column(String(16), default="")        # up / down
    correction = Column(Text, default="")          # 纠错/正确答案
    note = Column(Text, default="")                # 备注
    grounded = Column(String(8), default="")       # 是否命中知识库
    model = Column(String(64), default="")         # 使用模型
    user = Column(String(64), default="")          # 反馈人
    created_at = Column(String(32), default=_now)
