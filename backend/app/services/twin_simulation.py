"""阶段四 任务1: 推演仿真引擎 (what-if 故障注入)。

simulate(): 基于拓扑图与孪生图, 对指定场景做故障注入, 沿供电/制冷边 BFS 计算下游波及,
输出 baseline vs after 的容量/能耗/健康影响, 以及冗余接管评估。供前端"推演场景库/方舟闭环"调用。
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.services import twin_graph as tg

logger = logging.getLogger(__name__)


# 场景 -> 注入故障的设备 domain (None 表示全部)
_SCENARIO_FAIL_DOMAINS: dict[str, tuple[str, ...] | None] = {
    "市电失电": ("power_hv", "power_lv", "power_genset", "power_batt"),
    "冷源故障": ("hvac_source",),
    "全停演练": None,
}


def simulate(req: dict) -> dict:
    """对外入口: 构建拓扑/孪生图后执行一次故障注入推演。"""
    topo = tg.build_topology_graph()
    twin = tg.build_twin_graph()
    return _simulate(topo, twin, req)


def _simulate(topo: dict, twin: dict, req: dict) -> dict:
    """仿真核心: 复用已构建的拓扑/孪生图, 供场景库批量推演避免重复建图。"""
    nodes_by_id = {n["id"]: n for n in topo["nodes"]}
    edges = topo["edges"]
    scenario = req.get("scenario", "全停演练")

    # ---- 1. 初始故障集 ----
    if req.get("affectedIds"):
        failed = set(int(x) for x in req["affectedIds"])
    else:
        doms = _SCENARIO_FAIL_DOMAINS.get(scenario)
        failed = {n["id"] for n in topo["nodes"] if doms is None or n["domain"] in doms}

    # ---- 2. 沿边 BFS 计算下游波及 ----
    adj: dict[int, list[tuple[int, str]]] = defaultdict(list)
    if scenario == "全停演练":
        for e in edges:
            adj[e["source"]].append((e["target"], e["type"]))
    elif scenario == "冷源故障":
        for e in edges:
            if e["type"] == "cool":
                adj[e["source"]].append((e["target"], e["type"]))
    else:  # 市电失电 -> 供电边
        for e in edges:
            if e["type"] == "power":
                adj[e["source"]].append((e["target"], e["type"]))

    affected = set(failed)
    stack = list(failed)
    while stack:
        cur = stack.pop()
        for tgt, _ in adj.get(cur, []):
            if tgt not in affected:
                affected.add(tgt)
                stack.append(tgt)

    # ---- 3. 包间映射 (来自孪生图) ----
    room_of_eq: dict[int, dict] = {}
    for idc in twin["idcs"]:
        for room in idc["rooms"]:
            for eq in room["equipments"]:
                room_of_eq[eq["id"]] = room

    affected_room_ids: set[int] = set()
    it_lost_power = 0
    it_lost_cool = 0
    for eid in affected:
        room = room_of_eq.get(eid)
        if room is None:
            continue
        affected_room_ids.add(room["id"])
        if room["kind"] == "it_room":
            node = nodes_by_id.get(eid, {})
            if (node.get("domain") or "").startswith("power"):
                it_lost_power += 1
            if node.get("category") == "crac":
                it_lost_cool += 1

    # ---- 4. baseline vs after ----
    total = twin["summary"]["equipmentCount"]
    online = total - len(affected)
    healths_after = [n["health"] for n in topo["nodes"] if n["id"] not in affected]
    avg_health_after = round(sum(healths_after) / len(healths_after), 1) if healths_after else 0.0

    def _sum_load(domain_prefix: str, only_online: bool) -> float:
        s = 0.0
        for n in topo["nodes"]:
            if not (n["domain"] or "").startswith(domain_prefix):
                continue
            if only_online and n["id"] in affected:
                continue
            s += n["loadPct"]
        return round(s, 1)

    power_load = _sum_load("power", False)
    cool_load = _sum_load("hvac", False)
    power_load_after = _sum_load("power", True)
    cool_load_after = _sum_load("hvac", True)

    redundancy_cover = _redundancy_cover(topo, failed)

    return {
        "scenario": scenario,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "equipmentTotal": total,
            "avgHealth": twin["summary"]["avgHealth"],
            "powerLoad": power_load,
            "coolLoad": cool_load,
        },
        "after": {
            "equipmentOnline": online,
            "avgHealth": avg_health_after,
            "powerLoad": power_load_after,
            "coolLoad": cool_load_after,
        },
        "impact": {
            "equipmentLost": len(affected),
            "roomsAffected": len(affected_room_ids),
            "itRoomsLostPower": it_lost_power,
            "itRoomsLostCool": it_lost_cool,
            "redundancyCover": redundancy_cover,
        },
        "affectedEquipmentIds": sorted(affected),
        "affectedRoomIds": sorted(affected_room_ids),
    }


# ---------------------------------------------------------------------------
# 阶段四 任务3: 数据驱动推演场景库 (前端可点选运行, 对比前后)
# ---------------------------------------------------------------------------

_SCENARIO_DEFS: list[dict] = [
    {
        "id": "utility_loss",
        "scenario": "市电失电",
        "name": "市电失电 · 柴发接管推演",
        "desc": "10kV 双路市电同时失电, 沿供电链路推演下游波及, 校验柴发启动与 ATS 切换能否在 UPS 后备时间内接管关键负载。",
        "tags": ["供电", "柴发接管", "ATS 切换"],
    },
    {
        "id": "cooling_loss",
        "scenario": "冷源故障",
        "name": "冷源故障 · 备冷切换推演",
        "desc": "冷水机组群故障, 沿制冷链路推演末端断冷范围, 校验备用冷机/蓄冷罐接管与 IT 包间温升窗口。",
        "tags": ["制冷", "冷源切换", "蓄冷接管"],
    },
    {
        "id": "full_shutdown",
        "scenario": "全停演练",
        "name": "全停演练 · 全链路推演",
        "desc": "园区级年度全停演练, 供电与制冷链路同时注入故障, 评估全链路波及范围与恢复上电顺序。",
        "tags": ["全链路", "年度演练", "恢复顺序"],
    },
]


def _risk_level(result: dict, total: int) -> str:
    """按波及占比 + 冗余接管结论定风险等级。"""
    lost = result["impact"]["equipmentLost"]
    ratio = (lost / total) if total else 0.0
    if not result["impact"]["redundancyCover"] or ratio >= 0.6:
        return "high"
    if ratio >= 0.25 or result["impact"]["itRoomsLostCool"] > 0:
        return "medium"
    return "low"


def scenario_library() -> dict:
    """推演场景库: 每个场景预跑一次仿真, 给出可点选前的波及预览 (建图仅一次)。"""
    topo = tg.build_topology_graph()
    twin = tg.build_twin_graph()
    total = twin["summary"]["equipmentCount"]

    scenarios = []
    for d in _SCENARIO_DEFS:
        doms = _SCENARIO_FAIL_DOMAINS.get(d["scenario"])
        target = len([n for n in topo["nodes"] if doms is None or n["domain"] in doms])
        res = _simulate(topo, twin, {"scenario": d["scenario"]})
        scenarios.append({
            **d,
            "targetCount": target,
            "impactCount": res["impact"]["equipmentLost"],
            "roomsAffected": res["impact"]["roomsAffected"],
            "redundancyCover": res["impact"]["redundancyCover"],
            "riskLevel": _risk_level(res, total),
            "runnable": target > 0,
        })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": topo.get("source", "generated"),
        "equipmentTotal": total,
        "scenarios": scenarios,
    }


# ---------------------------------------------------------------------------
# 阶段四 任务3: 方舟闭环 (真实节能测算)
# ---------------------------------------------------------------------------

_GRID_CO2_KG_PER_KWH = 0.581   # 全国电网平均排放因子 kgCO2/kWh
_COOL_RATIO_BENCHMARK = 0.32   # 制冷功率占设施功率的行业基准比
_PUE_DESIGN = 1.35             # 设计 PUE (无历史基线时兜底)
_HOURS_PER_YEAR = 8760


def _power_snapshot() -> tuple[dict, str, list[float]]:
    """取真实功率快照 (facility/cooling/it/loss) 与 PUE 历史; 无真实数据时回退生成器。"""
    try:
        from app.db.session import SessionLocal
        from app.services import capacity_energy as ce

        db = SessionLocal()
        try:
            snap = ce.snapshot_power(db)
            # 有设备但功率测点全 0 时同样视为无有效数据, 回退生成器避免全 0 展示
            if snap.get("has_data") and float(snap.get("facility") or 0) > 0:
                trend = [float(v) for v in (ce.get_history_series(db, ce.KEY_PUE, 30) or [])]
                return snap, "real", trend
        finally:
            db.close()
    except Exception as e:
        logger.warning("真实功率快照获取失败, 回退生成数据: %s", e)

    from app.services import dc_ioc_data as generated

    e = generated.energy()
    bd = {str(b["id"]).replace(" ", ""): float(b["kw"]) for b in e.get("breakdown", [])}
    it = bd.get("IT负载", 0.0)
    cooling = bd.get("制冷系统", 0.0)
    loss = bd.get("供配电损耗", 0.0)
    other = bd.get("照明及其他", 0.0)
    snap = {"facility": it + cooling + loss + other, "cooling": cooling, "it": it, "loss": loss}
    return snap, "generated", [float(v) for v in (e.get("pueTrend") or [])]


def _crac_balance() -> tuple[float, float, int]:
    """末端 CRAC 负载均衡度: 返回 (平均负载率, 极差, 数量)。"""
    topo = tg.build_topology_graph()
    loads = [n["loadPct"] for n in topo["nodes"] if n.get("category") == "crac"]
    if not loads:
        return 0.0, 0.0, 0
    return round(sum(loads) / len(loads), 1), round(max(loads) - min(loads), 1), len(loads)


def ark_closed_loop() -> dict:
    """方舟闭环: 基于真实功率/PUE/末端负载, 测算各闭环策略的已实现节能与可挖潜力。"""
    snap, source, pue_hist = _power_snapshot()
    facility = float(snap.get("facility") or 0.0)
    cooling = float(snap.get("cooling") or 0.0)
    it = float(snap.get("it") or 0.0)

    pue = round(facility / it, 3) if it > 0 else None
    baseline_pue = round(sum(pue_hist) / len(pue_hist), 3) if pue_hist else _PUE_DESIGN

    def _kwh_year(kw: float) -> int:
        return int(round(kw * _HOURS_PER_YEAR))

    loops: list[dict] = []

    # 1) 冷机群控寻优: 实测制冷占比 vs 行业基准
    cool_ratio = (cooling / facility) if facility > 0 else 0.0
    gap_kw = (_COOL_RATIO_BENCHMARK - cool_ratio) * facility
    achieved = max(gap_kw, 0.0)
    potential = max(-gap_kw, 0.0)
    loops.append({
        "id": "chiller_group_control",
        "name": "冷机群控寻优",
        "desc": "冷冻水供回水温差与冷机加载率联合寻优, 按实测制冷占比对标行业基准核算收益。",
        "state": "闭环运行" if achieved > 0 else "待优化",
        "kind": "achieved" if achieved > 0 else "potential",
        "savedKw": round(achieved or potential, 1),
        "savingPct": round((achieved or potential) / facility * 100, 2) if facility > 0 else 0.0,
        "savedKwhYear": _kwh_year(achieved or potential),
        "basis": f"实测制冷占比 {cool_ratio * 100:.1f}% vs 行业基准 {_COOL_RATIO_BENCHMARK * 100:.0f}%",
        "metrics": [
            {"k": "制冷功率", "v": f"{cooling:.0f} kW"},
            {"k": "设施功率", "v": f"{facility:.0f} kW"},
            {"k": "制冷占比", "v": f"{cool_ratio * 100:.1f}%"},
        ],
    })

    # 2) 末端空调联动调优: 依据 CRAC 负载均衡度
    crac_avg, crac_spread, crac_n = _crac_balance()
    balance_saving = round(cooling * min(crac_spread, 40.0) / 100 * 0.3, 1)
    balanced = crac_spread <= 15
    loops.append({
        "id": "terminal_linkage",
        "name": "末端空调联动调优",
        "desc": "按包间冷热通道压差与末端负载均衡度联动调速, 消除末端抢风与过供。",
        "state": "闭环运行" if balanced else "待优化",
        "kind": "achieved" if balanced else "potential",
        "savedKw": balance_saving,
        "savingPct": round(balance_saving / facility * 100, 2) if facility > 0 else 0.0,
        "savedKwhYear": _kwh_year(balance_saving),
        "basis": f"{crac_n} 台末端平均负载 {crac_avg:.0f}%, 负载极差 {crac_spread:.0f}%",
        "metrics": [
            {"k": "末端数量", "v": f"{crac_n} 台"},
            {"k": "平均负载", "v": f"{crac_avg:.0f}%"},
            {"k": "负载极差", "v": f"{crac_spread:.0f}%"},
        ],
    })

    # 3) PUE 闭环寻优: 当前 PUE vs 30 天基线
    if pue is not None and baseline_pue > 0:
        delta = baseline_pue - pue
        pue_kw = abs(delta) / baseline_pue * facility
        loops.append({
            "id": "pue_closed_loop",
            "name": "PUE 闭环寻优",
            "desc": "以 30 天 PUE 均值为基线做闭环反馈, 偏离即回调冷源与气流策略。",
            "state": "闭环运行" if delta > 0 else "待优化",
            "kind": "achieved" if delta > 0 else "potential",
            "savedKw": round(pue_kw, 1),
            "savingPct": round(pue_kw / facility * 100, 2) if facility > 0 else 0.0,
            "savedKwhYear": _kwh_year(pue_kw),
            "basis": f"当前 PUE {pue:.3f} vs 30 天基线 {baseline_pue:.3f}",
            "metrics": [
                {"k": "当前 PUE", "v": f"{pue:.3f}"},
                {"k": "基线 PUE", "v": f"{baseline_pue:.3f}"},
                {"k": "IT 功率", "v": f"{it:.0f} kW"},
            ],
        })

    achieved_kw = round(sum(loop["savedKw"] for loop in loops if loop["kind"] == "achieved"), 1)
    potential_kw = round(sum(loop["savedKw"] for loop in loops if loop["kind"] == "potential"), 1)
    achieved_kwh = _kwh_year(achieved_kw)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "source": source,
            "pue": pue,
            "baselinePue": baseline_pue,
            "facilityKw": round(facility, 1),
            "itKw": round(it, 1),
            "coolingKw": round(cooling, 1),
            "achievedKw": achieved_kw,
            "achievedKwhYear": achieved_kwh,
            "potentialKw": potential_kw,
            "carbonTonYear": round(achieved_kwh * _GRID_CO2_KG_PER_KWH / 1000, 1),
            "loopCount": len(loops),
            "runningCount": len([loop for loop in loops if loop["state"] == "闭环运行"]),
        },
        "loops": loops,
    }


def _redundancy_cover(topo: dict, failed: set[int]) -> bool:
    """故障设备若带冗余 (N+1/2N/主备), 需存在同类在线设备可接管; 任一不可接管即判 False。"""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for n in topo["nodes"]:
        by_cat[n["category"]].append(n)
    for fid in failed:
        node = next((n for n in topo["nodes"] if n["id"] == fid), None)
        if node is None:
            continue
        r = (node.get("redundancy") or "").strip()
        if r in ("N+1", "2N", "主备"):
            siblings = [
                n for n in by_cat.get(node["category"], [])
                if n["id"] != fid and n["id"] not in failed
            ]
            if not siblings:
                return False
    return True
