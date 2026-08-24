"""值班排班 / 交接班模型 (2.3)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text, JSON

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class ShiftSchedule(Base):
    __tablename__ = "shift_schedule"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(16), index=True, nullable=False)   # YYYY-MM-DD
    shift = Column(String(16), index=True, default="day")   # day/night
    members = Column(JSON, default=list)                      # 成员 [{name, role, phone}]
    leader = Column(String(64), default="")
    note = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)


class ShiftHandover(Base):
    """交接班记录 (2.3 · 交接表)。"""
    __tablename__ = "shift_handover"

    id = Column(Integer, primary_key=True, index=True)
    shift_date = Column(String(16), index=True, default="")     # 关联班次日期
    shift_type = Column(String(16), default="day")              # day/night
    from_user = Column(String(64), default="")                  # 交班人
    to_user = Column(String(64), default="")                    # 接班人
    items = Column(Text, default="")                            # 交接事项 (JSON 串 [{level, text}])
    note = Column(Text, default="")                             # 补充说明
    status = Column(String(16), default="pending")              # pending/done
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
