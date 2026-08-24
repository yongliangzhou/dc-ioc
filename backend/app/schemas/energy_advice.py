"""电量节能建议采纳 schema (批次C)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EnergyAdviceAdoptIn(BaseModel):
    suggestionId: str = ""
    title: str = ""
    priority: str = ""
    savingKw: float = 0.0
    savingPct: float = 0.0
    detail: str = ""
    basis: str = ""
    action: str = "adopt"          # adopt / ignore
    note: str = ""
    pueCurrent: Optional[float] = None
    pueTarget: Optional[float] = None
    user: str = ""


class EnergyAdviceAdoptOut(BaseModel):
    id: int
    suggestionId: str
    title: str
    priority: str
    savingKw: float
    savingPct: float
    detail: str
    basis: str
    action: str
    note: str
    pueCurrent: float
    pueTarget: float
    user: str
    createdAt: str
