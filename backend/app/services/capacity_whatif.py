"""上架模拟器 (容量 What-if 推演)。

与 twin_simulation 的"故障注入 What-if"完全独立: 这里回答的是
"再上架 N 个机柜、单柜功率 P kW, 电力/制冷/空间/U 位还能撑多久"。

输入基线: capacity_energy.capacity(db) 的 dims 五维
    [{id, used, total, unit}, ...]  (id ∈ 机柜空间/电力容量/制冷容量/承重容量/网络端口)

推演模型 (纯函数, O(months×5)):
    1. 即时增量: 每新增一柜按 per-rack delta 叠加到对应维度 used;
    2. 增长外推: 复用 capacity_forecast._ANNUAL_GROWTH 的年度增长率,
       月因子 (1+g)^(1/12) 逐月复利, 找出 used_pct 首次 ≥85% / ≥100% 的月份。

U 位/端口/承重的 per-rack 增量按行业常用配比取常量 (42U/柜、2 上联口/柜),
电力按单柜功率 1:1, 制冷按 IT 功率 ×1.25 (显热+冗余系数)。
"""
import logging
from datetime import date

logger = logging.getLogger("capacity.whatif")

# 每新增一柜对各维度的增量 (与 capacity_energy.dims 的 unit 对齐)
_PER_RACK_DELTA = {
    "机柜空间": 42,          # U
    "电力容量": None,        # 动态: kw_per_cabinet / 1000 (MW)
    "制冷容量": None,        # 动态: kw_per_cabinet × 1.25 / 1000 (MW)
    "承重容量": round(100 / 3600, 4),  # % (3600 柱总量均摊)
    "网络端口": 2,           # 口 (每柜 2 上联)
}
_COOLING_PER_IT_KW = 1.25  # 制冷跟随 IT 负载系数 (显热 + 冗余)
_WARN_PCT = 85.0
_FULL_PCT = 100.0

# 与 capacity_forecast._ANNUAL_GROWTH 一致的年度用量增长率 (兜底 0.05)
_DEFAULT_GROWTH = {"机柜空间": 0.05, "电力容量": 0.07, "制冷容量": 0.06,
                   "承重容量": 0.03, "网络端口": 0.08}


def _growth_of(dim_id: str) -> float:
    try:
        from app.services.capacity_forecast import _ANNUAL_GROWTH

        return float(_ANNUAL_GROWTH.get(dim_id, 0.05))
    except Exception as e:  # noqa: BLE001  # 预测模块异常不阻断推演
        logger.debug("读取年度增长率失败, 用默认 0.05: %s", e)
        return _DEFAULT_GROWTH.get(dim_id, 0.05)


def _per_rack_delta(dim_id: str, kw_per_cabinet: float) -> float:
    if dim_id == "电力容量":
        return kw_per_cabinet / 1000.0
    if dim_id == "制冷容量":
        return kw_per_cabinet * _COOLING_PER_IT_KW / 1000.0
    return _PER_RACK_DELTA.get(dim_id, 0.0)


def _reach_month(used: float, total: float, growth: float, horizon: int, threshold: float):
    """从当前 used 起, 按 (1+g)^(1/12) 月复利, 找首次 used_pct ≥ threshold 的月份。

    返回 "YYYY-MM" 字符串; horizon 内到不了返回 None; 当前已超返回 "now"。
    """
    if total <= 0:
        return None
    pct = used / total * 100.0
    if pct >= threshold:
        return "now"
    monthly = (1.0 + growth) ** (1.0 / 12.0)
    base = date.today().replace(day=1)
    for m in range(1, horizon + 1):
        pct *= monthly
        if pct >= threshold:
            yy = base.year + (base.month - 1 + m) // 12
            mm = (base.month - 1 + m) % 12 + 1
            return f"{yy:04d}-{mm:02d}"
    return None


def simulate(base: dict, cabinets: int = 10, kw_per_cabinet: float = 8.0,
             months_horizon: int = 24) -> dict:
    """纯函数推演: 返回四/五维余量、到达阈值月份、瓶颈排序与建议。"""
    dims_out = []
    for d in base.get("dims", []):
        dim_id = d.get("id", "")
        used_now = float(d.get("used") or 0)
        total = float(d.get("total") or 0)
        unit = d.get("unit") or ""
        delta = _per_rack_delta(dim_id, kw_per_cabinet) * cabinets
        used_after = used_now + delta
        if total > 0:
            headroom = max(0.0, (total - used_after) / total * 100.0)
        else:
            headroom = 0.0
        growth = _growth_of(dim_id)
        dims_out.append({
            "id": dim_id,
            "unit": unit,
            "usedNow": round(used_now, 3),
            "usedAfter": round(used_after, 3),
            "capacity": total,
            "pctNow": round(used_now / total * 100.0, 1) if total > 0 else 0.0,
            "pctAfter": round(used_after / total * 100.0, 1) if total > 0 else 0.0,
            "headroomPercent": round(headroom, 1),
            "reach85Month": _reach_month(used_after, total, growth, months_horizon, _WARN_PCT),
            "reach100Month": _reach_month(used_after, total, growth, months_horizon, _FULL_PCT),
            "addedByRacks": round(delta, 3),
        })

    # 瓶颈排序: 余量最小者优先 (total<=0 的维度视为无穷小余量)
    ranked = sorted(dims_out, key=lambda d: d["headroomPercent"])
    bottleneck = ranked[0]["id"] if ranked else ""

    suggestions: list[str] = []
    for d in ranked:
        if d["reach100Month"]:
            when = "当前已超限" if d["reach100Month"] == "now" else f"约 {d['reach100Month']} 达 100%"
            suggestions.append(f"【{d['id']}】为首要瓶颈: 新增上架后占用 {d['pctAfter']}%, {when}, 建议优先扩容或控制上架节奏。")
        elif d["reach85Month"]:
            suggestions.append(f"【{d['id']}】新增上架后占用 {d['pctAfter']}%, 约 {d['reach85Month']} 触及 85% 预警线, 请纳入扩容规划。")
    if kw_per_cabinet > 20:
        suggestions.append(f"单柜功率 {kw_per_cabinet}kW 已属高密度上架, 请同步确认供电母线与制冷末端 (CDU/CRAC) 就位容量。")
    if not suggestions:
        suggestions.append("当前配置下各维度余量充足, 未触及预警阈值; 可在容量预测页跟踪长期趋势。")

    return {
        "cabinets": cabinets,
        "kwPerCabinet": kw_per_cabinet,
        "monthsHorizon": months_horizon,
        "source": base.get("_source", "generated"),
        "dims": dims_out,
        "bottleneck": bottleneck,
        "suggestions": suggestions,
    }
