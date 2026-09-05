"""DC-IOC 数据聚合服务 —— 统一数据流向的唯一出口。

设计原则：
- 所有业务端点由此取数，不再直接依赖 dc_ioc_data 硬编码生成器。
- 优先从真实采集链路（external_devices + metric_raws）聚合数据；
  无真实数据时自动回退到 dc_ioc_data 生成器，并在返回体中标记 "_source": "generated"。
- MockCollector 通过 external 契约推送的实时数据被本层消费，实现"自动生成 + 上线无缝切换"。
- 生产环境接入真实采集器后，只需关闭 MockCollector，业务端点零改动。
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_

from app.core.config import settings
from app.crud import external as ext_crud
from app.crud.external import ONLINE_THRESHOLD_SEC
from app.db.session import SessionLocal
from app.models.control_log import ControlLog
from app.models.external import ExternalDevice, MetricRaw
from app.services import dc_ioc_data as generated

logger = logging.getLogger("dc_aggregator")


class DataSourceNotReadyError(RuntimeError):
    """[S-04] 真实数据源模式下, 真实外部设备数据缺失, 拒绝服务。

    由 main.py 的全局异常处理器捕获, 返回 HTTP 503 + 结构化错误体,
    避免生产环境把演示生成数据当真实数据展示。
    """

    status_code: int = 503

# ---- 数据库会话获取 ----
def _get_db():
    """尽量返回 DB 会话，不可用时返回 None（走内存/生成器兜底）。"""
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("select 1"))
        return db
    except Exception as e:
        logger.debug("DB 不可用，聚合层将使用兜底数据: %s", e)
        return None

# ---- 工具 ----
def _stamp(obj: dict, source: str) -> dict:
    obj["_source"] = source
    return obj

# ---- 实时测点查询 ----
def _latest_metric_for_device(device_id: str, metric_name: str, db=None, fallback_val: float = 0.0) -> float:
    """获取某设备最新一个测点的值。"""
    try:
        rows = ext_crud.recent_metrics(db, device_id, limit=1)
        for r in rows:
            if r.metric_name == metric_name:
                return r.value
    except Exception as e:
        logger.debug("测点 %s 实时值读取失败, 回退 metric_raws: %s", metric_name, e)
    # 兜底：从 metric_raws 批量取最近数据
    if db is not None:
        try:
            from sqlalchemy import desc
            from app.models.external import MetricRaw
            row = db.query(MetricRaw).filter(
                MetricRaw.device_id == device_id,
                MetricRaw.metric_name == metric_name,
            ).order_by(desc(MetricRaw.received_at)).limit(1).first()
            if row:
                return row.value
        except Exception as e:
            logger.debug("测点 %s metric_raws 兜底查询失败, 返回默认值: %s", metric_name, e)
    return fallback_val

# ======================================================================
#  [S-04] 数据源模式守卫
# ======================================================================
def _real_mode_requires_real_data() -> bool:
    """当前是否处于 real 模式 (需要真实外部设备数据)。"""
    return settings.DATA_SOURCE == "real"


def _guard_real_source_has_devices() -> None:
    """real 模式下, 若已注册外部设备数量为 0, 拒绝服务并报错。

    在依赖真实设备的聚合入口调用 (驾驶舱总览 / 各域 _aggregate)。
    纯生成类数据 (演练/工单/知识库等) 不依赖外部设备, 不受此约束。
    """
    if not _real_mode_requires_real_data():
        return
    db = _get_db()
    try:
        _, total, _, _ = ext_crud.list_devices(db, skip=0, limit=1)
    finally:
        if db is not None:
            db.close()
    if total == 0:
        raise DataSourceNotReadyError(
            "真实数据源模式 (DATA_SOURCE=real) 下未检测到任何已注册外部设备。"
            "请确认采集器已接入并向 /api/external/* 推送数据, 或将 DATA_SOURCE 改回 mock。"
        )


# ======================================================================
#  KPI / 驾驶舱总览 (从真实数据聚合)
# ======================================================================
def dashboard_overview() -> dict:
    _guard_real_source_has_devices()
    db = _get_db()
    try:
        items, total, online, offline = ext_crud.list_devices(db, skip=0, limit=10000)
    finally:
        if db is not None:
            db.close()

    if total > 0:
        # 有真实设备数据 → 从真实链路聚合
        online_rate = round(online / total * 100, 2) if total > 0 else 0.0
        # 分业务域在线率：按设备 domain 前缀聚合真实在线/总数，根治前端 ±1 派生
        biz: dict[str, list[int]] = {}
        for d in items:
            dom = (getattr(d, "domain", "") or "").lower()
            if dom.startswith("hvac"):
                key = "hvac"
            elif dom.startswith("power"):
                key = "power"
            elif dom.startswith("sec"):
                key = "security"
            else:
                continue
            bucket = biz.setdefault(key, [0, 0])
            bucket[1] += 1
            if getattr(d, "online", False):
                bucket[0] += 1
        domain_online = {
            k: {
                "online": v[0],
                "total": v[1],
                "rate": round(v[0] / v[1] * 100, 2) if v[1] else 0.0,
            }
            for k, v in biz.items()
        }
        # PUE 等运营指标仍用生成器兜底（需真实传感器 + 计算逻辑）
        k = generated.kpi()
        return _stamp({
            "total_devices": total,
            "online_devices": online,
            "online_rate": online_rate,
            "today_alarms": sum(k["alarms"].values()),
            "pue": k["pue"],
            "wue": k["wue"],
            "it_load_mw": k["itLoad"],
            "total_load_mw": k["totalLoad"],
            "cool_load_mw": k["coolLoad"],
            "availability": k["availability"],
            "free_cool_hours": k["freeCoolHours"],
            "alarms": {"crit": k["alarms"]["crit"], "warn": k["alarms"]["warn"], "info": k["alarms"]["info"]},
            "domain_online": domain_online,
        }, "aggregated")
    # 无真实设备 → 回退生成器
    return _stamp(generated_dashboard_overview(), "generated")

def kpi_trends(hours: int = 48) -> dict:
    """驾驶舱 KPI 趋势 (后端 kpi_history 时序表, 根治前端合成示例曲线)。"""
    from app.services import kpi_history as kh

    return {
        "hours": hours,
        "points": kh.get_kpi_trends(hours=hours, max_points=60),
        "source": "kpi_history",
    }


def generated_dashboard_overview() -> dict:
    """从旧版生成器构造总览（保持格式一致）。"""
    k = generated.kpi()
    total = 48 * 60
    online = int(total * 0.993)
    return {
        "total_devices": total,
        "online_devices": online,
        "online_rate": round(online / total * 100, 2),
        "today_alarms": sum(k["alarms"].values()),
        "pue": k["pue"],
        "wue": k["wue"],
        "it_load_mw": k["itLoad"],
        "total_load_mw": k["totalLoad"],
        "cool_load_mw": k["coolLoad"],
        "availability": k["availability"],
        "free_cool_hours": k["freeCoolHours"],
        "alarms": {"crit": k["alarms"]["crit"], "warn": k["alarms"]["warn"], "info": k["alarms"]["info"]},
    }

# ======================================================================
#  业务域聚合函数 —— 优先从真实测点组装，无数据则回退生成器
# ======================================================================

def _aggregate(domain: str, gen_fn, categories: list[str]) -> dict:
    """统一聚合: 单次拉取设备列表, 同时用于域计数与测点注入, 避免重复慢查询。

    - 无真实设备 → 直接返回生成器结果 (generated)。
    - 有真实设备 → 以生成器结构为骨架, 注入真实测点值 (aggregated)。
    """
    _guard_real_source_has_devices()
    db = _get_db()
    try:
        devices_all, _, _, _ = ext_crud.list_devices(
            db, skip=0, limit=10000, with_metric_count=False
        )
    except Exception:
        logger.exception("设备列表拉取失败, 回退生成数据: %s", domain)
        return _stamp(gen_fn(), "generated")
    finally:
        if db is not None:
            db.close()
    cnt = len([d for d in devices_all if getattr(d, "domain", None) == domain])
    if cnt == 0:
        return _stamp(gen_fn(), "generated")
    data = gen_fn()
    try:
        for cat in categories:
            _inject_metric_values(data, cat, devices_all)
    except Exception:
        logger.exception("%s 实时指标注入失败, 回退生成数据", domain)
    return _stamp(data, "aggregated")

def _devices_in_domain(db, domain: str) -> list[dict]:
    """获取某业务域下的已注册设备列表（简化视图）。"""
    try:
        items, _, _, _ = ext_crud.list_devices(db, domain=domain, skip=0, limit=10000, with_metric_count=False)
        return [i.model_dump() for i in items]
    except Exception as e:
        logger.warning("业务域 %s 设备列表查询失败, 返回空列表: %s", domain, e)
        return []

# ---- 暖通 ----
# D6 持久化: 快控指令先记录到 ControlLog, 这里把"最新指令"作为覆盖项叠加到聚合结果,
# 使下发在 30s 轮询刷新后依然生效 (真实执行器未接入, 演示态以留痕指令覆盖)。
# 模式指令不便入独立列(feature), 以 value 的整数编码记录: 1=制冷模式 2=预冷模式 3=自然冷却
_CONTROL_MODES = ["制冷模式", "预冷模式", "自然冷却"]


def _apply_control_overrides(data: dict) -> dict:
    if not isinstance(data, dict) or "chillerGroups" not in data:
        return data

    db = None
    try:
        db = SessionLocal()
        logs = (
            db.query(ControlLog)
            .filter(ControlLog.result == "accepted")
            .order_by(ControlLog.id.desc())
            .all()
        )
    except Exception:
        logger.exception("读取控制指令留痕失败, 跳过覆盖")
        if db is not None:
            db.close()
        return data
    finally:
        if db is not None:
            db.close()

    state_by_chiller: dict[str, str] = {}
    latest_mode: str | None = None
    latest_temp: float | None = None

    # logs 已按 id 倒序(最新在前), 各维度首次命中即采用
    for log in logs:
        if log.action in ("start", "stop"):
            cid = str(log.chiller_id)
            if cid not in state_by_chiller:
                state_by_chiller[cid] = "运行" if log.action == "start" else "停机"
        elif log.action == "mode":
            if latest_mode is None and log.value is not None:
                idx = int(log.value) - 1
                if 0 <= idx < len(_CONTROL_MODES):
                    latest_mode = _CONTROL_MODES[idx]
        elif log.action == "temp":
            if latest_temp is None and log.value is not None:
                latest_temp = float(log.value)

    for g in data.get("chillerGroups", []) or []:
        if not isinstance(g, dict):
            continue
        c = g.get("chiller") or {}
        cid = str(c.get("id", ""))
        if cid in state_by_chiller:
            c["state"] = state_by_chiller[cid]

    if latest_mode is not None:
        data["mode"] = latest_mode
    if latest_temp is not None:
        data["targetSupplyT"] = latest_temp
    return data


def chiller_plant() -> dict:
    data = _aggregate("hvac_source", generated.chiller_plant, ["chiller", "sec_pump", "storage_tank", "ambient"])
    return _apply_control_overrides(data)

def crac() -> dict:
    return _aggregate("hvac_terminal", generated.crac, ["leak", "crac"])

def chiller_trends() -> dict:
    """冷源趋势数据 (7类趋势图 + 1类柱状图) —— 纯时序数据，无需聚合"""
    return generated.chiller_trends()

def crac_trends() -> dict:
    """空调末端趋势诊断 (7类趋势图) —— 纯时序数据，无需聚合"""
    return generated.crac_trends()

def liquid_cooling() -> dict:
    """液冷系统聚合: CDU + 冷板 + 管路 + 漏液检测 + 热回收"""
    return _aggregate("hvac_liquid_cooling", generated.liquid_cooling, ["primary_cdu", "secondary_cdu", "leak", "heat_rejection"])

# ---- 电力 ----
def hv() -> dict:
    return _aggregate("power_hv", generated.hv, [])

def lv() -> dict:
    return _aggregate("power_lv", generated.lv, [])

def genset() -> dict:
    return _aggregate("power_genset", generated.genset, [])

def fuel() -> dict:
    return _aggregate("power_fuel", generated.fuel, [])

def battery() -> dict:
    return _aggregate("power_batt", generated.battery, [])

# ---- 安防消防 ----
def cctv() -> dict:
    return _aggregate("sec_cctv", generated.cctv, [])

def acs() -> dict:
    return _aggregate("sec_acs", generated.acs, [])

def ids() -> dict:
    return _aggregate("sec_ids", generated.ids, [])

def fire() -> dict:
    return _aggregate("sec_fire", generated.fire, [])

# ---- 智能运营 + 运维作业 (纯运营数据，无物理设备，继续使用生成器) ----
def twin() -> dict:
    return _stamp(generated.twin(), "generated")

def capacity() -> dict:
    # [B4] 真实容量/能耗数据底座: 基于真实设备测点聚合, 无设备时回退生成器
    from app.db.session import SessionLocal
    from app.services import capacity_energy as ce

    db = SessionLocal()
    try:
        return ce.capacity(db)
    finally:
        db.close()

def alarms() -> dict:
    return _stamp(generated.alarms(), "generated")

def energy() -> dict:
    # [B4] 真实容量/能耗数据底座: 基于真实设备测点聚合, 无设备时回退生成器
    from app.db.session import SessionLocal
    from app.services import capacity_energy as ce

    db = SessionLocal()
    try:
        return ce.energy(db)
    finally:
        db.close()

def tickets() -> dict:
    return _stamp(generated.tickets(), "generated")

def inspect() -> dict:
    return _stamp(generated.inspect(), "generated")

def maintain() -> dict:
    return _stamp(generated.maintain(), "generated")

def drill() -> dict:
    return _stamp(generated.drill(), "generated")

def shift() -> dict:
    return _stamp(generated.shift(), "generated")

def risk() -> dict:
    return _stamp(generated.risk(), "generated")

def knowledge() -> dict:
    return _stamp(generated.knowledge(), "generated")

# ---- 统一设备台账 (B2: external_devices 为单一事实源) ----
def _ext_device_to_equipment(dev: ExternalDevice) -> dict:
    """将 external_devices ORM 行映射为统一台账 dict (B2 单一事实源)。"""
    online = False
    if dev.last_seen is not None:
        try:
            delta = (datetime.now(timezone.utc) - dev.last_seen).total_seconds()
            online = delta <= ext_crud.ONLINE_THRESHOLD_SEC
        except Exception as e:  # noqa: BLE001
            logger.debug("设备 %s last_seen 解析失败, 视为离线: %s", dev.device_id, e)
            online = False
    return {
        "id": dev.id,
        "idc_id": 1,
        "room_id": None,
        "code": dev.device_id,
        "name": dev.name or dev.device_id,
        "domain": dev.domain or "",
        "category": dev.category or "",
        "vendor": dev.vendor or "",
        "model": dev.model,
        "status": "运行" if online else "离线",
        "load_pct": 0,
        "run_hours": 0,
        "redundancy": "",
        "attrs": {
            "location": dev.location,
            "protocol": dev.protocol,
            "ip": dev.ip,
            "sn": dev.sn,
            "tags": list(dev.tags or []),
            "description": dev.description,
            "online": online,
            "last_seen": dev.last_seen.isoformat() if dev.last_seen else None,
        },
    }


def list_equipment(domain=None, category=None, room=None, status=None,
                   db=None, kw=None, page=1, page_size=20):
    """统一设备台账: external_devices 为单一事实源, generated 仅零设备/异常兜底 (B2)。

    返回 EquipmentPage 兼容 dict {items, total, page, page_size}。
    优先从 external_devices 取数 (支持 domain/category/keyword 过滤与分页); 当无 DB /
    查询异常 / 无设备时, 回退 generated 生成器, 保证页面始终可用。
    """
    if db is not None:
        try:
            q = db.query(ExternalDevice)
            if domain:
                q = q.filter(ExternalDevice.domain == domain)
            if category:
                q = q.filter(ExternalDevice.category == category)
            if kw:
                like = f"%{kw}%"
                q = q.filter(
                    or_(
                        ExternalDevice.device_id.ilike(like),
                        ExternalDevice.name.ilike(like),
                        ExternalDevice.vendor.ilike(like),
                        ExternalDevice.model.ilike(like),
                    )
                )
            total = q.count()
            if total > 0:
                rows = (
                    q.order_by(ExternalDevice.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .all()
                )
                return {
                    "items": [_ext_device_to_equipment(r) for r in rows],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
        except Exception:  # noqa: BLE001
            logger.debug("台账 external_devices 查询失败, 回退 generated", exc_info=True)

    # ---- 兜底: generated 生成器 (零设备场景) ----
    gen = generated.list_equipment(domain=domain, category=category, room=room, status=status)
    if kw:
        k = kw.strip().lower()
        gen = [
            e for e in gen
            if k in (str(e.get("code", "")) + str(e.get("name", "")) + str(e.get("vendor", ""))).lower()
        ]
    total = len(gen)
    start = (page - 1) * page_size
    return {
        "items": [dict(e) for e in gen[start : start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_equipment(equipment_id: int, db=None) -> dict | None:
    """按台账 id 取设备详情; 优先 external_devices, 回退 generated。"""
    if db is not None:
        try:
            dev = ext_crud.get_device_by_id(db, equipment_id)
            if dev is not None:
                return _ext_device_to_equipment(dev)
        except Exception:  # noqa: BLE001
            logger.debug("台账详情 external_devices 查询失败, 回退 generated", exc_info=True)
    return generated.get_equipment(equipment_id)


def equipment_metrics(equipment_id: int, minutes: int = 60, step_sec: int = 60,
                      metrics: list | None = None, db=None):
    """台账设备指标序列: 优先取 external_devices 真实遥测, 无数据回退 generated 合成。"""
    device_id = None
    if db is not None:
        try:
            dev = ext_crud.get_device_by_id(db, equipment_id)
            if dev is not None:
                device_id = dev.device_id
        except Exception:  # noqa: BLE001
            logger.debug("台账指标取设备失败", exc_info=True)

    if device_id is not None:
        try:
            names = metrics or [
                m for (m,) in db.query(MetricRaw.metric_name)
                .filter(MetricRaw.device_id == device_id)
                .distinct()
                .all()
            ]
            if not names:
                names = list(ext_crud.latest_metrics(device_id).keys())
            if names:
                end = datetime.now(timezone.utc)
                start = end - timedelta(minutes=minutes)
                limit = max(50, min(2000, int(minutes * 60 / max(1, step_sec))))
                series, _unit = ext_crud.query_history(
                    db, device_id, names, start.isoformat(), end.isoformat(), limit
                )
                return {
                    "equipment_id": equipment_id,
                    "code": device_id,
                    "range_minutes": minutes,
                    "metrics": names,
                    "series": {
                        m: [{"ts": p["ts"], "value": p["value"]} for p in series.get(m, [])]
                        for m in names
                    },
                }
        except Exception:  # noqa: BLE001
            logger.debug("台账指标取真实遥测失败, 回退 generated", exc_info=True)

    return generated.equipment_metrics(equipment_id, minutes=minutes, step_sec=step_sec, metrics=metrics)


# ---- 辅助：从真实测点注入值到生成器结构 ----
def _mean_metric(realtime: list[dict], metric_name: str):
    """取所有真实设备某测点的数值平均值 (忽略非数值 / 缺失)。"""
    vals: list[float] = []
    for dev in realtime:
        for p in dev.get("points", []):
            if p.get("metric_name") == metric_name:
                v = p.get("value")
                if isinstance(v, (int, float)):
                    vals.append(float(v))
    return sum(vals) / len(vals) if vals else None


def _inject_metric_values(data: dict, category: str, devices_all: list) -> None:
    """用真实设备 (注册表 + 最新上报) 覆盖生成器结构中的关键数值字段, 使 aggregated 分支携带真实测点值。

    - devices_all 为预先拉取的设备列表 (单次查询复用), 避免重复慢查询。
    - 通过 category 过滤真实设备 (与 MockCollector / 真实采集器注册的类别对应)。
    - 对 chiller 冷源: 用真实冷水机组测点聚合覆盖 plant 级 supplyT/returnT/flow/plr。
    - 始终附加 realtimeDevices 明细 (每个真实设备的实时测点 + quality), 前端可选用渲染。
    """
    if not devices_all:
        return

    # 仅取本类别真实设备
    real_devs = [d for d in devices_all if getattr(d, "category", None) == category]
    if not real_devs:
        return

    # 构造每个真实设备的实时测点快照
    realtime: list[dict] = []
    for d in real_devs:
        did = getattr(d, "device_id", None)
        if not did:
            continue
        try:
            latest = ext_crud.latest_metrics(did) or {}
        except Exception as e:
            logger.debug("设备 %s 最新测点缓存读取失败: %s", did, e)
            latest = {}
        points = []
        for mn, mv in latest.items():
            if isinstance(mv, dict):
                points.append({
                    "metric_name": mn,
                    "value": mv.get("value"),
                    "unit": mv.get("unit"),
                    "quality": mv.get("quality", "good"),
                    "ts": mv.get("ts"),
                })
            else:
                points.append({"metric_name": mn, "value": mv})
        realtime.append({
            "device_id": did,
            "name": getattr(d, "name", None) or did,
            "category": category,
            "domain": getattr(d, "domain", None),
            "online": getattr(d, "online", True),
            "points": points,
        })

    if not realtime:
        return

    # 真实明细挂到返回体 (多类别调用时累积, 不覆盖)
    data.setdefault("realtimeDevices", []).extend(realtime)

    # 对 chiller 冷源: 用真实测点聚合覆盖 plant 级关键字段
    if category == "chiller":
        st = _mean_metric(realtime, "supply_temp")
        rt = _mean_metric(realtime, "return_temp")
        fl = _mean_metric(realtime, "flow_rate")
        plr = _mean_metric(realtime, "load_ratio")
        if st is not None:
            data["supplyT"] = round(st, 1)
        if rt is not None:
            data["returnT"] = round(rt, 1)
        if fl is not None:
            data["flow"] = round(fl, 0)
        if plr is not None:
            data["plr"] = round(plr, 0)

    # 二次冷冻水泵 (二次泵): 用真实测点覆盖 pumps.sec (按位映射, 设备ID为自动生成)
    if category == "sec_pump":
        sec = data.get("pumps", {}).get("sec")
        if sec is not None and realtime:

            def _num(pts, k):
                try:
                    return float(pts[k])
                except (KeyError, TypeError, ValueError):
                    return None

            n = min(len(sec), len(realtime))
            for i in range(n):
                rec = sec[i]
                pts = {p["metric_name"]: p["value"] for p in realtime[i].get("points", [])}
                v = _num(pts, "sec_flow_rate")
                if v is not None:
                    rec["flow"] = round(v, 0)
                v = _num(pts, "pump_hz")
                if v is not None:
                    rec["hz"] = round(v, 0)
                v = _num(pts, "pump_kw")
                if v is not None:
                    rec["kw"] = round(v, 0)
                v = _num(pts, "sec_pressure")
                if v is not None:
                    rec["pressure"] = round(v, 3)
                v = _num(pts, "run_status")
                if v is not None:
                    rec["state"] = "运行" if v == 1 else ("故障" if v == 2 else "停机")

    # 蓄冷罐: 多罐测点聚合覆盖 storageTank
    if category == "storage_tank":
        st = data.get("storageTank")
        if st is not None and realtime:

            def _g(r, k):
                pts = {p["metric_name"]: p["value"] for p in r.get("points", [])}
                try:
                    return float(pts[k])
                except (KeyError, TypeError, ValueError):
                    return None

            def _avg(k):
                vals = [_g(r, k) for r in realtime]
                vals = [x for x in vals if x is not None]
                return sum(vals) / len(vals) if vals else None

            a = _avg("tank_level")
            if a is not None:
                st["level"] = round(a, 0)
            a = _avg("top_temp")
            if a is not None:
                st["topTemp"] = round(a, 1)
            a = _avg("bottom_temp")
            if a is not None:
                st["botTemp"] = round(a, 1)
            a = _avg("flow_rate")
            if a is not None:
                st["flow"] = round(a, 0)
            a = _avg("storage_power")
            if a is not None:
                st["power"] = round(a, 0)
            first_mode = _g(realtime[0], "storage_mode")
            if first_mode is not None:
                st["mode"] = "蓄冷" if first_mode == 1 else ("放冷" if first_mode == 2 else "保冷")

    # 室内外温湿度: 室外取 ENV-OUT, 室内取其余测点均值
    if category == "ambient":
        amb = data.get("ambient")
        if amb is not None and realtime:

            def _g2(r, k):
                pts = {p["metric_name"]: p["value"] for p in r.get("points", [])}
                try:
                    return float(pts[k])
                except (KeyError, TypeError, ValueError):
                    return None

            def _avg2(rs, k):
                vals = [_g2(r, k) for r in rs]
                vals = [x for x in vals if x is not None]
                return sum(vals) / len(vals) if vals else None

            # 首台 ambient (device_id 最小) 为室外站, 其余为机房室内测点
            _rt = sorted(realtime, key=lambda r: r.get("device_id") or "")
            out = _rt[:1]
            ins = _rt[1:]
            if out:
                o = out[0]
                v = _g2(o, "outdoor_temp")
                if v is not None:
                    amb["outdoorTemp"] = round(v, 1)
                v = _g2(o, "wet_bulb")
                if v is not None:
                    amb["wetBulb"] = round(v, 1)
                v = _g2(o, "outdoor_rh")
                if v is not None:
                    amb["outdoorRH"] = round(v, 0)
            v = _avg2(ins, "indoor_temp")
            if v is not None:
                amb["indoorTemp"] = round(v, 1)
            v = _avg2(ins, "indoor_rh")
            if v is not None:
                amb["indoorRH"] = round(v, 0)
            wb = amb.get("wetBulb")
            if wb is not None:
                amb["freeCooling"] = "可自然冷(预冷/全自然冷)" if wb < 15.0 else "需机械制冷"


# ---- 网络监控域 ----
def network_overview() -> dict:
    data = generated.network()
    return {
        "total_switches": data["total_switches"],
        "online_switches": data["online_switches"],
        "offline_switches": data["offline_switches"],
        "total_ports": data["total_ports"],
        "up_ports": data["up_ports"],
        "down_ports": data["down_ports"],
        "overall_port_rate": data["overall_port_rate"],
        "total_traffic_bps": data["total_traffic_bps"],
        "avg_cpu_pct": data["avg_cpu_pct"],
        "avg_mem_pct": data["avg_mem_pct"],
        "switches": data["switches"],
        "routers": data["routers"],
        "firewalls": data["firewalls"],
        "wireless": data["wireless"],
        "ping_targets": data["ping_targets"],
        "avg_ping_rtt_ms": data["avg_ping_rtt_ms"],
        "avg_ping_loss_pct": data["avg_ping_loss_pct"],
        "worst_ping_target": data["worst_ping_target"],
        "bw_topn": data["bw_topn"],
    }


def network_ping() -> dict:
    data = generated.network()
    return {
        "targets": data["ping_targets"],
        "avg_rtt_ms": data["avg_ping_rtt_ms"],
        "avg_loss_pct": data["avg_ping_loss_pct"],
        "worst_rtt_target": data["worst_ping_target"],
    }


def network_bandwidth() -> dict:
    data = generated.network()
    return {"items": data["bw_topn"]}


# ---- 多 DC 聚合 ----
def multi_campus_overview() -> dict:
    """返回多园区概览列表 (默认 4 个 DC)。"""
    import random as _r
    _r.seed(42)

    configs = [
        {"id": "ec1", "name": "华东-杭州 EC1", "short_name": "EC1", "region": "华东", "city": "杭州",
         "status": "online", "pue_base": 1.25, "devices_base": 680, "it_load_base": 12.5, "alarm_base": 2},
        {"id": "ec2", "name": "华东-上海 EC2", "short_name": "EC2", "region": "华东", "city": "上海",
         "status": "online", "pue_base": 1.32, "devices_base": 520, "it_load_base": 9.8, "alarm_base": 1},
        {"id": "nc1", "name": "华北-张家口 NC1", "short_name": "NC1", "region": "华北", "city": "张家口",
         "status": "online", "pue_base": 1.18, "devices_base": 910, "it_load_base": 18.2, "alarm_base": 3},
        {"id": "sc1", "name": "华南-广州 SC1", "short_name": "SC1", "region": "华南", "city": "广州",
         "status": "degraded", "pue_base": 1.40, "devices_base": 410, "it_load_base": 7.2, "alarm_base": 5},
    ]
    campuses = []
    for c in configs:
        pue = c["pue_base"] + _r.uniform(-0.03, 0.05)
        pue = round(max(1.05, min(1.55, pue)), 2)
        wue = round(pue * _r.uniform(1.4, 2.2), 2)
        online = max(1, c["devices_base"] - _r.randint(2, 15))
        online_rate = round(online / c["devices_base"] * 100, 1)
        it_load = round(c["it_load_base"] + _r.uniform(-0.5, 0.8), 1)
        total_load = round(it_load * pue * 0.92, 1)
        today_alarms = max(0, c["alarm_base"] + _r.randint(-1, 4))
        crit = max(0, _r.randint(0, min(2, today_alarms)))
        warn = today_alarms - crit
        avail = round(99.9 + _r.uniform(0, 0.099) if c["status"] != "degraded" else 99.7 + _r.uniform(0, 0.2), 3)

        campuses.append({
            "id": c["id"], "name": c["name"], "short_name": c["short_name"],
            "region": c["region"], "city": c["city"], "status": c["status"],
            "total_devices": c["devices_base"], "online_devices": online,
            "online_rate": online_rate, "pue": pue, "wue": wue,
            "it_load_mw": it_load, "total_load_mw": total_load,
            "today_alarms": today_alarms, "availability": avail,
            "alerts_crit": crit, "alerts_warn": warn,
        })
    return {"campuses": campuses}


def campus_comparison() -> dict:
    """返回跨园区 KPI 对比: PUE / 在线率 / IT 负载 / 总负载 / 告警数。"""
    import random as _r
    _r.seed(42)

    configs = [
        {"short_name": "EC1", "pue": 1.24, "online_rate": 99.1, "it_load_mw": 12.6, "total_load_mw": 15.6, "alarms": 1},
        {"short_name": "EC2", "pue": 1.31, "online_rate": 98.5, "it_load_mw": 9.7, "total_load_mw": 12.8, "alarms": 3},
        {"short_name": "NC1", "pue": 1.17, "online_rate": 99.5, "it_load_mw": 18.4, "total_load_mw": 21.5, "alarms": 2},
        {"short_name": "SC1", "pue": 1.42, "online_rate": 96.3, "it_load_mw": 7.1, "total_load_mw": 10.1, "alarms": 7},
    ]
    metrics_def = [
        ("pue", "PUE", ""),
        ("online_rate", "在线率", "%"),
        ("it_load_mw", "IT负载", "MW"),
        ("total_load_mw", "总功率", "MW"),
        ("alarms", "今日告警", "条"),
    ]
    comparisons = []
    for key, label, unit in metrics_def:
        data = [{"campus": c["short_name"], "value": c[key]} for c in configs]
        # best = min for PUE/alarms, max for others
        if key in ("pue", "alarms"):
            best = min(configs, key=lambda x: x[key])["short_name"]
            worst = max(configs, key=lambda x: x[key])["short_name"]
        else:
            best = max(configs, key=lambda x: x[key])["short_name"]
            worst = min(configs, key=lambda x: x[key])["short_name"]
        comparisons.append({"metric": key, "label": label, "unit": unit, "data": data, "best": best, "worst": worst})
    return {"comparisons": comparisons}


# ---- B5 专业域通用概览: 真实 external_devices 为骨架 + 物模型定义指标 ----
def _domain_is_online(last_seen) -> bool:
    if last_seen is None:
        return False
    now = datetime.now(timezone.utc)
    try:
        delta = (now - last_seen).total_seconds()
    except TypeError:
        delta = (datetime.now() - last_seen).total_seconds()
    return delta <= ONLINE_THRESHOLD_SEC


def _domain_device_metrics(db, device_id, category, ranges):
    """取设备各测点最新值 + 物模型标签 + 阈值状态 (normal/warn/alarm)。"""
    from app.collectors import thing_models

    if db is not None:
        sub = (
            db.query(MetricRaw.metric_name, func.max(MetricRaw.ts).label("mt"))
            .filter(MetricRaw.device_id == device_id)
            .group_by(MetricRaw.metric_name)
            .subquery()
        )
        rows = (
            db.query(MetricRaw.metric_name, MetricRaw.value, MetricRaw.unit)
            .join(
                sub,
                (MetricRaw.metric_name == sub.c.metric_name) & (MetricRaw.ts == sub.c.mt),
            )
            .all()
        )
        raw = {m: {"value": v, "unit": u} for (m, v, u) in rows}
    else:
        latest = ext_crud.latest_metrics(device_id) or {}
        raw = {}
        for m, v in latest.items():
            if isinstance(v, dict):
                raw[m] = {"value": v.get("value"), "unit": v.get("unit", "")}
            else:
                raw[m] = {"value": v, "unit": ""}

    metrics = []
    for m, info in raw.items():
        lo, hi = ranges.get(m, (None, None))
        value = info.get("value")
        status = "normal"
        if lo is not None and hi is not None and value is not None:
            try:
                fv = float(value)
                if fv >= hi:
                    status = "alarm"
                elif fv >= 0.9 * hi:
                    status = "warn"
            except (TypeError, ValueError):
                pass
        metrics.append(
            {
                "key": m,
                "label": thing_models.METRIC_LABELS.get(m, m),
                "value": value,
                "unit": info.get("unit", ""),
                "status": status,
            }
        )
    metrics.sort(key=lambda x: x["key"])
    return metrics


def _domain_synth_stubs(category):
    """零真实设备时的生成器骨架 (扁平设备列表, 供前端统一渲染)。"""
    from app.collectors import mock_collector, thing_models

    defs = mock_collector._CATEGORY_METRICS.get(category)
    if not defs:
        return []
    meta = thing_models.CATEGORY_META.get(category, (category, "", ""))
    short = meta[0] if len(meta) > 0 else category
    domain = meta[1] if len(meta) > 1 else ""
    proto = meta[2] if len(meta) > 2 else ""
    out = []
    for i in (1, 2, 3):
        metrics = []
        for (m, u, lo, hi) in defs:
            val = lo if lo == hi else round(random.uniform(lo, hi), 3 if hi - lo < 1 else 2)
            status = "normal"
            if hi and val >= hi:
                status = "alarm"
            elif hi and val >= 0.9 * hi:
                status = "warn"
            metrics.append(
                {
                    "key": m,
                    "label": thing_models.METRIC_LABELS.get(m, m),
                    "value": val,
                    "unit": u,
                    "status": status,
                }
            )
        out.append(
            {
                "device_id": f"{category.upper()}-{i:02d}",
                "name": f"{short}-{i:02d}",
                "category": category,
                "domain": domain,
                "location": "模拟机房(骨架)",
                "protocol": proto,
                "online": True,
                "status": "运行",
                "metrics": metrics,
            }
        )
    return out


def domain_overview(db, category, minutes: int = 15):
    """专业域概览 (B5): 真实 external_devices 为骨架 + 物模型定义指标; 零设备回退生成器骨架。

    - category 支持逗号分隔多类别 (如 "transformer,ups"), 覆盖一个专业域的多个子类
    - 有真实设备 -> source="real", devices 为 external_devices + 其物模型测点最新值
    - 无真实设备 -> source="generated", 按首个类别合成骨架 (新接入类别也能看到占位)
    """
    from app.collectors import mock_collector

    cats = [c.strip() for c in str(category).split(",") if c.strip()]
    primary = cats[0] if cats else category
    ranges = {m: (lo, hi) for (m, u, lo, hi) in mock_collector._CATEGORY_METRICS.get(primary, [])}

    if db is not None and cats:
        rows = db.query(ExternalDevice).filter(ExternalDevice.category.in_(cats)).all()
    else:
        rows = []

    devices = []
    for r in rows:
        online = _domain_is_online(r.last_seen)
        devices.append(
            {
                "device_id": r.device_id,
                "name": r.name or r.device_id,
                "category": r.category,
                "domain": r.domain,
                "location": r.location,
                "protocol": r.protocol,
                "online": online,
                "status": "运行" if online else "离线",
                "metrics": _domain_device_metrics(db, r.device_id, r.category, ranges),
            }
        )
    if devices:
        return {"category": primary, "source": "real", "devices": devices}
    return {"category": primary, "source": "generated", "devices": _domain_synth_stubs(primary)}


# ---- B3 运维作业域与真实资产/告警联动 ----
_PM_CYCLE = {
    "chiller": "季度", "crac": "季度", "liquid": "季度", "cooling_tower": "季度",
    "chw_pump": "季度", "fau": "季度",
    "ups": "半年", "battery": "半年", "transformer": "半年", "hv_incomer": "半年",
    "camera": "半年",
    "genset": "月度带载", "fuel": "月度",
}
_CYCLE_DAYS = {"月度": 30, "月度带载": 30, "季度": 90, "半年": 180, "年度": 365}


def _alarm_device_ids(db) -> set:
    """当前真实活跃告警关联的设备集合, 用于巡检/维保优先级。"""
    try:
        from app.services import alarm_engine

        return {a.get("device_id") for a in alarm_engine.get_active_alarms() if a.get("device_id")}
    except Exception as e:
        logger.warning("活跃告警设备集合读取失败, 返回空集合: %s", e)
        return set()


def _pm_cycle(cat: str) -> str:
    return _PM_CYCLE.get(cat, "季度")


def _next_due(cycle: str) -> str:
    days = _CYCLE_DAYS.get(cycle, 90)
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def inspection_plan(db):
    """巡检计划 (B3): 真实 external_devices 为巡检对象, 告警设备优先; 合并用户自建路线。"""
    base: dict = {}
    if db is not None:
        try:
            from app.crud import inspection as ins_crud

            base = ins_crud.aggregate(db)
        except Exception as e:
            logger.warning("巡检计划聚合查询失败, 回退空基线: %s", e)
            base = {}
    routes = list(base.get("routes", []))
    findings = list(base.get("findings", []))

    if db is not None:
        alarm_devs = _alarm_device_ids(db)
        rid = 1
        for r in db.query(ExternalDevice).all():
            online = _domain_is_online(r.last_seen)
            triggered = r.device_id in alarm_devs
            routes.insert(
                0,
                {
                    "id": -rid,
                    "code": r.device_id,
                    "freq": "每周",
                    "items": 6,
                    "last": r.last_seen.strftime("%Y-%m-%d") if r.last_seen else "—",
                    "next": "—",
                    "state": "告警触发" if triggered else ("待执行" if online else "离线待巡检"),
                    "deviceId": r.device_id,
                    "deviceName": r.name or r.device_id,
                    "area": r.location or "",
                    "source": "real",
                },
            )
            rid += 1

    today = base.get("today") or {}
    if not today:
        real_cnt = sum(1 for x in routes if x.get("source") == "real")
        today = {
            "plan": real_cnt,
            "done": int(real_cnt * 0.7),
            "abnormal": len(alarm_devs),
            "rate": 92,
        }
    robot = base.get("robot") or {"units": 3, "running": 2, "coverage": 78, "findings": len(findings)}
    return {"today": today, "robot": robot, "routes": routes, "findings": findings}


def maintain_plan(db):
    """维保计划 (B3): 按真实设备类别生成 PM 计划并关联代表设备; 零设备回退生成器基线。"""
    from app.collectors import thing_models

    cats: dict = {}
    if db is not None:
        for r in db.query(ExternalDevice).all():
            cats.setdefault(r.category, []).append(r)

    if cats:
        plans = []
        for cat, devs in cats.items():
            meta = thing_models.CATEGORY_META.get(cat, (cat, "", ""))
            label = meta[0] if meta else cat
            sample = devs[0].device_id
            cycle = _pm_cycle(cat)
            plans.append(
                {
                    "id": f"PM-{cat.upper()}",
                    "equip": f"{label} ({sample})",
                    "cycle": cycle,
                    "last": "—",
                    "next": _next_due(cycle),
                    "vendor": "自维",
                    "state": "正常",
                    "deviceId": sample,
                    "category": cat,
                    "source": "real",
                }
            )
    else:
        plans = generated.maintain()["plans"]

    overdue = sum(1 for p in plans if p.get("state") == "逾期")
    done = sum(1 for p in plans if p.get("state") in ("正常", "已完成"))
    stats = {"plan": len(plans), "done": done, "overdue": overdue, "thisWeek": 1}
    spares = generated.maintain()["spares"]
    return {"stats": stats, "plans": plans, "spares": spares}


def drill_plan(db):
    """演练计划 (B3): 依据真实专业域类别生成建议演练, 合并 DB 演练计划。"""
    cats: set = set()
    if db is not None:
        cats = {r.category for r in db.query(ExternalDevice).all()}

    suggestions = []
    if {"hv_incomer", "transformer", "ups", "genset"} & cats:
        suggestions.append(
            {"id": -1, "code": "DR-PWR", "name": "市电全停-柴发接管演练", "type": "电力",
             "date": "—", "state": "建议(真实资产)", "result": "—", "source": "real"}
        )
    if {"chiller", "crac", "liquid", "cooling_tower"} & cats:
        suggestions.append(
            {"id": -2, "code": "DR-HVAC", "name": "冷源系统故障切换演练", "type": "暖通",
             "date": "—", "state": "建议(真实资产)", "result": "—", "source": "real"}
        )
    if "camera" in cats:
        suggestions.append(
            {"id": -3, "code": "DR-SEC", "name": "周界入侵应急演练", "type": "安防",
             "date": "—", "state": "建议(真实资产)", "result": "—", "source": "real"}
        )

    db_plans = []
    try:
        from app.crud import drill as drill_crud

        rows = drill_crud.list_plans(db)
        db_plans = [drill_crud._to_dict(o) for o in rows] if hasattr(drill_crud, "_to_dict") else rows
    except Exception as e:
        logger.warning("演练计划查询失败, 回退生成数据: %s", e)
        db_plans = generated.drill()["plans"]

    plans = suggestions + list(db_plans)
    stats = {"year": 12, "done": 8, "pass": 8, "next": "2026-08-05 全停演练"}
    try:
        from app.crud import drill as drill_crud
        stats = drill_crud.stats(db)
    except Exception as e:
        logger.warning("演练统计查询失败, 保留默认统计: %s", e)
    return {"stats": stats, "plans": plans}


# ---- 阶段四 任务1 + build-graph-apis: 数字孪生 / 链路拓扑 数据底座门面 ----
def twin_graph() -> dict:
    """数据驱动 园区→包间→设备 层级图 (Twin 页去写死假数据的基础)。"""
    from app.services import twin_graph as svc

    return svc.build_twin_graph()


def twin_topology() -> dict:
    """build-graph-apis: 数据底座 — 合并孪生层级图 + 链路拓扑图 + 汇总指标, 前端一次取全。"""
    from app.services import twin_topology as svc
    return svc.build_topology_data()


def topology_graph() -> dict:
    """供电/制冷链路 节点 + 边 (故障传播与实时流动画的基础)。"""
    from app.services import twin_graph as svc

    return svc.build_topology_graph()


def topology_metrics() -> dict:
    """Link 节点实时测点映射 (任务①): 真实测点驱动能流速度 / 温度, 与 /api/external/.../metrics/realtime 同源。"""
    from app.services import twin_topology as svc

    return svc.build_topology_metrics()


def twin_simulate(req: dict) -> dict:
    """推演仿真 (what-if 故障注入): 故障下游波及 + 容量/能耗/健康影响 + 冗余接管评估。"""
    from app.services import twin_simulation as svc

    return svc.simulate(req)


# ---- 阶段四 任务3: 推演场景库 + 方舟闭环真实节能 ----
def twin_scenarios() -> dict:
    """数据驱动推演场景库 (含波及预览, 前端可点选运行)。"""
    from app.services import twin_simulation as svc

    return svc.scenario_library()


def twin_ark() -> dict:
    """方舟闭环: 基于真实功率/PUE/末端负载测算的节能收益与挖潜空间。"""
    from app.services import twin_simulation as svc

    return svc.ark_closed_loop()
