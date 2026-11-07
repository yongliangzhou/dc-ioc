"""阶段三 DTO: IPAM / 自动发现 / 采购盘点 / 自定义字段。"""
from __future__ import annotations

import ipaddress
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

FieldType = Literal["text", "number", "date", "select"]
RowStatus = Literal["allocated", "reserved", "available"]


class VlanIn(BaseModel):
    vlan_id: int = Field(ge=1, le=4094)
    name: str = ""
    site: str = ""
    description: str = ""


class SubnetIn(BaseModel):
    cidr: str = Field(min_length=7, max_length=64)
    vlan_id: int | None = None
    gateway: str = ""
    description: str = ""

    @field_validator("cidr")
    @classmethod
    def valid_network(cls, v: str) -> str:
        try:
            net = ipaddress.ip_network(v, strict=True)
        except ValueError as exc:
            raise ValueError(f"非法 CIDR: {v}") from exc
        return str(net)


class AddressIn(BaseModel):
    address: str = Field(min_length=7, max_length=64)
    subnet_id: int | None = None
    status: RowStatus = "allocated"
    device_ci: str = ""
    note: str = ""

    @field_validator("address")
    @classmethod
    def valid_ip(cls, v: str) -> str:
        try:
            return str(ipaddress.ip_address(v.split("/")[0]))
        except ValueError as exc:
            raise ValueError(f"非法 IP: {v}") from exc


class ScanIn(BaseModel):
    cidr: str = Field(default="192.168.1.0/30", max_length=64)
    ports: list[int] = Field(default_factory=lambda: [22, 80, 443, 161, 8080])
    concurrency: int = Field(default=50, ge=1, le=50)

    @field_validator("ports")
    @classmethod
    def valid_ports(cls, v: list[int]) -> list[int]:
        if len(v) > 20 or any(p < 1 or p > 65535 for p in v):
            raise ValueError("端口数量 ≤ 20 且范围 1-65535")
        return v


class CandidateDecision(BaseModel):
    matched_ci: str = ""


class OrderIn(BaseModel):
    order_no: str = Field(min_length=1, max_length=64)
    vendor: str = ""
    category: str = ""
    quantity: int = Field(default=1, ge=1)
    amount: float = Field(default=0, ge=0)
    purchase_date: str = ""
    warranty_until: str = ""
    contract_no: str = ""
    status: str = "active"
    note: str = ""


class TaskIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scope: str = ""
    status: str = "open"


class ItemIn(BaseModel):
    asset_ci: str = Field(min_length=1, max_length=128)
    expected_location: str = ""
    result: Literal["matched", "missing", "unexpected"] = "matched"
    confirmed_by: str = ""


class CustomFieldIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label_zh: str = Field(min_length=1, max_length=128)
    label_en: str = ""
    type: FieldType = "text"
    options: list[str] = Field(default_factory=list)
    required: bool = False
    applies_to: str = "*"

    @field_validator("key")
    @classmethod
    def valid_key(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", v):
            raise ValueError("key 必须是小写字母开头的 snake_case 标识符")
        return v

    @field_validator("options")
    @classmethod
    def select_needs_options(cls, v: list[str], info) -> list[str]:
        if info.data.get("type") == "select" and not v:
            raise ValueError("select 类型必须提供 options")
        return v


class CustomValuesIn(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
