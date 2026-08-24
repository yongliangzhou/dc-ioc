"""风险项模型 (阶段三 A · 运维作业-风险管理)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class RiskItem(Base):
    __tablename__ = "risk_item"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), index=True, default="")          # R-xx
    risk = Column(Text, default="")                             # 风险描述
    cat = Column(String(64), default="")                        # 类别
    prob = Column(Integer, default=2)                           # 概率 1-4
    impact = Column(Integer, default=2)                         # 影响 1-4
    level = Column(String(16), default="中")                    # 高/中/低 (由 prob*impact 推导)
    ctrl = Column(Text, default="")                             # 管控措施
    owner = Column(String(64), default="")                      # 责任
    closed = Column(Integer, default=0)                         # 0/1 是否已关闭
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
