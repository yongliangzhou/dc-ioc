"""数据中心 (IDC) Pydantic Schema (phase: datacenter)。

与前端数据中心管理/切换/对比一致:
- 列表/详情返回 camelCase 字段, is_current 标识当前默认中心。
- compare 返回各中心电力/制冷/机柜/告警的并排对比指标。
- alarms 返回跨中心统一告警汇总。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class IdcBase(BaseModel):
    code: str = Field(..., max_length=32, description="站点编码 如 EC1-HZ (唯一)")
    name: str = Field(..., max_length=128, description="数据中心名称")
    region: str = Field("", max_length=64, description="地域/可用区")
    address: str = Field("", max_length=255, description="地址")
    power_capacity_mw: float = Field(0, description="电力容量 MW")
    cooling_capacity_mw: float = Field(0, description="制冷容量 MW")
    rack_capacity: int = Field(0, description="机柜总容量")
    rooms: int = Field(0, description="包间数量")
    status: str = Field("运营", max_length=16, description="运营/建设/下线")
    capacity_kw: int = Field(0, description="机柜额定功率 kW (单体)")
    description: str = Field("", max_length=512, description="站点说明")


class IdcCreate(IdcBase):
    pass


class IdcUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    power_capacity_mw: Optional[float] = None
    cooling_capacity_mw: Optional[float] = None
    rack_capacity: Optional[int] = None
    rooms: Optional[int] = None
    status: Optional[str] = None
    capacity_kw: Optional[int] = None
    description: Optional[str] = None


class IdcOut(IdcBase):
    id: int
    is_current: bool = False
    created_at: str = ""
    updated_at: str = ""


class IdcCompareMetric(BaseModel):
    """单个中心的对比指标行。"""
    id: int
    code: str
    name: str
    region: str
    status: str
    power_capacity_mw: float
    cooling_capacity_mw: float
    rack_capacity: int
    rack_used: int = 0
    device_count: int = 0
    online_count: int = 0
    active_alarm_count: int = 0


class IdcCompareOut(BaseModel):
    centers: list[IdcCompareMetric] = Field(default_factory=list)
    current_idc_id: Optional[int] = None


class IdcAlarmItem(BaseModel):
    idc_id: int
    idc_name: str
    idc_code: str
    alarm_id: Optional[str] = None
    device_id: Optional[str] = None
    category: Optional[str] = None
    metric_name: Optional[str] = None
    level: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    desc: Optional[str] = None
    state: Optional[str] = None
    ts: Optional[float] = None


class IdcAlarmsOut(BaseModel):
    total: int
    items: list[IdcAlarmItem] = Field(default_factory=list)
    by_idc: dict[int, int] = Field(default_factory=dict)
