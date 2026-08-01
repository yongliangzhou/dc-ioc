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
