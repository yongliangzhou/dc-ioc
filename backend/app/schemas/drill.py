"""演练计划 Pydantic Schema (阶段三 A)。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DrillStep(BaseModel):
    """演练步骤 (深化设计: 可持久化)。"""

    title: str
    minutes: int = 0
    desc: str = ""


class DrillCreate(BaseModel):
    name: str
    type: str = "电力"
    date: str = ""
    state: str = "计划中"
    result: str = "—"
    code: Optional[str] = None
    note: str = ""
    level: str = "—"
    scope: str = ""
    duration: int = 0
    steps: List[DrillStep] = []


class DrillUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    state: Optional[str] = None
    result: Optional[str] = None
    note: Optional[str] = None
    level: Optional[str] = None
    scope: Optional[str] = None
    duration: Optional[int] = None
    steps: Optional[List[DrillStep]] = None
