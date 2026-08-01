"""告警引擎运行态持久化模型 (P0-3)。

与 B7(规则配置化) 同源设计:
- alarm_rule          规则定义 + 启停状态 (enabled), 后端为规则配置单一事实源
- alarm_active_state  活跃告警状态 (收敛时间 / 首见时间 / 确认状态), 重启与多 worker 一致
- alarm_suppressed_device  设备级告警抑制 (维保 / 离线)
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AlarmRule(Base):
    __tablename__ = "alarm_rule"

    # rule_id 形如 "chiller:supply_temp"
    rule_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), default="")
    metric: Mapped[str] = mapped_column(String(64), default="")
    warn_lo: Mapped[float | None] = mapped_column(Float, nullable=True)
    warn_hi: Mapped[float | None] = mapped_column(Float, nullable=True)
    crit_lo: Mapped[float | None] = mapped_column(Float, nullable=True)
    crit_hi: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(16), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    silenced: Mapped[bool] = mapped_column(Boolean, default=False)
    silence_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlarmActiveState(Base):
    __tablename__ = "alarm_active_state"

    # key = "device_id:metric_name:level"
    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    metric_name: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[str] = mapped_column(String(16), default="warn")
    alarm_json: Mapped[str] = mapped_column(Text, default="{}")  # 完整 alarm dict 序列化
    conv_ts: Mapped[float] = mapped_column(Float, default=0.0)       # 最近触发 (收敛窗口)
    first_seen_ts: Mapped[float] = mapped_column(Float, default=0.0)  # 本轮首见 (升级窗口)
    ack_state: Mapped[str] = mapped_column(String(16), default="待确认")  # 待确认 / 已确认
    status: Mapped[str] = mapped_column(String(16), default="active")    # active / resolved
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlarmSuppressedDevice(Base):
    __tablename__ = "alarm_suppressed_device"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reason: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
