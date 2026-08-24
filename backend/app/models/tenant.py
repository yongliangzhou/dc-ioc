"""租户模型 (阶段三 A · 资源运营-租户管理)。

深化设计: 在原有基础字段上扩展配额 (quota) 与实时用量 (usage),
后端按阈值评估 status (正常/预警/超限), 供前端资源用量明细与超阈值预警使用。
"""
from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, String, Text, Float

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), default="")                       # 租户名称 (公司)
    code = Column(String(32), index=True, default="")            # TH-xx 编码
    contact = Column(String(64), default="")                     # 联系人
    phone = Column(String(32), default="")                       # 联系电话
    industry = Column(String(64), default="")                    # 行业
    contractNo = Column(String(64), default="")                  # 合同编号
    validFrom = Column(String(16), default="")                   # 合同起始 YYYY-MM-DD
    validTo = Column(String(16), default="")                     # 合同到期 YYYY-MM-DD
    status = Column(String(32), default="active")                # active/pending/expired
    rent = Column(Float, default=0)                              # 月租金 (元)
    cabinets = Column(Integer, default=0)                        # 已承租机柜数
    # ---- 深化设计: 配额 (容量上限) ----
    quotaCabinets = Column(Integer, default=0)                   # 机柜配额
    quotaDevices = Column(Integer, default=0)                    # 设备配额
    quotaPowerKw = Column(Float, default=0)                      # 功耗配额 (kW)
    quotaBandwidthMbps = Column(Integer, default=0)              # 带宽配额 (Mbps)
    # ---- 深化设计: 实时用量 (由采集/台账聚合, 无数据时回退默认值) ----
    usedDevices = Column(Integer, default=0)                     # 在用设备数
    usedPowerKw = Column(Float, default=0)                       # 实时功耗 (kW)
    usedBandwidthMbps = Column(Integer, default=0)               # 实时带宽 (Mbps)
    uOccupied = Column(Integer, default=0)                       # 已用 U 位
    note = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
