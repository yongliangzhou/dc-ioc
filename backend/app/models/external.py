"""外部设备接入契约 ORM 模型 — 落库实体。

与 services/collectors 通过 app.schemas.external 的 Pydantic 契约对齐:
- ExternalDevice  <-> DeviceRegisterRequest
- MetricRaw       <-> MetricPoint
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class ExternalDevice(Base, TimestampMixin):
    """已注册外部设备 (采集器注册落库)。"""

    __tablename__ = "external_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False,
                                            comment="采集侧唯一标识")
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    sn: Mapped[str] = mapped_column(String(128), nullable=False, comment="出厂序列号")
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(String(128), default=None)
    vendor: Mapped[str | None] = mapped_column(String(64), default=None)
    domain: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    category: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    location: Mapped[str | None] = mapped_column(String(128), default=None)
    protocol: Mapped[str | None] = mapped_column(String(32), default=None)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(String(512), default=None)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None,
                                                        comment="最近一次测点上报时间")


class MetricRaw(Base):
    """原始测点时序 (采集器上报落库, 未做聚合)。

    生产环境建议对该表做 TimescaleDB hypertable / 分区; 当前为通用关系表。
    """

    __tablename__ = "metric_raws"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False,
                                          comment="测点采样时间")
    metric_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String(16), default="good", comment="good/uncertain/bad")
    unit: Mapped[str | None] = mapped_column(String(32), default=None)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                  nullable=False, comment="平台接收时间")

    __table_args__ = (
        Index("ix_metric_raw_device_ts", "device_id", "ts"),
        Index("ix_metric_raw_device_name", "device_id", "metric_name"),
        # [P1-4 FIX] 幂等唯一键: Kafka at-least-once 重投 / 采集器重发时,
        # 后端 bulk_insert_metrics 走 ON CONFLICT DO NOTHING 直接跳过, 不产生重复行。
        UniqueConstraint(
            "device_id", "metric_name", "ts",
            name="uq_metric_raw_device_name_ts",
        ),
    )
