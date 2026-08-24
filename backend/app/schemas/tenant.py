"""租户 Pydantic Schema (阶段三 A · 资源运营-租户管理)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    name: str
    code: Optional[str] = None
    contact: str = ""
    phone: str = ""
    industry: str = ""
    contractNo: str = ""
    validFrom: str = ""
    validTo: str = ""
    status: str = "active"
    rent: float = 0
    cabinets: int = 0
    quotaCabinets: int = 0
    quotaDevices: int = 0
    quotaPowerKw: float = 0
    quotaBandwidthMbps: int = 0
    usedDevices: int = 0
    usedPowerKw: float = 0
    usedBandwidthMbps: int = 0
    uOccupied: int = 0
    note: str = ""


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    code: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    contractNo: Optional[str] = None
    validFrom: Optional[str] = None
    validTo: Optional[str] = None
    status: Optional[str] = None
    rent: Optional[float] = None
    cabinets: Optional[int] = None
    quotaCabinets: Optional[int] = None
    quotaDevices: Optional[int] = None
    quotaPowerKw: Optional[float] = None
    quotaBandwidthMbps: Optional[int] = None
    usedDevices: Optional[int] = None
    usedPowerKw: Optional[float] = None
    usedBandwidthMbps: Optional[int] = None
    uOccupied: Optional[int] = None
    note: Optional[str] = None
