"""(演练记录模型 (阶段三 A · 运维作业-演练管理)。

演练记录关联演练计划, 记录实际执行情况 (执行人/起止时间/评分/结果)。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class DrillRecord(Base):
    __tablename__ = "drill_record"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("drill_plan.id"), nullable=True, index=True)
    plan_code = Column(String(32), default="")          # 关联计划编号 DR-xx
    plan_name = Column(String(128), default="")          # 演练科目
    executed_by = Column(String(64), default="")         # 执行人
    started_at = Column(String(32), default="")          # 开始时间
    completed_at = Column(String(32), default="")        # 完成时间
    score = Column(Integer, nullable=True)              # 评分 0-100
    result = Column(String(32), default="—")             # 通过/未通过/—
    notes = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
