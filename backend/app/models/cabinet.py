"""机柜 (Cabinet) 模型。"""
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Integer, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.idc import IDC
    from app.models.server import Server


class Cabinet(Base, TimestampMixin):
    __tablename__ = "cabinet"

    id: Mapped[int] = mapped_column(primary_key=True)
    idc_id: Mapped[int] = mapped_column(
        ForeignKey("idc.id", ondelete="CASCADE"), nullable=False, comment="所属数据中心"
    )
    code: Mapped[str] = mapped_column(String(32), index=True, comment="机柜编号 如 R01-A05")
    room: Mapped[str] = mapped_column(String(32), index=True, comment="所在包间")
    row: Mapped[str] = mapped_column(String(16), default="", comment="机列")
    u_total: Mapped[int] = mapped_column(Integer, default=42, comment="U位总数")
    u_used: Mapped[int] = mapped_column(Integer, default=0, comment="已用U位")
    rated_power_kw: Mapped[float] = mapped_column(Numeric(8, 2), default=10.0, comment="额定功率 kW")
    current_power_kw: Mapped[float] = mapped_column(Numeric(8, 2), default=0, comment="当前功率 kW")
    status: Mapped[str] = mapped_column(String(16), default="在用", index=True, comment="在用/预留/停用")

    idc: Mapped["IDC"] = relationship(back_populates="cabinets")
    servers: Mapped[List["Server"]] = relationship(
        back_populates="cabinet", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        # 同一 IDC 内机柜编号唯一
        Index("uq_cabinet_idc_code", "idc_id", "code", unique=True),
        # 高频查询: 某 IDC 某包间下的机柜
        Index("ix_cabinet_idc_room", "idc_id", "room"),
        {"comment": "机柜"},
    )
