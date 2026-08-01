"""演练计划模型 (阶段三 A · 运维作业-演练管理)。"""
from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class DrillPlan(Base):
    __tablename__ = "drill_plan"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), index=True, default="")          # DR-xx
    name = Column(String(128), default="")                      # 演练科目
    type = Column(String(32), default="电力")                   # 电力/暖通/消防/安防
    date = Column(String(16), default="")                       # 计划日期 YYYY-MM-DD
    state = Column(String(32), default="计划中")                # 计划中/已编排/已完成
    result = Column(String(32), default="—")                    # 通过/未通过/—
    note = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
