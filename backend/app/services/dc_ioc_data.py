# 回退数据生成器 —— dc_aggregator 的兜底数据源。
# 当真实采集链路 (external_devices + metric_raws) 无数据时，dc_aggregator 回退到此模块。
# 上线后: 真实采集器覆盖全量设备后，本模块可逐步删除各域函数。
"""DC-IOC 全量 Mock 数据生成器 (dc_aggregator 的兜底数据源)。

完整镜像 dc-ioc/js/data.js 的 22 个业务域:
  暖通(冷源/末端) / 电力(10KV/0.4KV/柴发/燃油/电池)
  安防消防(视频/门禁/防入侵/消防) / 智能运营+运维作业(孪生/容量/告警/电量/工单/巡检/维保/演练/排班/风险/知识)

采用固定种子构造, 保证多次请求数据稳定 (机柜/设备曲线以 id 为种子做平滑随机游走)。
"""
import math
import random
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------------ 基础工具
_SEED = 20260723
_rng = random.Random(_SEED)


def rnd(a: float, b: float, f: int = 1) -> float:
    return round(a + _rng.random() * (b - a), f)


def pick(arr):
    return arr[_rng.randint(0, len(arr) - 1)]


def drift(v, amp, lo, hi, f=1):
    return round(min(hi, max(lo, v + (_rng.random() - 0.5) * amp)), f)


def series(n, a, b):
    return [rnd(a, b) for _ in range(n)]


def _walk(rng: random.Random, base, amp, n, now: datetime, step: timedelta, f=2):
    """带轻微正弦趋势的平滑随机游走序列 -> [{ts,value}]。"""
    pts = []
    v = base
    for i in range(n):
        d = math.sin(i / n * math.pi * 2) * amp * 0.4
        v = base + d + (rng.random() - 0.5) * amp
        pts.append({"ts": (now - step * (n - 1 - i)).isoformat(), "value": round(v, f)})
    return pts


# ------------------------------------------------------------------ 全局 KPI
def kpi():
    return {
        "pue": 1.247, "wue": 1.62, "itLoad": 24.6, "totalLoad": 30.7,
        "coolLoad": 4.9, "availability": 99.9995,
        "alarms": {"crit": 1, "warn": 6, "info": 14},
        "freeCoolHours": 4382,
    }


# ------------------------------------------------------------------ 暖通·冷源
def chiller_plant():
    # 智算中心级冷站: 8 台冷机 (4+2+N), 8 个冷却塔, 8 套泵组, 4 台板换, 8 个电动阀
    # 单台冷机 3500kW ≈ 1000RT, 总装机 28MW
    chillers = [
        {"id": "CH-01", "state": "运行", "load": 76, "cop": 6.38, "evapT": 15.0, "condT": 29.1, "current": 74, "runHrs": 12480},
        {"id": "CH-02", "state": "运行", "load": 71, "cop": 6.45, "evapT": 15.1, "condT": 29.3, "current": 70, "runHrs": 11923},
        {"id": "CH-03", "state": "运行", "load": 68, "cop": 6.52, "evapT": 15.2, "condT": 29.0, "current": 67, "runHrs": 11405},
        {"id": "CH-04", "state": "运行", "load": 73, "cop": 6.28, "evapT": 14.9, "condT": 29.5, "current": 72, "runHrs": 10892},
        {"id": "CH-05", "state": "待机", "load": 0, "cop": 0, "evapT": "-", "condT": "-", "current": 0, "runHrs": 10102},
        {"id": "CH-06", "state": "待机", "load": 0, "cop": 0, "evapT": "-", "condT": "-", "current": 0, "runHrs": 9620},
        {"id": "CH-07", "state": "检修", "load": 0, "cop": 0, "evapT": "-", "condT": "-", "current": 0, "runHrs": 13877},
        {"id": "CH-08", "state": "待机", "load": 0, "cop": 0, "evapT": "-", "condT": "-", "current": 0, "runHrs": 8843},
    ]
    towers = [
        {"id": "CT-01", "state": "运行", "fanHz": 38, "outT": 19.2},
        {"id": "CT-02", "state": "运行", "fanHz": 38, "outT": 19.4},
        {"id": "CT-03", "state": "运行", "fanHz": 36, "outT": 19.1},
        {"id": "CT-04", "state": "运行", "fanHz": 35, "outT": 19.0},
        {"id": "CT-05", "state": "运行", "fanHz": 33, "outT": 18.9},
        {"id": "CT-06", "state": "待机", "fanHz": 0, "outT": "-"},
        {"id": "CT-07", "state": "待机", "fanHz": 0, "outT": "-"},
        {"id": "CT-08", "state": "检修", "fanHz": 0, "outT": "-"},
    ]
    pumps_chw = [{"id": "CHWP-01", "state": "运行", "hz": 40, "kw": 55},
                 {"id": "CHWP-02", "state": "运行", "hz": 40, "kw": 54},
                 {"id": "CHWP-03", "state": "运行", "hz": 38, "kw": 52},
                 {"id": "CHWP-04", "state": "运行", "hz": 38, "kw": 53},
                 {"id": "CHWP-05", "state": "运行", "hz": 36, "kw": 50},
                 {"id": "CHWP-06", "state": "待机", "hz": 0, "kw": 0},
                 {"id": "CHWP-07", "state": "待机", "hz": 0, "kw": 0},
                 {"id": "CHWP-08", "state": "检修", "hz": 0, "kw": 0}]
    pumps_cw = [{"id": "CWP-01", "state": "运行", "hz": 42, "kw": 75},
                {"id": "CWP-02", "state": "运行", "hz": 42, "kw": 74},
                {"id": "CWP-03", "state": "运行", "hz": 40, "kw": 72},
                {"id": "CWP-04", "state": "运行", "hz": 40, "kw": 73},
                {"id": "CWP-05", "state": "运行", "hz": 38, "kw": 70},
                {"id": "CWP-06", "state": "待机", "hz": 0, "kw": 0},
                {"id": "CWP-07", "state": "待机", "hz": 0, "kw": 0},
                {"id": "CWP-08", "state": "检修", "hz": 0, "kw": 0}]
    pumps_sec = [{"id": "SCHWP-01", "state": "运行", "hz": 40, "kw": 52, "flow": 620},
                 {"id": "SCHWP-02", "state": "运行", "hz": 40, "kw": 51, "flow": 615},
                 {"id": "SCHWP-03", "state": "运行", "hz": 38, "kw": 49, "flow": 590},
                 {"id": "SCHWP-04", "state": "运行", "hz": 38, "kw": 50, "flow": 595},
                 {"id": "SCHWP-05", "state": "待机", "hz": 0, "kw": 0, "flow": 0},
                 {"id": "SCHWP-06", "state": "待机", "hz": 0, "kw": 0, "flow": 0}]
    hexs = [
        {"id": "HEX-01", "state": "投入", "eff": 93, "priIn": 16.8, "priOut": 14.6, "secIn": 13.2, "secOut": 15.9},
        {"id": "HEX-02", "state": "投入", "eff": 92, "priIn": 16.9, "priOut": 14.7, "secIn": 13.3, "secOut": 16.0},
        {"id": "HEX-03", "state": "投入", "eff": 94, "priIn": 16.7, "priOut": 14.5, "secIn": 13.1, "secOut": 15.8},
        {"id": "HEX-04", "state": "待机", "eff": 0, "priIn": "-", "priOut": "-", "secIn": "-", "secOut": "-"},
    ]
    valves = [
        {"id": "V-101", "name": "CH-01~02 冷机侧电动阀", "pos": 100, "state": "开"},
        {"id": "V-102", "name": "CH-03~04 冷机侧电动阀", "pos": 100, "state": "开"},
        {"id": "V-201", "name": "板换 A 组电动阀", "pos": 100, "state": "开"},
        {"id": "V-202", "name": "板换 B 组电动阀", "pos": 65, "state": "调节"},
        {"id": "V-301", "name": "蓄冷罐放冷阀", "pos": 0, "state": "关"},
        {"id": "V-401", "name": "旁通调节阀", "pos": 18, "state": "调节"},
        {"id": "V-501", "name": "供回水总管隔离阀", "pos": 100, "state": "开"},
        {"id": "V-601", "name": "二次侧分水器调阀", "pos": 80, "state": "调节"},
    ]
    return {
        "mode": "预冷模式",
        "modes": ["制冷模式", "预冷模式", "自然冷却模式"],
        "outdoorT": 18.4, "outdoorRH": 62, "wetBulb": 14.1,
        "supplyT": 15.2, "returnT": 20.8, "targetSupplyT": 15.0,
        "flow": 4860, "coolingCap": 22.4, "plr": 64,
        "storageTank": {"level": 88, "dischargeMin": 20, "mode": "保冷备用", "capacity": 6000,
                        "topTemp": 5.6, "botTemp": 12.8, "flow": 0, "power": 0},
        "ambient": {"outdoorTemp": 18.4, "outdoorRH": 62, "wetBulb": 14.1,
                    "indoorTemp": 23.6, "indoorRH": 48, "freeCooling": "部分自然冷"},
        "chillers": chillers,
        "towers": towers,
        "pumps": {"chw": pumps_chw, "cw": pumps_cw, "sec": pumps_sec},
        "hex": hexs,
        "valves": valves,
        "staging": {"rule": "供水温度 > 设定+1.0℃ 持续 5min 加机；PLR < 45% 持续 15min 减机",
                    "lastAction": "10:42 CH-03 自动加机(负载爬升)", "next": "—"},
        # ===== 基于《阿里云数据中心弱电手册》的运行模式决策（设计阈值）=====
        # 冷却水回水温度：由冷冻水回水 + 换热器温升近似（稳定处于预冷区间）
        "cwReturnT": 22.3,
        "thresholds": {
            "chwSupplyDesign": 18, "chwReturnDesign": 24,   # 冷冻水供/回 ℃
            "hexDiffDesign": 1.5,                            # 板换换热温差 ℃
            "ctDiffDesign": 5.5,                             # 冷却塔温差 ℃
            "coolToPrecoolCwRetMax": 22.5,                   # 制冷→预冷：冷却水回水 ≤
            "coolToPrecoolDiff": 1.5,                        # 冷却水回水低于冷冻水回水
            "coolToPrecoolChwOutMax": 19.3,                  # 冷冻水出水 <
            "precoolToFreeWetBulbMax": 11.0,                # 预冷→自然冷：室外湿球 <
            "precoolToFreeChwInMax": 19.5,                  # 冷机冷冻水进水 <
            "freeToPrecoolHexOutMin": 18.5,                 # 自然冷→预冷：板换冷冻水出水 >
            "freeToPrecoolCwFreq": 50,                       # 冷却泵频率 =
            "precoolToCoolCwRetMin": 22.5,                 # 预冷→制冷：冷却水回水 >
            "precoolToCoolCtFreq": 50,                       # 冷却塔风机频率 =
        },
        "modeLogic": {
            "current": "预冷模式",
            "modes": [
                {"name": "制冷模式", "desc": "冷水机组机械制冷为主"},
                {"name": "预冷模式", "desc": "板换预冷 + 冷机，部分自然冷"},
                {"name": "自然冷却模式", "desc": "板换完全自然冷，冷机退出"},
            ],
            "transitions": [
                {"from": "制冷模式", "to": "预冷模式", "conditions": [
                    {"label": "冷却水回水温度 ≤ 22.5℃", "ok": 22.3 <= 22.5},
                    {"label": "冷却水回水低于冷冻水回水 1.5℃", "ok": (22.3 - 20.8) >= 1.5},
                    {"label": "冷冻水出水 < 19.3℃ 且本单元无故障", "ok": 15.2 < 19.3},
                ]},
                {"from": "预冷模式", "to": "自然冷却模式", "conditions": [
                    {"label": "室外湿球温度 < 11℃", "ok": 14.1 < 11.0},
                    {"label": "冷却泵频率降至最低", "ok": True},
                    {"label": "冷机冷冻水进水温度 < 19.5℃", "ok": 16.2 < 19.5},
                    {"label": "该状态持续 > 30min", "ok": True},
                ]},
                {"from": "自然冷却模式", "to": "预冷模式", "conditions": [
                    {"label": "板换冷冻水出水温度 > 18.5℃", "ok": 18.2 > 18.5},
                    {"label": "冷却泵频率为 50Hz", "ok": True},
                ]},
                {"from": "预冷模式", "to": "制冷模式", "conditions": [
                    {"label": "冷却水回水温度 > 22.5℃", "ok": 22.3 > 22.5},
                    {"label": "冷却塔风机频率为 50Hz", "ok": True},
                ]},
            ],
        },
        # ===== 冷源故障锁定知识库（手册 §制冷单元故障切换）=====
        "faults": [
            {"no": 1, "fault": "(水泵/冷却塔/冷机) 启停 mismatch", "lock": "锁定", "action": "报警、切换、限制制冷模式切换", "manualReset": True},
            {"no": 2, "fault": "(水泵/冷却塔) 变频 mismatch", "lock": "锁定", "action": "报警、切换、限制制冷模式切换", "manualReset": True},
            {"no": 3, "fault": "电动阀开关/调节 mismatch", "lock": "锁定", "action": "报警、切换、限制制冷模式切换", "manualReset": True},
            {"no": 4, "fault": "制冷单元 IO 子站通讯故障", "lock": "锁定", "action": "报警、切换、限制制冷模式切换", "manualReset": True},
            {"no": 5, "fault": "(水泵/冷却塔/冷机) 硬接线故障", "lock": "不允许启动", "action": "报警、不切换、限制制冷模式切换", "manualReset": True},
            {"no": 6, "fault": "(水泵/冷却塔) MCC 柜处于“就地”状态", "lock": "不允许启动", "action": "报警、不切换、限制制冷模式切换", "manualReset": True},
            {"no": 7, "fault": "(水泵/冷却塔) MCC 柜断电", "lock": "不允许启动", "action": "报警、不切换、限制制冷模式切换", "manualReset": True},
            {"no": 8, "fault": "电动阀阀控柜处于“就地”状态", "lock": "不允许启动", "action": "报警、不切换、限制制冷模式切换", "manualReset": True},
            {"no": 9, "fault": "(水泵/冷却塔/冷机) 处于“手动”状态", "lock": "仅报警", "action": "只报警、不切换、不限制", "manualReset": True},
            {"no": 10, "fault": "冷冻水出水温度过高", "lock": "仅报警", "action": "只报警、不切换、不限制", "manualReset": True},
            {"no": 11, "fault": "所有传感器数值超出阈值上下限", "lock": "仅报警", "action": "只报警、不切换、不限制", "manualReset": True},
        ],
        "tempTrend": series(48, 14.6, 15.8),
        "loadTrend": series(48, 55, 80),
        "knowledge": {
            "arch": {
                "components": ["冷机群(8台 CH)", "冷却塔(8台 CT)", "冷冻/冷却/二次泵(8/8/6)", "板式换热器(4台 自然冷)", "蓄冷罐(6000m³)", "电动阀/旁通(8个)"],
                "design": "8 台冷机 (4+2+N 冗余)，三级自然冷(制冷/预冷/自然冷)按需切换；蓄冷罐保冷 20min 停电续冷。",
                "redundancy": "冷机 N+2、冷却塔 N+3、水泵 N+2、双路供电、蓄冷罐兜底。",
            },
            "logic": [
                {"title": "温升趋势告警(DCGoT)", "steps": [
                    {"step": 1, "text": "多点温湿度时序采集", "ok": True},
                    {"step": 2, "text": "时空图模型(GoT)建模", "ok": True},
                    {"step": 3, "text": "趋势/异常预测，提前 ≥10min 预警", "ok": True},
                    {"step": 4, "text": "相比阈值法：有效率 55%→99.5%，告警量 ↓58.5%", "ok": True},
                ]},
            ],
            "note": "制冷系统占数据中心总电费约 24%；充分利用自然冷(source free cooling)是 PUE 优化的核心。温升是 IT 设备宕机的第一大杀手——从“阈值报警”升级为“趋势预警”可大幅减少漏报与误报。",
        },
    }


# ---- 液冷系统 (CDU + 冷板 + 管路 + 漏液检测) ----
def liquid_cooling():
    """智算中心液冷分配系统数据。涵盖一次侧 CDU、二次侧 CDU、
    冷板监控、分集液管路、漏液检测、冷却液品质和余热回收。"""
    return {
        # ===== 全局 KPI =====
        "systemMode": "自动运行",
        "outdoorT": 26.3,
        "outdoorRH": 55,
        "totalCoolingCap": 8.4,      # MW
        "coolingCapUsed": 5.9,       # MW
        "capRate": 70,               # % 制冷利用率
        "supplyTemp": 32.0,          # ℃ 一次侧供水 (中温水)
        "returnTemp": 38.5,          # ℃ 一次侧回水
        "primaryFlow": 680,          # m³/h 一次侧总流量
        "primaryPressure": 2.8,      # bar 一次侧总管压
        "secSupplyTemp": 35.0,       # ℃ 二次侧供液
        "secReturnTemp": 45.2,       # ℃ 二次侧回液
        "secFlow": 520,              # m³/h 二次侧总流量
        "secPressure": 3.2,          # bar 二次侧总管压
        "deltaT": 10.2,              # ℃ 二次侧供回温差
        "pueContribution": 0.06,     # 液冷对 PUE 贡献值
        "freeCoolingHours": 4380,    # 年自然冷可用小时
        "heatRecovery": 1.2,         # MW 余热回收量

        # ===== 一次侧 CDU(冷却液分配单元) =====
        "primaryCDUs": [
            {"id": "PCDU-01", "name": "一次侧 CDU-A", "state": "运行",
             "heatExEff": 94, "priInTemp": 26.3, "priOutTemp": 32.0,
             "secInTemp": 36.8, "secOutTemp": 32.5,
             "flowPri": 170, "flowSec": 130, "dpPri": 0.8, "dpSec": 1.2,
             "pumpSpeed": 78, "pumpKw": 12.5, "valve": 82,
             "leakStatus": "正常", "runHrs": 15840},
            {"id": "PCDU-02", "name": "一次侧 CDU-B", "state": "运行",
             "heatExEff": 93, "priInTemp": 26.3, "priOutTemp": 32.1,
             "secInTemp": 37.0, "secOutTemp": 32.6,
             "flowPri": 168, "flowSec": 128, "dpPri": 0.8, "dpSec": 1.2,
             "pumpSpeed": 76, "pumpKw": 12.2, "valve": 80,
             "leakStatus": "正常", "runHrs": 15320},
            {"id": "PCDU-03", "name": "一次侧 CDU-C", "state": "运行",
             "heatExEff": 94, "priInTemp": 26.4, "priOutTemp": 32.0,
             "secInTemp": 36.9, "secOutTemp": 32.5,
             "flowPri": 172, "flowSec": 132, "dpPri": 0.9, "dpSec": 1.3,
             "pumpSpeed": 80, "pumpKw": 12.8, "valve": 84,
             "leakStatus": "正常", "runHrs": 16005},
            {"id": "PCDU-04", "name": "一次侧 CDU-D", "state": "运行",
             "heatExEff": 92, "priInTemp": 26.5, "priOutTemp": 32.3,
             "secInTemp": 37.2, "secOutTemp": 32.8,
             "flowPri": 170, "flowSec": 130, "dpPri": 0.8, "dpSec": 1.1,
             "pumpSpeed": 74, "pumpKw": 11.8, "valve": 78,
             "leakStatus": "正常", "runHrs": 14890},
        ],

        # ===== 二次侧 CDU(直接与冷板对接) =====
        "secondaryCDUs": [
            {"id": "SCDU-A1", "name": "A 区 CDU-1", "rackGroup": "A 区 GPU 集群",
             "state": "运行", "supplyTemp": 35.0, "returnTemp": 45.0,
             "flow": 65, "dp": 1.5, "pumpSpeed": 70, "pumpKw": 3.5,
             "leakStatus": "正常", "coldPlateCount": 48, "coldPlateOnline": 48},
            {"id": "SCDU-A2", "name": "A 区 CDU-2", "rackGroup": "A 区 GPU 集群",
             "state": "运行", "supplyTemp": 34.8, "returnTemp": 45.3,
             "flow": 63, "dp": 1.4, "pumpSpeed": 68, "pumpKw": 3.3,
             "leakStatus": "正常", "coldPlateCount": 48, "coldPlateOnline": 48},
            {"id": "SCDU-B1", "name": "B 区 CDU-1", "rackGroup": "B 区 GPU 集群",
             "state": "运行", "supplyTemp": 35.2, "returnTemp": 45.5,
             "flow": 62, "dp": 1.4, "pumpSpeed": 66, "pumpKw": 3.2,
             "leakStatus": "正常", "coldPlateCount": 48, "coldPlateOnline": 46},
            {"id": "SCDU-B2", "name": "B 区 CDU-2", "rackGroup": "B 区 GPU 集群",
             "state": "待机", "supplyTemp": "-", "returnTemp": "-",
             "flow": 0, "dp": 0, "pumpSpeed": 0, "pumpKw": 0,
             "leakStatus": "正常", "coldPlateCount": 48, "coldPlateOnline": 48},
            {"id": "SCDU-C1", "name": "C 区 CDU-1", "rackGroup": "C 区推理集群",
             "state": "运行", "supplyTemp": 34.9, "returnTemp": 44.8,
             "flow": 58, "dp": 1.3, "pumpSpeed": 62, "pumpKw": 2.8,
             "leakStatus": "正常", "coldPlateCount": 40, "coldPlateOnline": 40},
            {"id": "SCDU-C2", "name": "C 区 CDU-2", "rackGroup": "C 区推理集群",
             "state": "运行", "supplyTemp": 35.1, "returnTemp": 44.6,
             "flow": 57, "dp": 1.3, "pumpSpeed": 60, "pumpKw": 2.7,
             "leakStatus": "正常", "coldPlateCount": 40, "coldPlateOnline": 40},
            {"id": "SCDU-D1", "name": "D 区 CDU-1", "rackGroup": "D 区训练集群",
             "state": "运行", "supplyTemp": 34.7, "returnTemp": 46.0,
             "flow": 68, "dp": 1.6, "pumpSpeed": 75, "pumpKw": 3.8,
             "leakStatus": "正常", "coldPlateCount": 56, "coldPlateOnline": 56},
            {"id": "SCDU-D2", "name": "D 区 CDU-2", "rackGroup": "D 区训练集群",
             "state": "运行", "supplyTemp": 34.8, "returnTemp": 45.8,
             "flow": 67, "dp": 1.6, "pumpSpeed": 73, "pumpKw": 3.6,
             "leakStatus": "预警", "coldPlateCount": 56, "coldPlateOnline": 56},
        ],

        # ===== 冷板级别监控 (关键 GPU 节点) =====
        "coldPlateMonitoring": [
            {"rackId": "R-A01", "nodeType": "H800x8", "inletTemp": 35.0, "outletTemp": 45.2,
             "flow": 2.8, "dp": 0.35, "gpuTemp": [68.2, 67.8, 69.1, 71.3, 68.5, 66.9, 70.4, 67.2],
             "state": "正常"},
            {"rackId": "R-A02", "nodeType": "H800x8", "inletTemp": 34.8, "outletTemp": 45.5,
             "flow": 2.7, "dp": 0.34, "gpuTemp": [69.1, 68.4, 70.2, 71.8, 67.9, 66.5, 69.3, 68.0],
             "state": "正常"},
            {"rackId": "R-A03", "nodeType": "H800x8", "inletTemp": 35.2, "outletTemp": 47.1,
             "flow": 2.6, "dp": 0.33, "gpuTemp": [72.3, 71.5, 73.1, 74.8, 70.2, 69.1, 72.6, 70.8],
             "state": "关注"},
            {"rackId": "R-D01", "nodeType": "H100x8", "inletTemp": 34.6, "outletTemp": 46.2,
             "flow": 3.0, "dp": 0.38, "gpuTemp": [71.2, 70.5, 72.1, 73.4, 69.8, 68.5, 71.9, 70.1],
             "state": "正常"},
            {"rackId": "R-D02", "nodeType": "H100x8", "inletTemp": 34.7, "outletTemp": 46.5,
             "flow": 2.9, "dp": 0.37, "gpuTemp": [72.4, 71.8, 73.2, 74.1, 70.5, 69.2, 72.8, 71.3],
             "state": "正常"},
            {"rackId": "R-D03", "nodeType": "H100x8", "inletTemp": 34.9, "outletTemp": 48.2,
             "flow": 2.8, "dp": 0.36, "gpuTemp": [74.5, 73.8, 75.2, 76.9, 72.1, 71.0, 74.3, 72.8],
             "state": "预警"},
            {"rackId": "R-C01", "nodeType": "A800x8", "inletTemp": 35.1, "outletTemp": 44.5,
             "flow": 2.5, "dp": 0.30, "gpuTemp": [65.2, 64.8, 66.1, 65.5, 64.2, 63.9, 65.8, 64.5],
             "state": "正常"},
            {"rackId": "R-C02", "nodeType": "A800x8", "inletTemp": 35.0, "outletTemp": 44.2,
             "flow": 2.5, "dp": 0.30, "gpuTemp": [64.8, 64.2, 65.5, 65.1, 63.8, 63.2, 65.0, 64.1],
             "state": "正常"},
        ],

        # ===== 分/集液管路 (Manifold) =====
        "manifolds": {
            "supply": [
                {"id": "SM-A", "zone": "A 区", "temp": 35.0, "pressure": 3.2, "flow": 260, "valvesOpen": 8, "branchCount": 8},
                {"id": "SM-B", "zone": "B 区", "temp": 35.1, "pressure": 3.1, "flow": 248, "valvesOpen": 8, "branchCount": 8},
                {"id": "SM-C", "zone": "C 区", "temp": 35.0, "pressure": 3.1, "flow": 230, "valvesOpen": 8, "branchCount": 8},
                {"id": "SM-D", "zone": "D 区", "temp": 34.8, "pressure": 3.3, "flow": 272, "valvesOpen": 8, "branchCount": 8},
            ],
            "return": [
                {"id": "RM-A", "zone": "A 区", "temp": 45.2, "pressure": 1.6, "flow": 260},
                {"id": "RM-B", "zone": "B 区", "temp": 45.4, "pressure": 1.6, "flow": 248},
                {"id": "RM-C", "zone": "C 区", "temp": 44.7, "pressure": 1.6, "flow": 230},
                {"id": "RM-D", "zone": "D 区", "temp": 46.0, "pressure": 1.7, "flow": 272},
            ],
        },

        # ===== 漏液检测 =====
        "leakDetection": {
            "totalSensors": 128,
            "alarmCount": 2,
            "warningCount": 3,
            "ropeLeak": [
                {"id": "LR-A01", "location": "A 区 机柜底部", "status": "正常", "length": 15, "coverage": 100},
                {"id": "LR-A02", "location": "A 区 CDU 底座", "status": "正常", "length": 8, "coverage": 100},
                {"id": "LR-B01", "location": "B 区 机柜底部", "status": "正常", "length": 15, "coverage": 100},
                {"id": "LR-B02", "location": "B 区 CDU 底座", "status": "预警", "length": 8, "coverage": 95},
                {"id": "LR-C01", "location": "C 区 机柜底部", "status": "正常", "length": 15, "coverage": 100},
                {"id": "LR-D01", "location": "D 区 机柜底部", "status": "正常", "length": 15, "coverage": 100},
                {"id": "LR-D02", "location": "D 区 CDU 底座", "status": "报警", "length": 8, "coverage": 80},
                {"id": "LR-D03", "location": "D 区 管路接口", "status": "正常", "length": 20, "coverage": 100},
            ],
            "pointLeak": [
                {"id": "LP-A-01..06", "zone": "A 区", "count": 6, "alarmCount": 0},
                {"id": "LP-B-01..06", "zone": "B 区", "count": 6, "alarmCount": 1},
                {"id": "LP-C-01..06", "zone": "C 区", "count": 6, "alarmCount": 0},
                {"id": "LP-D-01..06", "zone": "D 区", "count": 6, "alarmCount": 1},
            ],
        },

        # ===== 冷却液品质 =====
        "coolantQuality": {
            "type": "25% 乙二醇溶液",
            "conductivity": 12.5,          # μS/cm
            "ph": 8.2,
            "corrosionInhibitor": 98,       # % 腐蚀抑制剂浓度（正常值）
            "glycolConcentration": 25.2,    # % 乙二醇浓度
            "particleCount": 85,            # 颗粒数/mL (ISO 4406)
            "lastTested": "2026-07-25T10:00:00Z",
            "nextTest": "2026-08-25T10:00:00Z",
            "status": "正常",
        },

        # ===== 二次侧热排放（散热至冷却塔/干冷器）=====
        "heatRejection": {
            "type": "闭式冷却塔 + 干冷器",
            "towerFans": [
                {"id": "LCT-01", "state": "运行", "fanHz": 42, "outletTemp": 28.2, "approach": 3.8},
                {"id": "LCT-02", "state": "运行", "fanHz": 44, "outletTemp": 28.4, "approach": 4.0},
                {"id": "LCT-03", "state": "运行", "fanHz": 40, "outletTemp": 28.1, "approach": 3.7},
                {"id": "LCT-04", "state": "待机", "fanHz": 0, "outletTemp": "-", "approach": "-"},
            ],
            "dryCoolers": [
                {"id": "DC-01", "state": "备用", "fanHz": 0, "ambientT": 26.3},
                {"id": "DC-02", "state": "备用", "fanHz": 0, "ambientT": 26.3},
            ],
            "rejectionPumps": [
                {"id": "LRP-01", "state": "运行", "hz": 45, "kw": 18.5},
                {"id": "LRP-02", "state": "运行", "hz": 45, "kw": 18.2},
                {"id": "LRP-03", "state": "待机", "hz": 0, "kw": 0},
            ],
            "totalHeatRejected": 6.2,  # MW 总散热量
            "approachTemp": 3.8,       # ℃ 逼近温度
            "freeCoolingAvailable": True,
        },

        # ===== 余热回收 =====
        "heatRecoveryDetail": {
            "enabled": True,
            "recoveryRate": 1.2,       # MW
            "recoveryTemp": 48.5,      # ℃ 余热供应温度
            "returnTemp": 36.2,        # ℃ 余热回水温度
            "flow": 85,                # m³/h
            "usageType": "园区供暖",
            "co2Reduction": 3200,      # 吨/年 CO2减排
            "annualSaving": 1800000,   # 元/年 节费
        },

        # ===== 控制策略与告警阈值 =====
        "controlStrategy": {
            "primarySupplySetpoint": 32.0,     # ℃ 一次侧供水设定
            "secondarySupplySetpoint": 35.0,   # ℃ 二次侧供液设定
            "approachTarget": 3.5,             # ℃ 换热器逼近温差目标
            "glycolMin": 20,                   # % 乙二醇最低浓度
            "conductivityMax": 50,             # μS/cm 电导率上限
            "leakResponseTime": 30,            # s 漏液响应时间
            "pumpRedundancy": "N+1",
            "cdurRedundancy": "N+1",
            "description": "一次侧中温水(32/38℃)经 CDU 板换换至二次侧洁净液(35/45℃)送至冷板；CDU 内置精密温控+PID 调节，支持 N+1 冗余自动切换。",
        },

        # ===== 趋势数据(48点/分钟, 供 sparkline) =====
        "supplyTempTrend": [round(34.5 + math.sin(i/48*math.pi*2)*0.8 + (_rng.random()-0.5)*0.4, 1) for i in range(48)],
        "returnTempTrend": [round(44.5 + math.sin(i/48*math.pi*2)*1.2 + (_rng.random()-0.5)*0.6, 1) for i in range(48)],
        "flowTrend": [round(510 + math.sin(i/48*math.pi*2)*25 + (_rng.random()-0.5)*10, 0) for i in range(48)],
        "deltaTTrend": [round(9.8 + math.sin(i/48*math.pi*2)*0.8 + (_rng.random()-0.5)*0.3, 1) for i in range(48)],

        # ===== 知识面板 =====
        "knowledge": {
            "arch": {
                "components": [
                    "一次侧 CDU (冷却液分配单元)",
                    "二次侧 CDU (精密流量分配)",
                    "冷板 (Cold Plate, 直接 GPU/CPU)",
                    "分/集液管路 (Manifold)",
                    "闭式冷却塔 + 干冷器",
                    "循环泵组 (N+1 冗余)",
                    "漏液检测 (绳式 + 点式)",
                    "冷却液品质监测 (电导率/pH/乙二醇)",
                    "余热回收系统",
                ],
                "design": "一次侧 32/38℃ 中温水经 CDU 换热至二次侧 35/45℃ 洁净冷却液，由 CDU 精密分配至各机柜冷板，单机柜散热能力 ≥50kW。闭塔+干冷器全年自然冷覆盖 >50% 时间。",
                "redundancy": "CDU N+1、循环泵 N+1、分集液管路双路冗余。任一 CDU 故障 30s 内自动切换。",
            },
            "logic": [
                {"title": "供液温度 PID 控制", "steps": [
                    {"step": 1, "text": "二次侧回液温度采样(周期1s)", "ok": True},
                    {"step": 2, "text": "PID 算法计算一次侧阀门开度与泵速", "ok": True},
                    {"step": 3, "text": "调节一次侧流量使二次侧供液温度稳定在 35±0.5℃", "ok": True},
                    {"step": 4, "text": "当 GPU 负载骤升(推理/训练)时前馈补偿, 温控波动 ≤1.5℃", "ok": True},
                ]},
                {"title": "漏液应急处置", "steps": [
                    {"step": 1, "text": "漏液绳/点式传感器测量信号采集(周期 ≤ 1s)", "ok": True},
                    {"step": 2, "text": "区域漏液检测 → 立即切断该区供液阀门", "ok": True},
                    {"step": 3, "text": "报警推送至运维平台 + 微信/钉钉", "ok": True},
                    {"step": 4, "text": "启动应急排水泵, 防扩散隔离", "ok": True},
                    {"step": 5, "text": "运维人员现场确认 + 手动复位", "ok": True},
                ]},
                {"title": "自然冷切换策略", "steps": [
                    {"step": 1, "text": "室外湿球温度 < 12℃ 启动干冷器预冷", "ok": True},
                    {"step": 2, "text": "湿球 < 8℃ 部分自然冷模式 (闭塔低功率)", "ok": True},
                    {"step": 3, "text": "湿球 < 4℃ 完全自然冷模式 (闭塔旁通, 干冷器工作)", "ok": True},
                    {"step": 4, "text": "全年自然冷可利用时间 > 4380h (50%+)", "ok": True},
                ]},
            ],
            "thresholds": {
                "supplyTempHigh": 37.0,     # ℃ 供液温度告警
                "supplyTempLow": 32.0,      # ℃ 供液温度低告警
                "returnTempHigh": 50.0,     # ℃ 回液温度告警
                "deltaTHigh": 14.0,         # ℃ 供回温差告警
                "gpuTempMax": 85.0,         # ℃ GPU 核心温度上限
                "gpuTempThrottle": 80.0,    # ℃ GPU 降频温度
                "flowMin": 0.5,             # L/min 冷板最低流量
                "conductivityMax": 50.0,    # μS/cm
                "phMin": 7.0, "phMax": 9.5,
                "glycolMin": 20.0, "glycolMax": 30.0,
            },
            "note": "液冷是智算中心散热的必然选择——单 GPU 功耗超 700W, 风冷已无法满足密集部署需求。冷板式液冷可直接带走 GPU 热量的 80%+, PUE 可从 1.4 降至 1.1 以下。与传统冷冻水 (7/12℃) 不同, 液冷采用中温水 (32/38℃) 架构, 大幅提升自然冷利用时间, 降低全年冷机能耗 40%+。",
        },
    }


def crac():
    # 室外参考温度 (用于房间内外差 / 自然冷判据)
    outdoor_ref = round(rnd(2, 38, 1), 1)

    room_names = ["A 包间", "B 包间", "C 包间", "D 包间", "E 包间", "F 包间"]
    leak_zones = [
        ("机柜区东侧", 1), ("机柜区西侧", 2), ("UPS 区", 3),
        ("主走道北段", 4), ("主走道南段", 5), ("电池室", 6),
    ]

    rooms = []
    for i, name in enumerate(room_names):
        avg_temp = rnd(22.0, 26.0, 1)
        avg_rh = rnd(40, 55, 0)
        hot = round(avg_temp + rnd(6, 11, 1), 1)        # 热通道温度
        cold = round(avg_temp - rnd(4, 9, 1), 1)         # 冷通道温度
        hot_rh = rnd(28, 42, 0)
        cold_rh = rnd(45, 62, 0)
        dew = round(avg_temp - rnd(2, 6, 1), 1)
        in_out = round(avg_temp - outdoor_ref, 1)          # 室内减室外
        leak_on = _rng.random() < 0.08
        room_leak = {
            "status": "报警" if leak_on else "正常",
            "level": "严重" if leak_on else "正常",
            "position": round(rnd(8.5, 42.0), 1) if leak_on else None,
            "zone": leak_zones[i][1],
        }
        rooms.append({
            "id": name, "name": name,
            "avgTemp": avg_temp, "avgRh": avg_rh,
            "hotAisle": hot, "hotRh": hot_rh,
            "coldAisle": cold, "coldRh": cold_rh,
            "inOutDiff": in_out,
            "dewPoint": dew,
            "cracRun": pick([6, 7, 8]), "cracN": 8, "state": "正常",
            "leak": room_leak,
        })

    # 精密空调机组 (包间级 + 列间)
    crac_units = {"A 包间": 4, "B 包间": 3, "C 包间": 3}
    units = []
    idx = 0
    for room, n in crac_units.items():
        prefix = room[0]
        for k in range(n):
            offline = idx == 7
            standby = idx == 4
            state = "故障" if offline else ("待机" if standby else "运行")
            supply_t = "-" if (offline or standby) else rnd(17.5, 19.5, 1)
            return_t = "-" if (offline or standby) else rnd(26, 30, 1)
            chilled_wt = "-" if (offline or standby) else rnd(8.5, 11.5, 1)
            return_wt = "-" if (offline or standby) else rnd(14.0, 17.5, 1)
            fan = 0 if (offline or standby) else rnd(60, 90, 0)
            valve = 0 if (offline or standby) else rnd(35, 85, 0)
            wvalve = 0 if (offline or standby) else rnd(40, 80, 0)
            power = 0 if (offline or standby) else rnd(8, 22, 1)
            dp = "-" if (offline or standby) else rnd(40, 120, 0)
            units.append({
                "id": f"CRAC-{prefix}{str(k + 1).zfill(2)}",
                "room": room,
                "type": "列间空调" if k % 3 == 0 else "房间级精密空调",
                "state": state,
                "supplyT": supply_t, "returnT": return_t,
                "supplyRh": "-" if (offline or standby) else rnd(40, 55, 0),
                "returnRh": "-" if (offline or standby) else rnd(45, 60, 0),
                "chilledWaterT": chilled_wt, "returnWaterT": return_wt,
                "fan": fan, "valve": valve, "waterValve": wvalve,
                "power": power, "dp": dp,
                "filter": "脏堵" if (not offline and _rng.random() < 0.1) else "正常",
                "control": {
                    "fanEnable": not standby,
                    "fanSpeedSet": fan if not standby else 0,
                    "waterValveSet": wvalve if not standby else 0,
                    "coolingMode": "制冷" if not offline else "停机",
                    "humidOn": _rng.random() < 0.3,
                },
                "setpoints": {
                    "supplyTSet": 18.0, "rhSet": 50.0, "roomTSet": 24.0,
                    "highTempAlarm": 30.0, "lowTempAlarm": 18.0, "highRhAlarm": 60.0,
                },
            })
            idx += 1

    # 定位式漏水检测线缆 (沿包间/区域敷设, 可定位漏点距离)
    leak_devices = []
    leak_alarm = 0
    for i, (loc, zid) in enumerate(leak_zones):
        on = _rng.random() < 0.08
        pos = round(rnd(8.5, 42.0), 1) if on else None
        leak_devices.append({
            "id": f"LEAK-{str(i + 1).zfill(2)}",
            "location": loc,
            "zone": zid,
            "status": "报警" if on else "正常",
            "position": pos,
            "cableLength": round(rnd(45.0, 60.0), 1),
            "cableStatus": "断线" if _rng.random() < 0.03 else "正常",
        })
        if on:
            leak_alarm += 1

    running = sum(1 for u in units if u["state"] == "运行")
    standby_n = sum(1 for u in units if u["state"] == "待机")
    fault = sum(1 for u in units if u["state"] == "故障")
    sup = [u["supplyT"] for u in units if isinstance(u["supplyT"], (int, float))]
    ret = [u["returnT"] for u in units if isinstance(u["returnT"], (int, float))]
    cw = [u["chilledWaterT"] for u in units if isinstance(u["chilledWaterT"], (int, float))]
    rw = [u["returnWaterT"] for u in units if isinstance(u["returnWaterT"], (int, float))]
    avg_supply = round(sum(sup) / len(sup), 1) if sup else 0
    avg_return = round(sum(ret) / len(ret), 1) if ret else 0
    avg_cw = round(sum(cw) / len(cw), 1) if cw else 0
    avg_rw = round(sum(rw) / len(rw), 1) if rw else 0
    avg_inout = round(sum(r["inOutDiff"] for r in rooms) / len(rooms), 1)

    return {
        "summary": {
            "total": len(units), "running": running, "standby": standby_n,
            "fault": fault, "maint": 0,
            "avgSupply": avg_supply, "avgReturn": avg_return,
            "avgSupplyWater": avg_cw, "avgReturnWater": avg_rw,
            "outdoorRef": outdoor_ref,
            "avgInOutDiff": avg_inout,
            "leakAlarm": leak_alarm, "leakTotal": len(leak_devices),
        },
        "rooms": rooms,
        "units": units,
        "leak": {
            "total": len(leak_devices), "alarm": leak_alarm,
            "devices": leak_devices,
        },
        "fresh": [
            {"id": "FAU-01", "state": "运行", "supplyT": 20.1, "rh": 55, "co2": 520, "filterDp": 86},
            {"id": "FAU-02", "state": "运行", "supplyT": 20.3, "rh": 54, "co2": 545, "filterDp": 92},
            {"id": "FAU-03", "state": "待机", "supplyT": "-", "rh": "-", "co2": "-", "filterDp": 44},
        ],
        "humid": [
            {"id": "HUM-01", "name": "恒湿机", "state": "运行", "rh": 51, "mode": "加湿"},
            {"id": "HUM-02", "name": "恒湿机", "state": "运行", "rh": 49, "mode": "除湿"},
            {"id": "HUM-03", "name": "恒湿机", "state": "待机", "rh": "-", "mode": "-"},
        ],
        "funcRooms": [
            {"id": "电池室 A", "t": 24.2, "rh": 48}, {"id": "电池室 B", "t": 24.6, "rh": 47},
            {"id": "UPS 室", "t": 25.1, "rh": 45}, {"id": "网络汇聚间", "t": 23.8, "rh": 50},
            {"id": "消防控制室", "t": 25.4, "rh": 52}, {"id": "柴发机房", "t": 28.9, "rh": 55},
        ],
        # ===== 末端控制策略（手册）=====
        "ctrl": {
            "humId": {"rhLowOn": 30, "rhHighOff": 65,
                       "desc": "恒湿一体机：相对湿度 < 30% 开启加湿，> 65% 开启除湿"},
            "positivePressure": {"min": 5, "max": 10, "unit": "Pa",
                                "desc": "包间与走廊压差（正压）维持 5~10Pa，新风变频按压差调节"},
            "secPump": {"diffTarget": 0.1, "diffUnit": "MPa", "addHz": 50, "addDelayMin": 5,
                         "reduceHz": 35, "reduceDelayMin": 5, "minRun": 1,
                         "desc": "二次泵维持末端压差 0.1MPa：频率=50Hz 延时5min 增开一台；均<35Hz 延时5min 关一台；运行数量≥1台"},
        },
        "knowledge": {
            "arch": {
                "components": ["房间级/列间精密空调", "风机/压缩机/加湿", "温湿度/漏水传感器", "正压/压差控制", "二次泵(冷冻水)", "新风/排风"],
                "design": "冷热通道隔离、近端制冷；正压防尘，相对湿度维持 40~55%。",
                "redundancy": "N+1 机组冗余，单台故障后其余加载。",
            },
            "logic": [
                {"title": "温升趋势告警(DCGoT)", "steps": [
                    {"step": 1, "text": "包间多点温湿度时序采集", "ok": True},
                    {"step": 2, "text": "时空图模型(GoT)识别异常趋势", "ok": True},
                    {"step": 3, "text": "提前 ≥10min 预警，争取处置窗口", "ok": True},
                    {"step": 4, "text": "告警有效率 99.5%，告警量 ↓58.5%", "ok": True},
                ]},
            ],
            "note": "机房温升(冷热通道温度异常)是 IT 宕机首要诱因；末端空调失效将直接推高包间温度，需以趋势预警替代单一阈值报警。",
        },
    }


# ------------------------------------------------------------------ 电力
def hv():
    incomers = [
        {"id": "10KV 1# 进线", "src": "城东 220KV 变电站", "state": "合闸", "breaker": "合闸",
         "ua": 10.41, "ub": 10.43, "uc": 10.42, "u": 10.42,
         "ia": 388, "ib": 383, "ic": 387, "i": 386,
         "p": 6.62, "q": 1.93, "pf": 0.96, "freq": 50.01, "energy": 142860},
        {"id": "10KV 2# 进线", "src": "城西 220KV 变电站", "state": "合闸", "breaker": "合闸",
         "ua": 10.37, "ub": 10.39, "uc": 10.38, "u": 10.38,
         "ia": 374, "ib": 369, "ic": 372, "i": 371,
         "p": 6.35, "q": 1.85, "pf": 0.95, "freq": 49.99, "energy": 138420},
    ]
    feeders = [
        {"id": "F-01", "load": "1# 变压器", "state": "合闸", "breaker": "合闸",
         "ua": 10.41, "ub": 10.42, "uc": 10.43, "ia": 124, "ib": 120, "ic": 122, "i": 122,
         "p": 2.05, "pf": 0.95, "energy": 42150},
        {"id": "F-02", "load": "2# 变压器", "state": "合闸", "breaker": "合闸",
         "ua": 10.40, "ub": 10.41, "uc": 10.42, "ia": 120, "ib": 117, "ic": 118, "i": 118,
         "p": 1.98, "pf": 0.94, "energy": 40780},
        {"id": "F-03", "load": "3# 变压器", "state": "合闸", "breaker": "合闸",
         "ua": 10.42, "ub": 10.43, "uc": 10.44, "ia": 128, "ib": 124, "ic": 126, "i": 126,
         "p": 2.12, "pf": 0.96, "energy": 43890},
        {"id": "F-04", "load": "4# 变压器", "state": "合闸", "breaker": "合闸",
         "ua": 10.39, "ub": 10.40, "uc": 10.41, "ia": 116, "ib": 112, "ic": 114, "i": 114,
         "p": 1.92, "pf": 0.93, "energy": 39620},
        {"id": "F-05", "load": "冷机房变", "state": "合闸", "breaker": "合闸",
         "ua": 10.38, "ub": 10.39, "uc": 10.40, "ia": 98, "ib": 95, "ic": 96, "i": 96,
         "p": 1.61, "pf": 0.92, "energy": 33140},
        {"id": "F-06", "load": "备用", "state": "分闸", "breaker": "分闸",
         "ua": 10.40, "ub": 10.41, "uc": 10.42, "ia": 0, "ib": 0, "ic": 0, "i": 0,
         "p": 0, "pf": 0, "energy": 0},
    ]
    # 10KV/0.4KV 配电变压器 — 由出线供电, 含温湿度与遥测/遥信
    transformers = [
        {"id": "1# 变压器 2500kVA", "feeder": "F-01", "state": "运行",
         "load": 61, "uHigh": 10.42, "iHigh": 122, "uLow": 0.398, "iLow": 1860,
         "windingT": 78, "oilT": 62, "ambT": 26.5, "humidity": 48, "tap": 5, "fan": "运行",
         "signals": [
             {"name": "运行状态", "value": "运行", "level": "g"},
             {"name": "高压断路器", "value": "合闸", "level": "g"},
             {"name": "低压断路器", "value": "合闸", "level": "g"},
             {"name": "轻瓦斯", "value": "无", "level": "g"},
             {"name": "重瓦斯", "value": "无", "level": "g"},
             {"name": "绕组超温", "value": "无", "level": "g"},
             {"name": "压力释放", "value": "无", "level": "g"},
             {"name": "冷却风机", "value": "运行", "level": "g"},
             {"name": "有载调压", "value": "自动 5档", "level": "b"},
         ]},
        {"id": "2# 变压器 2500kVA", "feeder": "F-02", "state": "运行",
         "load": 58, "uHigh": 10.41, "iHigh": 118, "uLow": 0.397, "iLow": 1795,
         "windingT": 76, "oilT": 60, "ambT": 26.2, "humidity": 47, "tap": 5, "fan": "运行",
         "signals": [
             {"name": "运行状态", "value": "运行", "level": "g"},
             {"name": "高压断路器", "value": "合闸", "level": "g"},
             {"name": "低压断路器", "value": "合闸", "level": "g"},
             {"name": "轻瓦斯", "value": "无", "level": "g"},
             {"name": "重瓦斯", "value": "无", "level": "g"},
             {"name": "绕组超温", "value": "无", "level": "g"},
             {"name": "压力释放", "value": "无", "level": "g"},
             {"name": "冷却风机", "value": "运行", "level": "g"},
             {"name": "有载调压", "value": "自动 5档", "level": "b"},
         ]},
        {"id": "3# 变压器 2500kVA", "feeder": "F-03", "state": "运行",
         "load": 63, "uHigh": 10.43, "iHigh": 126, "uLow": 0.399, "iLow": 1910,
         "windingT": 81, "oilT": 64, "ambT": 26.8, "humidity": 49, "tap": 4, "fan": "运行",
         "signals": [
             {"name": "运行状态", "value": "运行", "level": "g"},
             {"name": "高压断路器", "value": "合闸", "level": "g"},
             {"name": "低压断路器", "value": "合闸", "level": "g"},
             {"name": "轻瓦斯", "value": "无", "level": "g"},
             {"name": "重瓦斯", "value": "无", "level": "g"},
             {"name": "绕组超温", "value": "预警", "level": "a"},
             {"name": "压力释放", "value": "无", "level": "g"},
             {"name": "冷却风机", "value": "运行", "level": "g"},
             {"name": "有载调压", "value": "自动 4档", "level": "b"},
         ]},
        {"id": "4# 变压器 2500kVA", "feeder": "F-04", "state": "运行",
         "load": 55, "uHigh": 10.40, "iHigh": 114, "uLow": 0.396, "iLow": 1670,
         "windingT": 74, "oilT": 59, "ambT": 26.1, "humidity": 46, "tap": 6, "fan": "运行",
         "signals": [
             {"name": "运行状态", "value": "运行", "level": "g"},
             {"name": "高压断路器", "value": "合闸", "level": "g"},
             {"name": "低压断路器", "value": "合闸", "level": "g"},
             {"name": "轻瓦斯", "value": "无", "level": "g"},
             {"name": "重瓦斯", "value": "无", "level": "g"},
             {"name": "绕组超温", "value": "无", "level": "g"},
             {"name": "压力释放", "value": "无", "level": "g"},
             {"name": "冷却风机", "value": "运行", "level": "g"},
             {"name": "有载调压", "value": "自动 6档", "level": "b"},
         ]},
        {"id": "冷机房变 1600kVA", "feeder": "F-05", "state": "运行",
         "load": 52, "uHigh": 10.39, "iHigh": 96, "uLow": 0.395, "iLow": 1380,
         "windingT": 71, "oilT": 57, "ambT": 27.3, "humidity": 51, "tap": 5, "fan": "运行",
         "signals": [
             {"name": "运行状态", "value": "运行", "level": "g"},
             {"name": "高压断路器", "value": "合闸", "level": "g"},
             {"name": "低压断路器", "value": "合闸", "level": "g"},
             {"name": "轻瓦斯", "value": "无", "level": "g"},
             {"name": "重瓦斯", "value": "无", "level": "g"},
             {"name": "绕组超温", "value": "无", "level": "g"},
             {"name": "压力释放", "value": "无", "level": "g"},
             {"name": "冷却风机", "value": "运行", "level": "g"},
             {"name": "有载调压", "value": "自动 5档", "level": "b"},
         ]},
    ]
    return {
        "scheme": "两路市电 + 母联备自投 (单母线分段)",
        "incomers": incomers,
        "busTie": {"id": "10KV 母联 QF-M", "state": "分闸(热备用)", "autoSwitch": "投入", "mode": "备自投·自动"},
        "ats": {"logic": "任一进线失压 → 延时 2.5s 确认 → 跳故障进线 → 合母联 (先分后合)",
                "lastTest": "2026-07-05 全停演练通过", "switchTime": "1.82s"},
        "feeders": feeders,
        "transformers": transformers,
        "quality": {"thdU": 2.1, "thdI": 3.4, "unbalance": 0.8},
        "knowledge": {
            "thresholds": [
                {"k": "额定线电压", "v": "10 kV"},
                {"k": "电压偏差", "v": "±7%", "note": "GB 50174 电子信息机房"},
                {"k": "额定频率", "v": "50 Hz"},
                {"k": "失电确认延时", "v": "3 s", "note": "时间可调"},
                {"k": "馈线断开延时", "v": "2 s"},
                {"k": "母联合闸延时", "v": "2 s"},
                {"k": "分步合闸步距", "v": "2 s"},
                {"k": "市电恢复延时", "v": "10 min", "note": "1~10 可调"},
                {"k": "柴发启动超时", "v": "3~10 min", "note": "超时判并机故障"},
                {"k": "ATS 切换中断", "v": "<100 ms", "note": "低于高压侧响应"},
                {"k": "可调延时范围", "v": "0~60 s", "note": "调试后固化，部分 HMI 可调"},
            ],
            "arch": {
                "components": ["高压隔离柜", "高压电压电流互感器柜(PT/CT)", "高压断路器柜", "高压计量柜", "母联柜(备自投)", "馈线柜"],
                "design": "系统通过双环、双星型网络实现高可用；按不同场景实现两路市电并用 / 市电与柴发并用 / 柴发与 UPS 并用等切换。",
                "redundancy": "双路市电独立电源(城东/城西 220KV 变电站) + 母联备自投",
            },
            "logic": [
                {
                    "title": "市电电源互锁逻辑(两锁三钥匙)",
                    "steps": [
                        {"step": 1, "text": "同组两路市电进线、两路柴发进线、母联开关柜断路器之间设电气联锁", "ok": True},
                        {"step": 2, "text": "只有两只市电开关及母联开关均断开时，才能闭合发电机进线开关", "ok": True},
                        {"step": 3, "text": "只有两只发电机进线开关均断开时，才能闭合市电进线开关与母线开关", "ok": True},
                        {"step": 4, "text": "三只开关(两路市电+母联)同一时间最多只允许合其二", "ok": True},
                    ],
                },
                {
                    "title": "市电之间切换逻辑",
                    "steps": [
                        {"step": 1, "text": "任一路市电进线前 PT 失电且开关无保护动作 → 监测另一路 PT 有压，延时 3s 断开该进线开关", "ok": True},
                        {"step": 2, "text": "延时 2s 断开失电母线上的馈出开关", "ok": True},
                        {"step": 3, "text": "延时 2s 闭合母联开关", "ok": True},
                        {"step": 4, "text": "按 2s 步距分步闭合失电母线馈出开关", "ok": True},
                        {"step": 5, "text": "失电恢复后经延时 10min(1~10 可调) 先断母联→断馈出→合进线→分步合馈出；或手动恢复", "ok": True},
                    ],
                },
                {
                    "title": "市电↔柴发切换逻辑",
                    "steps": [
                        {"step": 1, "text": "两路市电 PT 均失电且开关无保护分闸 → 延时 5s 断开市电进线/母联，延时 2s 断本段馈电，发柴发启动信号", "ok": True},
                        {"step": 2, "text": "并机系统收到信号后所有机组启动并在应急母线并机，闭合并机馈出开关向市电母线供电", "ok": True},
                        {"step": 3, "text": "启动信号发出后超过 3~10min 柴发 PT 仍无压 → 判并机系统故障，中止备自投逻辑", "ok": True},
                        {"step": 4, "text": "柴发进线 PT 带电且市电无压 → 延时 2s 闭合备用电源进线开关", "ok": True},
                        {"step": 5, "text": "按 2s 步序合闸变压器馈线 → 完成市电切柴发分步加载", "ok": True},
                        {"step": 6, "text": "仅一台柴发 PT 有压不自动合母联(可手动)；市电恢复延时 10min 跳油机进线→确认全部分位→分步恢复市电", "ok": True},
                    ],
                },
                {
                    "title": "故障切换逻辑",
                    "steps": [
                        {"step": 1, "text": "切换过程中控制/被控设备故障 → 报警并转手动；进线/柴发进线/母联因保护分闸且动作失败 → 终止自动逻辑，运维现场排查", "ok": True},
                        {"step": 2, "text": "本段某馈线开关处于分闸 → 分步合闸过程不向其发合闸令", "ok": True},
                        {"step": 3, "text": "备自投控制器 Modbus TCP 服务端(只监不控)，动环/电力监控可读取信号数据", "ok": True},
                        {"step": 4, "text": "控制器与 IO 模块由双路 UPS 交流 220V 供电；调试期时间可调，运行后固化，部分延时 HMI 可调(0~60s)", "ok": True},
                    ],
                },
            ],
            "faults": [
                {"no": 1, "fault": "备自投控制器故障", "lock": "自动逻辑终止", "action": "报警转手动，运维现场排查", "manualReset": True},
                {"no": 2, "fault": "进线/母联保护分闸", "lock": "动作失败即停止自动逻辑", "action": "排查保护原因(过流/接地等)后复位", "manualReset": True},
                {"no": 3, "fault": "柴发并机系统故障(启动超时)", "lock": "中止柴发备自投", "action": "检查机组启动/并机控制，必要时手动", "manualReset": True},
                {"no": 4, "fault": "馈线开关分闸态", "lock": "分步合闸跳过该开关", "action": "确认开关状态及负荷，不误合闸", "manualReset": False},
                {"no": 5, "fault": "通讯中断(Modbus TCP)", "lock": "仅监视不控制", "action": "检查网口/交换机，ping 控制器 IP", "manualReset": False},
                {"no": 6, "fault": "控制器电源失电", "lock": "双路 UPS 交流 220V 失电", "action": "检查 UPS 供电与整流模块", "manualReset": False},
            ],
            "note": "高压备自投核心目标：两路市电互为备用、市电与柴发互为备用，确保供电连续性。所有切换时序均可在调试期调整，投入运行后需固化并记录。",
        },
    }


def lv():
    transformers = [
        {"id": "T1 2500KVA", "load": 61, "t": 78, "state": "运行",
         "u": 0.398, "i": 1860, "p": 1455, "q": 430, "pf": 0.96, "freq": 50.02,
         "energy": 28940, "thdu": 2.3, "thdi": 4.1},
        {"id": "T2 2500KVA", "load": 58, "t": 76, "state": "运行",
         "u": 0.397, "i": 1795, "p": 1380, "q": 410, "pf": 0.96, "freq": 50.01,
         "energy": 27620, "thdu": 2.2, "thdi": 4.0},
        {"id": "T3 2500KVA", "load": 63, "t": 81, "state": "运行",
         "u": 0.399, "i": 1910, "p": 1505, "q": 450, "pf": 0.96, "freq": 50.02,
         "energy": 30110, "thdu": 2.5, "thdi": 4.3},
        {"id": "T4 2500KVA", "load": 55, "t": 74, "state": "运行",
         "u": 0.396, "i": 1670, "p": 1295, "q": 380, "pf": 0.96, "freq": 50.00,
         "energy": 25900, "thdu": 2.1, "thdi": 3.9},
    ]
    upsGroups = [
        {"id": "UPS-A 组 (2N)", "n": "4×600KVA", "load": 47, "uIn": 380, "uOut": 380, "mode": "在线双变换", "bypass": "正常", "state": "正常",
         "iIn": 720, "iOut": 700, "p": 268, "pf": 0.98, "freq": 50.01, "energyIn": 6420, "thdu": 1.6, "thdi": 3.2},
        {"id": "UPS-B 组 (2N)", "n": "4×600KVA", "load": 45, "uIn": 381, "uOut": 380, "mode": "在线双变换", "bypass": "正常", "state": "正常",
         "iIn": 690, "iOut": 672, "p": 255, "pf": 0.98, "freq": 50.02, "energyIn": 6110, "thdu": 1.5, "thdi": 3.0},
    ]
    hvdc = [
        {"id": "HVDC-01", "u": 243.2, "load": 52, "modN": 40, "modRun": 26, "state": "正常",
         "i": 530, "p": 126, "pf": 0.99, "energy": 2980, "thdi": 2.8},
        {"id": "HVDC-02", "u": 242.8, "load": 49, "modN": 40, "modRun": 24, "state": "正常",
         "i": 499, "p": 119, "pf": 0.99, "energy": 2810, "thdi": 2.6},
        {"id": "HVDC-03", "u": 243.5, "load": 54, "modN": 40, "modRun": 27, "state": "正常",
         "i": 551, "p": 131, "pf": 0.99, "energy": 3120, "thdi": 2.9},
    ]
    ats = [
        {"id": "ATS-01 制冷动力", "state": "常用侧", "mode": "自动", "lastSw": "2026-06-18 演练", "uIn": 381, "uOut": 380, "pf": 0.95, "p": 320},
        {"id": "ATS-02 应急照明", "state": "常用侧", "mode": "自动", "lastSw": "2026-06-18 演练", "uIn": 380, "uOut": 379, "pf": 0.92, "p": 58},
        {"id": "ATS-03 消防负荷", "state": "常用侧", "mode": "自动", "lastSw": "2026-05-22 演练", "uIn": 382, "uOut": 381, "pf": 0.90, "p": 88},
        {"id": "ATS-04 安防负荷", "state": "常用侧", "mode": "自动", "lastSw": "2026-05-22 演练", "uIn": 380, "uOut": 380, "pf": 0.93, "p": 42},
    ]
    busbars = [{"id": f"母排 BB-{str(i+1).zfill(2)}", "load": rnd(38, 68, 0),
                "i": rnd(800, 1500, 0), "state": "正常",
                "u": 0.398, "pf": 0.95, "energy": rnd(8000, 16000, 0), "thdu": rnd(2, 3, 1)}
               for i in range(8)]
    # 低压馈线回路（出线/断路器柜）—— 全电参量采集
    branches = [
        {"id": "LP-A01", "name": "A 栋 IT 机柜排 1", "breaker": "合闸", "rated": 630,
         "ua": 228, "ub": 230, "uc": 229, "u": 229, "ia": 412, "ib": 398, "ic": 405, "i": 405,
         "freq": 50.02, "p": 268, "q": 76, "pf": 0.96, "energy": 5210, "thdu": 2.4, "thdi": 5.1, "loadPct": 64},
        {"id": "LP-A02", "name": "A 栋 IT 机柜排 2", "breaker": "合闸", "rated": 630,
         "ua": 229, "ub": 231, "uc": 230, "u": 230, "ia": 396, "ib": 388, "ic": 391, "i": 392,
         "freq": 50.01, "p": 255, "q": 72, "pf": 0.95, "energy": 4980, "thdu": 2.3, "thdi": 5.3, "loadPct": 62},
        {"id": "LP-B01", "name": "B 栋 IT 机柜排 1", "breaker": "合闸", "rated": 630,
         "ua": 227, "ub": 229, "uc": 228, "u": 228, "ia": 428, "ib": 414, "ic": 421, "i": 421,
         "freq": 50.02, "p": 272, "q": 80, "pf": 0.96, "energy": 5330, "thdu": 2.5, "thdi": 5.0, "loadPct": 67},
        {"id": "LP-B02", "name": "B 栋 IT 机柜排 2", "breaker": "合闸", "rated": 630,
         "ua": 230, "ub": 228, "uc": 229, "u": 229, "ia": 380, "ib": 372, "ic": 375, "i": 376,
         "freq": 50.00, "p": 242, "q": 68, "pf": 0.94, "energy": 4730, "thdu": 2.2, "thdi": 5.4, "loadPct": 59},
        {"id": "LP-C01", "name": "制冷机组 A", "breaker": "合闸", "rated": 400,
         "ua": 226, "ub": 228, "uc": 227, "u": 227, "ia": 296, "ib": 288, "ic": 292, "i": 292,
         "freq": 49.99, "p": 188, "q": 70, "pf": 0.93, "energy": 3680, "thdu": 2.8, "thdi": 7.2, "loadPct": 73},
        {"id": "LP-C02", "name": "制冷机组 B", "breaker": "合闸", "rated": 400,
         "ua": 229, "ub": 227, "uc": 228, "u": 228, "ia": 281, "ib": 274, "ic": 277, "i": 277,
         "freq": 50.01, "p": 179, "q": 66, "pf": 0.92, "energy": 3510, "thdu": 2.9, "thdi": 7.5, "loadPct": 69},
        {"id": "LP-D01", "name": "应急照明 / 消防", "breaker": "合闸", "rated": 160,
         "ua": 230, "ub": 231, "uc": 229, "u": 230, "ia": 98, "ib": 92, "ic": 95, "i": 95,
         "freq": 50.00, "p": 58, "q": 22, "pf": 0.91, "energy": 980, "thdu": 1.9, "thdi": 3.1, "loadPct": 59},
        {"id": "LP-D02", "name": "安防 / 弱电", "breaker": "合闸", "rated": 160,
         "ua": 231, "ub": 229, "uc": 230, "u": 230, "ia": 72, "ib": 69, "ic": 70, "i": 70,
         "freq": 50.01, "p": 42, "q": 16, "pf": 0.90, "energy": 760, "thdu": 1.8, "thdi": 2.9, "loadPct": 44},
        {"id": "LP-E01", "name": "备用回路", "breaker": "分闸", "rated": 250,
         "ua": 230, "ub": 230, "uc": 230, "u": 230, "ia": 0, "ib": 0, "ic": 0, "i": 0,
         "freq": 50.00, "p": 0, "q": 0, "pf": 0, "energy": 0, "thdu": 0, "thdi": 0, "loadPct": 0},
    ]
    # 防雷 / 浪涌保护器 (SPD)
    spds = [
        {"id": "配电间 A 进线柜 SPD", "state": "正常", "level": "g", "leakI": 0.08, "count": 2, "status": "正常"},
        {"id": "配电间 B 进线柜 SPD", "state": "正常", "level": "g", "leakI": 0.11, "count": 1, "status": "正常"},
        {"id": "UPS 室 A SPD", "state": "正常", "level": "g", "leakI": 0.05, "count": 0, "status": "正常"},
        {"id": "UPS 室 B SPD", "state": "劣化", "level": "a", "leakI": 0.62, "count": 7, "status": "报警"},
        {"id": "制冷机房 SPD", "state": "正常", "level": "g", "leakI": 0.09, "count": 3, "status": "正常"},
        {"id": "弱电井 SPD", "state": "正常", "level": "g", "leakI": 0.04, "count": 0, "status": "正常"},
    ]
    return {
        "transformers": transformers,
        "upsGroups": upsGroups,
        "hvdc": hvdc,
        "ats": ats,
        "busbars": busbars,
        "branches": branches,
        "spds": spds,
        "knowledge": {
            "thresholds": [
                {"k": "配电层级", "v": "总进线 → UPS → PDU(机柜)"},
                {"k": "ATS 切换中断", "v": "<100 ms", "note": "101V 时约 3ms，低于高压侧响应"},
                {"k": "ATS 切换延时", "v": "100 ms"},
                {"k": "市电恢复切换", "v": "自动转换(先断后合)"},
                {"k": "UPS 模式", "v": "在线双变换 / 逆变后备"},
                {"k": "谐波 THDu 限值", "v": "5%"},
                {"k": "谐波 THDi 限值", "v": "8%"},
                {"k": "可调延时范围", "v": "0~60 s"},
            ],
            "arch": {
                "components": ["一级配电 低压总进线", "自动转换开关 ATS", "二级配电 UPS 不间断电源", "列头柜", "末端机柜 PDU", "动力配电(新风/暖通)"],
                "design": "低压总进线接入 ATS，任一回路断电时 ATS 自动转换(中断<100ms)；一部分作动力配电供新风与暖通，另一部分供 UPS 为末端机柜提供不间断供电。",
                "redundancy": "双路市电 + ATS(N 侧/备用侧) + UPS 2N；PLC 主备提高可用性",
            },
            "logic": [
                {
                    "title": "倒闸送停电逻辑",
                    "steps": [
                        {"step": 1, "text": "送电时先合电源侧开关，后合负荷侧开关", "ok": True},
                        {"step": 2, "text": "停电时先拉负荷侧开关，后拉电源侧开关", "ok": True},
                    ],
                },
                {
                    "title": "储能停送电逻辑( UPS )",
                    "steps": [
                        {"step": 1, "text": "市电正常 → UPS 稳压后供电，并向机内电池充电", "ok": True},
                        {"step": 2, "text": "市电中断(事故停电) → UPS 逆变器立即将电池直流电转为 220V 交流持续供电", "ok": True},
                    ],
                },
                {
                    "title": "闭锁控制逻辑(两锁三钥匙)",
                    "steps": [
                        {"step": 1, "text": "只有两路市电开关及母联开关均断开，才能闭合发电机进线开关", "ok": True},
                        {"step": 2, "text": "切换中控制/被控设备故障 → 报警转手动现场排查", "ok": True},
                    ],
                },
                {
                    "title": "0.4KV 掉电检修倒闸",
                    "steps": [
                        {"step": 1, "text": "任一路低压总进线掉电 → ATS 自动转换(依1为主/依2为备)，延时 100ms", "ok": True},
                        {"step": 2, "text": "检修时 运行→热备用→冷备用→检修，先停一次设备后停保护/自动装置", "ok": True},
                        {"step": 3, "text": "检修后投运 先投保护/自动装置后投一次设备，冷备→热备→运行", "ok": True},
                    ],
                },
                {
                    "title": "电量预测与 PUE 优化",
                    "steps": [
                        {"step": 1, "text": "参与电网直购电/现货交易，按预测负荷曲线申报用电计划", "ok": True},
                        {"step": 2, "text": "电量预测准确率每提升 1% ≈ 节约 >100 万元/年", "ok": True},
                        {"step": 3, "text": "制冷系统占电费 ~24%，PUE 每降 0.1 显著降本", "ok": True},
                        {"step": 4, "text": "依托温升/负荷趋势预测提前调度冷机与柴发，削峰填谷", "ok": True},
                    ],
                },
            ],
            "faults": [
                {"no": 1, "fault": "ATS 切换失败", "lock": "未自动转换", "action": "检查 ATS 控制电源与机械联锁，必要时手动", "manualReset": True},
                {"no": 2, "fault": "UPS 逆变故障", "lock": "转旁路供电", "action": "排查逆变器/电池，旁路带载", "manualReset": False},
                {"no": 3, "fault": "馈线过载/谐波超标", "lock": "THDi>8% 预警", "action": "核对负荷与谐波源，调整", "manualReset": False},
                {"no": 4, "fault": "母联/ATS 通讯中断", "lock": "仅监视", "action": "检查 PLC 与 I/O 子站通讯", "manualReset": False},
                {"no": 5, "fault": "保护分闸", "lock": "终止自动逻辑", "action": "运维现场排查保护原因后复位", "manualReset": True},
            ],
            "note": "低压侧核心：ATS 保证两路市电无缝切换，UPS 保证末端 IT 设备零中断；动力与不间断供电分区设置。",
        },
    }


def genset():
    # 机组状态: DG-06 备用(空载待命), DG-07 维保(退出保护检修), 其余 6 台并机带载运行
    states = ["运行"] * 8
    states[5] = "备用"   # DG-06
    states[6] = "维保"   # DG-07

    PROT = [
        "过速保护", "低油压保护", "高水温保护", "过电流保护", "过电压保护", "欠电压保护",
        "逆功率保护", "接地故障保护", "差动保护", "失磁保护", "启动失败保护", "紧急停机",
    ]

    units = []
    for i in range(8):
        st = states[i]
        running = st == "运行"
        breaker = "合闸" if running else "分闸"
        incomer = "合闸" if running else "分闸"
        if running:
            load = rnd(62, 95, 0)
            u_base = rnd(10.4, 10.6, 2)
            ua = round(u_base + rnd(-0.05, 0.05, 2), 2)
            ub = round(u_base + rnd(-0.05, 0.05, 2), 2)
            uc = round(u_base + rnd(-0.05, 0.05, 2), 2)
            u = round((ua + ub + uc) / 3, 2)
            p = round(2500 * load / 100 * rnd(0.96, 1.04), 0)
            pf = round(rnd(0.82, 0.92), 2)
            q = round(p * math.tan(math.acos(pf)), 0)
            freq = round(rnd(49.9, 50.1, 1), 2)
            i_base = round(p / (math.sqrt(3) * u_base * pf), 0)
            ia = i_base + rnd(-6, 6, 0)
            ib = i_base + rnd(-6, 6, 0)
            ic = i_base + rnd(-6, 6, 0)
            i_avg = round((ia + ib + ic) / 3, 0)
            energy = rnd(18600, 64200, 0)
            rpm = 1500 + rnd(-3, 3, 0)
            waterT = rnd(82, 92, 0)
            oilP = round(rnd(3.6, 5.2, 1), 1)
            faults = []
            prots = [{"name": n, "state": "投入", "level": "g"} for n in PROT]
        elif st == "维保":
            ua = ub = uc = u = 0
            ia = ib = ic = i_avg = 0
            p = q = 0
            pf = 0
            freq = 0
            energy = rnd(16000, 30000, 0)
            rpm = 0
            waterT = rnd(38, 46, 0)
            oilP = 0
            faults = [
                {"name": "维保中", "value": "待检", "level": "a"},
                {"name": "启动电池", "value": "电压偏低", "level": "a"},
            ]
            prots = []
            for n in PROT:
                if n == "过速保护":
                    prots.append({"name": n, "state": "退出", "level": "a"})
                elif n == "启动失败保护":
                    prots.append({"name": n, "state": "试验", "level": "b"})
                else:
                    prots.append({"name": n, "state": "投入", "level": "g"})
        else:  # 备用
            ua = ub = uc = u = 0
            ia = ib = ic = i_avg = 0
            p = q = 0
            pf = 0
            freq = 0
            energy = rnd(20000, 40000, 0)
            rpm = 0
            waterT = rnd(38, 46, 0)
            oilP = 0
            faults = []
            prots = [{"name": n, "state": "投入", "level": "g"} for n in PROT]

        units.append({
            "id": f"DG-{str(i + 1).zfill(2)}",
            "state": st,
            "breaker": breaker,
            "incomer": incomer,
            "ua": ua, "ub": ub, "uc": uc, "u": u,
            "ia": ia, "ib": ib, "ic": ic, "i": i_avg,
            "p": p, "q": q, "pf": pf, "freq": freq, "energy": energy,
            "rpm": rpm, "waterT": waterT, "oilP": oilP,
            "battU": round(rnd(25.6, 27.2), 1),
            "heater": "投入",
            "startCnt": rnd(42, 88, 0), "runHrs": rnd(220, 480, 0),
            "faults": faults,
            "protections": prots,
        })

    running_n = sum(1 for u in units if u["state"] == "运行")
    return {
        "scheme": "8 台 2500KW 高压柴发 · N+1 并机",
        "busState": f"市电失电 · 柴发并机带载 ({running_n}/8)",
        "autoMode": "自动 (市电失电 15s 内首台建压, 60s 内并机带载)",
        "units": units,
        "lastTest": {"date": "2026-07-12", "type": "带载并机测试 (加载 50%)", "result": "通过", "duration": "2h"},
        "parallelSteps": ["市电失压确认", "首台启动建压", "同期并机", "分级加载", "带载运行", "市电恢复反并", "冷却停机"],
        "stepActive": 4,
        "knowledge": {
            "thresholds": [
                {"k": "机组配置", "v": "8×2500 kW 高压柴发 (N+1)"},
                {"k": "启动马达连续工作", "v": "3~5 s"},
                {"k": "启动失败重试等待", "v": "20 s"},
                {"k": "加机负载率", "v": "80%", "note": "可调"},
                {"k": "减机负载率", "v": "35%", "note": "可调；低于运行机组功率 75%"},
                {"k": "卸负载停机", "v": "3~5 min 后停机"},
                {"k": "市电恢复延时", "v": "10 min", "note": "3~10 可调"},
                {"k": "分级加载步序", "v": "2 s 步距"},
                {"k": "并机逻辑", "v": "频率/相位调至与母线一致后合闸"},
            ],
            "arch": {
                "components": ["并机控制模块", "并联控制线", "并联合闸开关", "接地电阻", "PLC 控制主机(主备)", "AVR/DVR 调压器", "调速板", "电流互感器/传感器"],
                "design": "N 台柴发经并机控制器在应急母线完成并机，负荷分配器按比率分配有功；PLC 主备提高可用性，支持加机/减机/待机控制。",
                "redundancy": "N+1 冗余；并机系统自动增减速与增减机",
            },
            "logic": [
                {
                    "title": "柴油发电机启动逻辑",
                    "steps": [
                        {"step": 1, "text": "市电掉电 → 控制系统收到任一启动信号 → 合控制箱保险 → 启动马达驱动发动机(连续 3~5s)", "ok": True},
                        {"step": 2, "text": "启动不成功 → 等待 20s 重试；多次失败 → 停启，排除电瓶电压/油路后重启", "ok": True},
                        {"step": 3, "text": "启动后观察机油压力，无显示/过低立即停机检查", "ok": True},
                    ],
                },
                {
                    "title": "柴油发电机并机逻辑",
                    "steps": [
                        {"step": 1, "text": "机组启动成功送电并机 → PLC 调节待并机组频率/相位与母线一致 → 发并机信号 → 空气开关合闸并机", "ok": True},
                        {"step": 2, "text": "多台并机后负荷分配器按负载状况自动调节、按比例分配负荷", "ok": True},
                    ],
                },
                {
                    "title": "柴油发电机加减机逻辑",
                    "steps": [
                        {"step": 1, "text": "负载率 ≥ 80%(可调) → 启动一台并入，执行并机流程", "ok": True},
                        {"step": 2, "text": "负载率 ≤ 35%(可调) 或 低于运行机组功率 75% → 解列一台机组", "ok": True},
                        {"step": 3, "text": "卸负载机组需空转 3~5min 后停机", "ok": True},
                    ],
                },
                {
                    "title": "市电恢复 / 故障切换",
                    "steps": [
                        {"step": 1, "text": "市电恢复 → 延时 10min(3~10可调) 先跳油机进线 → 确认全部分位 → 分步恢复市电", "ok": True},
                        {"step": 2, "text": "运行中机组异常 → 立即停机；紧急停机按下急停按钮或喷油泵手柄至停车位", "ok": True},
                    ],
                },
            ],
            "faults": [
                {"no": 1, "fault": "多次启动不成功", "lock": "停止起动", "action": "排除电瓶电压/油路故障后重启", "manualReset": True},
                {"no": 2, "fault": "机油压力低/无显示", "lock": "立即停机", "action": "检查机油液位与油泵", "manualReset": True},
                {"no": 3, "fault": "并机系统故障(启动超时无压)", "lock": "中止柴发备自投", "action": "检查并机控制与母线电压", "manualReset": True},
                {"no": 4, "fault": "机组异常运行", "lock": "紧急停机", "action": "按急停或推喷油泵手柄至停车", "manualReset": True},
                {"no": 5, "fault": "逆功率/接地故障保护动作", "lock": "该机组解列", "action": "排查负载与接地后复位", "manualReset": True},
            ],
            "note": "柴发并机核心目标：市电失电后 15s 内首台建压、60s 内并机带载；按负载率自动加/减机，保证冗余与效率。",
        },
    }


def fuel():
    # 油位四段开关: 低低位 LL(5%) / 低位 L(12%) / 高位 H(88%) / 高高位 HH(95%)
    # 开关为常开型, 液位越限即"闭合"(触发告警)
    def _switches(level):
        thr = {"LL": ("低低位 LL", 5, "r"), "L": ("低位 L", 12, "a"),
               "H": ("高位 H", 88, "a"), "HH": ("高高位 HH", 95, "r")}
        out = []
        for k, (name, t, sev) in thr.items():
            trig = (k in ("LL", "L") and level <= t) or (k in ("H", "HH") and level >= t)
            out.append({"name": name, "th": k, "state": "闭合" if trig else "断开",
                        "level": sev if trig else "g"})
        return out

    MAIN_PROT = ["高液位保护", "低液位保护", "低低位联锁停泵", "渗漏检测保护",
                  "静电接地保护", "温度高保护", "高低液位联锁"]
    DAY_PROT = ["高液位保护", "低液位保护", "渗漏检测保护", "温度高保护", "进油阀联锁"]
    PUMP_PROT = ["过载保护", "短路保护", "干转保护", "轴承温度高保护",
                  "密封泄漏保护", "出口过压保护"]

    def _main_prots(level):
        res = []
        for n in MAIN_PROT:
            if n == "高液位保护" and level >= 88:
                res.append({"name": n, "state": "动作", "level": "a"})
            else:
                res.append({"name": n, "state": "投入", "level": "g"})
        return res

    # 主油罐 #1 正常; #2 液位偏高(90%)→ 高位开关闭合 / 高液位保护动作
    mainTanks = [
        {"id": "地埋主油罐 #1", "cap": 50000, "level": 86, "t": 21.3, "water": "无", "leak": "正常",
         "valves": [{"name": "进油阀", "state": "闭合", "level": "g"},
                    {"name": "出油阀", "state": "开启", "level": "g"}],
         "switches": _switches(86), "protections": _main_prots(86)},
        {"id": "地埋主油罐 #2", "cap": 50000, "level": 90, "t": 21.1, "water": "无", "leak": "正常",
         "valves": [{"name": "进油阀", "state": "闭合", "level": "g"},
                    {"name": "出油阀", "state": "开启", "level": "g"}],
         "switches": _switches(90), "protections": _main_prots(90)},
    ]
    dayTanks = [{
        "id": f"日用油箱 DT-{i+1}", "cap": 1000, "level": rnd(78, 96, 0), "leak": "正常",
        "valve": {"name": "进油阀", "state": "开启", "level": "g"},
        "switches": _switches(rnd(78, 96, 0)),
        "protections": [{"name": n, "state": "投入", "level": "g"} for n in DAY_PROT],
    } for i in range(8)]

    pump_states = [("输油泵 P-1", "运行", "自动"), ("输油泵 P-2", "运行", "自动"),
                   ("输油泵 P-3(备)", "待机", "自动")]
    pumps = []
    for idx, (pid, st, mode) in enumerate(pump_states):
        alarms = [{"name": n, "value": "正常", "level": "g"} for n in
                  ["轴承温度", "电机电流", "密封泄漏", "出口压力"]]
        if idx == 1:  # P-2 轴承温度高告警 → 轴承温度高保护动作
            alarms[0] = {"name": "轴承温度", "value": "偏高 78℃", "level": "a"}
        prots = [{"name": n, "state": "投入", "level": "g"} for n in PUMP_PROT]
        if idx == 1:
            for pp in prots:
                if pp["name"] == "轴承温度高保护":
                    pp["state"] = "动作"
                    pp["level"] = "a"
        pumps.append({"id": pid, "state": st, "mode": mode, "alarms": alarms, "protections": prots})

    return {
        "mainTanks": mainTanks, "dayTanks": dayTanks, "pumps": pumps,
        "endurance": 11.6, "contract": "2h 应急供油合同 ×2 家",
        "pipeline": {"pressure": 0.32, "state": "正常", "tracing": "伴热正常"},
        "knowledge": {
            "thresholds": [
                {"k": "日用油箱 低低液位", "v": "30 cm", "note": "可调"},
                {"k": "日用油箱 低液位(启动补油)", "v": "40 cm", "note": "可调"},
                {"k": "日用油箱 高液位(结束补油)", "v": "70 cm", "note": "可调"},
                {"k": "日用油箱 高高液位", "v": "80 cm", "note": "可调"},
                {"k": "主油罐 低低液位", "v": "30 cm", "note": "可调"},
                {"k": "主油罐 低液位", "v": "50 cm", "note": "可调"},
                {"k": "主油罐 高液位", "v": "180 cm", "note": "可调"},
                {"k": "主油罐 高高液位", "v": "200 cm", "note": "可调"},
                {"k": "油位四段开关", "v": "LL / L / H / HH", "note": "常开型，越限闭合"},
            ],
            "arch": {
                "components": ["地埋油罐", "供油泵/回油泵(2N)", "日用油箱", "进油阀/泄油阀", "紧急切断阀", "漏油报警", "液位传感器", "I/O 子站", "控制柜/接入交换机"],
                "design": "地埋油罐与供回油泵组成 2N 实现高可用；可配置不同油箱运行参数，实现低低液位/低液位/高液位/高高液位告警与消防紧急联动。",
                "redundancy": "供油/回油泵 2N 互为备用；油罐补油泵 A/B 按运行时间轮询",
            },
            "logic": [
                {
                    "title": "日用油箱补油控制",
                    "steps": [
                        {"step": 1, "text": "液位低于 40cm 发低液位信号，且 无高/高高液位告警、无漏油、无消防、泄油阀关到位、紧急切断阀开到位、补油阀远程档 → 开补油阀 A/B 并发补油请求", "ok": True},
                        {"step": 2, "text": "液位补到 70cm 或任一条件不满足 → 结束补油、关阀、取消请求", "ok": True},
                    ],
                },
                {
                    "title": "日用油箱泄油控制",
                    "steps": [
                        {"step": 1, "text": "有机房消防火灾报警 或 高高液位报警 → 自动开泄油阀(远程档)", "ok": True},
                        {"step": 2, "text": "泄油阀开到位 → 本机房 2 台泄油泵同时开启泄油", "ok": True},
                        {"step": 3, "text": "所有油箱泄油请求消失 → 泄油泵停止", "ok": True},
                    ],
                },
                {
                    "title": "主油罐补油控制",
                    "steps": [
                        {"step": 1, "text": "油罐低液位/低低液位报警，或紧急切断阀未开到位 → 即使日用油箱请求补油，补油泵也不启动", "ok": True},
                        {"step": 2, "text": "任一油箱发 A 路补油请求 → 两油罐补油泵 A 按时间轮询选运行时间短者；故障则切另一台", "ok": True},
                    ],
                },
                {
                    "title": "消防及紧急控制",
                    "steps": [
                        {"step": 1, "text": "某机房消防火灾报警 → 对应紧急切断阀立即关闭", "ok": True},
                        {"step": 2, "text": "消防报警取消 → 紧急切断阀自动打开", "ok": True},
                        {"step": 3, "text": "收到消防报警 → 本机房所有油箱泄油阀打开 → 启泄油泵 → 向消防发反馈信号", "ok": True},
                    ],
                },
            ],
            "faults": [
                {"no": 1, "fault": "漏油报警", "lock": "禁止补油(条件不满足)", "action": "现场查漏、清理，确认后复位", "manualReset": True},
                {"no": 2, "fault": "高高液位(>80cm 日用 / >200cm 主油罐)", "lock": "触发泄油请求", "action": "开泄油阀/启泄油泵，液位回降至高液位后告警消失", "manualReset": False},
                {"no": 3, "fault": "紧急切断阀未开到位", "lock": "补油泵禁止启动", "action": "检查阀门执行机构与联锁", "manualReset": True},
                {"no": 4, "fault": "补油泵故障/限制启动", "lock": "自动切换另一油罐补油泵 A", "action": "排查泵过载/短路/干转", "manualReset": True},
                {"no": 5, "fault": "消防火灾报警", "lock": "关紧急切断阀+泄油", "action": "联动消防，解除后阀门自动复开", "manualReset": False},
            ],
            "note": "燃油系统核心：供油 2N 高可用，补油按低液位触发、高液位结束；消防报警联动紧急切断阀关闭与泄油，确保消防安全。",
        },
    }


def battery():
    # (id, 类型, 单体数, 单体基准电压V, SOC, 模式)
    specs = [
        ("UPS-A 电池组1", "铅酸 12V×40×4串", 40, 13.6, 100, "浮充"),
        ("UPS-A 电池组2", "铅酸 12V×40×4串", 40, 13.6, 100, "浮充"),
        ("UPS-B 电池组1", "铅酸 12V×40×4串", 40, 13.6, 100, "浮充"),
        ("HVDC-01 电池组", "磷酸铁锂 240V", 80, 3.35, 98, "浮充"),
        ("HVDC-02 电池组", "磷酸铁锂 240V", 80, 3.35, 99, "浮充"),
        ("HVDC-03 电池组", "磷酸铁锂 240V", 80, 3.35, 97, "浮充"),
    ]
    groups, cell_alarms = [], []
    for gid, gtype, ncell, vbase, soc, gstate in specs:
        is_li = "磷酸铁锂" in gtype
        cells = []
        for c in range(1, ncell + 1):
            if is_li:
                u = round(vbase + rnd(-0.08, 0.08, 3), 3)
                ir = round(rnd(0.25, 0.55, 2), 2)
                t = round(rnd(23, 28, 1), 1)
            else:
                u = round(vbase + rnd(-0.15, 0.15, 2), 2)
                ir = round(rnd(5.0, 8.5, 2), 2)
                t = round(rnd(22, 27, 1), 1)
            level = "g"
            if (is_li and ir > 0.5) or ((not is_li) and ir > 8.0):
                level = "a"
            cells.append({"no": f"#{c:02d}", "u": u, "t": t, "ir": ir, "level": level})
        # 制造 HVDC-03 单体 #28 内阻偏高 (+18%) 告警
        if gid == "HVDC-03 电池组":
            cells[27]["ir"] = round(0.62, 2)
            cells[27]["level"] = "a"
        total_u = round(sum(c["u"] for c in cells), 1)
        max_t = max(c["t"] for c in cells)
        worst = max(cells, key=lambda x: x["ir"])
        ir_concl = "偏高" if gid == "HVDC-03 电池组" else "正常"
        groups.append({
            "id": gid, "type": gtype, "soc": soc, "u": total_u,
            "i": round(rnd(0.1, 0.4, 2), 2), "cdState": "浮充", "maxT": max_t,
            "worstCell": f"{worst['no']} {worst['u']}V", "ir": ir_concl,
            "state": gstate, "cells": cells,
        })
        if gid == "HVDC-03 电池组":
            cell_alarms.append({"g": gid, "cell": worst["no"], "item": "内阻偏高 (+18%)",
                                "lv": "预警", "ts": "07-21 03:12"})

    return {
        "groups": groups, "backupMin": 15,
        "lastDischarge": "2026-06-30 核容放电 30% · 通过",
        "cellAlarms": cell_alarms,
        "knowledge": {
            "thresholds": [
                {"k": "单体电压(2V 电池)", "v": "1.5~2.5 V", "note": "±0.1%"},
                {"k": "单体电压(12V 电池)", "v": "9.0~15.0 V", "note": "±0.1%"},
                {"k": "单体内阻(2V)", "v": "100~65535 μΩ", "note": "±(2%+3μΩ)"},
                {"k": "单体内阻(6V/12V)", "v": "±(2%+30μΩ)"},
                {"k": "告警响应时间", "v": "≤10 s"},
                {"k": "放电采集周期", "v": "≤10 s"},
                {"k": "非放电采集周期", "v": "15 min", "note": "可调"},
                {"k": "收敛模块容量", "v": "≤6 组电池"},
                {"k": "模块吸收电流(2V)", "v": "7mA(最大13) / (6V/12V): 3mA(最大7)"},
                {"k": "监控数据处理容量", "v": "≥800,000 点"},
            ],
            "arch": {
                "components": ["TA 单体采集模块(电压/内阻/温度)", "TC 组采集模块(充放电电流/环境温度)", "电池收敛模块(轮巡/显示/告警)", "RJ11/RJ45 接口", "电流互感器", "嵌入式服务器/网络交换机", "2N(N+1) 高可用"],
                "design": "TA 模块采集每节电池电压/内阻/温度，TC 采集组充放电电流与环境温度，经 UART 互连至收敛模块，收敛模块通过串口/网络接入后台，实现远程集中管理。",
                "redundancy": "电池收敛模块 2N(N+1)；监测数据 RS485/网络上传，超限自动告警",
            },
            "logic": [
                {
                    "title": "电池监测逻辑",
                    "steps": [
                        {"step": 1, "text": "TA 模块采集单节电压/内阻/温度并上传收敛模块(本身不判断告警)", "ok": True},
                        {"step": 2, "text": "TC 模块采集一组电池充放电电流与一个环境温度，UART 与收敛模块通讯", "ok": True},
                        {"step": 3, "text": "收敛模块轮巡读取各 TA/TC 值并分析处理，1 个收敛模块最多监测 6 组电池", "ok": True},
                        {"step": 4, "text": "超限自动告警：LED 亮+蜂鸣器响+对应干接点闭合", "ok": True},
                    ],
                },
                {
                    "title": "电池充放电状态",
                    "steps": [
                        {"step": 1, "text": "市电正常 → 电池浮充(或均充)，监测组电压/充放电电流", "ok": True},
                        {"step": 2, "text": "市电断电且柴发未起 → 电池放电为 IT 包间供电，直至柴发带载或放电终止", "ok": True},
                    ],
                },
                {
                    "title": "告警与采集周期",
                    "steps": [
                        {"step": 1, "text": "告警发生到监控中心接收 ≤10s；放电时数据保存周期 ≤10s", "ok": True},
                        {"step": 2, "text": "非放电时采集/存储周期默认 15min(可调)", "ok": True},
                    ],
                },
                {
                    "title": "智能电池分析(放电时间)",
                    "steps": [
                        {"step": 1, "text": "市电闪断年均 80+ 次，电池串联劣化会逐级传递", "ok": True},
                        {"step": 2, "text": "单路市电闪断即可致 IT 末端失电宕机，需关注整组放电时间", "ok": True},
                        {"step": 3, "text": "人工检测每年仅 2 次，易遗漏早期劣化，应在线持续监测单体", "ok": True},
                        {"step": 4, "text": "基于单体电压/内阻趋势预测剩余放电时间，提前预警更换", "ok": True},
                    ],
                },
            ],
            "faults": [
                {"no": 1, "fault": "单体内阻偏高(+18% 等)", "lock": "单体预警", "action": "核对出厂内阻，必要时更换单体", "manualReset": False},
                {"no": 2, "fault": "单体电压越限(1.5~2.5 / 9~15V)", "lock": "超限告警", "action": "检查充电电压与连接，均充活化", "manualReset": False},
                {"no": 3, "fault": "收敛模块通讯异常", "lock": "弹出采集器通讯异常告警", "action": "ping 设备 IP；不通超 1min 现场检查上电与指示灯", "manualReset": False},
                {"no": 4, "fault": "负极柱温度超阈", "lock": "温度告警", "action": "检查环境温度与通风散热", "manualReset": False},
                {"no": 5, "fault": "漏电流/保护动作", "lock": "硬件保护", "action": "检查模块绝缘与接地", "manualReset": True},
            ],
            "note": "电池监控核心：TA/TC 采集 + 收敛模块轮巡分析，实现单体级电压/内阻/温度全量监测；超限自动告警并干接点联动，保障后备供电可靠。",
        },
    }


# ------------------------------------------------------------------ 安防消防
def cctv():
    return {
        "total": 486, "online": 482, "offline": 4,
        "nvr": {"total": 12, "ok": 12, "storeDays": 92, "required": 90},
        "zones": [
            {"id": "园区周界", "cams": 64, "offline": 0}, {"id": "大堂/门厅", "cams": 22, "offline": 0},
            {"id": "走廊/通道", "cams": 118, "offline": 1}, {"id": "机房包间", "cams": 192, "offline": 2},
            {"id": "动力机房", "cams": 58, "offline": 1}, {"id": "柴发/油罐区", "cams": 32, "offline": 0},
        ],
        "ai": ["周界入侵检测", "人员徘徊识别", "未戴安全帽识别", "离岗检测"],
        "events": [
            {"ts": "13:52", "zone": "园区周界-东", "desc": "AI 周界检测: 小动物触发, 已自动过滤", "lv": "info"},
            {"ts": "11:20", "zone": "走廊 C2", "desc": "摄像机 CAM-C2-07 视频丢失", "lv": "warn"},
            {"ts": "09:47", "zone": "机房 R03", "desc": "人员徘徊识别: 已联动复核, 为巡检人员", "lv": "info"},
        ],
        "knowledge": {
            "thresholds": [
                {"k": "录像存储时长", "v": "≥ 90 天", "note": "NVR 多路冗余存储"},
                {"k": "主码流设计码率", "v": "≈ 4 Mbps (H.265/1080P)", "note": "容量(GB)=码流×3600×24×天数÷8÷1024"},
                {"k": "实时预览取流时延", "v": "≤ 300 ms", "note": "编解码 + 网络传输"},
                {"k": "AI 识别准确率", "v": "≥ 99%", "note": "周界/人形/车牌，误报自动过滤"},
                {"k": "重点区域覆盖", "v": "园区/楼栋/机房三级无盲区", "note": "室外周界 + 出入口 AI 赋能"},
            ],
            "arch": {
                "components": ["前端摄像机(球/枪/半球/防雾)", "传输(六类线 / RVVP 2×1.0)", "DVR/NVR 存储", "视频矩阵/解码上墙", "AI 智能分析服务器", "IOC 集中监控平台"],
                "design": "园区-楼栋-机房三级覆盖、重点区域无盲区；室外周界与出入口 AI 赋能，事件自动联动复核。",
                "redundancy": "NVR 多路冗余存储，关键区域双机互备。",
            },
            "logic": [
                {"title": "视频联动复核", "steps": [
                    {"step": 1, "text": "安防/消防事件触发", "ok": True},
                    {"step": 2, "text": "关联摄像机跳转预置位、实时画面弹窗", "ok": True},
                    {"step": 3, "text": "自动锁定录像、AI 智能检索", "ok": True},
                    {"step": 4, "text": "复核取证、闭环处置", "ok": True},
                ]},
                {"title": "周界主动防控", "steps": [
                    {"step": 1, "text": "周界入侵/徘徊触发", "ok": True},
                    {"step": 2, "text": "声光报警 + 广播喊话", "ok": True},
                    {"step": 3, "text": "弹出画面、保安到场处置", "ok": True},
                ]},
            ],
            "faults": [
                {"no": 1, "fault": "视频丢失(单点)", "lock": "报警", "action": "核查供电/光纤，4h 内恢复", "manualReset": True},
                {"no": 2, "fault": "存储异常(硬盘坏)", "lock": "告警", "action": "更换硬盘、冗余补录", "manualReset": True},
                {"no": 3, "fault": "AI 误报率过高", "lock": "仅报警", "action": "优化算法/阈值，不盲目联动", "manualReset": False},
                {"no": 4, "fault": "设备时间不同步", "lock": "仅报警", "action": "NTP 校时", "manualReset": False},
                {"no": 5, "fault": "夜间照度不足", "lock": "仅报警", "action": "补光或更换低照度机型", "manualReset": False},
            ],
            "note": "监控不只是“看得见”，更通过 AI 智能分析与事件联动，把“被动录像”升级为“主动防控”。",
        },
    }


def acs():
    return {
        "doors": 268, "online": 266, "openAbnormal": 1, "todayEvents": 1642, "denied": 12, "visitors": 9,
        "areas": [
            {"id": "一级区 · 园区/大堂", "auth": "刷卡", "doors": 24},
            {"id": "二级区 · 办公/走廊", "auth": "刷卡+密码", "doors": 86},
            {"id": "三级区 · 机房包间", "auth": "刷卡+指纹", "doors": 118},
            {"id": "四级区 · 动力/网络核心", "auth": "刷卡+人脸+双人互锁", "doors": 40},
        ],
        "events": [
            {"ts": "14:05", "door": "R06 包间北门", "person": "王强(运维)", "act": "刷卡+指纹通过", "lv": "info"},
            {"ts": "13:41", "door": "UPS 室 A", "person": "李敏(厂商)", "act": "访客授权通过·陪同", "lv": "info"},
            {"ts": "12:58", "door": "R11 包间南门", "person": "未授权卡", "act": "拒绝 · 已联动视频复核", "lv": "warn"},
            {"ts": "11:33", "door": "油罐区大门", "person": "—", "act": "门磁异常开启 > 60s", "lv": "crit"},
        ],
        "knowledge": {
            "thresholds": [
                {"k": "读卡响应", "v": "≤ 0.5 s", "note": "刷卡到开门"},
                {"k": "胁迫码", "v": "4 位特定码(静默报警)", "note": "遇胁迫不惊动对方"},
                {"k": "双门互锁(AB门)", "v": "一门开则另一门闭锁", "note": "防尾随"},
                {"k": "主机供电/通讯", "v": "DC12V / TCP-IP", "note": "双电源备份"},
                {"k": "容量", "v": "1 万卡 / 5 万记录", "note": "脱机本地认证"},
                {"k": "工作温度", "v": "-20 ~ +65 ℃", "note": "动力/室外区适配"},
            ],
            "arch": {
                "components": ["识读(卡/密码/指纹/人脸)", "门禁控制器(主机)", "电锁(磁力锁/电控锁)", "出门按钮/破玻", "管理软件+数据库", "消防/视频联动"],
                "design": "分级分区：一级园区 → 四级动力核心，越核心认证越复合(卡+密码+生物+双人互锁)。",
                "redundancy": "双电源、断网本地决策、离线仍可刷卡。",
            },
            "logic": [
                {"title": "正常开门", "steps": [
                    {"step": 1, "text": "刷卡/生物识读", "ok": True},
                    {"step": 2, "text": "身份比对与权限校验", "ok": True},
                    {"step": 3, "text": "电锁开启、记录上传", "ok": True},
                ]},
                {"title": "非法闯入处置", "steps": [
                    {"step": 1, "text": "无效卡/胁迫码触发", "ok": True},
                    {"step": 2, "text": "声光报警 + 视频复核 + IOC 弹窗", "ok": True},
                    {"step": 3, "text": "安保秘密/到场处置", "ok": True},
                ]},
                {"title": "消防联动释放", "steps": [
                    {"step": 1, "text": "接收火警信号", "ok": True},
                    {"step": 2, "text": "全区门禁断电开锁(疏散)", "ok": True},
                    {"step": 3, "text": "反馈释放状态", "ok": True},
                ]},
                {"title": "双门互锁防尾随", "steps": [
                    {"step": 1, "text": "A 门开启", "ok": True},
                    {"step": 2, "text": "B 门保持闭锁直至 A 门关", "ok": True},
                ]},
            ],
            "faults": [
                {"no": 1, "fault": "门磁异常开启 > 60s", "lock": "告警", "action": "现场核查、防尾随复核", "manualReset": True},
                {"no": 2, "fault": "控制器通讯中断", "lock": "告警", "action": "查网络/电源，离线本地认证", "manualReset": True},
                {"no": 3, "fault": "电锁失效", "lock": "不允许(安全隐患)", "action": "停用该门、人工值守", "manualReset": True},
                {"no": 4, "fault": "胁迫报警", "lock": "静默报警", "action": "安保秘密处置，不惊动对方", "manualReset": True},
                {"no": 5, "fault": "非法卡多次尝试", "lock": "仅报警", "action": "锁定卡片、联动视频", "manualReset": False},
            ],
            "note": "门禁是物理安全的第一道关口：分级授权 + 防尾随 + 消防联动，兼顾安全与疏散。",
        },
    }


def ids():
    return {
        "perimeter": {"type": "电子围栏 + 振动光纤", "zones": 16, "armed": 16, "alarm": 0},
        "indoor": {"ir": 84, "glass": 36, "armed": "夜间自动布防", "state": "白天撤防(重点区布防)"},
        "linkage": "报警 → 联动摄像机预置位 + 声光 + IOC 弹窗",
        "events": [
            {"ts": "02:14", "zone": "周界 Z-07", "desc": "振动光纤扰动, AI 判定树枝刮碰, 自动消警", "lv": "info"},
            {"ts": "昨日 23:40", "zone": "周界 Z-03", "desc": "电子围栏触网报警, 保安 3min 到场, 无异常", "lv": "warn"},
        ],
        "knowledge": {
            "thresholds": [
                {"k": "周界布防", "v": "16 防区全布防", "note": "电子围栏 + 振动光纤"},
                {"k": "夜间自动布防", "v": "22:00", "note": "白天重点区布防"},
                {"k": "报警响应到场", "v": "≤ 3 min", "note": "保安巡场"},
                {"k": "电子围栏电压", "v": "高压脉冲 ≈ 5 kV", "note": "触网即报警"},
                {"k": "振动光纤", "v": "灵敏度可调 + AI 扰动识别", "note": "降误报"},
            ],
            "arch": {
                "components": ["周界探测器(电子围栏/振动光纤/红外对射)", "室内被动红外/玻璃破碎", "数字报警主机/接警机", "RS-485 融合处理器", "联动控制(声光/摄像机/广播)"],
                "design": "周界多层防护 + 室内重点区，融合判断降误报。",
                "redundancy": "双总线、双电源、断网本地仍报警。",
            },
            "logic": [
                {"title": "周界报警处置", "steps": [
                    {"step": 1, "text": "围栏/光纤触发", "ok": True},
                    {"step": 2, "text": "AI 判定(人/动物/树枝)", "ok": True},
                    {"step": 3, "text": "真警联动摄像机预置位+声光+喊话", "ok": True},
                    {"step": 4, "text": "保安 3min 到场处置", "ok": True},
                ]},
                {"title": "室内布防", "steps": [
                    {"step": 1, "text": "夜间自动布防", "ok": True},
                    {"step": 2, "text": "红外/玻璃破碎触发", "ok": True},
                    {"step": 3, "text": "接警机确认 + 复核", "ok": True},
                ]},
                {"title": "防区旁路(维护)", "steps": [
                    {"step": 1, "text": "单防区旁路", "ok": True},
                    {"step": 2, "text": "其余防区正常布防", "ok": True},
                    {"step": 3, "text": "维护完成恢复", "ok": True},
                ]},
            ],
            "faults": [
                {"no": 1, "fault": "误报(树枝/小动物)", "lock": "自动消警", "action": "AI 学习/调灵敏度", "manualReset": False},
                {"no": 2, "fault": "防区故障(断线/短路)", "lock": "告警", "action": "查线缆/接头", "manualReset": True},
                {"no": 3, "fault": "接警机离线", "lock": "告警", "action": "查通信/主备切换", "manualReset": True},
                {"no": 4, "fault": "围栏高压异常", "lock": "告警", "action": "查高压箱/绝缘", "manualReset": True},
            ],
            "note": "防入侵强调“融合判断 + 快速响应”，用 AI 扰动识别压降误报，把保安精力留给真警。",
        },
    }


def fire():
    return {
        "hostState": "正常运行", "loops": 8, "points": 5860, "faultPoints": 2,
        "detectors": [
            {"type": "感烟探测器", "n": 3120, "fault": 1}, {"type": "感温探测器", "n": 1480, "fault": 1},
            {"type": "极早期(VESDA)", "n": 96, "fault": 0}, {"type": "手报/声光", "n": 420, "fault": 0},
            {"type": "气体灭火控制盘", "n": 46, "fault": 0}, {"type": "防火门监控", "n": 268, "fault": 0},
        ],
        "gas": {"zones": 46, "ready": 46, "released": 0, "agent": "七氟丙烷"},
        "vesda": [{"id": f"VESDA R{str(i*2+1).zfill(2)}", "level": pick(["正常", "正常", "正常", "轻微"]),
                   "val": rnd(0.001, 0.018, 3)} for i in range(6)],
        "qieFei": {"desc": "确认火警 → 切除非消防电源(切非) → 联动气灭 → 应急照明投入",
                   "state": "自动允许", "lastDrill": "2026-06-28 消防演练通过"},
        "emergency": {"lights": 1240, "ok": 1236, "batteryOk": 99.2, "evacSigns": 386},
        "events": [
            {"ts": "07-20 16:02", "desc": "R08 VESDA 轻微烟雾预警, 现场复核为清洁扬尘", "lv": "warn"},
            {"ts": "07-18 10:00", "desc": "月度消防联动测试: 切非/气灭启动回路校验通过", "lv": "info"},
        ],
        "knowledge": {
            "thresholds": [
                {"k": "极早期 VESDA", "v": "采样管网 > 400 Pa, 自学习 30 天", "note": "ISO 11690-1, 激光探测腔+灰尘抑制"},
                {"k": "电气火灾切非", "v": "确认火警→切除非消防电源", "note": "-24V 分励脱扣"},
                {"k": "气体灭火", "v": "七氟丙烷, 确认→延时 30s→释放", "note": "两路独立探测确认"},
                {"k": "应急照明", "v": "蓄电池 ≥ 90 min 续航", "note": "集中控制型"},
                {"k": "防火门监控", "v": "常闭门开度/故障实时监测", "note": "联动关闭阻隔烟火"},
            ],
            "arch": {
                "components": ["分布式智能探测(烟/温/手报)", "火灾报警控制器(联网跨区联动)", "声光/应急广播", "电气火灾监控(切非)", "气体灭火控制盘", "应急照明+疏散指示", "极早期吸气式 VESDA"],
                "design": "探测-报警-联动-疏散四级，极早期预警争取处置时间。",
                "redundancy": "双回路、双电源、主备控制器。",
            },
            "logic": [
                {"title": "火警确认与联动", "steps": [
                    {"step": 1, "text": "探测器/手报报警", "ok": True},
                    {"step": 2, "text": "控制器确认 + 声光/广播", "ok": True},
                    {"step": 3, "text": "切除非消防电源(切非)", "ok": True},
                    {"step": 4, "text": "气灭联动 + 应急照明投入", "ok": True},
                ]},
                {"title": "极早期预警(VESDA)", "steps": [
                    {"step": 1, "text": "管网采样送激光探测腔", "ok": True},
                    {"step": 2, "text": "灰尘抑制 + 自学习基线", "ok": True},
                    {"step": 3, "text": "异常早于传统探测器预警", "ok": True},
                ]},
                {"title": "气体灭火", "steps": [
                    {"step": 1, "text": "两路独立探测确认", "ok": True},
                    {"step": 2, "text": "延时 30s + 防火门关闭", "ok": True},
                    {"step": 3, "text": "释放七氟丙烷", "ok": True},
                ]},
            ],
            "faults": [
                {"no": 1, "fault": "探测器故障/污染", "lock": "告警", "action": "清洁/更换，屏蔽期间加强巡查", "manualReset": True},
                {"no": 2, "fault": "回路故障(短路/断线)", "lock": "告警", "action": "查回路/隔离故障点", "manualReset": True},
                {"no": 3, "fault": "气灭控制盘故障", "lock": "不允许释放", "action": "停用，改水喷淋/人工", "manualReset": True},
                {"no": 4, "fault": "应急照明蓄电池欠压", "lock": "告警", "action": "充放电维护/更换", "manualReset": True},
                {"no": 5, "fault": "切非回路失效", "lock": "告警", "action": "查分励脱扣/接线", "manualReset": True},
            ],
            "note": "消防核心是“早预警、快联动、保疏散”：VESDA 把发现时间前移，联动切非与气灭守住设备与人员双重安全。",
        },
    }


# ------------------------------------------------------------------ 智能运营 + 运维作业
def twin():
    return {
        "platform": "Raptor / 方舟自动化运营平台",
        "coverage": {"points": 128500, "mapped": 99.6, "models": 42, "refreshMs": 800},
        "layers": ["园区", "楼栋", "楼层", "包间", "机柜", "设备"],
        "scenes": [
            {"id": "全停演练推演", "state": "已编排", "last": "2026-07-05"},
            {"id": "冷源故障切换推演", "state": "已编排", "last": "2026-06-20"},
            {"id": "市电失电-柴发接管推演", "state": "已编排", "last": "2026-06-12"},
        ],
        "autoOps": [
            {"id": "冷机群控寻优", "state": "闭环运行", "saving": "3.8%"},
            {"id": "末端空调联动调优", "state": "闭环运行", "saving": "2.4%"},
            {"id": "无人巡检机器人", "state": "运行 · 2 台", "saving": "—"},
        ],
        "knowledge": {
            "arch": {
                "components": ["IT 侧(档案/采集/直控)", "设施侧(档案/采集/直控)", "EMS1.4/EMS3.1/AIMS/IOT 协议接入", "结构化数据+拓扑关联", "监控大屏/运维大盘", "事件/问题/风险闭环", "容量/能耗管理", "知识文档库", "数字孪生/CFD"],
                "design": "以“标准化接入—结构化处理—规范化流程—智能化辅助”为主线，把本地专家经验沉淀为平台能力；人机协同，平台做强大脑、人做决策闭环。",
                "redundancy": "分布式采集+双链路，跨地域主站统一纳管(近20国/100+主站)。",
            },
            "logic": [
                {"title": "数据接入架构(EMS3.1/AIMS/IOT)", "steps": [
                    {"step": 1, "text": "设备经串口/网口/IOT 网关采集(标准化录入: 空间/资产/分类/型号/厂商)", "ok": True},
                    {"step": 2, "text": "EMS1.4/EMS3.1/AIMS 规约解析，统一成结构化测点", "ok": True},
                    {"step": 3, "text": "测点与拓扑/资产关联，进入监控平台与运维大盘", "ok": True},
                    {"step": 4, "text": "事件→问题→风险逐层收敛，驱动 EOP 闭环", "ok": True},
                ]},
                {"title": "智能运维能力", "steps": [
                    {"step": 1, "text": "AI 收敛同源告警(1284→63)、降噪", "ok": True},
                    {"step": 2, "text": "趋势预测(温升/负荷/电量)把故障处置前移", "ok": True},
                    {"step": 3, "text": "数字孪生/CFD 支撑演练推演与容量调度", "ok": True},
                ]},
            ],
            "note": "方舟是阿里自研的自动化运营平台：把分布各地、各厂商的设备“标准化接入+结构化处理”，再用“规范化流程+智能化辅助”实现人机协同。最强大脑在平台，最终决策与闭环仍由人完成。",
        },
    }


def capacity():
    return {
        "dims": [
            {"id": "机柜空间", "used": 3212, "total": 3600, "unit": "架"},
            {"id": "电力容量", "used": 24.6, "total": 36, "unit": "MW"},
            {"id": "制冷容量", "used": 26.1, "total": 40, "unit": "MW"},
            {"id": "承重容量", "used": 68, "total": 100, "unit": "%"},
            {"id": "网络端口", "used": 41200, "total": 57600, "unit": "口"},
        ],
        "rooms": [{"id": f"R{str(i+1).zfill(2)}", "racks": 300, "used": rnd(240, 296, 0),
                   "powerPct": rnd(55, 88, 0), "coolPct": rnd(50, 82, 0)} for i in range(12)],
        "forecast": "按当前上架速率, 电力容量预计 14 个月后达 85% 预警线",
        "knowledge": {
            "thresholds": [
                {"k": "五维容量", "v": "机柜空间/供电/制冷/承重/网络", "note": "任一维达 85% 即预警"},
                {"k": "电力容量", "v": "预计 14 个月后达 85%", "note": "最早触顶，需优先评估扩容/削峰"},
                {"k": "机柜空间", "v": "上架速率驱动", "note": "需提前规划上架"},
            ],
            "arch": {
                "components": ["机柜空间", "供电功率", "制冷功率", "承重", "网络端口"],
                "design": "五维容量统一建模、按月滚动预测，识别最先触顶维度。",
                "redundancy": "预测 horizon 24 个月，growth ~3.2%/年。",
            },
            "logic": [
                {"title": "容量→风险 前瞻联动", "steps": [
                    {"step": 1, "text": "容量预测发现电力容量 14 个月达 85%", "ok": True},
                    {"step": 2, "text": "自动在风险管理生成容量预警项(概率×影响)", "ok": True},
                    {"step": 3, "text": "驱动扩容评估/削峰填谷/负载再平衡", "ok": True},
                ]},
            ],
            "note": "容量管理的价值是“把扩容从救火变为可预测”。当某一维逼近 85%，应自动在风险中心生成前瞻项，闭环到改造工单。",
        },
    }


def alarms():
    return {
        "convergence": {"raw": 1284, "converged": 63, "rate": 95.1},
        "rules": ["同源合并", "拓扑根因分析", "抖动抑制", "维保屏蔽窗口"],
        "trend": [
            {"id": "CH-02 冷凝器趋近温度缓升", "pred": "预计 21 天后越限", "conf": 87, "sug": "安排冷凝器在线清洗"},
            {"id": "HVDC-03 #28 单体内阻上升", "pred": "预计 30 天内达更换阈值", "conf": 82, "sug": "备件申领, 择机更换"},
            {"id": "CT-03 风机振动幅值缓升", "pred": "预计 45 天后达注意值", "conf": 74, "sug": "下次月检加测振动频谱"},
        ],
        "active": [
            {"lv": "crit", "sys": "安防-门禁", "desc": "油罐区大门 门磁异常开启 > 60s", "ts": "11:33", "state": "处理中", "owner": "保安班组"},
            {"lv": "warn", "sys": "暖通-末端", "desc": "CRAC-08 风机故障停机, 备机自动投入", "ts": "10:18", "state": "已派单", "owner": "暖通班组"},
            {"lv": "warn", "sys": "电力-电池", "desc": "HVDC-03 电池 #28 内阻偏高", "ts": "03:12", "state": "观察中", "owner": "电气班组"},
            {"lv": "warn", "sys": "安防-视频", "desc": "CAM-C2-07 视频丢失", "ts": "11:20", "state": "已派单", "owner": "弱电班组"},
            {"lv": "warn", "sys": "消防", "desc": "R08 VESDA 轻微预警(已复核)", "ts": "07-20", "state": "已闭环", "owner": "消控室"},
            {"lv": "warn", "sys": "暖通-冷源", "desc": "CH-02 冷凝趋近温度趋势预警", "ts": "07-19", "state": "计划检修", "owner": "暖通班组"},
            {"lv": "info", "sys": "电力-10KV", "desc": "2# 进线电压轻微波动(合格范围内)", "ts": "13:05", "state": "自动消警", "owner": "—"},
        ],
        "sla": {"mttaMin": 2.1, "mttrMin": 38, "autoCloseRate": 71},
        "knowledge": {
            "thresholds": [
                {"k": "同源告警收敛", "v": "1284 → 63 条", "note": "降噪, 减少无效打扰"},
                {"k": "闭环率(自动关闭)", "v": "71%", "note": "SLA 跟踪 MTTA/MTTR"},
                {"k": "智能趋势告警(DCGoT)", "v": "有效率 55%→99.5%, 告警量 ↓58.5%", "note": "提前 ≥10min 预警, 优于阈值法"},
            ],
            "arch": {
                "components": ["采集/直控", "规则引擎(阈值/趋势)", "同源收敛", "联动工单/知识库", "EOP 闭环"],
                "design": "告警不是终点，而是运维闭环的起点：告警→事件工单→问题定位→风险沉淀。",
                "redundancy": "趋势预测与阈值双引擎并存, 互补降漏报。",
            },
            "logic": [
                {"title": "事件→问题→风险 双闭环", "steps": [
                    {"step": 1, "text": "告警触发 → 生成事件工单(Tickets)", "ok": True},
                    {"step": 2, "text": "工单处置沉淀为问题根因", "ok": True},
                    {"step": 3, "text": "反复/高危问题升级为风险项(Risk)并跟踪", "ok": True},
                    {"step": 4, "text": "EOP 覆盖 62 类主要事件, 一键拉预案", "ok": True},
                ]},
                {"title": "智能趋势告警(DCGoT)", "steps": [
                    {"step": 1, "text": "采集温升/负荷/电量时序", "ok": True},
                    {"step": 2, "text": "时空图模型(GoT)预测趋势异常", "ok": True},
                    {"step": 3, "text": "提前 ≥10min 预警, 有效率达 99.5%", "ok": True},
                ]},
            ],
            "note": "告警中心的定位是“运维闭环的起点”：一条告警应可追溯为工单、沉淀为问题、升级为风险。结合 EOP 预案库与智能趋势告警，把被动响应变成主动预防。",
        },
    }


def energy():
    return {
        "todayKwh": 512300, "monthKwh": 11.82, "yearKwh": 78.4,
        "pueTrend": [round(v, 3) for v in series(30, 1.22, 1.31)],
        "loadForecast": [{"h": h, "actual": rnd(23.2, 25.4) if h <= 14 else None,
                          "pred": rnd(23.0, 25.8)} for h in range(24)],
        "aiSaving": {"enabled": True, "algo": "冷源 AI 寻优 + 负载预测联动", "monthSaveKwh": 286000, "saveRate": 3.1},
        "breakdown": [
            {"id": "IT 负载", "kw": 24600, "pct": 80.1}, {"id": "制冷系统", "kw": 4900, "pct": 16.0},
            {"id": "供配电损耗", "kw": 780, "pct": 2.5}, {"id": "照明及其他", "kw": 420, "pct": 1.4},
        ],
        "carbon": {"greenPct": 34, "pv": "屋顶光伏 2.1MWp", "monthCO2": 5620},
    }


def tickets():
    return {
        "stats": {"open": 6, "doing": 4, "pending": 2, "done": 128},
        "list": [
            {"id": "WO-260723-018", "title": "油罐区大门门磁异常处置", "sys": "安防", "lv": "crit", "state": "处理中", "owner": "保安班组", "created": "07-23 11:33", "sla": "1h", "progress": 60},
            {"id": "WO-260723-017", "title": "CRAC-08 风机更换", "sys": "暖通", "lv": "warn", "state": "处理中", "owner": "暖通班组", "created": "07-23 10:18", "sla": "4h", "progress": 45},
            {"id": "WO-260723-015", "title": "CAM-C2-07 视频链路检修", "sys": "弱电", "lv": "warn", "state": "待处理", "owner": "弱电班组", "created": "07-23 11:20", "sla": "8h", "progress": 10},
            {"id": "WO-260721-042", "title": "HVDC-03 #28 电池更换备件申领", "sys": "电力", "lv": "warn", "state": "待处理", "owner": "电气班组", "created": "07-21 03:12", "sla": "72h", "progress": 25},
            {"id": "WO-260719-033", "title": "CH-02 冷凝器在线清洗", "sys": "暖通", "lv": "info", "state": "处理中", "owner": "暖通班组", "created": "07-19 09:00", "sla": "计划", "progress": 70},
            {"id": "WO-260723-012", "title": "R08 VESDA 误报复核闭环", "sys": "消防", "lv": "info", "state": "已完成", "owner": "消控室", "created": "07-20 16:02", "sla": "已闭环", "progress": 100},
        ],
    }


def inspect():
    return {
        "today": {"plan": 24, "done": 18, "abnormal": 2, "rate": 75},
        "robot": {"units": 2, "running": 2, "coverage": 96, "findings": 3},
        "routes": [
            {"id": "冷冻机房日巡", "freq": "每 4h", "last": "12:30", "next": "16:30", "items": 42, "state": "进行中"},
            {"id": "高低压配电巡检", "freq": "每班", "last": "08:15", "next": "20:15", "items": 68, "state": "已完成"},
            {"id": "电池室专项巡检", "freq": "每日", "last": "09:40", "next": "明日", "items": 36, "state": "已完成"},
            {"id": "柴发机房巡检", "freq": "每周", "last": "07-22", "next": "07-29", "items": 55, "state": "已完成"},
            {"id": "消防设施巡检", "freq": "每日", "last": "10:00", "next": "明日", "items": 48, "state": "已完成"},
            {"id": "安防周界巡逻", "freq": "每 2h", "last": "13:00", "next": "15:00", "items": 24, "state": "进行中"},
        ],
        "findings": [
            {"ts": "12:48", "route": "冷冻机房日巡", "item": "CH-02 冷凝器压差偏高", "lv": "warn", "action": "已转工单 WO-260719-033"},
            {"ts": "13:22", "route": "安防周界巡逻", "item": "Z-05 段照明灯珠损坏 2 处", "lv": "info", "action": "记录待修"},
        ],
    }


def maintain():
    return {
        "stats": {"plan": 42, "done": 38, "overdue": 1, "thisWeek": 6},
        "plans": [
            {"id": "PM-CH", "equip": "冷水机组", "cycle": "季度", "last": "2026-05-10", "next": "2026-08-10", "vendor": "厂商+自维", "state": "正常"},
            {"id": "PM-UPS", "equip": "UPS 系统", "cycle": "半年", "last": "2026-04-18", "next": "2026-10-18", "vendor": "厂商", "state": "正常"},
            {"id": "PM-DG", "equip": "柴发机组", "cycle": "月度带载", "last": "2026-07-12", "next": "2026-08-12", "vendor": "自维", "state": "正常"},
            {"id": "PM-BAT", "equip": "蓄电池组", "cycle": "半年核容", "last": "2026-06-30", "next": "2026-12-30", "vendor": "自维", "state": "正常"},
            {"id": "PM-FIRE", "equip": "消防系统", "cycle": "月度联动", "last": "2026-07-18", "next": "2026-08-18", "vendor": "第三方", "state": "正常"},
            {"id": "PM-CRAC", "equip": "精密空调", "cycle": "季度", "last": "2026-06-05", "next": "2026-09-05", "vendor": "自维", "state": "临期"},
            {"id": "PM-ATS", "equip": "ATS/备自投", "cycle": "半年演练", "last": "2026-01-20", "next": "2026-07-20", "vendor": "厂商", "state": "逾期"},
        ],
        "spares": [
            {"id": "冷机压缩机油滤", "stock": 12, "min": 6, "state": "充足"},
            {"id": "精密空调风机", "stock": 3, "min": 4, "state": "预警"},
            {"id": "HVDC 整流模块", "stock": 5, "min": 3, "state": "充足"},
            {"id": "铅酸电池单体 12V", "stock": 24, "min": 20, "state": "充足"},
            {"id": "感烟探测器", "stock": 40, "min": 30, "state": "充足"},
        ],
    }


def drill():
    return {
        "stats": {"year": 12, "done": 8, "pass": 8, "next": "2026-08-05 全停演练"},
        "plans": [
            {"id": "DR-01", "name": "市电全停-柴发接管演练", "type": "电力", "date": "2026-08-05", "state": "已编排", "result": "—"},
            {"id": "DR-02", "name": "冷源系统故障切换演练", "type": "暖通", "date": "2026-06-20", "state": "已完成", "result": "通过"},
            {"id": "DR-03", "name": "母联备自投切换演练", "type": "电力", "date": "2026-07-05", "state": "已完成", "result": "通过"},
            {"id": "DR-04", "name": "气体灭火联动演练", "type": "消防", "date": "2026-06-28", "state": "已完成", "result": "通过"},
            {"id": "DR-05", "name": "周界入侵应急演练", "type": "安防", "date": "2026-05-16", "state": "已完成", "result": "通过"},
            {"id": "DR-06", "name": "UPS 切旁路演练", "type": "电力", "date": "2026-09-12", "state": "计划中", "result": "—"},
        ],
    }


def shift():
    return {
        "teams": ["暖通班组", "电气班组", "弱电班组", "消控室", "保安班组"],
        "today": {"onDuty": 14, "dayShift": 9, "nightShift": 5, "leader": "张伟 (值班经理)"},
        "roster": [{"day": i + 1, "day1": ["A 组", "B 组", "C 组"][i % 3],
                    "night": ["C 组", "A 组", "B 组"][i % 3]} for i in range(28)],
    }


def risk():
    return {
        "matrix": [
            {"id": "R-01", "risk": "ATS 半年演练逾期", "cat": "电力", "prob": 3, "impact": 4, "level": "高", "ctrl": "已排 07-25 补做演练", "owner": "电气班组"},
            {"id": "R-02", "risk": "精密空调备件库存不足", "cat": "备件", "prob": 3, "impact": 3, "level": "中", "ctrl": "紧急补货中", "owner": "物资组"},
            {"id": "R-03", "risk": "HVDC-03 电池老化", "cat": "电力", "prob": 2, "impact": 4, "level": "中", "ctrl": "监测+择机更换", "owner": "电气班组"},
            {"id": "R-04", "risk": "夏季冷源高负荷运行", "cat": "暖通", "prob": 3, "impact": 3, "level": "中", "ctrl": "蓄冷罐+错峰策略", "owner": "暖通班组"},
            {"id": "R-05", "risk": "油罐区物理安防薄弱点", "cat": "安防", "prob": 2, "impact": 3, "level": "低", "ctrl": "增设摄像机+门磁", "owner": "保安班组"},
            {"id": "R-06", "risk": "电力容量 14 个月后达 85%, 需扩容/削峰", "cat": "容量", "prob": 3, "impact": 4, "level": "中", "ctrl": "容量预警驱动扩容评估", "owner": "电气班组"},
        ],
        "stats": {"high": 1, "mid": 3, "low": 1, "closed": 22},
        "knowledge": {
            "thresholds": [
                {"k": "风险等级", "v": "概率(1-5) × 影响(1-5)", "note": "≥12 红 / 6-11 黄 / <6 蓝"},
                {"k": "闭环跟踪", "v": "high 1 / mid 3 / low 1 / closed 22", "note": "问题→风险逐层收敛"},
            ],
            "logic": [
                {"title": "事件→问题→风险 闭环", "steps": [
                    {"step": 1, "text": "告警/巡检发现隐患", "ok": True},
                    {"step": 2, "text": "工单处置并沉淀根因(问题)", "ok": True},
                    {"step": 3, "text": "反复/高危升级为风险项并跟踪闭环", "ok": True},
                    {"step": 4, "text": "容量预警(供电 14 月达 85%)自动入风险中心", "ok": True},
                ]},
            ],
            "note": "风险中心是运维闭环的沉淀层：把瞬时告警与单次工单升华为可跟踪的风险项。容量触顶、演练短板等都应自动汇聚于此，驱动改造与排班。",
        },
    }


def knowledge():
    return {
        "stats": {"sop": 186, "drawing": 420, "manual": 92, "emergency": 34},
        "cats": [
            {"id": "应急预案", "n": 34, "hot": "市电全停应急处置预案 v3.2"},
            {"id": "运行 SOP", "n": 186, "hot": "冷源加减机操作规程"},
            {"id": "设备手册", "n": 92, "hot": "HVDC 整流模块检修手册"},
            {"id": "竣工图纸", "n": 420, "hot": "10KV 供配电系统单线图"},
            {"id": "故障案例库", "n": 148, "hot": "精密空调高压报警典型案例"},
            {"id": "培训资料", "n": 76, "hot": "弱电高级运维工程师认证课件"},
        ],
        "recent": [
            {"title": "市电全停应急处置预案", "ver": "v3.2", "date": "2026-07-10", "by": "运维部"},
            {"title": "冷源 AI 群控参数配置指南", "ver": "v1.4", "date": "2026-06-28", "by": "能效组"},
            {"title": "蓄电池核容放电作业指导书", "ver": "v2.1", "date": "2026-06-15", "by": "电气班组"},
        ],
        "knowledge": {
            "thresholds": [
                {"k": "EOP 覆盖", "v": "62 类主要事件", "note": "故障处置一键拉预案"},
                {"k": "知识库规模", "v": "SOP 186 / 图纸 420 / 手册 92 / 应急 34", "note": "按业务域/测点自动推荐"},
            ],
            "arch": {
                "components": ["SOP 标准作业程序", "设备图纸", "运维手册", "应急预案(EOP)", "故障树/案例库"],
                "design": "把专家经验沉淀为可检索、可推荐的知识资产；故障处置时按业务域与测点自动关联预案。",
                "redundancy": "版本化管理, 每次演练/故障后复盘更新。",
            },
            "logic": [
                {"title": "EOP 62 类事件(典型分类)", "steps": [
                    {"step": 1, "text": "电力类: 进线失电/柴发失败/UPS 故障/母联异常", "ok": True},
                    {"step": 2, "text": "暖通类: 冷机失效/水泵故障/自然冷切换", "ok": True},
                    {"step": 3, "text": "消防类: 烟感/温感/气体灭火/切非联动", "ok": True},
                    {"step": 4, "text": "弱电类: 门禁失效/视频丢失/周界报警", "ok": True},
                ]},
            ],
            "note": "知识库是“把人脑变平台能力”的载体：EOP 覆盖 62 类主要事件，故障发生时按测点自动推荐预案，缩短 MTTR。",
        },
    }


# ------------------------------------------------------------------ 统一设备台账 (派生)
def _build_equipment() -> list[dict]:
    """从各业务域数据派生扁平设备台账, 映射阿里云课程 domain/category 业务单元分类。"""
    items: list[dict] = []
    eid = 1

    def add(domain, category, code, name, status, **attrs):
        nonlocal eid
        items.append({
            "id": eid, "idc_id": 1, "room_id": None, "code": code, "name": name,
            "domain": domain, "category": category, "vendor": "",
            "model": "", "status": status, "load_pct": attrs.pop("load_pct", 0.0),
            "run_hours": attrs.pop("run_hours", 0), "redundancy": attrs.pop("redundancy", ""),
            "attrs": attrs,
        })
        eid += 1

    cp = chiller_plant()
    for c in cp["chillers"]:
        add("hvac_source", "chiller", c["id"], "冷水机组", c["state"], load_pct=c["load"], cop=c["cop"],
            evapT=c["evapT"], condT=c["condT"], current=c["current"], run_hours=c["runHrs"])
    for c in cp["towers"]:
        add("hvac_source", "cooling_tower", c["id"], "冷却塔", c["state"], fanHz=c["fanHz"], outT=c["outT"])
    for p in cp["pumps"]["chw"]:
        add("hvac_source", "chw_pump", p["id"], "冷冻水泵", p["state"], hz=p["hz"], kw=p["kw"])
    for p in cp["pumps"]["cw"]:
        add("hvac_source", "cw_pump", p["id"], "冷却水泵", p["state"], hz=p["hz"], kw=p["kw"])
    for h in cp["hex"]:
        add("hvac_source", "hex", h["id"], "板式换热器", h["state"], eff=h["eff"])
    for v in cp["valves"]:
        add("hvac_source", "valve", v["id"], v["name"], v["state"], pos=v["pos"])

    cr = crac()
    for u in cr["units"]:
        add("hvac_terminal", "crac", u["id"], "精密空调", u["state"], supplyT=u["supplyT"],
            returnT=u["returnT"], fan=u["fan"], valve=u["valve"], room=u["room"])
    for f in cr["fresh"]:
        add("hvac_terminal", "fau", f["id"], "新风机组", f["state"], co2=f["co2"], filterDp=f["filterDp"])
    for h in cr["humid"]:
        add("hvac_terminal", "humidifier", h["id"], h["name"], h["state"], rh=h["rh"], mode=h["mode"])

    h = hv()
    for inc in h["incomers"]:
        add("power_hv", "hv_incomer", inc["id"], "中压进线柜", inc["state"], u=inc["u"], i=inc["i"],
            p=inc["p"], q=inc["q"], pf=inc["pf"], freq=inc["freq"], energy=inc["energy"], src=inc["src"])
    add("power_hv", "bus_tie", h["busTie"]["id"], "母联柜(备自投)", h["busTie"]["state"], auto=h["busTie"]["autoSwitch"])
    for f in h["feeders"]:
        add("power_hv", "hv_feeder", f["id"], "中压馈线柜", f["state"], load=f["load"],
            i=f["i"], p=f["p"], pf=f["pf"], energy=f["energy"])
    for t in h["transformers"]:
        add("power_hv", "hv_transformer", t["id"], "10KV配电变压器", t["state"],
            feeder=t["feeder"], load_pct=t["load"], windingT=t["windingT"], oilT=t["oilT"],
            ambT=t["ambT"], humidity=t["humidity"], tap=t["tap"], fan=t["fan"])

    lv_snap = lv()
    for t in lv_snap["transformers"]:
        add("power_lv", "transformer", t["id"], "变压器", t["state"], load_pct=t["load"], t=t["t"],
            u=t["u"], i=t["i"], p=t["p"], pf=t["pf"], energy=t["energy"], thdu=t["thdu"], thdi=t["thdi"])
    for u in lv_snap["upsGroups"]:
        add("power_lv", "ups", u["id"], "UPS 组", u["state"], load_pct=u["load"], uOut=u["uOut"], mode=u["mode"],
            iOut=u["iOut"], p=u["p"], pf=u["pf"], energy=u["energyIn"], thdu=u["thdu"], thdi=u["thdi"])
    for hvdc in lv_snap["hvdc"]:
        add("power_lv", "hvdc", hvdc["id"], "高压直流", hvdc["state"], load_pct=hvdc["load"], u=hvdc["u"],
            modRun=hvdc["modRun"], modN=hvdc["modN"], i=hvdc["i"], p=hvdc["p"], pf=hvdc["pf"],
            energy=hvdc["energy"], thdi=hvdc["thdi"])
    for a in lv_snap["ats"]:
        add("power_lv", "ats", a["id"], "ATS 自动切换", a["state"], mode=a["mode"], lastSw=a["lastSw"],
            uOut=a["uOut"], pf=a["pf"], p=a["p"])
    for b in lv_snap["busbars"]:
        add("power_lv", "busbar", b["id"], "低压母排", b["state"], load_pct=b["load"], i=b["i"], u=b["u"],
            pf=b["pf"], energy=b["energy"], thdu=b["thdu"])
    for br in lv_snap["branches"]:
        add("power_lv", "branch", br["id"], "低压馈线回路", br["breaker"], load=br["name"], rated=br["rated"],
            u=br["u"], i=br["i"], p=br["p"], pf=br["pf"], freq=br["freq"], energy=br["energy"],
            thdu=br["thdu"], thdi=br["thdi"], load_pct=br["loadPct"])
    for s in lv_snap["spds"]:
        add("power_lv", "spd", s["id"], "浪涌保护器(SPD)", s["status"], state=s["state"], leakI=s["leakI"],
            count=s["count"], level=s["level"])

    g = genset()
    for u in g["units"]:
        add("power_genset", "genset", u["id"], "柴油发电机", u["state"],
            breaker=u["breaker"], incomer=u["incomer"], u=u["u"], i=u["i"], p=u["p"], q=u["q"],
            pf=u["pf"], freq=u["freq"], energy=u["energy"], rpm=u["rpm"], waterT=u["waterT"],
            oilP=u["oilP"], battU=u["battU"], startCnt=u["startCnt"], run_hours=u["runHrs"],
            faults=len(u["faults"]), protections=len(u["protections"]), redundancy="N+1")
    f = fuel()
    for t in f["mainTanks"]:
        add("power_fuel", "fuel_tank", t["id"], "地埋主油罐", "正常", level=t["level"], t=t["t"],
            cap=t["cap"], leak=t["leak"], valves=len(t["valves"]), switches=len(t["switches"]),
            protections=len(t["protections"]))
    for t in f["dayTanks"]:
        add("power_fuel", "day_tank", t["id"], "日用油箱", "正常", level=t["level"], cap=t["cap"],
            leak=t["leak"], switches=len(t["switches"]), protections=len(t["protections"]))
    for p in f["pumps"]:
        add("power_fuel", "fuel_pump", p["id"], "输油泵", p["state"], mode=p["mode"],
            alarms=len(p["alarms"]), protections=len(p["protections"]))

    b = battery()
    for grp in b["groups"]:
        add("power_batt", "battery_group", grp["id"], "蓄电池组", grp["state"], soc=grp["soc"], u=grp["u"],
            i=grp["i"], cdState=grp["cdState"], maxT=grp["maxT"], ir=grp["ir"],
            cells=len(grp["cells"]), type=grp["type"])

    cct = cctv()
    for z in cct["zones"]:
        add("sec_cctv", "camera", f"CAM-{z['id']}", f"摄像机-{z['id']}", "在线" if z["offline"] == 0 else "离线",
            cams=z["cams"], offline=z["offline"])
    ac = acs()
    for a in ac["areas"]:
        add("sec_acs", "door_ctrl", f"ACS-{a['id']}", f"门禁-{a['id']}", "在线", doors=a["doors"], auth=a["auth"])
    idso = ids()
    add("sec_ids", "fence", "FENCE-01", "电子围栏", "布防", zones=idso["perimeter"]["zones"])
    add("sec_ids", "vibration_fiber", "VIB-01", "振动光纤", "布防", zones=idso["perimeter"]["zones"])
    fr = fire()
    for d in fr["detectors"]:
        add("sec_fire", "smoke_detector" if "烟" in d["type"] else "heat_detector",
            f"DET-{d['type']}", d["type"], "正常" if d["fault"] == 0 else "故障", n=d["n"], fault=d["fault"])

    return items


EQUIPMENT: list[dict] = _build_equipment()


def list_equipment(domain=None, category=None, room=None, status=None):
    data = EQUIPMENT
    if domain:
        data = [e for e in data if e["domain"] == domain]
    if category:
        data = [e for e in data if e["category"] == category]
    if status:
        data = [e for e in data if e["status"] == status]
    if room:
        data = [e for e in data if e.get("attrs", {}).get("room") == room]
    return data


def get_equipment(equipment_id: int):
    return next((e for e in EQUIPMENT if e["id"] == equipment_id), None)


# 各 domain/category 默认测点
_METRIC_MAP = {
    "chiller": ["evapT", "condT", "cop", "load"],
    "cooling_tower": ["outT", "fanHz"],
    "transformer": ["load", "t"],
    "ups": ["load", "uOut"],
    "hvdc": ["load", "u"],
    "crac": ["supplyT", "returnT", "fan"],
    "genset": ["u", "i", "p", "pf", "freq", "battU", "waterT"],
    "fuel_tank": ["level", "t", "switches"],
    "day_tank": ["level", "switches"],
    "fuel_pump": ["alarms", "protections"],
    "battery_group": ["soc", "u", "i", "maxT"],
}


def equipment_metrics(equipment_id: int, minutes: int = 60, step_sec: int = 60, metrics: list[str] | None = None):
    eq = get_equipment(equipment_id)
    if eq is None:
        return None
    rng = random.Random(equipment_id)
    now = datetime.now(timezone.utc)
    step = timedelta(seconds=step_sec)
    n = max(2, int(minutes * 60 / step_sec))
    cat = eq["category"]
    metric_names = metrics or _METRIC_MAP.get(cat, ["load"])
    base_vals = {
        m: float(eq["attrs"].get(m, eq["load_pct"] if m == "load" else rnd(20, 80)))
        for m in metric_names
    }
    series_out = {}
    for m, base in base_vals.items():
        series_out[m] = _walk(rng, base, max(1.0, base * 0.05), n, now, step, f=2)
    return {
        "equipment_id": equipment_id,
        "code": eq["code"],
        "range_minutes": minutes,
        "metrics": metric_names,
        "series": series_out,
    }


# ------------------------------------------------------------------ 对外聚合
_DC_BUILDERS = {
    "chiller_plant": chiller_plant, "crac": crac,
    "hv": hv, "lv": lv, "genset": genset, "fuel": fuel, "battery": battery,
    "cctv": cctv, "acs": acs, "ids": ids, "fire": fire,
    "twin": twin, "capacity": capacity, "alarms": alarms, "energy": energy,
    "tickets": tickets, "inspect": inspect, "maintain": maintain,
    "drill": drill, "shift": shift, "risk": risk, "knowledge": knowledge,
}


def domain_data(name: str) -> dict:
    return _DC_BUILDERS[name]()


# ---- 网络监控域 ----
def network():
    """交换机 / 端口 / Ping / 带宽 全量模拟数据。"""
    import random as _r
    _r.seed(0)

    def _rnd(a, b, f=1):
        return round(_r.uniform(a, b), f)

    # 交换机
    switch_configs = [
        {"id": "SW-CORE-01", "name": "Core-SW-01", "ip": "10.1.0.1", "model": "CE12808", "role": "core", "location": "A01 核心机房"},
        {"id": "SW-CORE-02", "name": "Core-SW-02", "ip": "10.1.0.2", "model": "CE12808", "role": "core", "location": "A01 核心机房"},
        {"id": "SW-AGG-A01", "name": "Agg-A01-SW", "ip": "10.1.1.1", "model": "CE8850", "role": "agg", "location": "A01 汇聚"},
        {"id": "SW-AGG-A02", "name": "Agg-A02-SW", "ip": "10.1.1.2", "model": "CE8850", "role": "agg", "location": "A02 汇聚"},
        {"id": "SW-ACC-A03-1", "name": "Acc-A03-SW01", "ip": "10.1.3.1", "model": "S5735-L48P4X", "role": "access", "location": "A03 接入"},
        {"id": "SW-ACC-A03-2", "name": "Acc-A03-SW02", "ip": "10.1.3.2", "model": "S5735-L48P4X", "role": "access", "location": "A03 接入"},
        {"id": "SW-ACC-B01-1", "name": "Acc-B01-SW01", "ip": "10.2.1.1", "model": "S5735-L48P4X", "role": "access", "location": "B01 接入"},
        {"id": "SW-ACC-B01-2", "name": "Acc-B01-SW02", "ip": "10.2.1.2", "model": "S5735-L48P4X", "role": "access", "location": "B01 接入"},
        {"id": "SW-TOR-01", "name": "TOR-SW-01", "ip": "10.100.1.1", "model": "CE6860", "role": "tor", "location": "A03 TOR"},
        {"id": "SW-TOR-02", "name": "TOR-SW-02", "ip": "10.100.1.2", "model": "CE6860", "role": "tor", "location": "A03 TOR"},
    ]

    port_prefixes = {
        "core": ["10GE", "40GE", "100GE"],
        "agg": ["10GE", "40GE"],
        "access": ["GE", "10GE"],
        "tor": ["25GE", "100GE"],
    }
    port_speeds = {"GE": 1000, "10GE": 10000, "25GE": 25000, "40GE": 40000, "100GE": 100000}

    switches = []
    total_ports = 0
    up_ports_total = 0
    total_traffic = 0.0
    sum_cpu = 0.0
    sum_mem = 0.0
    online_count = 0

    for sw in switch_configs:
        prefixes = port_prefixes.get(sw["role"], ["GE", "10GE"])
        n_ports = _r.randint(24, 48) if sw["role"] in ("access", "tor") else _r.randint(12, 48)
        down_ports_count = _r.randint(0, max(1, n_ports // 10))
        up_ports_count = n_ports - down_ports_count

        ports = []
        in_total = 0.0
        out_total = 0.0
        for i in range(1, n_ports + 1):
            pf = _r.choice(prefixes)
            spd = port_speeds[pf]
            is_up = i > down_ports_count
            if is_up:
                util = _rnd(5, 85, 1) if _r.random() > 0.15 else _rnd(0.1, 4, 1)  # 大部分中等负载
                in_bps = spd * 1e6 * util / 100
                out_bps = in_bps * _rnd(0.6, 1.3, 1)
                in_util = util
                out_util = util * _rnd(0.6, 1.3, 1)
                in_err = _r.randint(0, 3) if _r.random() < 0.05 else 0
                out_err = _r.randint(0, 2) if _r.random() < 0.03 else 0
            else:
                in_bps = 0
                out_bps = 0
                in_util = 0
                out_util = 0
                in_err = 0
                out_err = 0
            ports.append({
                "name": f"{pf}/{i}",
                "alias": f"{sw['name']}-P{i}" if is_up else f"{sw['name']}-P{i} [DOWN]",
                "status": "up" if is_up else "down",
                "speed_mbps": spd,
                "in_bps": round(in_bps, 0),
                "out_bps": round(out_bps, 0),
                "in_util_pct": round(in_util, 1),
                "out_util_pct": round(out_util, 1),
                "in_errors": in_err,
                "out_errors": out_err,
                "in_discards": _r.randint(0, 2) if _r.random() < 0.02 else 0,
            })
            in_total += in_bps
            out_total += out_bps

        cpu = _rnd(15, 65, 1)
        mem = _rnd(30, 75, 1)
        uptime = _r.randint(30, 365)
        is_online = _r.random() > 0.05

        switches.append({
            "id": sw["id"], "name": sw["name"], "ip": sw["ip"],
            "model": sw["model"], "role": sw["role"],
            "location": sw["location"],
            "status": "online" if is_online else "offline",
            "cpu_pct": round(cpu, 1), "mem_pct": round(mem, 1),
            "uptime_days": uptime,
            "total_ports": n_ports, "up_ports": up_ports_count,
            "down_ports": down_ports_count,
            "ports": ports,
        })

        total_ports += n_ports
        up_ports_total += up_ports_count
        total_traffic += (in_total + out_total)
        if is_online:
            online_count += 1
            sum_cpu += cpu
            sum_mem += mem

    n_sw = len(switch_configs)

    # ---- Ping 目标 ----
    ping_targets = [
        ("10.1.0.1", "Core-SW-01", "core"),
        ("10.2.0.1", "Core-SW-02-B01", "core"),
        ("202.96.209.133", "上海电信 ISP1", "isp"),
        ("210.22.97.1", "上海联通 ISP2", "isp"),
        ("114.114.114.114", "公共 DNS", "isp"),
        ("10.200.1.1", "园区 B 核心 (Site-B)", "peer"),
        ("10.200.2.1", "广州容灾中心", "wan"),
        ("61.135.169.121", "华北灾备线路", "wan"),
    ]
    pings = []
    sum_rtt = 0.0
    sum_loss = 0.0
    worst_rtt_name = ""
    worst_rtt_val = 0.0

    for ip, desc, cat in ping_targets:
        if cat == "core":
            base_rtt, loss = (_rnd(0.3, 2.0), _rnd(0, 0.5))
        elif cat == "isp":
            base_rtt, loss = (_rnd(3, 12), _rnd(0, 2))
        elif cat == "peer":
            base_rtt, loss = (_rnd(2, 8), _rnd(0, 1))
        else:
            base_rtt, loss = (_rnd(15, 40), _rnd(0, 3))
        jitter = base_rtt * _rnd(0.05, 0.25, 2)
        status = "ok" if loss < 1 else ("lossy" if loss < 5 else "down")
        pings.append({
            "target": ip, "name": desc, "category": cat,
            "rtt_min_ms": round(base_rtt * 0.8, 1),
            "rtt_avg_ms": round(base_rtt, 1),
            "rtt_max_ms": round(base_rtt * 1.5, 1),
            "loss_pct": round(loss, 1),
            "jitter_ms": round(jitter, 1),
            "status": status,
        })
        sum_rtt += base_rtt
        sum_loss += loss
        if base_rtt > worst_rtt_val:
            worst_rtt_val = base_rtt
            worst_rtt_name = desc

    # ---- 带宽 TopN ----
    top_ports = ["10GE/1", "100GE/3", "10GE/5", "40GE/2", "10GE/8",
                 "25GE/1", "10GE/12", "40GE/4", "10GE/7", "100GE/1"]
    top_names = ["Core→Agg 上行", "A03 TOR→Core 上行", "B01→Core 上行",
                 "Agg→Core A 聚合", "办公网出口", "存储网络主干",
                 "管理口汇聚", "安全域互联", "视频流专线", "AI训练网络"]
    bw_items = []
    for i, (pn, desc) in enumerate(zip(top_ports, top_names), 1):
        util = _rnd(15, 95, 1)
        spd_name = pn.split("/")[0]
        cap = port_speeds.get(spd_name, 10000)
        bw_items.append({
            "rank": i, "name": desc, "device": f"SW {'Core' if i <= 4 else 'Access'}-{i:02d}",
            "direction": "out" if i % 2 == 0 else "in",
            "util_pct": round(util, 1),
            "traffic_bps": round(cap * 1e6 * util / 100, 0),
            "capacity_mbps": cap,
            "alert": util > 80,
        })

    return {
        "switches": switches,
        "total_switches": n_sw,
        "online_switches": online_count,
        "offline_switches": n_sw - online_count,
        "total_ports": total_ports,
        "up_ports": up_ports_total,
        "down_ports": total_ports - up_ports_total,
        "overall_port_rate": round(up_ports_total / total_ports * 100, 1) if total_ports else 0,
        "total_traffic_bps": round(total_traffic, 0),
        "avg_cpu_pct": round(sum_cpu / online_count, 1) if online_count else 0,
        "avg_mem_pct": round(sum_mem / online_count, 1) if online_count else 0,
        "ping_targets": pings,
        "avg_ping_rtt_ms": round(sum_rtt / len(ping_targets), 1),
        "avg_ping_loss_pct": round(sum_loss / len(ping_targets), 1),
        "worst_ping_target": worst_rtt_name,
        "bw_topn": bw_items,
    }


# network() 定义在 _DC_BUILDERS 之后, 需追加注册 (置于字典字面量中会 NameError)
_DC_BUILDERS["network"] = network
