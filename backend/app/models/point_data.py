"""实时测点数据 (Point_Data) 时序模型。

设计要点:
- 采用 (target_type, target_id) 多态关联, 支持机柜/服务器/环境等多种采集对象;
- metric 标识指标类型 (temperature/humidity/cpu_usage/mem_usage/power...);
- 大表按 ts 分区 (推荐 TimescaleDB hypertable), 并提供 BRIN/B-tree 复合索引。
"""
from datetime import datetime

from sqlalchemy import String, Float, SmallInteger, DateTime, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PointData(Base):
    __tablename__ = "point_data"

    # 时序主键: (id 自增, ts) — TimescaleDB 下以 ts 为分区键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, comment="采集时间(分区键)"
    )

    # 采集对象 (多态)
    target_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="对象类型: idc/cabinet/server/env"
    )
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="对象ID")

    # 指标
    metric: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="指标: temperature/humidity/cpu_usage/mem_usage/power_kw..."
    )
    value: Mapped[float] = mapped_column(Float, nullable=False, comment="数值")
    unit: Mapped[str] = mapped_column(String(16), default="", comment="单位")
    quality: Mapped[int] = mapped_column(SmallInteger, default=100, comment="数据质量 0-100")

    __table_args__ = (
        # 单对象单指标的时间序列拉取 (最常用): WHERE target AND metric ORDER BY ts
        Index("ix_pd_target_metric_ts", "target_type", "target_id", "metric", "ts"),
        # 按指标+时间的全局查询 (如同类温度对比)
        Index("ix_pd_metric_ts", "metric", "ts"),
        # 时间 BRIN 索引: 大范围时序扫描( Timescale/PG 顺序写表极高效 )
        Index("ix_pd_ts_brin", "ts", postgresql_using="brin"),
        {"comment": "实时测点时序数据"},
    )
