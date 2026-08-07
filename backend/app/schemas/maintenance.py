"""维保 Pydantic Schema (阶段三 A · 运维作业-维保管理)。

包含维保计划 (MaintenancePlan) 与维保记录 (MaintenanceRecord) 两套 schema。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- 维保计划 ----------
class MaintenancePlanCreate(BaseModel):
    code: str = ""
    name: str = ""
    equipmentCode: str = ""
    description: str = ""
    frequency: str = "monthly"
    nextDueDate: str = ""
    status: str = "active"
    owner: str = ""


class MaintenancePlanUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: Optional[str] = None
    name: Optional[str] = None
    equipmentCode: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    nextDueDate: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None


class MaintenancePlanOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    code: str = ""
    name: str = ""
    equipmentCode: str = ""
    description: str = ""
    frequency: str = "monthly"
    nextDueDate: str = ""
    status: str = "active"
    owner: str = ""
    createdAt: str = ""


# ---------- 维保记录 ----------
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
