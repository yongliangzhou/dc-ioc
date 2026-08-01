"""演练计划 Pydantic Schema (阶段三 A)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DrillCreate(BaseModel):
    name: str
    type: str = "电力"
    date: str = ""
    state: str = "计划中"
    result: str = "—"
    code: Optional[str] = None
    note: str = ""


class DrillUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    state: Optional[str] = None
    result: Optional[str] = None
    note: Optional[str] = None
