"""业务域 DTO: 统一设备台账 / 告警 / 通用查询/响应。

与 ORM 模型 (Equipment / Alarm) 字段对齐; 业务域聚合接口 (hvac/power/security/ops)
直接返回 services.dc_ioc_data 生成的 dict 结构 (与 dc-ioc data.js 一致), 无需额外 Schema。
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------- 设备台账 ----------
class EquipmentOut(BaseModel):
    """统一设备台账响应 (对齐 models.equipment.Equipment)。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    idc_id: int
    room_id: Optional[int] = None
    code: str
    name: str = ""
    domain: str
    category: str
    vendor: str = ""
    model: str = ""
    status: str = "运行"
    load_pct: float = 0
    run_hours: int = 0
    redundancy: str = ""
    attrs: dict = {}


class EquipmentPage(BaseModel):
    """设备台账分页响应。"""
    items: List[EquipmentOut]
    total: int
    page: int
    page_size: int


class EquipmentMetricPoint(BaseModel):
    ts: str
    value: float


class EquipmentMetrics(BaseModel):
    equipment_id: int
    code: str
    range_minutes: int
    metrics: List[str]                      # 本次返回的测点名列表
    series: dict[str, List[EquipmentMetricPoint]]   # metric -> points


# ---------- 告警 ----------
class AlarmOut(BaseModel):
    """告警响应 (对齐 models.alarm.Alarm)。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: str
    level: str
    system: str
    domain: str = ""
    category: str = ""
    code: str = ""
    desc: str = ""
    state: str = "处理中"
    owner: str = ""
    value: float = 0
    unit: str = ""
    ack: bool = False
    rule: str = ""


# ---------- 通用查询参数 ----------
class EquipmentFilter(BaseModel):
    domain: Optional[str] = None
    category: Optional[str] = None
    room: Optional[str] = None       # 包间编码 R01
    status: Optional[str] = None
