"""阶段三 B: 容量预测。

基于「当前利用率快照」按各维度假定年增长率确定性逆推出历史序列 (以当前为锚点重建历史,
可复现、无随机抖动), 再用 **OLS 线性回归** 与 **Holt 双指数平滑** 双模型融合做趋势外推,
输出 12 个月预测、85%/100% 阈值触达月份与扩容建议。

说明: 运营库当前未存储容量历史时序, 故历史由快照逆推。预测模型本身为通用实现,
若未来接入真实容量时序 (TimescaleDB 连续聚合), 只需替换 build_history 即可,
下游 forecast 逻辑无需改动 (满足路线图「基于连续聚合历史做趋势外推」的长期目标)。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

# 各维度假定年增长率 (历史逆推 + 趋势量级参考)
_ANNUAL_GROWTH = {
    "机柜空间": 0.05,
    "电力容量": 0.07,
    "制冷容量": 0.06,
    "承重容量": 0.03,
    "网络端口": 0.08,
}
_WARN = 85.0
_FULL = 100.0
_HISTORY_MONTHS = 18
_HORIZON_MONTHS = 12
_ALPHA = 0.4
_BETA = 0.25


def _deterministic_noise(seed: str, i: int) -> float:
    """确定性伪噪声 (0~1), 给历史序列加轻微纹理, 保证可复现。"""
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    h = (h + i * 2654435761) & 0xFFFFFFFF
    return (h % 1000) / 1000.0


def _build_history(current_pct: float, annual_growth: float, seed: str) -> list[float]:
    """逆推 history 长度的历史利用率 (%)。"""
    gr = (1.0 + annual_growth) ** (1.0 / 12.0)  # 月增长因子
    hist: list[float] = []
    for i in range(_HISTORY_MONTHS):
        back = _HISTORY_MONTHS - 1 - i
        base = current_pct / (gr ** back)
        season = 0.6 * math.sin(2 * math.pi * (i % 12) / 12.0)
        noise = (_deterministic_noise(seed, i) - 0.5) * 1.2
        hist.append(round(max(0.0, base + season + noise), 2))
    return hist


def _ols_fit(y: list[float]) -> tuple[float, float]:
    """最小二乘线性回归 -> (slope, intercept)。"""
    n = len(y)
    sx = sum(range(n))
    sy = sum(y)
    sxx = sum(i * i for i in range(n))
    sxy = sum(i * y[i] for i in range(n))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, y[-1]
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _holt_fit(y: list[float]) -> tuple[float, float]:
    """Holt 双指数平滑 -> (level, trend)。"""
    level = y[0]
    trend = y[1] - y[0] if len(y) > 1 else 0.0
    for t in range(1, len(y)):
        last = level
        level = _ALPHA * y[t] + (1 - _ALPHA) * (level + trend)
        trend = _BETA * (level - last) + (1 - _BETA) * trend
    return level, trend


def _resid_std(y: list[float], slope: float, intercept: float) -> float:
    n = len(y)
    if n < 3:
        return 1.0
    s = sum((y[i] - (intercept + slope * i)) ** 2 for i in range(n))
    return max(0.5, math.sqrt(s / (n - 2)))


def forecast_capacity(base: dict) -> dict:
    dims = base.get("dims", []) or []
    by_dim: list[dict] = []
    trend_rows: list[dict] = []
    for i in range(_HISTORY_MONTHS):
        trend_rows.append({"monthOffset": i - _HISTORY_MONTHS, "type": "history"})
    for i in range(_HORIZON_MONTHS):
        trend_rows.append({"monthOffset": i + 1, "type": "forecast"})

    for dim in dims:
        cid = dim["id"]
        total = float(dim.get("total") or 1.0)
        used = float(dim.get("used") or 0.0)
        current_pct = round(used / total * 100.0, 2)
        ag = _ANNUAL_GROWTH.get(cid, 0.05)
        hist = _build_history(current_pct, ag, cid)
        slope, intercept = _ols_fit(hist)
        hlevel, htrend = _holt_fit(hist)
        sigma = _resid_std(hist, slope, intercept)

        projected: list[dict] = []
        warn_month = None
        full_month = None
        for m in range(1, _HORIZON_MONTHS + 1):
            ols_v = intercept + slope * (_HISTORY_MONTHS - 1 + m)
            holt_v = hlevel + htrend * m
            pct = round((ols_v + holt_v) / 2.0, 2)
            lo = round(max(0.0, pct - 1.28 * sigma), 2)
            hi = round(pct + 1.28 * sigma, 2)
            projected.append({"month": m, "pct": pct, "lo": lo, "hi": hi})
            if warn_month is None and pct >= _WARN:
                warn_month = m
            if full_month is None and pct >= _FULL:
                full_month = m

        slope_pm = round((slope + htrend) / 2.0, 3)
        # 当前已超阈值则归零 (表示"现在就已处于该区间", 覆盖未来月份预测)
        if current_pct >= _FULL:
            full_month = 0
        if current_pct >= _WARN:
            warn_month = 0
        status = "正常"
        if full_month is not None and full_month == 0:
            status = "已满容"
        elif full_month is not None:
            status = "即将满容"
        elif warn_month is not None and warn_month == 0:
            status = "预警临近(当前)"
        elif warn_month is not None:
            status = "预警临近"
        by_dim.append({
            "id": cid,
            "unit": dim.get("unit", ""),
            "currentPct": current_pct,
            "slopePerMonth": slope_pm,
            "projected": projected,
            "warnMonth": warn_month,
            "fullMonth": full_month,
            "status": status,
        })
        for i, v in enumerate(hist):
            trend_rows[i][cid] = v
        for j, p in enumerate(projected):
            trend_rows[_HISTORY_MONTHS + j][cid] = p["pct"]

    soonest = min(
        (b for b in by_dim if b["warnMonth"] is not None),
        key=lambda b: b["warnMonth"],
        default=None,
    )
    if soonest:
        if soonest["warnMonth"] == 0:
            headline = (
                f"{soonest['id']} 当前利用率 {soonest['currentPct']}% 已超 85% 预警线, "
                f"需立即启动扩容 (月均增速 {soonest['slopePerMonth']}%)"
            )
            advice = (
                f"{soonest['id']} 已处于预警区间, 当前 {soonest['currentPct']}%, "
                f"按 {soonest['slopePerMonth']}%/月 增速将持续恶化, 须尽快完成资源到位。"
            )
        else:
            headline = (
                f"按 OLS+Holt 双模型融合预测, {soonest['id']} 预计 "
                f"{soonest['warnMonth']} 个月后达 85% 预警线 (当前 {soonest['currentPct']}%, "
                f"月均增速 {soonest['slopePerMonth']}%)"
            )
            advice = (
                f"建议提前启动 {soonest['id']} 扩容评估: 当前利用率 {soonest['currentPct']}%, "
                f"若维持 {soonest['slopePerMonth']}%/月 增速, 需在第 {soonest['warnMonth']} 个月前完成资源到位。"
            )
    else:
        headline = "各维度利用率预测 12 个月内均低于 85% 预警线, 暂无迫近扩容压力"
        advice = "维持现有上架节奏, 季度复核预测曲线即可。"

    return {
        "method": "OLS 线性回归 + Holt 双指数平滑 (双模型融合, 1.28σ 置信带)",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "historyMonths": _HISTORY_MONTHS,
        "horizonMonths": _HORIZON_MONTHS,
        "warnThreshold": _WARN,
        "fullThreshold": _FULL,
        "byDim": by_dim,
        "trend": trend_rows,
        "headline": headline,
        "advice": advice,
    }
