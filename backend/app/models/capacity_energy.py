"""容量/能耗「分析型长期时序」表 (B4)。

与 metric_raws 解耦: 该表由独立的每日 rollup 写入, 不受 P0-1 的
metric_raws 保留清理影响 (retention 循环只清 metric_raws / 聚合视图),
因此容量/能耗历史可长期留存, 不再依赖快照逆推。
"""
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    JSON,
    String,
    UniqueConstraint,
    Index,
)
from app.db.session import Base


class CapacityEnergyHistory(Base):
    __tablename__ = "capacity_energy_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # 作用域 (如 DC1); 多园区可扩展
    idc_code = Column(String(32), nullable=False, default="DC1")
    # 指标键: facility_kw / cooling_kw / it_load_kw / loss_kw / pue / energy_kwh_day
    metric_key = Column(String(64), nullable=False)
    # 日粒度起点 (UTC 00:00), 作为聚合桶
    bucket = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(16), nullable=True)
    # real=真实聚合生成; generated=回退生成器
    source = Column(String(16), nullable=False, default="real")
    meta = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "idc_code", "metric_key", "bucket",
            name="uq_ceh_scope_key_bucket",
        ),
        Index("ix_ceh_key_bucket", "metric_key", "bucket"),
    )
