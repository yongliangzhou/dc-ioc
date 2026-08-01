"""(维保模型 (阶段三 A · 运维作业-维保管理)。

维保计划当前由聚合器从真实设备类别动态生成, 这里仅持久化"维保记录"
(实际执行情况), 关联计划编号 (plan_code) 而非外键, 以兼容动态计划。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_record"

    id = Column(Integer, primary_key=True, index=True)
    plan_code = Column(String(64), default="", index=True)   # 关联计划编号 PM-xxx
    plan_name = Column(String(128), default="")              # 维保科目
    equipment_code = Column(String(128), default="")         # 关联设备
    maintained_by = Column(String(64), default="")           # 维保人
    started_at = Column(String(32), default="")              # 开始时间
    completed_at = Column(String(32), default="")            # 完成时间
    status = Column(String(32), default="已完成")            # 已完成/未完成
    result = Column(String(32), default="—")                 # 正常/异常
    action_description = Column(Text, default="")            # 处理说明
    notes = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
