"""维保模型 (阶段三 A · 运维作业-维保管理)。

- MaintenancePlan: 维保计划独立模型, 支持用户新建/编辑/删除 (批次补强)。
- MaintenanceRecord: 维保执行记录, 关联计划编号 (plan_code) 而非外键, 兼容动态计划。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class MaintenancePlan(Base):
    """维保计划 (用户可维护)。"""
    __tablename__ = "maintenance_plan"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), default="", index=True)       # 计划编号 PM-xxx
    name = Column(String(128), default="")                  # 维保科目
    equipment_code = Column(String(128), default="")        # 关联设备
    description = Column(Text, default="")                  # 说明 / 厂商信息
    frequency = Column(String(32), default="monthly")       # daily/weekly/monthly/quarterly/yearly
    next_due_date = Column(String(32), default="")          # 下次到期
    status = Column(String(32), default="active")           # active/paused/done
    owner = Column(String(64), default="")                  # 责任人
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)


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
