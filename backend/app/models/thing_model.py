"""物模型模型 (phase: thing-model)。

阿里云风格物模型三要素: property(属性) / service(服务) / event(事件)。
ThingModel 为某一类设备的模型模板, ThingModelItem 为其下具体测点/服务/事件定义。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class ThingModel(Base):
    __tablename__ = "thing_model"
    __table_args__ = (UniqueConstraint("model_key", name="uq_thing_model_key"),)

    id = Column(Integer, primary_key=True, index=True)
    # 模型唯一 key (设备类别语义, 如 chiller/crac/ups/...), 前端 / 采集器共用
    model_key = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False, default="")           # 模型中文名
    category = Column(String(64), index=True, default="")             # 设备类别 (chiller/ups/...)
    domain = Column(String(64), index=True, default="")               # 业务域 (hvac_source/power_hv/...)
    protocol = Column(String(32), default="")                         # 推荐采集协议 (modbus/snmp/...)
    vendor = Column(String(64), default="")                           # 厂商
    description = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)


class ThingModelItem(Base):
    __tablename__ = "thing_model_item"

    id = Column(Integer, primary_key=True, index=True)
    thing_model_id = Column(
        Integer, ForeignKey("thing_model.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # property(属性) / service(服务) / event(事件)
    item_type = Column(String(16), nullable=False, default="property", index=True)
    identifier = Column(String(64), nullable=False, default="")        # 标识符 (蛇形命名, 如 supply_temp)
    name = Column(String(128), default="")                            # 中文名 (如 送风温度)
    data_type = Column(String(32), default="float")                   # float/int/bool/enum/string/struct
    unit = Column(String(16), default="")                             # ℃ / kW / %
    desc = Column(Text, default="")                                    # 说明
    # 扩展信息: enum 值域 / 服务入参出参 / 事件等级等, 由前端按需填充
    extra = Column(JSON, default=dict)
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
