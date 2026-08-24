"""容量/能耗真实数据底座 (B4, 与 P0-1 协同设计)。

设计要点:
- 独立分析型长期时序表 capacity_energy_history, 不受 metric_raws 保留清理
  (P0-1 retention 循环) 影响 -> 容量/能耗历史长期留存, 不再依赖快照逆推。
- 容量/能耗基于真实设备测点的聚合计算:
    * 设施总功率 = 进线柜(active_power) 或所有功率测点之和
    * 制冷功率   = 暖通类设备功率测点之和
    * 供配电损耗 = 设施功率 × 损耗系数 (默认 4%)
    * IT 负载    = 设施 - 制冷 - 损耗  -> PUE = 设施 / IT
    * 当日能耗   ≈ 设施平均功率(kW) × 当日已过去小时数
- 每日 rollup 将当日聚合写入 capacity_energy_history, 形成真实趋势;
  查询接口读取真实聚合, 无真实设备时回退生成器以保留演示。
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.crud import external as ext_crud
from app.models.capacity_energy import CapacityEnergyHistory
from app.models.external import ExternalDevice

logger = logging.getLogger("capacity_energy")

# ---- 设计容量 (结构性常量, 真实环境应来自 IDC 配置/CMDB) ----
POWER_CAPACITY_MW = 36.0
COOL_CAPACITY_MW = 40.0
RACK_TOTAL = 3600
LOAD_CAPACITY_PCT = 100.0
NET_PORT_TOTAL = 57600
DISTRIBUTION_LOSS_RATIO = 0.04  # 供配电损耗占比 (变压器 + UPS 损耗)

# ---- 类别 -> 角色映射 ----
INTAKE_CATS = {"hv_incomer", "hv_feeder", "incomer"}
COOLING_CATS = {
    "chiller", "crac", "cooling_tower", "chw_pump", "cw_pump", "sec_pump",
    "storage_tank", "heat_exchanger", "humidifier", "fau", "ambient",
    "liquid", "valve",
}
POWER_METRIC_NAMES = {
    "power_kw", "pump_kw", "active_power", "input_power", "output_power",
    "storage_power", "power", "kw",
}

# 每日 rollup 后, capacity_energy_history 写入的指标键
KEY_FACILITY = "facility_kw"
KEY_COOLING = "cooling_kw"
KEY_IT = "it_load_kw"
KEY_LOSS = "loss_kw"
KEY_PUE = "pue"
KEY_ENERGY_DAY = "energy_kwh_day"


def _is_power_metric(name: str) -> bool:
    if name in POWER_METRIC_NAMES:
        return True
    low = (name or "").lower()
    return low.endswith("_kw") or "power" in low


def _role_of(category: str) -> str:
    cat = (category or "").lower()
    if cat in INTAKE_CATS:
        return "intake"
    if cat in COOLING_CATS or cat.startswith("hvac") or "cool" in cat:
        return "cooling"
    return "other"


def _pct(value: float, total: float) -> float:
    return round(value / total * 100.0, 1) if total > 0 else 0.0


# ======================================================================
#  实时聚合
# ======================================================================
def snapshot_power(db: Session) -> dict:
    """返回当前实时功率聚合 (kW): facility / cooling / it / loss / has_data。"""
    rows = db.execute(
        select(ExternalDevice.device_id, ExternalDevice.category)
    ).all()
    if not rows:
        return {"facility": 0.0, "cooling": 0.0, "it": 0.0, "loss": 0.0, "has_data": False}

    total = 0.0
    intake = 0.0
    cooling = 0.0
    for did, cat in rows:
        latest = ext_crud.latest_metrics(did)
        for mname, val in latest.items():
            if not _is_power_metric(mname):
                continue
            v = abs(float((val or {}).get("value", 0) or 0))
            total += v
            role = _role_of(cat)
            if role == "intake":
                intake += v
            elif role == "cooling":
                cooling += v

    facility = intake if intake > 0 else total
    loss = facility * DISTRIBUTION_LOSS_RATIO
    it = max(facility - cooling - loss, 0.0)
    return {"facility": facility, "cooling": cooling, "it": it, "loss": loss, "has_data": True}


def _aggregate_window_power(db: Session, start: datetime, end: datetime) -> Optional[dict]:
    """聚合某时间窗口内 (device, metric) 平均功率 -> 角色汇总。

    用于每日 rollup: 优先用原始测点窗口均值, 比瞬时快照更接近当日真实均值。
    """
    from app.models.external import MetricRaw

    rows = db.execute(
        select(
            ExternalDevice.device_id,
            ExternalDevice.category,
            MetricRaw.metric_name,
            func.avg(MetricRaw.value),
        )
        .join(MetricRaw, MetricRaw.device_id == ExternalDevice.device_id)
        .where(MetricRaw.ts >= start, MetricRaw.ts < end)
        .group_by(ExternalDevice.device_id, ExternalDevice.category, MetricRaw.metric_name)
    ).all()
    if not rows:
        return None

    total = 0.0
    intake = 0.0
    cooling = 0.0
    for _did, cat, mname, avg in rows:
        if not _is_power_metric(mname):
            continue
        v = abs(float(avg or 0))
        total += v
        role = _role_of(cat)
        if role == "intake":
            intake += v
        elif role == "cooling":
            cooling += v

    facility = intake if intake > 0 else total
    loss = facility * DISTRIBUTION_LOSS_RATIO
    it = max(facility - cooling - loss, 0.0)
    return {"facility": facility, "cooling": cooling, "it": it, "loss": loss}


# ======================================================================
#  历史序列读写 (供趋势与累计)
# ======================================================================
def get_history_series(db: Session, metric_key: str, days: int, idc_code: str = "DC1"):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(CapacityEnergyHistory.bucket, CapacityEnergyHistory.value)
        .where(
            and_(
                CapacityEnergyHistory.idc_code == idc_code,
                CapacityEnergyHistory.metric_key == metric_key,
                CapacityEnergyHistory.bucket >= cutoff,
            )
        )
        .order_by(CapacityEnergyHistory.bucket)
    ).all()
    return [r[1] for r in rows]


def sum_daily_energy(db: Session, start: datetime, end: datetime, idc_code: str = "DC1"):
    """返回 [start, end] 内 energy_kwh_day 的累计 (无数据返回 None)。"""
    val = db.execute(
        select(func.coalesce(func.sum(CapacityEnergyHistory.value), None)).where(
            and_(
                CapacityEnergyHistory.idc_code == idc_code,
                CapacityEnergyHistory.metric_key == KEY_ENERGY_DAY,
                CapacityEnergyHistory.bucket >= start,
                CapacityEnergyHistory.bucket <= end,
            )
        )
    ).scalar()
    return val


def _upsert(db: Session, idc_code: str, metric_key: str, bucket: datetime,
            value, unit: str, source: str) -> None:
    existing = db.execute(
        select(CapacityEnergyHistory).where(
            and_(
                CapacityEnergyHistory.idc_code == idc_code,
                CapacityEnergyHistory.metric_key == metric_key,
                CapacityEnergyHistory.bucket == bucket,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            CapacityEnergyHistory(
                idc_code=idc_code, metric_key=metric_key,
                bucket=bucket, value=value, unit=unit, source=source,
            )
        )
    else:
        existing.value = value
        existing.unit = unit
        existing.source = source


# ======================================================================
#  每日 rollup (写入分析型长期时序)
# ======================================================================
def rollup_day(db: Session, day: datetime, idc_code: str = "DC1") -> None:
    """将某日聚合写入 capacity_energy_history (幂等 upsert by scope/key/bucket)。

    day 可为任意 datetime/date, 内部归一为当日 00:00(UTC)。
    优先用当日原始测点窗口均值; 原始数据已被 retention 清掉时回退到实时快照。
    """
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    agg = _aggregate_window_power(db, start, end)
    if agg is None:
        agg = snapshot_power(db)

    facility, cooling, it, loss = agg["facility"], agg["cooling"], agg["it"], agg["loss"]
    pue = (facility / it) if it > 0 else None
    # 当日能耗: 平均设施功率 × 24h 估算 (今日为当日快照代理)
    energy_kwh = facility * 24.0

    _upsert(db, idc_code, KEY_FACILITY, start, round(facility, 3), "kW", "real")
    _upsert(db, idc_code, KEY_COOLING, start, round(cooling, 3), "kW", "real")
    _upsert(db, idc_code, KEY_IT, start, round(it, 3), "kW", "real")
    _upsert(db, idc_code, KEY_LOSS, start, round(loss, 3), "kW", "real")
    _upsert(db, idc_code, KEY_PUE, start, round(pue, 4) if pue is not None else None, "", "real")
    _upsert(db, idc_code, KEY_ENERGY_DAY, start, round(energy_kwh, 2), "kWh", "real")


def rollup_recent(db: Session, days: int = 1, idc_code: str = "DC1") -> None:
    """回补最近 N 天的 rollup (幂等), 用于历史初始化。"""
    now = datetime.now(timezone.utc)
    for d in range(days, -1, -1):
        rollup_day(db, now - timedelta(days=d), idc_code)


# ======================================================================
#  对外聚合接口 (供 dc_aggregator 调用)
# ======================================================================
def energy(db: Session, idc_code: str = "DC1") -> dict:
    from app.services import dc_ioc_data as generated

    snap = snapshot_power(db)
    if not snap["has_data"]:
        return _stamp(generated.energy(), "generated")

    facility, cooling, it, loss = snap["facility"], snap["cooling"], snap["it"], snap["loss"]
    pue = (facility / it) if it > 0 else None

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    hours_elapsed = max((now - today_start).total_seconds() / 3600.0, 0.0)
    today_kwh = facility * hours_elapsed

    # 趋势: 优先真实历史, 不足用当前 PUE 平铺补齐到 30 点
    pue_trend = get_history_series(db, KEY_PUE, 30, idc_code)
    if not pue_trend or pue is None:
        pue_trend = [round(pue, 2)] * 30 if pue is not None else [None] * 30
    else:
        while len(pue_trend) < 30:
            pue_trend.insert(0, pue_trend[0])

    month_kwh = sum_daily_energy(db, now.replace(day=1), now, idc_code)
    year_kwh = sum_daily_energy(
        db, datetime(now.year, 1, 1, tzinfo=timezone.utc), now, idc_code
    )
    if month_kwh is None:
        month_kwh = today_kwh + facility * 24.0 * (now.day - 1)
    if year_kwh is None:
        ytd_days = max((now - datetime(now.year, 1, 1, tzinfo=timezone.utc)).days, 0)
        year_kwh = today_kwh + facility * 24.0 * max(ytd_days - (now.day - 1), 0)

    breakdown = [
        {"id": "IT负载", "kw": round(it, 1), "pct": _pct(it, facility)},
        {"id": "制冷系统", "kw": round(cooling, 1), "pct": _pct(cooling, facility)},
        {"id": "供配电损耗", "kw": round(loss, 1), "pct": _pct(loss, facility)},
        {"id": "照明及其他", "kw": round(max(facility - it - cooling - loss, 0.0), 1),
         "pct": _pct(max(facility - it - cooling - loss, 0.0), facility)},
    ]

    gen = generated.energy()
    return {
        "todayKwh": round(today_kwh, 1),
        "monthKwh": round(month_kwh, 1),
        "yearKwh": round(year_kwh, 1),
        "pueTrend": [round(x, 2) if x is not None else None for x in pue_trend],
        "loadForecast": gen["loadForecast"],
        "aiSaving": gen["aiSaving"],
        "breakdown": breakdown,
        "carbon": gen["carbon"],
        "_source": "real",
    }


def _build_rooms(db: Session) -> list:
    from app.services import dc_ioc_data as generated

    devices = db.execute(
        select(ExternalDevice.device_id, ExternalDevice.category)
    ).all()
    if not devices:
        return generated.capacity()["rooms"]

    n = 12
    per_room_power = defaultdict(float)
    per_room_cool = defaultdict(float)
    for i, (did, cat) in enumerate(devices):
        ridx = i % n
        latest = ext_crud.latest_metrics(did)
        for mname, val in latest.items():
            if not _is_power_metric(mname):
                continue
            v = abs(float((val or {}).get("value", 0) or 0))
            per_room_power[ridx] += v
            if _role_of(cat) == "cooling":
                per_room_cool[ridx] += v

    room_cap_mw = POWER_CAPACITY_MW / n
    cool_cap_mw = COOL_CAPACITY_MW / n
    rooms = []
    for ridx in range(n):
        rp = per_room_power.get(ridx, 0.0)
        rc = per_room_cool.get(ridx, 0.0)
        rooms.append({
            "id": f"R{ridx + 1:02d}",
            "racks": 300,
            "used": max(int(rp // 50), 0),  # 代理: 每 ~50kW 占用 1 机架
            "powerPct": round(min(rp / 1000.0 / room_cap_mw * 100.0, 100.0), 1) if room_cap_mw else 0.0,
            "coolPct": round(min(rc / 1000.0 / cool_cap_mw * 100.0, 100.0), 1) if cool_cap_mw else 0.0,
        })
    return rooms


def capacity(db: Session, idc_code: str = "DC1") -> dict:
    from app.services import dc_ioc_data as generated

    snap = snapshot_power(db)
    if not snap["has_data"]:
        return _stamp(generated.capacity(), "generated")

    facility, cooling = snap["facility"], snap["cooling"]
    dev_count = db.scalar(select(func.count()).select_from(ExternalDevice)) or 0

    dims = [
        {"id": "机柜空间", "used": dev_count, "total": RACK_TOTAL, "unit": "U"},
        {"id": "电力容量", "used": round(facility / 1000.0, 2), "total": POWER_CAPACITY_MW, "unit": "MW"},
        {"id": "制冷容量", "used": round(cooling / 1000.0, 2), "total": COOL_CAPACITY_MW, "unit": "MW"},
        {"id": "承重容量", "used": round(min(dev_count / RACK_TOTAL * LOAD_CAPACITY_PCT, LOAD_CAPACITY_PCT), 1),
         "total": LOAD_CAPACITY_PCT, "unit": "%"},
        {"id": "网络端口", "used": dev_count, "total": NET_PORT_TOTAL, "unit": "口"},
    ]
    gen = generated.capacity()
    return {
        "dims": dims,
        "rooms": _build_rooms(db),
        "forecast": gen["forecast"],
        "knowledge": gen["knowledge"],
        "_source": "real",
    }


def _stamp(data: dict, source: str) -> dict:
    data = dict(data)
    data["_source"] = source
    return data
