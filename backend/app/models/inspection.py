"""巡检模型 (阶段三 A · 运维作业-巡检管理): 路线 / 发现 / 机器人配置。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class InspectionRoute(Base):
    """巡检路线 (人工/机器人)。"""
    __tablename__ = "inspection_route"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), index=True, default="")
    freq = Column(String(32), default="每日")                   # 频次
    items = Column(Integer, default=0)                          # 检查项数
    last = Column(String(32), default="")                       # 上次巡检
    next = Column(String(32), default="")                       # 下次巡检
    state = Column(String(32), default="进行中")                # 进行中/已完成
    note = Column(Text, default="")


class InspectionFinding(Base):
    """巡检发现 (异常闭环)。"""
    __tablename__ = "inspection_finding"

    id = Column(Integer, primary_key=True, index=True)
    route = Column(String(64), default="")                      # 所属路线
    item = Column(Text, default="")                             # 发现内容
    ts = Column(String(32), default="")                         # 时间戳
    lv = Column(String(16), default="info")                     # crit/warn/info
    action = Column(Text, default="")                           # 处置动作


class InspectionRobot(Base):
    """无人巡检机器人配置 (单例)。"""
    __tablename__ = "inspection_robot"

    id = Column(Integer, primary_key=True)
    units = Column(Integer, default=2)                          # 机器人总数
    running = Column(Integer, default=2)                        # 运行中
    coverage = Column(Integer, default=96)                      # 覆盖率 %
