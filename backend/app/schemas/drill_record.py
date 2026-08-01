"""(演练记录 Pydantic Schema (阶段三 A · 运维作业-演练管理)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DrillRecordCreate(BaseModel):
    planId: Optional[int] = None
    planCode: str = ""
    planName: str = ""
    executedBy: str = ""
    startedAt: str = ""
    completedAt: str = ""
    score: Optional[int] = None
    result: str = "—"
    notes: str = ""


class DrillRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planId: Optional[int] = None
    planCode: Optional[str] = None
    planName: Optional[str] = None
    executedBy: Optional[str] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    score: Optional[int] = None
    result: Optional[str] = None
    notes: Optional[str] = None


class DrillRecordOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    planId: Optional[int] = None
    planCode: str = ""
    planName: str = ""
    executedBy: str = ""
    startedAt: str = ""
    completedAt: str = ""
    score: Optional[int] = None
    result: str = "—"
    notes: str = ""
