"""阶段四 任务1: 数字孪生 / 链路拓扑 数据底座。

build_twin_graph():  数据驱动 园区→包间→设备 层级图 (去除 Twin.vue 写死假数据的基础)。
build_topology_graph(): 供电/制冷链路 节点+边 (故障传播与影响分析、实时流动画的基础)。

设备单一事实源遵循 B2: 统一走 dc_aggregator.list_equipment() (external_devices 骨架)。
当 DB 无设备数据时回退 generated 台账, 保证接口始终有数据可渲染。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.services import dc_aggregator as agg
from app.services.equipment_health import _score


# domain -> (room kind, room code 前缀, room 名称)
_DOMAIN_ROOM: dict[str, tuple[str, str, str]] = {
    "hvac_source":   ("chiller_station", "CS", "冷冻站"),
    "hvac_terminal": ("it_room",         "IT", "IT包间"),
    "power_hv":      ("substation",      "SS", "变电站"),
    "power_lv":      ("ups_room",        "UR", "UPS室"),
    "power_genset":  ("substation",      "GS", "柴发机房"),
    "power_fuel":    ("substation",      "FS", "燃油间"),
    "power_batt":    ("battery_room",    "BR", "电池室"),
    "sec_cctv":      ("noc",             "NV", "监控中心"),
    "sec_acs":       ("noc",             "AC", "门禁中心"),
    "sec_ids":       ("noc",             "ID", "安防中心"),
    "sec_fire":      ("noc",             "FR", "消防中心"),
}

_ROOM_KIND_LABEL: dict[str, str] = {
    "it_room": "IT包间", "substation": "变电站", "ups_room": "UPS室",
    "chiller_station": "冷冻站", "battery_room": "电池室", "carrier_room": "运营商机房",
    "noc": "监控中心",
}

# 供电链路阶段顺序 (category)
_POWER_STAGES: list[str] = [
    "hv_incomer", "hv_isolator", "hv_breaker", "transformer",
    "ups", "hvdc", "lv_feeder", "ats",
]
# 制冷链路阶段顺序 (category)
_COOL_STAGES: list[str] = [
    "chiller", "chw_pump", "cooling_tower", "hex", "sec_pump", "valve", "crac",
]

_CAT_LABEL: dict[str, str] = {
    "hv_incomer": "10kV进线", "hv_isolator": "隔离柜", "hv_breaker": "断路器柜",
    "transformer": "变压器", "ups": "UPS", "hvdc": "HVDC", "lv_feeder": "低压馈线",
    "ats": "ATS", "bus_tie": "母联柜", "chiller": "冷水机组", "chw_pump": "冷冻泵",
    "cooling_tower": "冷却塔", "hex": "板式换热", "sec_pump": "二次泵",
    "valve": "电动阀门", "crac": "精密空调", "battery_group": "电池组",
    "genset": "柴油发电机",
}


def _room_kind_of(eq: dict) -> tuple[str, str, str]:
    d = eq.get("domain") or ""
    return _DOMAIN_ROOM.get(d, ("it_room", "OT", "其他机房"))


def _label_of(eq: dict) -> str:
    return eq.get("name") or eq.get("code") or str(eq.get("id"))


def _source_of(items: list[dict]) -> str:
    """external_devices 台账带 attrs.online; generated 台账不带 -> 据此判定数据来源。"""
    for it in items:
        attrs = it.get("attrs")
        if isinstance(attrs, dict) and "online" in attrs:
            return "db"
    return "generated"


def _load_room_meta() -> dict[str, dict]:
    """可选: 用真实 Room 表补充包间元数据 (机架数/温湿度等); 缺表/空表则回退默认。"""
    out: dict[str, dict] = {}
    try:
        from app.db.session import SessionLocal
        from app.models.room import Room

        db = SessionLocal()
        try:
            for r in db.query(Room).all():
                out.setdefault(
                    r.kind,
                    {
                        "floor": r.floor,
                        "rack_capacity": r.rack_capacity,
                        "cold_aisle_t": r.cold_aisle_t,
                        "hot_aisle_t": r.hot_aisle_t,
                        "rh": r.rh,
                        "pressure_pa": r.pressure_pa,
                    },
                )
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        pass
    return out


def build_twin_graph() -> dict:
    """数据驱动 园区→包间→设备 层级图。

    设备按 domain 映射为包间类型 (如 冷机→冷冻站, 变压器/UPS→UPS室, CRAC→IT包间),
    每台设备复用 equipment_health._score 计算健康分, 包间聚合负载率/健康分/状态。
    """
    data = agg.list_equipment(page_size=10000)
    items = data.get("items") or []
    source = _source_of(items)
    room_meta = _load_room_meta()

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for it in items:
        kind, prefix, _ = _room_kind_of(it)
        groups[(kind, prefix)].append(it)

    rooms_out: list[dict] = []
    all_health: list[float] = []
    eq_total = 0
    online_eq = 0
    rid = 0
    for (kind, prefix), eqs in sorted(groups.items(), key=lambda kv: kv[0]):
        rid += 1
        eq_recs: list[dict] = []
        loads: list[float] = []
        hs: list[float] = []
        for e in eqs:
            h, _ = _score(e)
            hs.append(h)
            all_health.append(h)
            loads.append(float(e.get("load_pct") or 0))
            attrs = e.get("attrs")
            if isinstance(attrs, dict) and attrs.get("online"):
                online_eq += 1
            eq_total += 1
            eq_recs.append({
                "id": e.get("id"),
                "code": e.get("code"),
                "name": _label_of(e),
                "domain": e.get("domain"),
                "category": e.get("category"),
                "status": e.get("status"),
                "loadPct": float(e.get("load_pct") or 0),
                "health": h,
                "redundancy": e.get("redundancy") or "",
            })
        avg_h = round(sum(hs) / len(hs), 1) if hs else 0.0
        avg_load = round(sum(loads) / len(loads), 1) if loads else 0.0
        worst = min(hs) if hs else 100
        status = "normal"
        if worst < 60:
            status = "critical"
        elif worst < 75:
            status = "warning"
        meta = room_meta.get(kind, {})
        rooms_out.append({
            "id": rid,
            "code": f"{prefix}-01",
            "name": _ROOM_KIND_LABEL.get(kind, prefix),
            "kind": kind,
            "floor": meta.get("floor", ""),
            "rackCapacity": meta.get("rack_capacity", len(eqs) * 12),
            "coldAisleT": meta.get("cold_aisle_t", 0),
            "hotAisleT": meta.get("hot_aisle_t", 0),
            "rh": meta.get("rh", 0),
            "pressurePa": meta.get("pressure_pa", 0),
            "equipmentCount": len(eqs),
            "avgLoadPct": avg_load,
            "avgHealth": avg_h,
            "status": status,
            "equipments": eq_recs,
        })

    avg_all = round(sum(all_health) / len(all_health), 1) if all_health else 0.0
    if source == "db" and eq_total:
        mapped = round(online_eq / eq_total * 100, 1)
    else:
        mapped = 99.6  # generated 台账无 online 字段, 用既定映射率

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "idcs": [{
            "id": 1,
            "code": "EC1-HZ",
            "name": "杭州数据中心 (示例)",
            "region": "华东",
            "powerCapacityMw": 36.0,
            "coolingCapacityMw": 40.0,
            "rackCapacity": sum(r["rackCapacity"] for r in rooms_out),
            "rooms": rooms_out,
        }],
        "summary": {
            "idcCount": 1,
            "roomCount": len(rooms_out),
            "equipmentCount": eq_total,
            "mappedPct": mapped,
            "avgHealth": avg_all,
        },
    }


def build_topology_graph() -> dict:
    """供电/制冷链路 节点 + 边。

    节点 = 设备台账 (带 domain/category/负载/健康/冗余); 边 = 按 stage 顺序在同类设备间链式推导
    (10kV进线→变压器→UPS/HVDC→馈线 ...; 冷机→冷冻泵→冷却塔→板换→末端 ...)。
    该派生拓扑足以支撑故障传播 BFS 与冗余评估。
    """
    data = agg.list_equipment(page_size=10000)
    items = data.get("items") or []
    source = _source_of(items)

    nodes: list[dict] = []
    by_cat: dict[str, list[int]] = defaultdict(list)
    for it in items:
        cat = it.get("category") or ""
        h, _ = _score(it)
        nodes.append({
            "id": it.get("id"),
            "label": _label_of(it),
            "kind": _CAT_LABEL.get(cat, cat),
            "domain": it.get("domain"),
            "category": cat,
            "roomId": it.get("room_id"),
            "roomCode": "",
            "status": it.get("status"),
            "loadPct": float(it.get("load_pct") or 0),
            "health": h,
            "redundancy": it.get("redundancy") or "",
        })
        by_cat[cat].append(it.get("id"))

    edges: list[dict] = []
    edges += _chain_edges(by_cat, _POWER_STAGES, "power", "供电")
    edges += _chain_edges(by_cat, _COOL_STAGES, "cool", "制冷")

    red = defaultdict(int)
    for it in items:
        r = (it.get("redundancy") or "").strip()
        red[r if r in ("N+1", "2N", "主备") else "single"] += 1
    redundancy = {
        "N+1": red.get("N+1", 0),
        "2N": red.get("2N", 0),
        "single": red.get("single", 0),
    }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "nodes": nodes,
        "edges": edges,
        "redundancy": redundancy,
    }


def _chain_edges(by_cat: dict[str, list[int]], stages: list[str], etype: str, label: str) -> list[dict]:
    """在相邻 stage 的设备间按索引连边 (数量不等时以末节点兜底广播)。"""
    edges: list[dict] = []
    for i in range(len(stages) - 1):
        a, b = stages[i], stages[i + 1]
        src_ids = by_cat.get(a, [])
        dst_ids = by_cat.get(b, [])
        if not src_ids or not dst_ids:
            continue
        n = max(len(src_ids), len(dst_ids))
        for k in range(n):
            s = src_ids[k % len(src_ids)]
            d = dst_ids[k % len(dst_ids)]
            if s == d:
                continue
            edges.append({"source": s, "target": d, "type": etype, "label": f"{label}链路"})
    return edges
