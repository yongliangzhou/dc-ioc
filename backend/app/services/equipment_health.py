"""阶段三 D/E: 设备健康评分。

基于统一设备台账 (app.services.dc_aggregator.list_equipment) 的真实字段计算每台设备健康分,
并聚合到 系统域 维度。供 Twin.vue (健康评分面板) 与 Topology.vue (链路节点着色) 复用,
保证评分口径单一来源。

评分模型 (满分 100, 扣分制):
- 状态异常 (故障/检修/离线 ...) 重扣; 待机/备用轻微扣分。
- 负载率 >90% / >80% 扣分。
- 运行小时数偏高 (老化) 扣分。
- 类别特有指标:
    * 冷机 COP 偏低
    * 末端空调送/回风温度偏高
    * 蓄电池 SOC 偏低 / 单体温度偏高
    * 燃油箱液位偏低
    * 变压器绕组温度偏高
    * UPS 输出电压越限
    * HVDC 模块冗余不足
    * 冷却塔出水温度偏高
    * 中压进线功率因数偏低
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.services import dc_aggregator as agg


def _f(v) -> float:
    """安全浮点转换: 空值 / 非数字 (如 '-' 占位) 一律按 0 处理。"""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_BAD = {"故障", "检修", "维保", "离线", "故障停机", "异常", "故障 "}
_STANDBY = {"待机", "备用", "分闸", "浮充", "停机", "待机 "}

_DOMAIN_LABEL = {
    "hvac_source": "暖通冷源",
    "hvac_terminal": "暖通末端",
    "power_hv": "10kV 中压配电",
    "power_lv": "0.4kV 低压配电",
    "power_genset": "柴发并机",
    "power_fuel": "燃油系统",
    "power_batt": "蓄电池系统",
    "sec_cctv": "视频监控",
    "sec_acs": "门禁系统",
    "sec_ids": "防入侵系统",
    "sec_fire": "消防报警",
}


def _grade(h: float) -> str:
    if h >= 90:
        return "优"
    if h >= 75:
        return "良"
    if h >= 60:
        return "中"
    return "差"


def _score(eq: dict):
    """返回 (健康分, 问题列表)。"""
    score = 100.0
    issues: list[str] = []
    status = (eq.get("status") or "").strip()
    cat = eq.get("category") or ""
    load = _f(eq.get("load_pct"))
    hours = int(_f(eq.get("run_hours")))
    a = eq.get("attrs") or {}

    if status in _BAD:
        score -= 40
        issues.append(f"状态异常:{status}")
    elif status in _STANDBY:
        score -= 3

    if load > 90:
        score -= 15
        issues.append(f"负载率过高 {load:.0f}%")
    elif load > 80:
        score -= 8
        issues.append(f"负载率偏高 {load:.0f}%")

    if hours > 40000:
        score -= 6
        issues.append("运行小时数偏高")
    elif hours > 20000:
        score -= 3

    cop = _f(a.get("cop"))
    if cat == "chiller" and cop and cop < 5.0:
        score -= 10
        issues.append(f"COP 偏低 {cop:.1f}")
    if cat == "crac":
        supply_t = _f(a.get("supplyT"))
        if supply_t and supply_t > 26:
            score -= 8
            issues.append(f"送风温度偏高 {supply_t:.1f}℃")
        return_t = _f(a.get("returnT"))
        if return_t and return_t > 32:
            score -= 6
            issues.append(f"回风温度偏高 {return_t:.1f}℃")
    if cat == "battery_group":
        soc = _f(a.get("soc"))
        if soc and soc < 80:
            score -= 12
            issues.append(f"SOC 偏低 {soc:.0f}%")
        max_t = _f(a.get("maxT"))
        if max_t and max_t > 40:
            score -= 8
            issues.append(f"单体温度偏高 {max_t:.1f}℃")
    if cat == "fuel_tank":
        lv = _f(a.get("level"))
        if lv and lv < 20:
            score -= 10
            issues.append(f"液位偏低 {lv:.0f}%")
    if cat == "transformer":
        t = _f(a.get("t"))
        if t and t > 80:
            score -= 8
            issues.append(f"绕组温度偏高 {t:.1f}℃")
    if cat == "ups":
        u = _f(a.get("uOut"))
        if u and (u < 215 or u > 230):
            score -= 6
            issues.append(f"输出电压异常 {u:.0f}V")
    if cat == "hvdc":
        mod_run = _f(a.get("modRun"))
        mod_n = _f(a.get("modN"))
        if mod_n and mod_run and mod_run / mod_n < 0.6:
            score -= 5
            issues.append("模块冗余不足")
    if cat == "cooling_tower":
        out_t = _f(a.get("outT"))
        if out_t and out_t > 37:
            score -= 6
            issues.append(f"出水温度偏高 {out_t:.1f}℃")
    if cat == "hv_incomer":
        pf = _f(a.get("pf"))
        if pf and pf < 0.9:
            score -= 5
            issues.append(f"功率因数偏低 {pf:.2f}")

    score = max(0.0, min(100.0, round(score, 1)))
    return score, issues


def build_equipment_health():
    # B2: agg.list_equipment() 无 db 时回退生成器台账 (返回 EquipmentPage 兼容 dict);
    # 健康评分沿用生成器台账, 真实设备健康需 B5 引入 db 与真实负载数据后升级。
    data = agg.list_equipment()
    items = data["items"] if isinstance(data, dict) else data
    by_eq: list[dict] = []
    domain_acc: dict[str, list[float]] = defaultdict(list)

    for eq in items:
        h, issues = _score(eq)
        rec = {
            "id": eq.get("id"),
            "code": eq.get("code"),
            "name": eq.get("name"),
            "domain": eq.get("domain"),
            "category": eq.get("category"),
            "status": eq.get("status"),
            "loadPct": float(eq.get("load_pct") or 0),
            "health": h,
            "grade": _grade(h),
            "issues": issues,
        }
        by_eq.append(rec)
        domain_acc[eq.get("domain")].append(h)

    by_domain: list[dict] = []
    for d, hs in domain_acc.items():
        avg = round(sum(hs) / len(hs), 1)
        by_domain.append(
            {
                "domain": d,
                "label": _DOMAIN_LABEL.get(d, d),
                "avgHealth": avg,
                "count": len(hs),
                "grade": _grade(avg),
            }
        )
    by_domain.sort(key=lambda x: x["avgHealth"])

    buckets = {"优": 0, "良": 0, "中": 0, "差": 0}
    for rec in by_eq:
        buckets[rec["grade"]] += 1
    total = len(by_eq)
    avg_all = round(sum(r["health"] for r in by_eq) / total, 1) if total else 0.0
    worst = sorted(by_eq, key=lambda r: r["health"])[:8]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": total,
        "avgHealth": avg_all,
        "byDomain": by_domain,
        "byEquipment": by_eq,
        "worst": worst,
        "summary": {
            "优": buckets["优"],
            "良": buckets["良"],
            "中": buckets["中"],
            "差": buckets["差"],
        },
    }
