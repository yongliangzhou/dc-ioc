"""驾驶舱 / 机柜 / 指标 DTO。"""
from typing import List, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# ---------- 分页通用 ----------
class Paginated(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: List[T]


# ---------- 驾驶舱总览 ----------
class AlarmCount(BaseModel):
    crit: int = 0
    warn: int = 0
    info: int = 0


class DashboardOverview(BaseModel):
    total_devices: int
    online_devices: int
    online_rate: float            # 在线率 0-100
    today_alarms: int
    pue: float
    # 扩展指标 (与 dc-ioc data.js kpi 对齐, 前端可选展示)
    wue: float = 0.0
    it_load_mw: float = 0.0
    total_load_mw: float = 0.0
    cool_load_mw: float = 0.0
    availability: float = 99.999
    free_cool_hours: int = 0
    alarms: AlarmCount = AlarmCount()


# ---------- 机柜 ----------
class CabinetItem(BaseModel):
    id: int
    idc_id: int
    code: str
    room: str
    row: str = ""
    u_total: int
    u_used: int
    rated_power_kw: float
    current_power_kw: float
    status: str


# ---------- 机柜时序指标 ----------
class MetricPoint(BaseModel):
    ts: str        # ISO8601
    value: float


class CabinetMetrics(BaseModel):
    cabinet_id: int
    code: str
    range_minutes: int
    temperature: List[MetricPoint]
    humidity: List[MetricPoint]
    power_kw: List[MetricPoint]


# ---------- 多 DC 聚合 ----------
class DCCampus(BaseModel):
    id: str
    name: str
    short_name: str
    region: str
    city: str
    status: str
    total_devices: int
    online_devices: int
    online_rate: float
    pue: float
    wue: float = 0.0
    it_load_mw: float
    total_load_mw: float
    today_alarms: int
    availability: float = 99.999
    alerts_crit: int = 0
    alerts_warn: int = 0


class CampusesResponse(BaseModel):
    campuses: List[DCCampus]


class ComparisonItem(BaseModel):
    metric: str
    label: str
    unit: str
    data: list
    best: str
    worst: str


class CampusComparisonResponse(BaseModel):
    comparisons: List[ComparisonItem]
