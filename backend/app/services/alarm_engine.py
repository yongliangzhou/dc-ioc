"""告警引擎 — 纯函数式阈值评估 + 收敛/升级/确认状态机。

消费端 `sweep_recent_metrics` 与摄取端 `ingest_metrics` 共用本引擎, 确保告警口径一致。

[P0-3 持久化] 原先全部运行态 (活跃告警 / 收敛时间 / 首见时间 / 确认状态 / 规则启停 /
设备抑制) 都在进程内存, 导致: 多 worker 不一致、重启丢状态、规则启停不持久。现改为
DB 表 (alarm_rule / alarm_active_state / alarm_suppressed_device) 作为事实源:
- 内存态保留为热路径缓存 (evaluate 高频读取, O(1) 且不依赖 DB);
- 任何状态变更都「写穿」到 DB (upsert / delete), 重启或跨 worker 通过 hydrate 重建;
- 规则启停 / 设备抑制在启动时从 DB hydrate, 并由 toggle/ack/resolve 写穿;
- DB 不可用时全部静默降级为纯内存模式 (与改造前行为一致, 单元测试无 DB 仍通过)。
与 B7(规则配置化) 同源: alarm_rule 表既存阈值又存 enabled, 后端为规则单一事实源。
"""
from __future__ import annotations

import logging
from time import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import Base
from app.services import alarm_store

# [P2-8] 告警触发计数 (Prometheus). monitoring 不反向依赖本模块, 可安全导入。
from app.core import monitoring

logger = logging.getLogger("alarm.engine")

# 告警通知处理器 (由 lifespan 注册, 如 DB 落库 / WS 推送)
_NOTIFIERS: list = []

# --- 收敛 / 升级参数 ---
_CONVERGENCE_SEC = 300  # 同一 (category, metric, level) 5 分钟内只报一次
_ESCALATE_SEC = 600     # warn 持续 10 分钟升级为 crit

# ===== P0-3 运行态: 内存热路径缓存 (DB 为事实源, 启动时 hydrate) =====
_active_alarm_cache: dict[str, dict] = {}
_convergence_index: dict[str, float] = {}
_first_seen: dict[str, float] = {}
_alarm_states: dict[str, str] = {}          # conv_key -> 待确认 / 已确认
_disabled_rules: set[str] = set()           # 禁用的 rule_id 集合
_suppressed_devices: set[str] = set()       # 抑制告警的设备

# 阈值规则: 已按 (category, metric) 预先建索引, O(1) 匹配
DEFAULT_RULES = [
    {
        "category": "chiller", "unit": "℃",
        "metrics": {
            "supply_temp": {"warn": {"lo": 5, "hi": 15}, "crit": {"lo": 2, "hi": 18}},
            "return_temp": {"warn": {"lo": 10, "hi": 25}, "crit": {"lo": 5, "hi": 30}},
        },
    },
    {
        "category": "ups", "unit": "V",
        "metrics": {
            "output_voltage": {"warn": {"lo": 210, "hi": 242}, "crit": {"lo": 200, "hi": 250}},
            "load_percent": {"warn": {"lo": None, "hi": 85}, "crit": {"lo": None, "hi": 95}},
        },
    },
    {
        "category": "pdudevice", "unit": "%",
        "metrics": {
            "load_percent": {"warn": {"lo": None, "hi": 80}, "crit": {"lo": None, "hi": 95}},
        },
    },
    {
        "category": "acunit", "unit": "%",
        "metrics": {
            "humidity": {"warn": {"lo": 30, "hi": 70}, "crit": {"lo": 20, "hi": 80}},
            "temperature": {"warn": {"lo": 18, "hi": 28}, "crit": {"lo": 15, "hi": 32}},
        },
    },
    {
        "category": "WaterSystem", "unit": "%",
        "metrics": {
            "water_level": {"warn": {"lo": 20, "hi": 90}, "crit": {"lo": 10, "hi": 95}},
        },
    },
]

_MATCHED_RULES: dict[tuple, dict] = {}
RULE_ORDER: list[tuple] = []


def _build_index() -> None:
    """将 DEFAULT_RULES 扁平化为 (category, metric) -> rule 的索引。"""
    for item in DEFAULT_RULES:
        cat = item["category"]
        for m, cfg in item["metrics"].items():
            _MATCHED_RULES[(cat, m)] = cfg
            RULE_ORDER.append((cat, m))


_build_index()


def hydrate_rules(db: Session | None = None) -> None:
    """[B7] 从 DB alarm_rule 表加载阈值到内存索引 _MATCHED_RULES / RULE_ORDER。

    - 引擎运行时匹配以 DB 值为准 (DB 为单一事实源); DB 不可用 / 空时回退 import 期
      的 _build_index() (来自 DEFAULT_RULES), 行为与改造前一致。
    - 仅覆盖阈值 (warn/crit lo/hi); 启停由 _disabled_rules 单独管理 (load_disabled_set)。
    """
    own = db is None
    db = db or alarm_store._get_db()
    if db is None:
        logger.debug("hydrate_rules: 无 DB, 回退 DEFAULT_RULES 索引")
        return
    try:
        rows = db.execute(
            text(
                "SELECT category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit "
                "FROM alarm_rule"
            )
        ).fetchall()
        loaded = 0
        for r in rows:
            cat, m = r[0], r[1]
            _MATCHED_RULES[(cat, m)] = {
                "warn": {"lo": r[2], "hi": r[3]},
                "crit": {"lo": r[4], "hi": r[5]},
                "unit": r[6] or "",
            }
            if (cat, m) not in RULE_ORDER:
                RULE_ORDER.append((cat, m))
            loaded += 1
        logger.info("[B7] 已从 DB alarm_rule 加载 %d 条规则阈值到引擎索引", loaded)
    except Exception as e:  # noqa: BLE001
        logger.debug("hydrate_rules 失败, 回退 DEFAULT_RULES: %s", e)
    finally:
        if own and db is not None:
            db.close()


def _classify(value, rule: dict) -> str | None:
    """返回 'crit' / 'warn' / None。"""
    v = float(value)
    warn = rule.get("warn", {})
    crit = rule.get("crit", {})
    # crit 优先
    if crit.get("hi") is not None and v > float(crit["hi"]):
        return "crit"
    if crit.get("lo") is not None and v < float(crit["lo"]):
        return "crit"
    if warn.get("hi") is not None and v > float(warn["hi"]):
        return "warn"
    if warn.get("lo") is not None and v < float(warn["lo"]):
        return "warn"
    return None


def register_notify_handler(name: str, fn) -> None:
    """注册告警通知处理器 (DB 落库 / WS 推送等), 由 lifespan 调用。"""
    _NOTIFIERS.append((name, fn))


def _notify(alarm: dict) -> None:
    """分发告警事件到所有注册处理器 (DB 落库 / WS 实时推送)。"""
    for _, fn in _NOTIFIERS:
        try:
            fn(alarm)
        except Exception as e:  # noqa: BLE001
            logger.debug("告警通知处理器异常: %s", e)


def evaluate(device_id, category, metric_name, value, unit="", quality="good"):
    """评估单条测点, 命中阈值返回 alarm dict (含收敛去重 / 升级), 否则 None。

    [P0-3] 命中时同步写穿 alarm_active_state, 保证重启 / 多 worker 状态一致。
    """
    if device_id in _suppressed_devices:
        return None
    # 质量差 (bad/unknown 等) 的数据点跳过告警判定
    if quality and quality != "good":
        return None
    key = f"{category}:{metric_name}"
    if key in _disabled_rules:
        return None
    rule = (
        _MATCHED_RULES.get((category, metric_name))
        or _MATCHED_RULES.get((category, "*"))
        or _MATCHED_RULES.get(("*", metric_name))
    )
    if not rule:
        return None
    level = _classify(value, rule)
    if level is None:
        return None
    now_ts = time()
    conv_key = f"{category}:{metric_name}:{level}"
    conv_ts = _convergence_index.get(conv_key, 0.0)
    if (now_ts - conv_ts) < _CONVERGENCE_SEC:
        return None
    first_seen = _first_seen.get(conv_key, now_ts)
    # 升级: 同一 (category, metric, warn) 持续超阈值, 升级为 crit
    if level == "warn":
        if (now_ts - first_seen) >= _ESCALATE_SEC:
            level = "crit"
        else:
            _first_seen.setdefault(conv_key, now_ts)
    alarm = {
        "alarm_id": conv_key,
        "device_id": device_id,
        "category": category,
        "metric_name": metric_name,
        "level": level,
        "value": value,
        "unit": unit or "",
        "quality": quality,
        "ts": now_ts,
        "first_seen": first_seen,
        "ack_state": _alarm_states.get(conv_key, "待确认"),
    }
    _active_alarm_cache[conv_key] = alarm
    _convergence_index[conv_key] = now_ts
    _alarm_states.setdefault(conv_key, "待确认")
    # [P0-3] 写穿活跃告警状态
    alarm_store.upsert_active_state(
        conv_key, alarm, now_ts, _first_seen.get(conv_key, now_ts), _alarm_states[conv_key]
    )
    # [P2-8] 告警触发计数 (收敛窗口内每命中一次记一次, rate() 得告警触发率)
    monitoring.alarms_triggered.labels(
        severity=level, system=alarm.get("category", "unknown")
    ).inc()
    _notify(alarm)
    # 升级后再通知一次 crit (作为独立事件)
    if level == "crit" and (now_ts - first_seen) >= _ESCALATE_SEC:
        escalated = dict(alarm)
        escalated["level"] = "crit"
        escalated["reason"] = "持续超阈值升级"
        _active_alarm_cache[conv_key] = escalated
        alarm_store.upsert_active_state(
            conv_key, escalated, now_ts, _first_seen.get(conv_key, now_ts), _alarm_states[conv_key]
        )
        monitoring.alarms_triggered.labels(
            severity="crit", system=escalated.get("category", "unknown")
        ).inc()
        _notify(escalated)
    return alarm


# ===================== 持久化辅助 (P0-3) =====================

def refresh_engine_config() -> None:
    """从 DB 重新加载规则启停 / 设备抑制到内存缓存 (多 worker 一致性)。"""
    try:
        _disabled_rules.clear()
        _disabled_rules.update(alarm_store.load_disabled_set())
        _suppressed_devices.clear()
        _suppressed_devices.update(alarm_store.load_suppressed_set())
    except Exception as e:  # noqa: BLE001
        logger.debug("refresh_engine_config 失败: %s", e)


def hydrate_alarm_engine() -> None:
    """启动时从 DB 重建内存热路径缓存 (活跃告警 / 收敛 / 首见 / 确认)。"""
    refresh_engine_config()
    try:
        for r in alarm_store.load_active_states():
            k = r["key"]
            _active_alarm_cache[k] = r["alarm"]
            _convergence_index[k] = r["conv_ts"] or r["alarm"].get("ts", 0.0)
            if r["first_seen_ts"]:
                _first_seen[k] = r["first_seen_ts"]
            _alarm_states[k] = r["ack_state"]
    except Exception as e:  # noqa: BLE001
        logger.debug("hydrate_alarm_engine 失败: %s", e)
    # [B7] 从 DB alarm_rule 表 hydrate 阈值到内存索引, 使 DB 成为运行时单一事实源
    hydrate_rules()


def seed_alarm_rules(db: Session) -> int:
    """用 DEFAULT_RULES 向 alarm_rule 表播种 (已存在则跳过, 保留用户启停)。

    [B7] 种子 = DEFAULT_RULES (手调基线) + 物模型推导默认阈值带
    (derive_default_rules, 覆盖其余设备类别)。更新种子数统计。
    """
    # [B7] 合并手调基线 + 物模型推导 (推导补 DEFAULT_RULES 未覆盖的类别)
    from app.services.alarm_rule_derive import derive_default_rules

    seed_rules = list(DEFAULT_RULES) + derive_default_rules()

    Base.metadata.create_all(db.get_bind())
    seeded = 0
    for item in seed_rules:
        category = item.get("category", "")
        for m, cfg in item.get("metrics", {}).items():
            db.execute(
                text(
                    "INSERT INTO alarm_rule "
                    "(rule_id, category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit, enabled, updated_at) "
                    "VALUES (:rid, :cat, :m, :wlo, :whi, :clo, :chi, :u, TRUE, now()) "
                    "ON CONFLICT (rule_id) DO NOTHING"
                ),
                {
                    "rid": f"{category}:{m}",
                    "cat": category,
                    "m": m,
                    "wlo": cfg.get("warn", {}).get("lo"),
                    "whi": cfg.get("warn", {}).get("hi"),
                    "clo": cfg.get("crit", {}).get("lo"),
                    "chi": cfg.get("crit", {}).get("hi"),
                    # [B7] 优先测点级单位 (物模型推导带来), 回退类别级
                    "u": cfg.get("unit", item.get("unit", "")),
                },
            )
            seeded += 1
    db.commit()
    return seeded


# ===================== 运维接口 =====================

def get_active_alarms(limit: int = 200) -> list[dict]:
    if _active_alarm_cache:
        items = list(_active_alarm_cache.values())
    else:
        # [P0-3] 内存为空时回退到 DB (跨 worker / 重启后), 合并确认状态
        rows = alarm_store.load_active_states()
        items = []
        for r in rows:
            a = dict(r["alarm"])
            a["ack_state"] = r["ack_state"]
            items.append(a)
    items.sort(key=lambda a: a.get("ts", 0), reverse=True)
    return items[:limit]


def get_metric_limit(category: str, metric: str) -> float | None:
    """返回 (category, metric) 阈值上限 (优先 crit.hi, 否则 warn.hi), 无规则返回 None。

    供展示层构造告警文案 (阈值越限) 使用, 与 evaluate 共用 _MATCHED_RULES 索引。
    """
    rule = (
        _MATCHED_RULES.get((category, metric))
        or _MATCHED_RULES.get((category, "*"))
        or _MATCHED_RULES.get(("*", metric))
    )
    if not rule:
        return None
    hi = rule.get("crit", {}).get("hi")
    if hi is not None:
        return float(hi)
    return rule.get("warn", {}).get("hi")


def ack_alarm(alarm_id: str) -> bool:
    if alarm_id in _active_alarm_cache:
        _active_alarm_cache[alarm_id]["ack_state"] = "已确认"
    _alarm_states[alarm_id] = "已确认"
    alarm_store.set_active_ack(alarm_id, "已确认")  # [P0-3] 写穿
    return True


def resolve_alarm(alarm_id: str) -> bool:
    _active_alarm_cache.pop(alarm_id, None)
    _convergence_index.pop(alarm_id, None)
    _first_seen.pop(alarm_id, None)
    _alarm_states.pop(alarm_id, None)
    alarm_store.delete_active_state(alarm_id)  # [P0-3] 写穿
    return True


def suppress_device(device_id: str, suppressed: bool, reason: str = "") -> bool:
    if suppressed:
        _suppressed_devices.add(device_id)
    else:
        _suppressed_devices.discard(device_id)
    alarm_store.set_device_suppressed(device_id, suppressed, reason)  # [P0-3] 写穿
    return True


def check_escalations(now_ts: float | None = None) -> int:
    """扫描活跃 warn 告警, 持续超阈值则升级为 crit。返回升级条数。

    now_ts 可注入用于测试; 缺省使用当前时间。
    """
    escalated = 0
    now_ts = now_ts or time()
    for conv_key, alarm in list(_active_alarm_cache.items()):
        if alarm.get("level") != "warn":
            continue
        first_seen = _first_seen.get(conv_key, alarm.get("ts", now_ts))
        if (now_ts - first_seen) >= _ESCALATE_SEC:
            new_alarm = dict(alarm)
            new_alarm["level"] = "crit"
            new_alarm["reason"] = "持续超阈值升级"
            _active_alarm_cache[conv_key] = new_alarm
            _convergence_index[conv_key] = now_ts
            alarm_store.upsert_active_state(  # [P0-3] 写穿
                conv_key, new_alarm, now_ts, _first_seen.get(conv_key, now_ts),
                _alarm_states.get(conv_key, "待确认")
            )
            _notify(new_alarm)
            escalated += 1
    return escalated


def clear_device_alarms(device_id: str) -> int:
    """清除某设备的活跃告警 (巡检离场等场景)。返回清除条数。"""
    removed = 0
    for conv_key in [k for k in _active_alarm_cache if k.startswith(device_id + ":")]:
        _active_alarm_cache.pop(conv_key, None)
        _convergence_index.pop(conv_key, None)
        _first_seen.pop(conv_key, None)
        _alarm_states.pop(conv_key, None)
        alarm_store.delete_active_state(conv_key)  # [P0-3] 写穿
        removed += 1
    return removed


def clear_all() -> int:
    """清空全部活跃告警状态 (测试 / 复位用)。"""
    keys = list(_active_alarm_cache.keys())
    for k in keys:
        alarm_store.delete_active_state(k)  # [P0-3] 写穿
    _active_alarm_cache.clear()
    _convergence_index.clear()
    _first_seen.clear()
    _alarm_states.clear()
    return len(keys)


def engine_state() -> dict:
    active_count = len(_active_alarm_cache) or len(alarm_store.load_active_states())
    return {
        "active_alarms": active_count,
        "suppressed_devices": sorted(_suppressed_devices),
        "disabled_rules": sorted(_disabled_rules),
        "convergence_sec": _CONVERGENCE_SEC,
        "escalate_sec": _ESCALATE_SEC,
        "first_seen_count": len(_first_seen),
        "persistence": "db (alarm_rule / alarm_active_state / alarm_suppressed_device)",  # [P0-3]
    }


# ===================== 规则配置 (B7 同源) =====================

def _default_rules_view() -> list[dict]:
    out = []
    for item in DEFAULT_RULES:
        cat = item.get("category", "")
        for m, cfg in item.get("metrics", {}).items():
            out.append({
                "rule_id": f"{cat}:{m}",
                "category": cat,
                "metric": m,
                "warn": {"lo": cfg.get("warn", {}).get("lo"), "hi": cfg.get("warn", {}).get("hi")},
                "crit": {"lo": cfg.get("crit", {}).get("lo"), "hi": cfg.get("crit", {}).get("hi")},
                "unit": item.get("unit", ""),
                "enabled": True,
            })
    return out


def list_rules() -> list[dict]:
    """返回全部告警规则 + 启停状态。DB 不可用时回退 DEFAULT_RULES。"""
    db = alarm_store._get_db()
    if db is None:
        return _default_rules_view()
    try:
        rows = db.execute(
            text(
                "SELECT rule_id, category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit, enabled "
                "FROM alarm_rule"
            )
        ).fetchall()
        if not rows:
            return _default_rules_view()
        return [
            {
                "rule_id": r[0], "category": r[1], "metric": r[2],
                "warn": {"lo": r[3], "hi": r[4]},
                "crit": {"lo": r[5], "hi": r[6]},
                "unit": r[7], "enabled": bool(r[8]),
            }
            for r in rows
        ]
    except Exception as e:  # noqa: BLE001
        logger.debug("list_rules 回退 DEFAULT_RULES: %s", e)
        return _default_rules_view()
    finally:
        db.close()


def toggle_rule(rule_id: str) -> bool:
    """切换单条规则启停, 写穿 DB。返回是否启用。"""
    if rule_id in _disabled_rules:
        _disabled_rules.discard(rule_id)
        alarm_store.set_rule_enabled(rule_id, True)
    else:
        _disabled_rules.add(rule_id)
        alarm_store.set_rule_enabled(rule_id, False)
    return rule_id not in _disabled_rules


def set_rule_status(rule_id: str, status: str) -> bool:
    """显式设置规则状态 ('enabled' / 'disabled'), 写穿 DB。"""
    enabled = status == "enabled"
    if enabled:
        _disabled_rules.discard(rule_id)
    else:
        _disabled_rules.add(rule_id)
    alarm_store.set_rule_enabled(rule_id, enabled)
    return True


def silence_rule(rule_id: str, duration_minutes: int = 0) -> dict | None:
    """静默规则 'duration_minutes' 分钟 (0 = 永久), 返回静默后的规则视图。"""
    rule = _lookup_rule(rule_id)
    if rule is None:
        return None
    _disabled_rules.add(rule_id)
    alarm_store.set_rule_enabled(rule_id, False)
    alarm_store.set_rule_silenced(rule_id, True, duration_minutes)
    logger.debug("[英伟达|alarm_engine:silence]: 规则已静默: %s (%d min)", rule_id, duration_minutes)
    return _format_one_rule(rule_id, {"enabled": False, "silenced": True})


def _lookup_rule(rule_id: str) -> dict | None:
    """在 DB 或 DEFAULT_RULES 中查找规则详情。"""
    db = alarm_store._get_db()
    if db is not None:
        try:
            row = db.execute(
                text("SELECT * FROM alarm_rule WHERE rule_id = :rid"),
                {"rid": rule_id},
            ).fetchone()
            if row:
                cols = row._mapping
                return {
                    "rule_id": cols.get("rule_id", rule_id),
                    "category": cols.get("category", ""),
                    "metric": cols.get("metric", ""),
                    "warn_lo": cols.get("warn_lo"),
                    "warn_hi": cols.get("warn_hi"),
                    "crit_lo": cols.get("crit_lo"),
                    "crit_hi": cols.get("crit_hi"),
                    "unit": cols.get("unit", ""),
                    "enabled": bool(cols.get("enabled", True)),
                    "silenced": bool(cols.get("silenced", False)),
                }
        except Exception as e:
            logger.warning("规则 %s 查询 DB 失败, 回退 DEFAULT_RULES: %s", rule_id, e)
        finally:
            db.close()
    # fallback to DEFAULT_RULES
    for d in DEFAULT_RULES:
        # DEFAULT_RULES: {"category": ..., "unit": ..., "metrics": {"metric_name": { ... }}}
        cat = d.get("category", "")
        metrics = d.get("metrics", {}) or {}
        for m_name, cfg in metrics.items():
            rid = f"{cat}:{m_name}"
            if rid == rule_id:
                return {
                    "rule_id": rid,
                    "category": cat,
                    "metric": m_name,
                    "warn_lo": (cfg.get("warn") or {}).get("lo"),
                    "warn_hi": (cfg.get("warn") or {}).get("hi"),
                    "crit_lo": (cfg.get("crit") or {}).get("lo"),
                    "crit_hi": (cfg.get("crit") or {}).get("hi"),
                    "unit": cfg.get("unit") or d.get("unit", ""),
                    "enabled": rule_id not in _disabled_rules,
                    "silenced": False,
                }
    return None


def create_rule(category: str, metric: str, warn_lo: float | None, warn_hi: float | None,
                crit_lo: float | None, crit_hi: float | None, unit: str = "") -> dict | None:
    """创建新规则, 写入 DB + 刷新内存。"""
    # 同 cat+metric 去重
    existing = _lookup_rule(f"{category}:{metric}")
    if existing:
        logger.debug("[alarm_engine:create]: 规则已存在 %s:%s, 转为更新", category, metric)
        return update_rule(f"{category}:{metric}", category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit)

    rule_id = f"{category}:{metric}"
    alarm_store.insert_rule(rule_id, category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit)
    logger.info("[alarm_engine:create]: 新规则已创建: %s", rule_id)
    return _format_one_rule(rule_id, {"enabled": True, "silenced": False})


def update_rule(rule_id: str, category: str, metric: str, warn_lo: float | None, warn_hi: float | None,
                crit_lo: float | None, crit_hi: float | None, unit: str = "") -> dict | None:
    """更新规则, 写穿 DB。"""
    old = _lookup_rule(rule_id)
    if old is None:
        return None

    # 持久化写入 (best-effort)
    try:
        alarm_store.update_rule_db(rule_id, category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit)
    except Exception:  # best-effort: 保持引擎内存可用
        logger.debug("alarm_store.update_rule_db 异常 (已忽略)")

    # 立即更新内存索引，确保修改对实时评估生效
    # 构造新的规则配置
    new_cfg = {
        "warn": {"lo": warn_lo, "hi": warn_hi},
        "crit": {"lo": crit_lo, "hi": crit_hi},
        "unit": unit or old.get("unit", ""),
    }
    # 旧的 category/metric
    old_cat = old.get("category", "")
    old_met = old.get("metric", "")

    # 如果用户修改了 category/metric，则尝试执行重命名: 新 rule_id 不存在则创建并删除旧记录
    new_rule_id = f"{category}:{metric}"
    old_rule_id = rule_id
    if (category, metric) != (old_cat, old_met):
        # 检查目标是否已存在冲突
        if _lookup_rule(new_rule_id) and new_rule_id != old_rule_id:
            logger.debug("[alarm_engine:update]: 目标规则已存在，重命名失败: %s", new_rule_id)
            return None
        # 插入新记录并删除旧记录（best-effort）
        try:
            alarm_store.insert_rule(new_rule_id, category, metric, warn_lo, warn_hi, crit_lo, crit_hi, unit)
            alarm_store.delete_rule_db(old_rule_id)
        except Exception:
            logger.debug("alarm_store rename (insert/delete) 异常 (已忽略)")
        # 更新内存索引: 移动旧索引到新 key
        if (old_cat, old_met) in _MATCHED_RULES:
            _MATCHED_RULES.pop((old_cat, old_met), None)
        _MATCHED_RULES[(category, metric)] = new_cfg
        try:
            # 保持 RULE_ORDER 的顺序替换旧项为新项
            idx = RULE_ORDER.index((old_cat, old_met))
            RULE_ORDER[idx] = (category, metric)
        except ValueError:
            if (category, metric) not in RULE_ORDER:
                RULE_ORDER.append((category, metric))
        # 更新 numeric id 映射: 将旧 id 迁移到新 rule_id 保持前端 id 稳定
        if old_rule_id in _rule_id_index:
            nid = _rule_id_index.pop(old_rule_id)
            _rule_id_index[new_rule_id] = nid
    else:
        # 简单更新阈值
        _MATCHED_RULES[(category, metric)] = new_cfg
        if (category, metric) not in RULE_ORDER:
            RULE_ORDER.append((category, metric))

    logger.info("[alarm_engine:update]: 规则已更新: %s", rule_id)
    return _format_one_rule(rule_id, {})


def delete_rule(rule_id: str) -> bool:
    """删除规则, 写穿 DB。"""
    if _lookup_rule(rule_id) is None:
        return False
    alarm_store.delete_rule_db(rule_id)
    _disabled_rules.discard(rule_id)
    logger.info("[alarm_engine:delete]: 规则已删除: %s", rule_id)
    return True


# ============ 前端响应格式转换 ============

# rule_id → numeric id 的缓存映射
_rule_id_index: dict[str, int] = {}
_id_counter: int = 0


def _rule_numeric_id(rule_id: str) -> int:
    """为 rule_id 分配一个稳定的自增数字 ID, 供前端 AlarmRuleDef.id 使用。"""
    global _id_counter
    if rule_id not in _rule_id_index:
        _id_counter += 1
        _rule_id_index[rule_id] = _id_counter
    return _rule_id_index[rule_id]


def _rule_id_by_numeric(nid: int) -> str | None:
    """根据前端传来的数字 ID 反查 rule_id。"""
    for rid, n in _rule_id_index.items():
        if n == nid:
            return rid
    return None


def _format_one_rule(rule_id: str, overrides: dict) -> dict:
    """将单条规则格式化为前端 AlarmRuleDef 结构的 dict。"""
    r = _lookup_rule(rule_id)
    if r is None:
        return {}
    nid = _rule_numeric_id(r["rule_id"])
    enabled = overrides.get("enabled", r.get("enabled", True))
    silenced = overrides.get("silenced", r.get("silenced", False))
    status = "silenced" if silenced else ("enabled" if enabled else "disabled")
    return {
        "id": nid,
        "ruleCode": r["rule_id"],
        "category": r["category"],
        "metric": r["metric"],
        "warnLo": r.get("warn_lo"),
        "warnHi": r.get("warn_hi"),
        "critLo": r.get("crit_lo"),
        "critHi": r.get("crit_hi"),
        "unit": r.get("unit", ""),
        "enabled": enabled,
        "source": "default",
        "status": status,
    }


def format_rules_for_frontend(rules: list[dict]) -> list[dict]:
    """批量转换后端规则为前端 AlarmRuleDef 格式。"""
    out: list[dict] = []
    for r in rules:
        rid = r.get("rule_id", f"{r.get('category','?')}:{r.get('metric','?')}")
        nid = _rule_numeric_id(rid)
        enabled = r.get("enabled", True)
        # 后端原始数据无 silenced 字段
        status = "enabled" if enabled else "disabled"
        # 展平 warn/crit 避免嵌套
        warn = r.get("warn", {}) or {}
        crit = r.get("crit", {}) or {}
        out.append({
            "id": nid,
            "ruleCode": rid,
            "category": r.get("category", ""),
            "metric": r.get("metric", ""),
            "warnLo": warn.get("lo") if warn else r.get("warn_lo"),
            "warnHi": warn.get("hi") if warn else r.get("warn_hi"),
            "critLo": crit.get("lo") if crit else r.get("crit_lo"),
            "critHi": crit.get("hi") if crit else r.get("crit_hi"),
            "unit": r.get("unit", ""),
            "enabled": enabled,
            "source": "default",
            "status": status,
        })
    return out
