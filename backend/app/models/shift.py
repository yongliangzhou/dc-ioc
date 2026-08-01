"""值班排班模型 (2.3)。"""
from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.types import JSON

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class ShiftSchedule(Base):
    __tablename__ = "shift_schedule"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(16), index=True, nullable=False)   # YYYY-MM-DD
    shift = Column(String(16), index=True, default="day")   # day/night
    members = Column(JSON, default=list)                     # [{name, role, phone}]
    leader = Column(String(64), default="")
    note = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
