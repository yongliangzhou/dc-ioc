"""驾驶舱 / 机柜 / 指标 DTO。"""
from typing import Dict, List, Generic, Optional, TypeVar

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


class DomainOnline(BaseModel):
    """单业务域在线统计 (由后端按设备 domain 前缀聚合真实注册设备)。"""

    online: int = 0
    total: int = 0
    rate: float = 0.0  # 在线率 0-100


class KpiTrendPoint(BaseModel):
    """单条 campus KPI 快照 (来自 kpi_history 时序表)。"""

    ts: Optional[str] = None
    pue: float = 0.0
    wue: float = 0.0
    it_load_mw: float = 0.0
    total_load_mw: float = 0.0
    cool_load_mw: float = 0.0
    online_rate: float = 0.0
    availability: float = 0.0


class KpiTrendsResponse(BaseModel):
    hours: int = 48
    points: List[KpiTrendPoint] = []
    source: str = "kpi_history"


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
    # 分业务域在线率 (根治 overview 前端 ±1 派生): hvac / power / security 三域
    # 真实聚合各自注册设备的在线数; 无设备注册的域不出现在此 dict 中 (前端回退派生)
    domain_online: Optional[Dict[str, DomainOnline]] = None


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
