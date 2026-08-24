"""物理服务器 (Server) 模型。"""
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.cabinet import Cabinet


class Server(Base, TimestampMixin):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(
        ForeignKey("cabinet.id", ondelete="CASCADE"), nullable=False, comment="所在机柜"
    )
    asset_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="资产编号")
    hostname: Mapped[str] = mapped_column(String(128), default="")
    ip: Mapped[str] = mapped_column(String(45), index=True, comment="管理IP (IPv4/IPv6)")
    brand: Mapped[str] = mapped_column(String(64), default="", comment="厂商")
    model: Mapped[str] = mapped_column(String(128), default="", comment="型号")
    # U位 (起止, 含)
    u_start: Mapped[int] = mapped_column(Integer, nullable=False, comment="起始U位")
    u_end: Mapped[int] = mapped_column(Integer, nullable=False, comment="结束U位")
    # 配置
    cpu_model: Mapped[str] = mapped_column(String(128), default="", comment="CPU 型号")
    cpu_count: Mapped[int] = mapped_column(Integer, default=2, comment="CPU 颗数")
    cpu_cores: Mapped[int] = mapped_column(Integer, default=0, comment="总核数")
    memory_gb: Mapped[int] = mapped_column(Integer, default=0, comment="内存 GB")
    disk_desc: Mapped[str] = mapped_column(String(255), default="", comment="磁盘描述")
    business: Mapped[str] = mapped_column(String(128), default="", index=True, comment="所属业务")
    status: Mapped[str] = mapped_column(String(16), default="在线", index=True, comment="在线/离线/下架")

    cabinet: Mapped["Cabinet"] = relationship(back_populates="servers")

    __table_args__ = (
        # U位合法性
        CheckConstraint("u_end >= u_start", name="ck_server_u_range"),
        CheckConstraint("u_start >= 1", name="ck_server_u_start_pos"),
        # 高频查询: 按机柜 + U位定位 / 空间冲突检测
        Index("ix_server_cabinet_u", "cabinet_id", "u_start", "u_end"),
        # 按 IP + 状态查询
        Index("ix_server_ip_status", "ip", "status"),
        {"comment": "物理服务器"},
    )
