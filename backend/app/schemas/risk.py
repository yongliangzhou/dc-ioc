"""风险项 Pydantic Schema (阶段三 A)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class RiskCreate(BaseModel):
    risk: str
    cat: str = ""
    prob: int = 2
    impact: int = 2
    ctrl: str = ""
    owner: str = ""
    code: Optional[str] = None
    closed: int = 0


class RiskUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk: Optional[str] = None
    cat: Optional[str] = None
    prob: Optional[int] = None
    impact: Optional[int] = None
    ctrl: Optional[str] = None
    owner: Optional[str] = None
    closed: Optional[int] = None
