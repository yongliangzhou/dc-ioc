"""AI 运维助手反馈 Schema (批次B)。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AssistantFeedbackCreate(BaseModel):
    question: str = ""
    answer: str = ""
    rating: str = ""          # up / down
    correction: str = ""      # 纠错内容 / 正确答案
    note: str = ""
    grounded: str = ""
    model: str = ""
    user: str = ""


class AssistantFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    answer: str
    rating: str
    correction: str
    note: str
    grounded: str
    model: str
    user: str
    createdAt: str = ""
