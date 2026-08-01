"""物模型配置 —— 设备类别 / 测点中文说明的单一事实来源 (配置化)。

- 内置默认映射覆盖全业务域 (暖通 / 电力 / 安防消防), 键名与 mock_collector._CATEGORY_METRICS
  的类别键、各设备类别的测点名严格对齐, 保证 list_thing_models 输出完整中文名 / 业务域 / 协议。
- 支持从外部 JSON 文件覆盖 / 扩展 (通过 settings.THING_MODELS_FILE 指定路径),
  无需改代码即可新增设备类别 / 测点说明。覆盖文件格式示例见 deploy/thing_models.example.json。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("thing_models")

# 类别中文名 + 业务域 + 推荐协议: category -> (label, domain, protocol)
# 键名必须与 collectors/mock_collector.py 的 _CATEGORY_METRICS 严格一致。
CATEGORY_META: dict[str, tuple[str, str, str]] = {
    "chiller": ("冷水机组", "hvac_source", "modbus"),
    "cooling_tower": ("冷却塔", "hvac_source", "modbus"),
    "chw_pump": ("冷冻水泵", "hvac_source", "modbus"),
    "cw_pump": ("冷却水泵", "hvac_source", "modbus"),
    "heat_exchanger": ("板式换热器", "hvac_source", "modbus"),
    "valve": ("电动阀门", "hvac_source", "modbus"),
    "sec_pump": ("二次冷冻水泵", "hvac_source", "modbus"),
    "storage_tank": ("蓄冷罐", "hvac_source", "modbus"),
    "ambient": ("室内外温湿度", "hvac_source", "snmp"),
    "crac": ("精密空调", "hvac_terminal", "snmp"),
    "fau": ("新风机组", "hvac_terminal", "snmp"),
    "humidifier": ("加湿器", "hvac_terminal", "snmp"),
    "hv_incomer": ("中压进线柜", "power_hv", "modbus"),
    "hv_feeder": ("中压馈线柜", "power_hv", "modbus"),
    "bus_tie": ("母联柜", "power_hv", "modbus"),
    "transformer": ("变压器", "power_lv", "modbus"),
    "ups": ("UPS 电源", "power_lv", "snmp"),
    "hvdc": ("高压直流", "power_lv", "modbus"),
    "ats": ("ATS 双电源", "power_lv", "modbus"),
    "genset": ("柴油发电机", "power_genset", "modbus"),
    "fuel_tank": ("主油箱", "power_fuel", "modbus"),
    "day_tank": ("日用油箱", "power_fuel", "modbus"),
    "fuel_pump": ("供油泵", "power_fuel", "modbus"),
    "battery_group": ("电池组", "power_battery", "snmp"),
    "camera": ("摄像机", "security_cctv", "snmp"),
    "door_ctrl": ("门禁控制器", "security_acs", "snmp"),
    "perimeter": ("周界探测器", "security_ids", "snmp"),
    "smoke_detector": ("烟感探测器", "security_fire", "modbus"),
    "heat_detector": ("温感探测器", "security_fire", "modbus"),
    "vesda": ("极早期烟感 (VESDA)", "security_fire", "modbus"),
}

# 测点名中文说明映射 (覆盖所有设备类别约 110+ 测点)
METRIC_LABELS: dict[str, str] = {
    # ---- 温湿度 / 温度类 ----
    "supply_temp": "送风温度",
    "return_temp": "回风温度",
    "inlet_temp": "进风温度",
    "outlet_temp": "出风温度",
    "evap_temp": "蒸发温度",
    "cond_temp": "冷凝温度",
    "water_temp_in": "进水温度",
    "water_temp_out": "出水温度",
    "pri_in_temp": "一次侧进水温度",
    "pri_out_temp": "一次侧出水温度",
    "sec_in_temp": "二次侧进水温度",
    "sec_out_temp": "二次侧出水温度",
    "out_temp": "室外温度",
    "supply_water_temp": "供水温度",
    "return_water_temp": "回水温度",
    "oil_temp": "油温",
    "winding_temp": "绕组温度",
    "exhaust_temp": "排气温度",
    "water_temp": "水温",
    "max_temp": "最高温度",
    "min_temp": "最低温度",
    "ambient_temp": "环境温度",
    "temp": "温度",
    "cop_est": "估算 COP",
    "compressor_freq": "压缩机频率",
    "evap_pressure": "蒸发压力",
    "cond_pressure": "冷凝压力",
    "setpoint_supply": "供水设定",
    "load_ratio": "负载比",
    "fan_freq": "风机频率",
    "pump_hz": "水泵频率",
    "pump_kw": "水泵功率",
    "hex_eff": "换热效率",
    "primary_in": "一次侧进水",
    "primary_out": "一次侧出水",
    "secondary_in": "二次侧进水",
    "secondary_out": "二次侧出水",
    "valve_state": "阀门状态",
    "fan": "风机转速",
    "valve": "阀门开度",
    "u_in": "输入电压",
    "u_out": "输出电压",
    "module_n": "模块总数",
    "module_run": "运行模块数",
    "rpm": "转速",
    "tank_level": "液位",
    "tank_temp": "油温",
    "leak": "渗漏状态",
    "online": "在线状态",
    "unit_state": "设备状态",
    "run_state": "运行状态",
    # ---- 湿度 ----
    "supply_humidity": "送风湿度",
    "return_humidity": "回风湿度",
    "humidity": "湿度",
    # ---- 压力 / 压差 ----
    "chw_pressure": "冷冻水压力",
    "outlet_pressure": "出口压力",
    "oil_pressure": "机油压力",
    "pressure_diff": "压差",
    "filter_dp": "滤网压差",
    "room_dp": "室内外压差",
    # ---- 流量 ----
    "chw_flow_rate": "冷冻水流量",
    "flow_rate": "流量",
    # ---- 功率 / 电参量 ----
    "power_kw": "功耗",
    "active_power": "有功功率",
    "reactive_power": "无功功率",
    "output_power": "输出功率",
    "energy": "电度",
    "energy_kwh": "累计电量",
    "pf": "功率因数",
    "freq": "频率",
    "output_freq": "输出频率",
    "voltage": "电压",
    "voltage_ab": "AB线电压",
    "voltage_bc": "BC线电压",
    "voltage_ca": "CA线电压",
    "voltage_in": "高压侧电压",
    "voltage_out": "低压侧电压",
    "input_voltage": "输入电压",
    "output_voltage": "输出电压",
    "source1_voltage": "主用侧电压",
    "source2_voltage": "备用侧电压",
    "current": "电流",
    "current_a": "A相电流",
    "current_b": "B相电流",
    "current_c": "C相电流",
    "output_current": "输出电流",
    "battery_voltage": "电池电压",
    "battery_current": "电池电流",
    "motor_current": "电机电流",
    # ---- 运行参数 ----
    "cop": "能效比 COP",
    "load_pct": "负载率",
    "efficiency": "换热效率",
    "approach_temp": "逼近温度",
    "fan_hz": "风机频率",
    "fan_speed": "风机转速",
    "freq_hz": "运行频率",
    "guide_vane_pos": "导叶开度",
    "valve_pos": "阀门开度",
    "water_valve_pos": "水阀开度",
    "position_pct": "开度",
    "speed": "转速",
    "airflow": "气流",
    "run_hours": "运行小时数",
    "running_hours": "运行时间",
    "start_count": "启动次数",
    # ---- 状态 / 模式 ----
    "run_status": "运行状态",
    "fan_status": "风机状态",
    "filter_status": "滤网状态",
    "valve_status": "阀门状态",
    "switch_state": "开关状态",
    "state": "状态",
    "g_status": "并机状态",
    "run_mode": "运行模式",
    "mode": "工作模式",
    "online_status": "在线状态",
    "system_status": "系统状态",
    "interlock_ok": "互锁状态",
    # ---- 液位 / 油位 ----
    "water_level": "水位",
    "fuel_level": "油位",
    "level_cm": "液位(cm)",
    "level_pct": "液位(%)",
    # ---- 燃油子系统 ----
    "leak_alarm": "漏油报警",
    "emergency_valve": "紧急切断阀",
    "supply_valve_a": "补油阀A",
    "supply_valve_b": "补油阀B",
    "drain_valve": "泄油阀",
    # ---- 电池 ----
    "soc": "电池 SOC",
    "battery_temp": "电池温度",
    "single_voltage_min": "单体电压(最小)",
    "single_voltage_max": "单体电压(最大)",
    "internal_resistance": "内阻",
    "cell_count": "单体数量",
    # ---- HVDC ----
    "module_running": "运行模块数",
    "module_offline": "离线模块数",
    "module_total": "模块总数",
    # ---- 视频 ----
    "online_count": "在线数量",
    "offline_count": "离线数量",
    "storage_usage": "存储使用率",
    "bitrate": "码流速率",
    # ---- 门禁 ----
    "door_count": "门数",
    "today_events": "今日刷卡次数",
    "forced_alarm": "强行开门报警",
    "timeout_alarm": "超时未关报警",
    "lock_state": "门锁状态",
    # ---- 入侵 / 周界 ----
    "armed": "布防状态",
    "alarm_count": "告警数量",
    "zones": "防区数量",
    # ---- 消防 ----
    "total_count": "总数",
    "fault_count": "故障数量",
    "alarm_stage": "报警级别",
    # ---- 通用 ----
    "level": "浓度",
    "value": "测量值",
    "co2": "CO2 浓度",
    # ---- 冷源系统补充测点 ----
    "sec_flow_rate": "二次冷冻水流量",
    "sec_pressure": "二次冷冻水压力",
    "top_temp": "蓄冷罐上部水温",
    "bottom_temp": "蓄冷罐下部水温",
    "storage_mode": "蓄冷模式",
    "storage_power": "蓄放冷功率",
    "outdoor_temp": "室外干球温度",
    "wet_bulb": "室外湿球温度",
    "outdoor_rh": "室外相对湿度",
    "indoor_temp": "室内温度",
    "indoor_rh": "室内相对湿度",
    "status": "运行状态",
    # ---- 定位式漏水检测 ----
    "leak_status": "漏水状态",
    "leak_position": "漏点定位距离",
    "cable_length": "线缆总长",
    "cable_status": "线缆状态",
    "zone": "区域编号",
}


def load_overrides(path: Optional[str] = None) -> None:
    """从 JSON 文件加载类别 / 测点说明的覆盖 (不传 path 或文件不存在则跳过)。

    JSON 结构:
      {
        "category_meta": { "<category>": ["中文名", "业务域", "协议"], ... },
        "metric_labels": { "<metric_name>": "中文说明", ... }
      }
    """
    path = path or settings.THING_MODELS_FILE
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.warning("加载物模型覆盖文件失败 (%s): %s", path, e)
        return
    cat = data.get("category_meta")
    if isinstance(cat, dict):
        for k, v in cat.items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                CATEGORY_META[str(k)] = (str(v[0]), str(v[1]), str(v[2]))
    labels = data.get("metric_labels")
    if isinstance(labels, dict):
        for k, v in labels.items():
            METRIC_LABELS[str(k)] = str(v)
    logger.info("已加载物模型覆盖文件: %s (类别 %d, 测点 %d)", path, len(cat or {}), len(labels or {}))


# 应用启动时加载一次外部覆盖 (如配置了 THING_MODELS_FILE)
load_overrides()
