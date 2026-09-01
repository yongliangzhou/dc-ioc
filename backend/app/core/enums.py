"""枚举单一事实源 (数据库设计文档 第八章 8.4 枚举/CHECK)。

- 稳定低基数枚举: 用于生成 DB CHECK 约束 (值集对齐现有种子数据, 不破坏历史行)
- 增长型枚举 (equipment/external_devices 的 domain/category 等): 仅作应用层字典,
  不施加 DB CHECK, 避免未来新增类别被约束拒绝 (由应用层 Pydantic 校验约束)。

约束值集以开发库实际取值为准 (探查得到), 新增合法值请同步更新此处。
"""
from __future__ import annotations

# ============ 稳定低基数枚举 (生成 DB CHECK) ============
TICKET_STATE = ("open", "doing", "pending", "done", "closed")
WORKFLOW_STATUS = ("new", "progress", "approval", "rejected", "closed")
WORKFLOW_PRIORITY = ("P1", "P2", "P3", "P4")
WORKFLOW_TYPE = ("incident", "problem", "change", "risk")
KNOWLEDGE_REVIEW_STATUS = ("pending", "approved", "rejected")
KNOWLEDGE_TYPE = ("sop", "drawing", "manual", "emergency", "case", "training")
MAINTENANCE_FREQUENCY = ("daily", "weekly", "monthly", "quarterly", "yearly")
MAINTENANCE_STATUS = ("active", "paused", "done")
RISK_CLOSED = (0, 1)  # 0/1 整型
RISK_LEVEL = ("高", "中", "低")
DRILL_STATE = ("计划中", "已编排", "已完成")
DRILL_TYPE = ("电力", "暖通", "消防", "安防")
DRILL_RESULT = ("通过", "未通过", "—")
INSPECTION_ROUTE_STATE = ("active", "进行中", "已完成")
INSPECTION_FINDING_LV = ("info", "warn", "crit")
ALARM_LEVEL = ("info", "warn", "crit")  # 对齐代码实际写入 (告警引擎/指标服务)
ALARM_STATE = ("active", "acknowledged", "resolved", "suppressed")  # 对齐 alarm.py 实际状态机
EQUIPMENT_STATUS = ("运行", "待机", "检修", "故障", "离线")  # 对齐模型默认 "运行" 与 dc_aggregator
TENANT_STATUS = ("active", "pending", "expired")
THING_MODEL_ITEM_TYPE = ("property", "service", "event")
IDC_STATUS = ("运营", "建设", "下线")  # 机房生命周期态 (设计文档 8.4 附录基线)
ROOM_KIND = (
    "it_room", "substation", "battery_room", "chiller_station",
    "carrier_room", "ups_room", "noc",
)  # 房间类型 (稳定低基数, 设计文档 8.4 附录基线)

# (table, column, values, is_text) -> 生成 CHECK 约束
CHECK_SPECS: list[tuple[str, str, tuple, bool]] = [
    ("ticket", "state", TICKET_STATE, True),
    ("workflow_item", "status", WORKFLOW_STATUS, True),
    ("workflow_item", "priority", WORKFLOW_PRIORITY, True),
    ("workflow_item", "type", WORKFLOW_TYPE, True),
    ("knowledge_item", "review_status", KNOWLEDGE_REVIEW_STATUS, True),
    ("knowledge_item", "type", KNOWLEDGE_TYPE, True),
    ("maintenance_plan", "frequency", MAINTENANCE_FREQUENCY, True),
    ("maintenance_plan", "status", MAINTENANCE_STATUS, True),
    ("risk_item", "closed", RISK_CLOSED, False),
    ("risk_item", "level", RISK_LEVEL, True),
    ("drill_plan", "state", DRILL_STATE, True),
    ("drill_plan", "type", DRILL_TYPE, True),
    ("drill_plan", "result", DRILL_RESULT, True),
    ("inspection_route", "state", INSPECTION_ROUTE_STATE, True),
    ("inspection_finding", "lv", INSPECTION_FINDING_LV, True),
    ("alarm_event", "lv", ALARM_LEVEL, True),
    ("alarm_event", "state", ALARM_STATE, True),
    ("equipment", "status", EQUIPMENT_STATUS, True),
    ("tenant", "status", TENANT_STATUS, True),
    ("thing_model_item", "item_type", THING_MODEL_ITEM_TYPE, True),
    ("idc", "status", IDC_STATUS, True),
    ("room", "kind", ROOM_KIND, True),
]


def _in_sql(column: str, values: tuple, is_text: bool) -> str:
    if is_text:
        items = ", ".join(f"'{v}'" for v in values)
    else:
        items = ", ".join(str(v) for v in values)
    return f"{column} IN ({items})"


def constraint_name(table: str, column: str) -> str:
    return f"ck_{table}_{column}"


def check_condition(table: str, column: str) -> str:
    for _t, _c, vals, is_text in CHECK_SPECS:
        if _t == table and _c == column:
            return _in_sql(column, vals, is_text)
    raise KeyError(f"no CHECK spec for {table}.{column}")


# ============ 增长型枚举 (应用层字典, 不生成 DB CHECK) ============
EQUIPMENT_DOMAIN = (
    "hvac_source", "hvac_terminal", "power_hv", "power_lv", "power_batt",
    "power_genset", "power_fuel", "power_ups", "sec_acs", "sec_cctv",
    "sec_fire", "sec_ids", "security_cctv", "water",
)
EQUIPMENT_CATEGORY = (
    "ups", "battery", "rectifier", "pdu", "distribution", "meter",
    "transformer", "genset", "day_tank", "fuel_tank", "fuel_pump",
    "ac", "ahu", "crac", "chw_pump", "cw_pump", "cooling_tower",
    "heat_exchanger", "humidifier", "fau", "fan", "pump",
    "pressure", "temp", "humidity", "smoke_detector", "heat_detector",
    "vesda", "leak", "valve", "storage_tank", "hv_incomer", "hv_feeder",
    "hvdc", "bus_tie", "ats", "door_ctrl", "camera", "perimeter", "other",
)
EXTERNAL_DEVICE_CATEGORY = (
    "ambient", "ats", "battery_group", "bus_tie", "camera", "chiller",
    "chw_pump", "cooling_tower", "crac", "cw_pump", "day_tank", "door_ctrl",
    "fau", "fuel_pump", "fuel_tank", "genset", "heat_detector",
    "heat_exchanger", "humidifier", "hv_feeder", "hv_incomer", "hvdc",
    "leak", "perimeter", "sec_pump", "smoke_detector", "storage_tank",
    "transformer", "ups", "valve", "vesda",
)
EXTERNAL_DEVICE_DOMAIN = (
    "hvac_source", "hvac_terminal", "power_batt", "power_fuel",
    "power_genset", "power_hv", "power_lv", "sec_acs", "sec_cctv",
    "sec_fire", "sec_ids", "security_cctv",
)
