"""(维保记录 Pydantic Schema (阶段三 A · 运维作业-维保管理)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class MaintenanceRecordCreate(BaseModel):
    planCode: str = ""
    planName: str = ""
    equipmentCode: str = ""
    maintainedBy: str = ""
    startedAt: str = ""
    completedAt: str = ""
    status: str = "已完成"
    result: str = "—"
    actionDescription: str = ""
    notes: str = ""


class MaintenanceRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planCode: Optional[str] = None
    planName: Optional[str] = None
    equipmentCode: Optional[str] = None
    maintainedBy: Optional[str] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None
    actionDescription: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceRecordOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    planCode: str = ""
    planName: str = ""
    equipmentCode: str = ""
    maintainedBy: str = ""
    startedAt: str = ""
    completedAt: str = ""
    status: str = "已完成"
    result: str = "—"
    actionDescription: str = ""
    notes: str = ""
