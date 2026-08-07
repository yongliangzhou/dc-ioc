"""值班排班 Schema (2.3)。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemberIn(BaseModel):
    name: str
    role: str = ""
    phone: str = ""


class ShiftCreate(BaseModel):
    date: str
    shift: str = "day"  # day / night
    members: list[MemberIn] = Field(default_factory=list)
    leader: str = ""
    note: str = ""


class ShiftUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: Optional[str] = None
    shift: Optional[str] = None
    members: Optional[list[MemberIn]] = None
    leader: Optional[str] = None
    note: Optional[str] = None


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: str
    shift: str = "day"
    members: list[Any] = Field(default_factory=list)
    leader: str = ""
    note: str = ""
    createdAt: Any = None
    updatedAt: Any = None


# ===== 交接班 =====
class HandoverItemIn(BaseModel):
    level: str = "normal"  # normal / warn / critical
    text: str = ""


class HandoverCreate(BaseModel):
    shiftDate: str = ""
    shiftType: str = "day"
    fromUser: str = ""
    toUser: str = ""
    items: str = "[]"   # JSON 串 [{level, text}]
    note: str = ""
    status: str = "pending"


class HandoverUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shiftDate: Optional[str] = None
    shiftType: Optional[str] = None
    fromUser: Optional[str] = None
    toUser: Optional[str] = None
    items: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None


class HandoverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shiftDate: str = ""
    shiftType: str = "day"
    fromUser: str = ""
    toUser: str = ""
    items: str = "[]"
    note: str = ""
    status: str = "pending"
    createdAt: Any = None
    updatedAt: Any = None

