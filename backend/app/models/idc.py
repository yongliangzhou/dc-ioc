"""数据中心 (IDC) 模型。"""
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.cabinet import Cabinet


class IDC(Base, TimestampMixin):
    __tablename__ = "idc"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="站点编码 如 EC1-HZ")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="数据中心名称")
    region: Mapped[str] = mapped_column(String(64), index=True, comment="地域/可用区")
    address: Mapped[str] = mapped_column(String(255), default="", comment="地址")
    # 容量
    power_capacity_mw: Mapped[float] = mapped_column(Numeric(10, 3), default=0, comment="电力容量 MW")
    cooling_capacity_mw: Mapped[float] = mapped_column(Numeric(10, 3), default=0, comment="制冷容量 MW")
    rack_capacity: Mapped[int] = mapped_column(Integer, default=0, comment="机柜总容量")
    rooms: Mapped[int] = mapped_column(Integer, default=0, comment="包间数量")
    status: Mapped[str] = mapped_column(String(16), default="运营", index=True, comment="运营/建设/下线")

    cabinets: Mapped[List["Cabinet"]] = relationship(
        back_populates="idc", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        # 常用组合查询: 按地域+状态筛选站点
        {"comment": "数据中心"},
    )
