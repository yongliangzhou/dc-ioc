"""巡检 Pydantic Schema (阶段三 A)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class RouteCreate(BaseModel):
    code: Optional[str] = None
    freq: str = "每日"
    items: int = 0
    last: str = ""
    next: str = ""
    state: str = "进行中"
    note: str = ""


class RouteUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    freq: Optional[str] = None
    items: Optional[int] = None
    last: Optional[str] = None
    next: Optional[str] = None
    state: Optional[str] = None
    note: Optional[str] = None


class FindingCreate(BaseModel):
    route: str = ""
    item: str = ""
    ts: str = ""
    lv: str = "info"
    action: str = ""


class FindingUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    route: Optional[str] = None
    item: Optional[str] = None
    ts: Optional[str] = None
    lv: Optional[str] = None
    action: Optional[str] = None
