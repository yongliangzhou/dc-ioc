"""冷机机组控制指令记录 (D6 后端化: 快控指令由前端占位 toast 改为服务端下发+留痕)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Float, Integer, String

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class ControlLog(Base):
    __tablename__ = "control_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chiller_id = Column(String(32), default="")                 # 机组 id (对齐 ChillerGroupView.chiller.id)
    action = Column(String(16), default="")                     # start / stop / mode / temp
    value = Column(Float, default=None)                         # temp 动作的设定值 (℃)
    operator = Column(String(64), default="")
    result = Column(String(16), default="accepted")             # accepted / rejected
    created_at = Column(String(32), default=_now)
