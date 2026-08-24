"""电量节能建议采纳记录模型 (批次C · 节能闭环)。

运营人员在 EnergyDashboard 中查看 AI 节能建议后, 可对建议执行「采纳 / 忽略」操作,
本表持久化采纳结果, 供后续核查与节能量统计。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text, Float

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class EnergyAdviceAdopt(Base):
    __tablename__ = "energy_advice_adopt"

    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(String(64), default="")     # 建议唯一标识 (如 chws-setpoint)
    title = Column(String(255), default="")            # 建议标题
    priority = Column(String(16), default="")          # 高 / 中 / 低
    saving_kw = Column(Float, default=0.0)             # 估算节电量 (kW)
    saving_pct = Column(Float, default=0.0)            # 估算节能率 (%)
    detail = Column(Text, default="")                  # 建议详情
    basis = Column(Text, default="")                   # 依据测点
    action = Column(String(16), default="adopt")       # adopt / ignore
    note = Column(Text, default="")                    # 采纳备注 / 实施计划
    pue_current = Column(Float, default=0.0)           # 采纳时 PUE 现状
    pue_target = Column(Float, default=0.0)            # PUE 目标
    user = Column(String(64), default="")              # 操作人
    created_at = Column(String(32), default=_now)
