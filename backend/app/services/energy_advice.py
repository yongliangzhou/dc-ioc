"""阶段三 C: 能效优化建议。

基于真实外部设备测点 (冷机/冷冻水泵/冷却水泵/末端空调/UPS/HVDC) 计算:
- PUE (总设施能耗 / IT 负载)
- 冷机 COP、UPS 效率与平均负载率
并给出规则化节能建议 (含估算节能量、优先级与依据测点)。

若未取到真实测点, 回退到与生成器量级一致的兜底值, 保证端点契约不变、前端始终有数据。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.crud import external as ext_crud

# 缺失真实数据时的兜底 (与生成器量级一致)
_FB = {
    "it_load_kw": 24600.0,
    "chiller_power_kw": 3600.0,
    "chiller_cop": 6.0,
    "chiller_supply_temp": 7.5,
    "crac_power_kw": 1200.0,
    "pump_power_kw": 1000.0,
    "ups_avg_load": 48.0,
}


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _gather(db) -> dict:
    """聚合各设备类别最新测点 -> {category: {metric_name: [values]}}。"""
    cat_vals: dict[str, dict[str, list[float]]] = {}
    if db is None:
        return cat_vals
    items, _t, _o, _f = ext_crud.list_devices(db)
    if not items:
        return cat_vals
    for dev in items:
        cat = getattr(dev, "category", None)
        if not cat:
            continue
        lm = ext_crud.latest_metrics(dev.device_id)
        if not lm:
            continue
        bucket = cat_vals.setdefault(cat, {})
        for mk, mv in lm.items():
            val = _num(mv.get("value") if isinstance(mv, dict) else None)
            if val is None:
                continue
            bucket.setdefault(mk, []).append(val)
    return cat_vals


def _sum(vals: dict, mk: str) -> float | None:
    arr = vals.get(mk)
    return sum(arr) if arr else None


def _mean(vals: dict, mk: str) -> float | None:
    arr = vals.get(mk)
    return sum(arr) / len(arr) if arr else None


def build_energy_advice(db) -> dict:
    cv = _gather(db)
    fb = _FB

    chiller_power = _sum(cv.get("chiller", {}), "power_kw") or fb["chiller_power_kw"]
    chiller_cop = _mean(cv.get("chiller", {}), "cop") or fb["chiller_cop"]
    chiller_supply = _mean(cv.get("chiller", {}), "supply_temp") or fb["chiller_supply_temp"]
    crac_power = _sum(cv.get("crac", {}), "power_kw") or fb["crac_power_kw"]
    pump_power = (_sum(cv.get("chw_pump", {}), "power_kw") or 0) + (
        _sum(cv.get("cw_pump", {}), "power_kw") or 0
    ) or fb["pump_power_kw"]

    # IT 负载由其热负荷决定: 稳态下显热冷却量 ≈ IT 热负荷, 而
    # 冷机供冷量 = 冷机电功率 × 冷机 COP (均为真实测点)。以此锚定 IT 负载,
    # 避免对合成机群逐台求和导致的绝对量不一致。
    it_load = chiller_power * chiller_cop
    if it_load <= 0:
        it_load = fb["it_load_kw"]

    cooling_kw = chiller_power + crac_power + pump_power

    ups_loads = cv.get("ups", {}).get("load_pct")
    ups_avg_load = (sum(ups_loads) / len(ups_loads)) if ups_loads else fb["ups_avg_load"]
    # UPS 效率经验曲线: 40%~60% 负载率效率最优 ~0.96, 偏离下降
    ups_eff = round(0.96 - 0.0015 * abs(ups_avg_load - 50), 4)
    ups_eff = max(0.85, min(0.97, ups_eff))

    # 供配电损耗 (UPS/PDU) + 照明及其他
    distribution = it_load * (1.0 / ups_eff - 1.0)
    other = max(420.0, it_load * 0.02)
    facility_kw = it_load + cooling_kw + distribution + other
    pue = round(facility_kw / it_load, 3) if it_load > 0 else None

    breakdown = [
        {"id": "IT 负载", "kw": round(it_load), "pct": round(it_load / facility_kw * 100, 1)},
        {"id": "制冷系统", "kw": round(cooling_kw), "pct": round(cooling_kw / facility_kw * 100, 1)},
        {"id": "供配电损耗", "kw": round(distribution), "pct": round(distribution / facility_kw * 100, 1)},
        {"id": "照明及其他", "kw": round(other), "pct": round(other / facility_kw * 100, 1)},
    ]

    # ---- 节能建议 (规则引擎) ----
    suggestions: list[dict] = []

    # 1) 冷冻水供水温度提升
    if chiller_supply < 8.0:
        up = round(8.5 - chiller_supply, 1)
        save = int(round(chiller_power * 0.025 * up))
        suggestions.append({
            "id": "chws-setpoint",
            "title": "提高冷冻水供水温度设定",
            "priority": "高",
            "savingKw": save,
            "savingPct": round(save / chiller_power * 100, 1),
            "detail": (
                f"当前冷机冷冻水供水均温 {chiller_supply}℃, 低于推荐 8.5℃。每提升 1℃ 冷机 COP 约升 "
                f"2~3%, 提升 {up}℃ 预计降低冷机电耗约 {save}kW。"
            ),
            "basis": f"chiller.supply_temp≈{chiller_supply}℃, chiller.power_kw≈{round(chiller_power)}kW",
        })

    # 2) UPS 负载率优化
    if ups_avg_load < 40.0:
        save = int(round(fb["it_load_kw"] * (0.97 - ups_eff)))
        suggestions.append({
            "id": "ups-load",
            "title": "优化 UPS 负载率至高效区",
            "priority": "中",
            "savingKw": save,
            "savingPct": round(save / facility_kw * 100, 2),
            "detail": (
                f"UPS 平均负载率 {ups_avg_load:.0f}% 处于低效区 (<40%), 提升负载率可改善效率至 ~0.96。"
                f"建议整合负载或退出部分冗余模块。"
            ),
            "basis": f"ups.load_pct≈{ups_avg_load:.0f}%, 估算效率≈{ups_eff}",
        })

    # 3) 末端空调送风温度优化
    crac_supply = _mean(cv.get("crac", {}), "supply_temp")
    if crac_supply and crac_supply < 20.0:
        save = int(round(crac_power * 0.02))
        suggestions.append({
            "id": "crac-supply",
            "title": "提高末端空调送风温度设定",
            "priority": "中",
            "savingKw": save,
            "savingPct": round(save / crac_power * 100, 1),
            "detail": (
                f"末端空调送风均温 {crac_supply:.1f}℃ 偏低, 存在过冷。提高回风/送风设定 1~2℃ "
                f"可降风机与再热能耗约 {save}kW。"
            ),
            "basis": f"crac.supply_temp≈{crac_supply:.1f}℃",
        })

    # 4) 自然冷却 (板换) 机会 — 条件性
    fc_save = int(round(chiller_power * 0.15))
    suggestions.append({
        "id": "free-cooling",
        "title": "过渡季/冬季启用自然冷却(板换)",
        "priority": "中",
        "savingKw": fc_save,
        "savingPct": 15.0,
        "detail": (
            "当室外湿球温度低于冷冻水回水温度时, 优先投入板式换热器免费制冷, 可替代部分冷机运行, "
            "预计降低冷源电耗约 15%。需结合 BA 系统室外湿球测点联动。"
        ),
        "basis": "依据手册冷源系统运行策略 (过渡季板换优先)",
    })

    # 5) 冷源 AI 寻优
    ai_save = int(round(cooling_kw * 0.03))
    suggestions.append({
        "id": "ai-opt",
        "title": "冷源系统 AI 寻优 + 负荷预测联动",
        "priority": "低",
        "savingKw": ai_save,
        "savingPct": 3.0,
        "detail": (
            "基于实时 IT 负荷与室外气象预测, 动态寻优冷冻水温度/流量/冷机运行台数, "
            "行业实测可降冷源电耗 3% 左右。"
        ),
        "basis": f"cooling_kw≈{round(cooling_kw)}kW",
    })

    total_save = sum(s["savingKw"] for s in suggestions)

    return {
        "pue": {"current": pue, "target": 1.30},
        "efficiency": {
            "chillerCop": round(chiller_cop, 2),
            "upsEff": ups_eff,
            "upsAvgLoad": round(ups_avg_load, 1),
            "cracSupplyTemp": round(crac_supply, 1) if crac_supply else None,
            "chillerSupplyTemp": round(chiller_supply, 2),
        },
        "breakdown": breakdown,
        "suggestions": suggestions,
        "totalSavingKw": total_save,
        "totalSavingPct": round(total_save / facility_kw * 100, 2) if facility_kw else 0.0,
        "realData": {
            "itLoadKw": round(it_load),
            "coolingKw": round(cooling_kw),
            "chillerPowerKw": round(chiller_power),
            "cracPowerKw": round(crac_power),
            "pumpPowerKw": round(pump_power),
            "facilityKw": round(facility_kw),
            "distributionKw": round(distribution),
            "dataSource": "external_metrics" if cv else "fallback",
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
