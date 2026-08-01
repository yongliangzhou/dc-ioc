"""包间/功能间模型 (参考课程: IT包间/变电站/电池室/冷冻站/运营商机房等)。"""
from sqlalchemy import String, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class Room(Base, TimestampMixin):
    __tablename__ = "room"

    id: Mapped[int] = mapped_column(primary_key=True)
    idc_id: Mapped[int] = mapped_column(ForeignKey("idc.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, comment="包间编号 R01")
    name: Mapped[str] = mapped_column(String(64), default="")
    # 参考文件分类: it_room/substation/battery_room/chiller_station/carrier_room/ups_room/noc...
    kind: Mapped[str] = mapped_column(String(32), default="it_room", index=True, comment="房间类型")
    floor: Mapped[str] = mapped_column(String(16), default="")
    rack_capacity: Mapped[int] = mapped_column(Integer, default=0)
    cold_aisle_t: Mapped[float] = mapped_column(Float, default=0, comment="冷通道均温")
    hot_aisle_t: Mapped[float] = mapped_column(Float, default=0, comment="热通道均温")
    rh: Mapped[float] = mapped_column(Float, default=0, comment="相对湿度")
    pressure_pa: Mapped[float] = mapped_column(Float, default=0, comment="正压 Pa (参考: 5~10Pa)")

    __table_args__ = (
        Index("uq_room_idc_code", "idc_id", "code", unique=True),
        {"comment": "包间/功能间"},
    )
