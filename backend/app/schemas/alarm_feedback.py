"""告警处理反馈 Schema (批次B)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlarmFeedbackCreate(BaseModel):
    alarmId: str = ""
    system: str = ""
    result: str = ""
    note: str = ""
    operator: str = ""


class AlarmFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alarmId: str
    system: str
    result: str
    note: str
    operator: str
    createdAt: str = ""
