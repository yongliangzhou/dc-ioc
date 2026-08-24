"""B7: 告警规则配置化 + 物模型驱动默认阈值带。

设计:
- DEFAULT_RULES 仅作"手调基线"(少量关键规则, 阈值经人工校验), 不再是运行时唯一来源。
- 其余设备类别的默认规则由"物模型"推导:
  物理量程来自 mock_collector._CATEGORY_METRICS 的 (metric, unit, min, max),
  阈值带按"量程边缘 ±10% 触发 warn, 量程外触发 crit"自动生成。新增设备类别即可自动获得合理默认规则。
- 推导结果用于在 alarm_rule 表播种 (seed_alarm_rules), 用户后续可在 DB 上调整;
  引擎运行时从 DB hydrate 阈值 (hydrate_rules), DB 为单一事实源。

注意: 规则键名(category)与 DEFAULT_RULES 一致使用"采集器类别"(chiller/ups/...),
引擎匹配走 metric 名回退, 与既有语义兼容。
"""
from app.collectors.mock_collector import _CATEGORY_METRICS

# DEFAULT_RULES 已手调的关键类别, 不重复推导 (保留人工基线)
_TUNED_CATEGORIES = {"chiller", "ups", "pdudevice", "acunit", "WaterSystem"}

# 不适合作数值阈值告警的测点 (状态/枚举/模式/阀位类)
_SKIP_SUBSTR = (
    "status", "state", "_mode", "switch", "run_", "pos", "online",
    "valve_state", "fan", "module", "level_state",
)


def _is_skip(metric: str) -> bool:
    m = metric.lower()
    return any(s in m for s in _SKIP_SUBSTR)


def _derive_band(min_v: float, max_v: float) -> dict | None:
    """由量程推导 warn/crit 阈值带。

    - 量程外 => crit (物理不可行 / 越限)
    - 量程内靠近上下各 10% => warn (逼近临界)
    """
    if min_v is None or max_v is None or max_v <= min_v:
        return None
    span = max_v - min_v
    return {
        "warn": {
            "lo": round(min_v + 0.10 * span, 3),
            "hi": round(max_v - 0.10 * span, 3),
        },
        "crit": {"lo": min_v, "hi": max_v},
    }


def derive_default_rules() -> list[dict]:
    """返回 DEFAULT_RULES 形状的派生默认规则列表 (仅含未被手调的类别)。"""
    rules: list[dict] = []
    for cat, metric_list in _CATEGORY_METRICS.items():
        if cat in _TUNED_CATEGORIES:
            continue  # 手调基线优先
        mdict: dict[str, dict] = {}
        for entry in metric_list:
            if not entry or len(entry) < 4:
                continue
            name = entry[0]
            unit = entry[1] if len(entry) > 1 else ""
            min_v = entry[2]
            max_v = entry[3]
            if _is_skip(name):
                continue
            band = _derive_band(min_v, max_v)
            if not band:
                continue
            mdict[name] = {**band, "unit": unit}
        if mdict:
            # 类别级 unit 取首个有单位测点的单位 (仅用于展示)
            unit_hint = next((v["unit"] for v in mdict.values() if v.get("unit")), "")
            rules.append({"category": cat, "unit": unit_hint, "metrics": mdict})
    return rules
