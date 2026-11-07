"""阶段三数据模型 (IPAM / 自动发现 / 采购盘点 / 自定义字段)。

按层合并到一个模块, 但仍保持 endpoints → crud → models 的单向依赖:
- ip_vlan / ip_subnet / ip_address          : IPAM
- discovery_candidate                       : 自动发现「待确认区」
- purchase_order / stocktake_task / stocktake_item : 资产商务与实盘
- custom_field_def                          : 动态设备字段定义 (值存 equipment.custom_attributes)

全部使用通用列类型 (PG / SQLite 均可建表), 全部预留可空 tenant_id 供阶段四隔离。
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, JSON, String, Text, func

from app.db.session import Base


class IpVlan(Base):
    __tablename__ = "ip_vlan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vlan_id = Column(Integer, nullable=False, unique=True, index=True)
    name = Column(String(128), default="")
    site = Column(String(64), default="")
    description = Column(Text, default="")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IpSubnet(Base):
    __tablename__ = "ip_subnet"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidr = Column(String(64), nullable=False, unique=True, index=True)
    vlan_id = Column(Integer, nullable=True, index=True)
    gateway = Column(String(64), default="")
    description = Column(Text, default="")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IpAddress(Base):
    __tablename__ = "ip_address"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(64), nullable=False, unique=True, index=True)
    subnet_id = Column(Integer, nullable=True, index=True)
    status = Column(String(16), nullable=False, default="allocated")  # allocated/reserved/available
    device_ci = Column(String(128), default="")
    note = Column(Text, default="")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DiscoveryCandidate(Base):
    __tablename__ = "discovery_candidate"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(64), nullable=False, unique=True, index=True)
    hostname = Column(String(128), default="")
    mac = Column(String(64), default="")
    open_ports = Column(JSON, default=list)
    source = Column(String(32), default="tcp-probe")
    status = Column(String(16), nullable=False, default="pending")  # pending/confirmed/rejected
    first_seen = Column(String(32), default="")
    last_seen = Column(String(32), default="")
    matched_ci = Column(String(128), default="")
    tenant_id = Column(Integer, nullable=True, index=True)

    __table_args__ = (Index("ix_discovery_status", "status", "last_seen"),)


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(64), nullable=False, unique=True, index=True)
    vendor = Column(String(128), default="")
    category = Column(String(64), default="")
    quantity = Column(Integer, default=1)
    amount = Column(Float, default=0)
    purchase_date = Column(String(16), default="")
    warranty_until = Column(String(16), default="", index=True)
    contract_no = Column(String(64), default="")
    status = Column(String(16), default="active")
    note = Column(Text, default="")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StocktakeTask(Base):
    __tablename__ = "stocktake_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    scope = Column(String(128), default="")
    status = Column(String(16), default="open")  # open/closed
    created_by = Column(String(64), default="system")
    started_at = Column(String(32), default="")
    finished_at = Column(String(32), default="")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StocktakeItem(Base):
    __tablename__ = "stocktake_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    asset_ci = Column(String(128), nullable=False)
    expected_location = Column(String(128), default="")
    result = Column(String(16), default="matched")  # matched/missing/unexpected
    confirmed_by = Column(String(64), default="")
    confirmed_at = Column(String(32), default="")
    tenant_id = Column(Integer, nullable=True, index=True)

    __table_args__ = (Index("ix_stocktake_item_task_ci", "task_id", "asset_ci"),)


class CustomFieldDef(Base):
    __tablename__ = "custom_field_def"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False, unique=True, index=True)
    label_zh = Column(String(128), nullable=False)
    label_en = Column(String(128), default="")
    type = Column(String(16), nullable=False, default="text")  # text/number/date/select
    options = Column(JSON, default=list)
    required = Column(Boolean, default=False)
    applies_to = Column(String(64), default="*")
    tenant_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
