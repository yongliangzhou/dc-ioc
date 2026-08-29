"""campus 级 KPI 滚动历史 (供 overview 趋势曲线, 根治前端合成示例数据)。

与 metric_raws (逐设备测点) 解耦: 本表由 kpi_broadcast_loop 周期写入后端聚合出的
运营 KPI 快照 (PUE / WUE / 负载 / 在线率 / 可用性), 不受 metric_raws 的 retention 清理影响。
落库节奏由写入方节流 (默认每 5 分钟 1 条), 仅保留近 30 天。
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Index, Integer

from app.db.session import Base


class KpiHistory(Base):
    __tablename__ = "kpi_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    pue = Column(Float, nullable=False, default=0.0)
    wue = Column(Float, nullable=False, default=0.0)
    it_load_mw = Column(Float, nullable=False, default=0.0)
    total_load_mw = Column(Float, nullable=False, default=0.0)
    cool_load_mw = Column(Float, nullable=False, default=0.0)
    online_rate = Column(Float, nullable=False, default=0.0)
    availability = Column(Float, nullable=False, default=0.0)

    __table_args__ = (Index("ix_kpi_history_ts", "ts"),)

    def to_dict(self) -> dict:
        return {
            "ts": self.ts.isoformat() if self.ts else None,
            "pue": self.pue,
            "wue": self.wue,
            "it_load_mw": self.it_load_mw,
            "total_load_mw": self.total_load_mw,
            "cool_load_mw": self.cool_load_mw,
            "online_rate": self.online_rate,
            "availability": self.availability,
        }
