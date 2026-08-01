"""MockCollectorService v2 — 覆盖全业务域的模拟采集器 HTTP 客户端。

设计原则:
- **绝不直接写数据库**。只作为「采集器」, 严格按 API_CONTRACT.md v1 契约,
  通过真实 HTTP 向运行中的系统推送数据 (默认 http://127.0.0.1:8000)。
- 后端如何落库 (DB / Kafka / 内存兜底) 对它完全透明。
- 启动时注册 ~80 台设备覆盖全部业务域 (暖通/电力/安防消防),
  每 5 秒按类别推送相应语义化测点，带质量码 (5% uncertain, 1% bad)。
- 生产环境: 设置 EXTERNAL_MOCK_COLLECTOR_ENABLED=false 关闭;
  真实采集器只需按相同契约推送同名设备即可，业务端点零改动。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger("external.mock_collector")

# ---- 规模与节奏 ----
PUSH_INTERVAL_SEC = 5

# 质量码池: 约 5% uncertain + 1% bad, 其余 good (按条随机)
_QUALITY_POOL = ["good"] * 94 + ["uncertain"] * 5 + ["bad"] * 1

# ======================================================================
#  全业务域设备定义: (category, domain, model, vendor, metric_list)
#  metric_list: [(metric_name, unit, min_val, max_val), ...]
# ======================================================================
_CATEGORY_METRICS = {
    # ===== 暖通·冷源 (hvac_source) — 参照手册: 冷水机组/冷却塔/水泵/板换/阀门/蓄冷罐 =====
    "chiller": [  # 水冷冷水机组: 冷冻水供回 18/24℃, 蒸发/冷凝/导叶/油温/电机电流
        ("supply_temp", "℃", 6.5, 9.5),
        ("return_temp", "℃", 11.0, 16.0),
        ("power_kw", "kW", 250.0, 500.0),
        ("evap_temp", "℃", 5.0, 8.0),
        ("cond_temp", "℃", 25.0, 35.0),
        ("cop", "", 5.5, 7.0),
        ("load_pct", "%", 40.0, 90.0),
        ("chw_flow_rate", "m³/h", 280.0, 520.0),
        ("chw_pressure", "MPa", 0.15, 0.35),
        ("oil_temp", "℃", 38.0, 55.0),
        ("motor_current", "A", 180.0, 320.0),
        ("guide_vane_pos", "%", 30.0, 90.0),
        ("run_status", "", 0, 4),  # 0=停机 1=启动中 2=运行 3=卸载中 4=故障
    ],
    "cooling_tower": [  # 变频冷却塔: 5.5℃温差, 风机频率/水位/逼近温度
        ("out_temp", "℃", 15.0, 28.0),
        ("fan_hz", "Hz", 25.0, 50.0),
        ("water_temp_in", "℃", 28.0, 35.0),
        ("water_temp_out", "℃", 25.0, 30.0),
        ("approach_temp", "℃", 3.0, 6.0),
        ("water_level", "m", 0.6, 1.2),
        ("fan_status", "", 0, 2),  # 0=停机 1=工频 2=变频
    ],
    "chw_pump": [  # 变频冷冻水泵 (一次泵): 流量/功耗/频率/出口压力
        ("flow_rate", "m³/h", 400.0, 800.0),
        ("power_kw", "kW", 40.0, 70.0),
        ("freq_hz", "Hz", 30.0, 50.0),
        ("outlet_pressure", "MPa", 0.25, 0.45),
        ("run_status", "", 0, 2),  # 0=停机 1=运行 2=故障
    ],
    "cw_pump": [  # 变频冷却水泵: 流量/功耗/频率/出口压力
        ("flow_rate", "m³/h", 500.0, 900.0),
        ("power_kw", "kW", 55.0, 90.0),
        ("freq_hz", "Hz", 35.0, 50.0),
        ("outlet_pressure", "MPa", 0.20, 0.40),
        ("run_status", "", 0, 2),
    ],
    "heat_exchanger": [  # 板式换热器: 换热温差 1.5℃, 一次/二次侧温度
        ("efficiency", "%", 85.0, 96.0),
        ("pri_in_temp", "℃", 14.0, 19.0),
        ("pri_out_temp", "℃", 12.0, 16.0),
        ("sec_in_temp", "℃", 11.0, 15.0),
        ("sec_out_temp", "℃", 14.0, 18.0),
        ("approach_temp", "℃", 1.0, 2.0),
    ],
    "valve": [  # 电动开关/调节阀: 开度/流量/阀位状态
        ("position_pct", "%", 0.0, 100.0),
        ("flow_rate", "m³/h", 0.0, 300.0),
        ("valve_status", "", 0, 3),  # 0=关到位 1=开到位 2=调节中 3=故障
    ],
    "sec_pump": [  # 二次冷冻水泵 (二次泵): 二次冷冻水流量/压力/频率/功率/状态
        ("sec_flow_rate", "m³/h", 350.0, 780.0),
        ("sec_pressure", "MPa", 0.18, 0.38),
        ("pump_hz", "Hz", 28.0, 50.0),
        ("pump_kw", "kW", 32.0, 62.0),
        ("run_status", "", 0, 2),  # 0=停机 1=运行 2=故障
    ],
    "storage_tank": [  # 蓄冷罐: 液位/温度分层/流量/模式/蓄放冷功率
        ("tank_level", "%", 10.0, 95.0),
        ("top_temp", "℃", 4.5, 7.5),       # 罐顶 (冷水层) 温度
        ("bottom_temp", "℃", 11.0, 15.0),  # 罐底 (回水层) 温度
        ("flow_rate", "m³/h", 0.0, 600.0),
        ("storage_mode", "", 0, 2),          # 0=保冷 1=蓄冷 2=放冷
        ("storage_power", "kW", -1500.0, 1500.0),  # 负=放冷 正=蓄冷
    ],
    "ambient": [  # 室内外温湿度 (自然冷/免费冷决策): 室外干/湿球 + 室内温湿度
        ("outdoor_temp", "℃", 5.0, 35.0),
        ("wet_bulb", "℃", 2.0, 28.0),
        ("outdoor_rh", "%RH", 30.0, 90.0),
        ("indoor_temp", "℃", 20.0, 28.0),
        ("indoor_rh", "%RH", 35.0, 65.0),
    ],
    # ===== 暖通·末端 (hvac_terminal) — 参照手册: 精密空调/新风/恒湿一体机 =====
    "crac": [  # 水冷精密空调: 送/回风温度湿度, 风机/阀门, 压差, 供回水温度
        ("supply_temp", "℃", 17.0, 21.0),
        ("return_temp", "℃", 25.0, 32.0),
        ("supply_humidity", "%RH", 45.0, 55.0),
        ("return_humidity", "%RH", 30.0, 50.0),
        ("fan_speed", "%", 50.0, 95.0),
        ("valve_pos", "%", 30.0, 90.0),
        ("water_valve_pos", "%", 20.0, 80.0),
        ("power_kw", "kW", 5.0, 25.0),
        ("supply_water_temp", "℃", 7.0, 11.0),
        ("return_water_temp", "℃", 14.0, 19.0),
        ("pressure_diff", "Pa", 10.0, 80.0),
        ("filter_status", "", 0, 2),  # 0=正常 1=脏堵预警 2=脏堵告警
    ],
    "fau": [  # 新风处理机组: 送风温度/湿度/CO2/滤网压差, 内外压差 5-10Pa
        ("supply_temp", "℃", 18.0, 23.0),
        ("humidity", "%RH", 45.0, 60.0),
        ("co2", "ppm", 400.0, 700.0),
        ("filter_dp", "Pa", 50.0, 150.0),
        ("room_dp", "Pa", 5.0, 10.0),
    ],
    "humidifier": [  # 恒湿一体机: 加湿/除湿模式, 湿度/功耗/水位
        ("humidity", "%RH", 45.0, 55.0),
        ("power_kw", "kW", 1.0, 8.0),
        ("run_mode", "", 0, 2),  # 0=待机 1=加湿 2=除湿
        ("water_level", "cm", 5.0, 25.0),
    ],
    # ===== 电力·中压 (power_hv) — 参照手册: 10kV 进线/馈线/母联, 三相电参量+开关状态 =====
    "hv_incomer": [  # 10kV 进线柜: 三相电压/电流/功率/功率因数/频率/电度/开关状态
        ("voltage_ab", "kV", 10.0, 10.6),
        ("voltage_bc", "kV", 10.0, 10.6),
        ("voltage_ca", "kV", 10.0, 10.6),
        ("current_a", "A", 300.0, 450.0),
        ("current_b", "A", 300.0, 450.0),
        ("current_c", "A", 300.0, 450.0),
        ("active_power", "kW", 5000.0, 7500.0),
        ("reactive_power", "kvar", 800.0, 1500.0),
        ("pf", "", 0.93, 0.98),
        ("freq", "Hz", 49.9, 50.1),
        ("energy", "kWh", 800000.0, 1200000.0),
        ("switch_state", "", 0, 2),  # 0=分闸 1=合闸 2=故障
    ],
    "hv_feeder": [  # 10kV 馈线柜: 电流/功率/电压/开关状态
        ("current_a", "A", 80.0, 150.0),
        ("current_b", "A", 80.0, 150.0),
        ("current_c", "A", 80.0, 150.0),
        ("active_power", "kW", 1400.0, 2500.0),
        ("voltage_ab", "kV", 10.0, 10.6),
        ("switch_state", "", 0, 2),
    ],
    "bus_tie": [  # 母联柜: 互锁状态, 与两路进线和柴发进线电气联锁
        ("state", "", 0, 1),  # 0=分闸 1=合闸
        ("interlock_ok", "", 1, 1),  # 1=互锁正常 0=互锁异常
    ],
    # ===== 电力·低压 (power_lv) — 参照手册: 变压器/UPS/HVDC/ATS/0.4kV =====
    "transformer": [  # 变压器: 负载率/温度/湿度/输出电压/高压侧电压/绕组温度
        ("load_pct", "%", 35.0, 75.0),
        ("temp", "℃", 60.0, 90.0),
        ("winding_temp", "℃", 65.0, 95.0),
        ("humidity", "%RH", 30.0, 60.0),
        ("voltage_in", "kV", 10.0, 10.5),
        ("voltage_out", "V", 375.0, 385.0),
    ],
    "ups": [  # UPS 不间断电源: 输入/输出/电池电压, 负载率/电流/功率/工作模式
        ("load_pct", "%", 30.0, 65.0),
        ("input_voltage", "V", 375.0, 385.0),
        ("output_voltage", "V", 378.0, 382.0),
        ("output_current", "A", 80.0, 160.0),
        ("output_power", "kW", 30.0, 60.0),
        ("battery_voltage", "V", 530.0, 550.0),
        ("battery_current", "A", -5.0, 10.0),
        ("mode", "", 0, 3),  # 0=在线 1=电池 2=旁路 3=故障
    ],
    "hvdc": [  # 高压直流 HVDC: 负载率/电压/电流/模块运行数/离线数
        ("load_pct", "%", 35.0, 65.0),
        ("voltage", "V", 235.0, 245.0),
        ("output_current", "A", 150.0, 300.0),
        ("output_power", "kW", 35.0, 70.0),
        ("module_running", "个", 20.0, 30.0),
        ("module_offline", "个", 0, 2.0),
        ("module_total", "个", 40, 40),
    ],
    "ats": [  # ATS 双电源切换: 常用/备用侧电压+开关位置
        ("state", "", 0, 2),  # 0=常用侧 1=备用侧 2=中间位
        ("source1_voltage", "V", 375.0, 385.0),
        ("source2_voltage", "V", 375.0, 385.0),
    ],
    # ===== 电力·柴发 (power_genset) — 参照手册: 11+1 并机, 三相电参量/水温/排温/转速/油压/状态 =====
    "genset": [  # 柴油发电机组: 输出三相电参量+发动机参数+并机状态
        ("output_voltage", "V", 375.0, 385.0),
        ("output_current", "A", 0.0, 500.0),
        ("output_freq", "Hz", 49.8, 50.2),
        ("output_power", "kW", 0.0, 800.0),
        ("pf", "", 0.80, 1.0),
        ("speed", "rpm", 1490.0, 1510.0),
        ("water_temp", "℃", 35.0, 50.0),
        ("exhaust_temp", "℃", 350.0, 520.0),
        ("oil_pressure", "bar", 0.0, 5.0),  # 停机时为 0
        ("battery_voltage", "V", 25.0, 28.0),
        ("fuel_level", "%", 60.0, 98.0),
        ("start_count", "次", 40.0, 100.0),
        ("run_hours", "h", 200.0, 600.0),
        ("g_status", "", 0, 4),  # 0=待机 1=启动中 2=运行 3=并机 4=故障
    ],
    # ===== 电力·燃油 (power_fuel) — 参照手册: 油罐/油箱/油泵, 液位+补油/泄油/切断阀 =====
    "fuel_tank": [  # 地埋主油罐: 液位+温度+漏油+紧急切断阀
        ("level_cm", "cm", 80.0, 180.0),
        ("level_pct", "%", 75.0, 98.0),
        ("temp", "℃", 18.0, 25.0),
        ("leak_alarm", "", 0, 0),  # 0=正常 1=漏油报警
        ("emergency_valve", "", 1, 1),  # 0=关闭 1=开到位
    ],
    "day_tank": [  # 日用油箱: 液位+温度+补油阀AB+泄油阀+漏油
        ("level_cm", "cm", 30.0, 80.0),
        ("level_pct", "%", 70.0, 98.0),
        ("temp", "℃", 20.0, 28.0),
        ("supply_valve_a", "", 0, 1),
        ("supply_valve_b", "", 0, 1),
        ("drain_valve", "", 0, 0),
        ("leak_alarm", "", 0, 0),
    ],
    "fuel_pump": [  # 供油泵/回油泵: 状态/功耗/运行时间
        ("state", "", 0, 1),  # 0=待机 1=运行
        ("power_kw", "kW", 2.0, 8.0),
        ("running_hours", "h", 500.0, 2000.0),
    ],
    # ===== 电力·电池 (power_battery) — 参照手册: TA/TC/收敛模块, 单体电压/内阻/温度/充放电电流 =====
    "battery_group": [  # 电池组: SOC/组压/电流/单体极值/内阻/环境温度
        ("soc", "%", 95.0, 100.0),
        ("voltage", "V", 530.0, 550.0),
        ("current", "A", -2.0, 5.0),
        ("max_temp", "℃", 24.0, 30.0),
        ("min_temp", "℃", 22.0, 27.0),
        ("single_voltage_min", "V", 1.95, 2.25),
        ("single_voltage_max", "V", 2.20, 2.35),
        ("internal_resistance", "μΩ", 100.0, 350.0),
        ("ambient_temp", "℃", 22.0, 28.0),
        ("cell_count", "个", 240, 240),
    ],
    # ===== 安防·视频 (security_cctv) — 参照手册: 枪机/球机/半球, DVR/存储/码流 =====
    "camera": [
        ("online_count", "个", 50.0, 64.0),
        ("offline_count", "个", 0, 3.0),
        ("storage_usage", "%", 60.0, 85.0),
        ("bitrate", "Mbps", 4.0, 16.0),
    ],
    # ===== 安防·门禁 (security_acs) — 参照手册: 读卡器/门磁/电锁/人脸识别/反潜回 =====
    "door_ctrl": [
        ("door_count", "个", 20.0, 120.0),
        ("today_events", "次", 500.0, 2000.0),
        ("forced_alarm", "次", 0, 2.0),
        ("timeout_alarm", "次", 0, 3.0),
        ("online_status", "", 1, 1),  # 1=在线 0=离线
    ],
    # ===== 安防·入侵 (security_ids) — 参照手册: 红外对射/电子围栏/周界探测器 =====
    "perimeter": [
        ("armed", "", 1, 1),
        ("alarm_count", "次", 0, 1),
        ("zones", "个", 8.0, 16.0),
        ("system_status", "", 0, 0),  # 0=正常 1=故障
    ],
    # ===== 消防 (security_fire) — 参照手册: 烟感/温感/手报/消火栓/VESDA =====
    "smoke_detector": [
        ("total_count", "个", 500.0, 3200.0),
        ("online_count", "个", 498.0, 3198.0),
        ("alarm_count", "个", 0, 1.0),
        ("fault_count", "个", 0, 3.0),
    ],
    "heat_detector": [
        ("total_count", "个", 300.0, 1500.0),
        ("online_count", "个", 299.0, 1498.0),
        ("alarm_count", "个", 0, 1.0),
        ("fault_count", "个", 0, 2.0),
    ],
    "vesda": [  # 极早期吸气式烟感: 浓度/报警级别/气流状态
        ("level", "", 0, 3),  # 0=正常 1=轻微 2=预警 3=报警
        ("value", "%obs/m", 0.001, 0.025),
        ("alarm_stage", "", 0, 3),  # 0=无 1=Alert 2=Action 3=Fire1
        ("airflow", "%", 90.0, 110.0),
    ],
    # ---- 专业域骨架补充 (B5): 无真实接入设备时生成器兜底展示 ----
    "liquid": [  # 液冷 CDU: 供回液温度/流量/冷量/水泵频率/机柜进风/换热温差
        ("supply_temp", "℃", 18.0, 24.0),
        ("return_temp", "℃", 22.0, 30.0),
        ("flow_rate", "L/min", 200.0, 400.0),
        ("cooling_cap", "kW", 50.0, 120.0),
        ("pump_hz", "Hz", 30.0, 50.0),
        ("rack_inlet_temp", "℃", 20.0, 27.0),
        ("heat_exchange_dt", "℃", 3.0, 8.0),
    ],
    "battery": [  # 储能电池簇: 单体/簇电压/SOC/SOH/电流/温度/功率
        ("cell_voltage", "V", 3.2, 3.6),
        ("pack_voltage", "V", 600.0, 800.0),
        ("soc", "%", 20.0, 95.0),
        ("soh", "%", 90.0, 100.0),
        ("current", "A", -100.0, 100.0),
        ("temp", "℃", 20.0, 45.0),
        ("power", "kW", -200.0, 200.0),
    ],
    "fuel": [  # 日用油箱: 液位/油量/温度/供油压力/低液位报警
        ("level", "%", 40.0, 90.0),
        ("volume", "L", 2000.0, 5000.0),
        ("temp", "℃", 10.0, 35.0),
        ("supply_pressure", "kPa", 10.0, 40.0),
        ("low_level_alarm", "", 0, 1),
    ],
}

# ======================================================================
#  全业务域设备注册清单
# ======================================================================
def _build_all_devices() -> list[dict]:
    """构造覆盖 11 个业务域的 ~80 台模拟设备。"""
    devices: list[dict] = []
    did = 1

    def add(category, domain, model, vendor, name_prefix, count, location_prefix="R"):
        nonlocal did
        for i in range(1, count + 1):
            dev_id = f"MOCK-{category.upper()}-{i:02d}"
            protocol = "modbus" if did % 2 == 0 else "snmp"
            location = f"{location_prefix}{(i % 3) + 1:02d}"
            devices.append({
                "device_id": dev_id,
                "ip": f"10.30.0.{did}",
                "sn": f"MOCKSN{did:04d}",
                "model": model,
                "name": f"{name_prefix}{i:02d}",
                "vendor": vendor,
                "domain": domain,
                "category": category,
                "location": location,
                "protocol": protocol,
                "tags": ["mock", f"v2-{category}", "sim"],
            })
            did += 1

    # ---- 暖通·冷源 (hvac_source) ----
    add("chiller", "hvac_source", "Carrier-19XR", "Carrier", "冷水机组-", 4)
    add("cooling_tower", "hvac_source", "Marley-NC", "Marley", "冷却塔-", 4)
    add("chw_pump", "hvac_source", "Grundfos-CRE", "Grundfos", "冷冻水泵-", 4)
    add("cw_pump", "hvac_source", "Grundfos-CRE", "Grundfos", "冷却水泵-", 4)
    add("heat_exchanger", "hvac_source", "Alfa-Laval-TS6M", "AlfaLaval", "板式换热器-", 2)
    add("valve", "hvac_source", "Belimo-EV", "Belimo", "电动阀-", 6)
    add("sec_pump", "hvac_source", "Grundfos-CRE", "Grundfos", "二次冷冻水泵-", 4)
    add("storage_tank", "hvac_source", "CyrusTank-2000", "Cyrus", "蓄冷罐-", 2)
    add("ambient", "hvac_source", "Rotronic-HC2", "Rotronic", "机房室内温湿度-", 4)

    # ---- 暖通·末端 (hvac_terminal) ----
    add("crac", "hvac_terminal", "Emerson-DX", "Emerson", "精密空调-", 10)
    add("fau", "hvac_terminal", "SystemAir-TF", "SystemAir", "新风机组-", 3)
    add("humidifier", "hvac_terminal", "Carel-humiSteam", "Carel", "恒湿机-", 3)
    add("leak", "hvac_terminal", "TTC-LeakLoc", "TTC", "定位漏水-", 6)

    # ---- 电力·中压 (power_hv) ----
    add("hv_incomer", "power_hv", "Schneider-PIX", "Schneider", "中压进线-", 2)
    add("hv_feeder", "power_hv", "Schneider-PIX", "Schneider", "中压馈线-", 6)
    add("bus_tie", "power_hv", "Schneider-PIX", "Schneider", "母联柜-", 1)

    # ---- 电力·低压 (power_lv) ----
    add("transformer", "power_lv", "ABB-SCLB", "ABB", "变压器-", 4)
    add("ups", "power_lv", "Vertiv-LiebertEXL", "Vertiv", "UPS组-", 2)
    add("hvdc", "power_lv", "Huawei-TP48", "Huawei", "高压直流-", 3)
    add("ats", "power_lv", "ASCO-7000", "ASCO", "ATS-", 4)

    # ---- 电力·柴发 (power_genset) ----
    add("genset", "power_genset", "Cummins-QSK60", "Cummins", "柴发-", 4)

    # ---- 电力·燃油 (power_fuel) ----
    add("fuel_tank", "power_fuel", "Steel-DoubleWall", "国标", "地埋主油罐-", 2)
    add("day_tank", "power_fuel", "Steel-1000L", "国标", "日用油箱-", 4)
    add("fuel_pump", "power_fuel", "Grundfos-CR", "Grundfos", "输油泵-", 3)

    # ---- 电力·电池 (power_batt) ----
    add("battery_group", "power_batt", "EnerSys-12V", "EnerSys", "蓄电池组-", 4)

    # ---- 安防·视频 (sec_cctv) ----
    add("camera", "sec_cctv", "Hikvision-DS2", "Hikvision", "摄像机区-", 6)
    add("camera", "sec_cctv", "Dahua-HFW", "Dahua", "摄像机区-", 4, location_prefix="Z")

    # ---- 安防·门禁 (sec_acs) ----
    add("door_ctrl", "sec_acs", "Honeywell-PW7K", "Honeywell", "门禁控制器-", 4)

    # ---- 安防·入侵 (sec_ids) ----
    add("perimeter", "sec_ids", "Southwest-MMFD", "西南微波", "电子围栏-", 2)

    # ---- 消防 (sec_fire) ----
    add("smoke_detector", "sec_fire", "Honeywell-XLS", "Honeywell", "感烟探测器组-", 3)
    add("heat_detector", "sec_fire", "Honeywell-XLS", "Honeywell", "感温探测器组-", 2)
    add("vesda", "sec_fire", "Xtralis-VESDA-E", "Xtralis", "极早期VESDA-", 4)

    return devices


DEVICES = _build_all_devices()
MOCK_DEVICE_COUNT = len(DEVICES)


def _gen_metrics(device_id: str, category: str) -> list[dict]:
    """为一台设备生成一轮语义化测点 (按类别不同)。"""
    now = datetime.now(timezone.utc).isoformat()
    metric_defs = _CATEGORY_METRICS.get(category, [
        ("value", "", 0, 100),
    ])
    points = []
    for metric_name, unit, lo, hi in metric_defs:
        if lo == hi:
            val = float(lo)
        else:
            val = round(random.uniform(lo, hi), 3 if hi - lo < 1 else 2)
        points.append({
            "device_id": device_id,
            "timestamp": now,
            "metric_name": metric_name,
            "value": val,
            "quality": random.choice(_QUALITY_POOL),
            "unit": unit,
        })
    return points


async def maybe_start_mock_collector() -> "asyncio.Task | None":
    """若启用, 启动 Mock 采集器后台任务; 否则返回 None。

    生产环境默认不启动, 除非显式设置 EXTERNAL_MOCK_COLLECTOR_ENABLED=true。
    """
    if settings.APP_ENV == "production" and os.getenv("EXTERNAL_MOCK_COLLECTOR_ENABLED") is None:
        logger.warning("生产环境默认不启动 MockCollector, 如需启用请显式设置 EXTERNAL_MOCK_COLLECTOR_ENABLED=true")
        return None
    if not settings.EXTERNAL_MOCK_COLLECTOR_ENABLED:
        logger.info("MockCollector 未启用 (EXTERNAL_MOCK_COLLECTOR_ENABLED=False)")
        return None
    task = asyncio.create_task(_run(), name="mock-collector-v2")
    return task


async def _register_one(client: httpx.AsyncClient, dev: dict, headers: dict) -> None:
    try:
        r = await client.post("/api/external/device/register", json=dev, headers=headers)
        if r.status_code != 200:
            logger.warning("Mock 注册失败 %s: %s", dev["device_id"], r.text[:120])
    except Exception as e:
        logger.warning("Mock 注册异常 %s: %s", dev["device_id"], e)


async def _kafka_register(producer, dev: dict) -> None:
    """经 Kafka 发送设备注册信封 (复用 external 数据契约)。"""
    try:
        await producer.send_and_wait(
            settings.EXTERNAL_KAFKA_INGEST_TOPIC,
            {"type": "register", "payload": dev},
        )
    except Exception as e:
        logger.warning("Mock 经 Kafka 注册失败 %s: %s", dev["device_id"], e)


async def _kafka_send_metrics(producer, batch: list[dict]) -> None:
    """经 Kafka 发送批量测点信封 (复用 external 数据契约)。"""
    try:
        await producer.send_and_wait(
            settings.EXTERNAL_KAFKA_INGEST_TOPIC,
            {"type": "metrics", "payload": batch},
        )
    except Exception as e:
        logger.warning("Mock 经 Kafka 上报失败: %s", e)


async def _run() -> None:
    """注册 ~80 台设备 -> 每 5 秒批量上报测点。

    双通道 (HTTP + Kafka) 收敛:
    - 配置 EXTERNAL_KAFKA_BOOTSTRAP_SERVERS 时优先经 Kafka 发送 register/metrics 信封,
      由 kafka_consumer 复用同一 external 契约反序列化落库, 形成端到端 Kafka 接入演示;
    - producer 不可用 (broker 不可达 / 未装 aiokafka) 时自动回退到 HTTP 契约。
    """
    headers = {}
    if settings.EXTERNAL_COLLECTOR_TOKEN:
        headers["X-Collector-Token"] = settings.EXTERNAL_COLLECTOR_TOKEN

    # ---- Kafka producer (可选接入通道) ----
    producer = None
    if settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS:
        try:
            from aiokafka import AIOKafkaProducer

            producer = AIOKafkaProducer(
                bootstrap_servers=settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                acks="all",
            )
            await producer.start()
            logger.info("MockCollector Kafka producer 已连接: %s", settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.warning("MockCollector Kafka producer 启动失败, 回退 HTTP: %s", e)
            producer = None

    async with httpx.AsyncClient(base_url=settings.EXTERNAL_MOCK_COLLECTOR_BASE_URL, timeout=15) as client:
        # ---- 1) 注册 ----
        if producer:
            await asyncio.gather(*[_kafka_register(producer, dev) for dev in DEVICES])
            logger.info("MockCollector 经 Kafka 注册 %d 台设备", len(DEVICES))
        else:
            await asyncio.gather(*[_register_one(client, dev, headers) for dev in DEVICES])
            logger.info("MockCollector v2 注册完成, 开始推送循环 (%d 台设备)", len(DEVICES))

        # ---- 2) 启动横幅 ----
        domain_names = sorted(set(d["domain"] for d in DEVICES))
        chan = "Kafka" if producer else "HTTP"
        banner = (
            f"[MockCollector v2] 已启动 ({chan} 通道), 覆盖 {len(domain_names)} 个业务域 ({', '.join(domain_names)}), "
            f"每 {PUSH_INTERVAL_SEC}s 推送一轮测点..."
        )
        try:
            sys.stdout.buffer.write((banner + "\n").encode("utf-8"))
            sys.stdout.buffer.flush()
        except Exception:
            pass
        logger.info(banner)

        # ---- 3) 每 5 秒批量上报 ----
        round_no = 0
        while True:
            round_no += 1
            batch: list[dict] = []
            for dev in DEVICES:
                batch.extend(_gen_metrics(dev["device_id"], dev["category"]))
            if producer:
                await _kafka_send_metrics(producer, batch)
                logger.info("Mock v2 第%d轮(经Kafka): %d 条测点", round_no, len(batch))
            else:
                try:
                    r = await client.post(
                        "/api/external/metrics/upload", json=batch, headers=headers
                    )
                    if r.status_code != 200:
                        logger.warning("Mock v2 上报失败 (第%d轮): %s", round_no, r.text[:120])
                    else:
                        resp = r.json()
                        logger.info("Mock v2 第%d轮: %d 条测点, accepted=%d, rejected=%d",
                                    round_no, resp.get("total", 0), resp.get("accepted", 0), resp.get("rejected", 0))
                except Exception as e:
                    logger.warning("Mock v2 上报异常 (第%d轮): %s", round_no, e)
            await asyncio.sleep(PUSH_INTERVAL_SEC)
