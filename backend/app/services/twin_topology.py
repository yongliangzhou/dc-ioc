"""阶段四 build-graph-apis: 数字孪生 / 链路拓扑 数据底座 (图数据 + 推演接口 统一出口)。

本模块是 Twin/Topology 视图的"数据底座": 一次调用返回孪生层级图 + 链路拓扑图 +
汇总指标, 避免前端多次往返; 推演接口 (what-if 仿真 / 场景库 / 方舟闭环) 同样在此收敛,
统一走 twin_simulation 的仿真核心。

设备单一事实源遵循 B2: 统一走 dc_aggregator.list_equipment()。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.services import twin_graph as tg
from app.services import twin_simulation as ts

logger = logging.getLogger("twin_topology")

# 各类别 → 语义测点映射 (原始 metric_name → 归一化字段)。
# 仅挑选驱动"能流速度 / 温度"可视化所需的真实测点, 其余 (电流/电压/振动等) 不在此消费。
_METRIC_SEMANTICS: dict[str, dict[str, str]] = {
    # 供电域: loadPct 驱动能流速度, powerKw 用于功率标注
    "chiller": {"load_pct": "loadPct", "power_kw": "powerKw", "supply_temp": "supplyTemp", "return_temp": "returnTemp"},
    "crac": {"supply_temp": "supplyTemp", "return_temp": "returnTemp", "power_kw": "powerKw", "fan_speed": "loadPct"},
    "cooling_tower": {"water_temp_out": "supplyTemp", "water_temp_in": "returnTemp", "fan_hz": "loadPct", "power_kw": "powerKw"},
    "chw_pump": {"power_kw": "powerKw"},
    "cw_pump": {"power_kw": "powerKw"},
    "sec_pump": {"pump_kw": "powerKw"},
    "valve": {"position_pct": "loadPct"},
    "transformer": {"load_pct": "loadPct", "winding_temp": "temp", "temp": "temp"},
    "ups": {"load_pct": "loadPct", "output_power": "powerKw"},
    "hvdc": {"load_pct": "loadPct", "output_power": "powerKw"},
    "hv_incomer": {"active_power": "powerKw"},
    "hv_feeder": {"active_power": "powerKw"},
    "battery_group": {"soc": "loadPct", "max_temp": "temp"},
    "genset": {"output_power": "powerKw", "water_temp": "temp"},
    "ambient": {"outdoor_temp": "temp"},
    "fau": {"supply_temp": "supplyTemp", "return_temp": "returnTemp"},
    "storage_tank": {"top_temp": "supplyTemp", "bottom_temp": "returnTemp"},
    "liquid": {"s_t": "supplyTemp", "r_t": "returnTemp"},
}


def build_topology_data() -> dict:
    """数据底座: 合并孪生层级图 + 链路拓扑图 + 汇总指标, 供前端图视图一次取全。

    返回结构 (TwinTopology):
      generatedAt / source        数据生成时间与来源 (db | generated)
      twinGraph                   园区→包间→设备 层级图
      topology                    供电/制冷 节点 + 边 (故障传播/能流动画基础)
      summary                     合并后的关键汇总指标
    """
    twin = tg.build_twin_graph()
    topo = tg.build_topology_graph()
    tsrc = twin.get("source") or topo.get("source") or "generated"

    rooms = [r for idc in twin.get("idcs", []) for r in idc.get("rooms", [])]
    t_eq = twin.get("summary", {}).get("equipmentCount", 0)
    t_health = twin.get("summary", {}).get("avgHealth", 0.0)
    n_nodes = len(topo.get("nodes", []))
    n_edges = len(topo.get("edges", []))
    red = topo.get("redundancy", {})

    summary = {
        "source": tsrc,
        "idcCount": twin.get("summary", {}).get("idcCount", 0),
        "roomCount": twin.get("summary", {}).get("roomCount", len(rooms)),
        "equipmentCount": t_eq,
        "avgHealth": t_health,
        "mappedPct": twin.get("summary", {}).get("mappedPct", 0.0),
        "topoNodes": n_nodes,
        "topoEdges": n_edges,
        "topoRedundancy": red,
        "topoSource": topo.get("source", tsrc),
    }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": tsrc,
        "twinGraph": twin,
        "topology": topo,
        "summary": summary,
    }


# ---- 推演接口 (与 twin_simulation 仿真核心收敛, 供 /twin/topology 路由组复用) ----
def simulate(req: dict) -> dict:
    """推演仿真 (what-if 故障注入): 故障下游波及 + 容量/能耗/健康影响 + 冗余接管评估。"""
    return ts.simulate(req)


def scenario_library() -> dict:
    """数据驱动推演场景库 (含波及预览, 前端可点选运行)。"""
    return ts.scenario_library()


def ark_closed_loop() -> dict:
    """方舟闭环: 基于真实功率/PUE/末端负载测算的节能收益与挖潜空间。"""
    return ts.ark_closed_loop()


# ---- 阶段四 任务①: 链路节点实时测点映射 (真实测点驱动能流速度 / 温度) ----
def build_topology_metrics() -> dict:
    """将链路拓扑每个节点映射到其外部设备的真实实时测点, 归一化为可视化语义字段。

    数据路径: 拓扑节点 id == external_devices.id (整数主键) → 查 device_id (MOCK-xxx)
    → ext_crud.latest_metrics(device_id) 取采集器推送的实时缓存 (与 /api/external/.../metrics/realtime 同源)。

    返回 { source, updated_at, nodes: { [nodeId]: {loadPct?, powerKw?, supplyTemp?, returnTemp?, temp?, online?} } }
    节点无对应设备 / 无可用测点时, 不出该节点 (前端回退到模拟负载), 保证空数据下页面仍可用。
    """
    from app.crud import external as ext_crud
    from app.db.session import SessionLocal
    from app.models.external import ExternalDevice

    topo = tg.build_topology_graph()
    nodes = topo.get("nodes", [])

    # id(整数) → device_id(字符串) 映射: 拓扑节点 id 即 external_devices 主键
    id2dev: dict[int, str] = {}
    db = None
    try:
        db = SessionLocal()
        rows = db.query(ExternalDevice.id, ExternalDevice.device_id).all()
        id2dev = {int(r[0]): r[1] for r in rows}
    except Exception:  # noqa: BLE001
        logger.warning("build_topology_metrics: 设备映射查询失败 (DB 不可用时回退为空映射)", exc_info=False)
    finally:
        if db is not None:
            db.close()

    nodes_out: dict[int, dict] = {}
    for n in nodes:
        nid = n.get("id")
        cat = n.get("category") or ""
        sem = _METRIC_SEMANTICS.get(cat)
        if not sem:
            continue
        dev_id = id2dev.get(nid)
        if not dev_id:
            continue
        latest = ext_crud.latest_metrics(dev_id)  # {metric_name: {value, unit, quality, ts}}
        rec: dict = {}
        for raw, field in sem.items():
            mv = latest.get(raw)
            if isinstance(mv, dict) and mv.get("value") is not None:
                try:
                    rec[field] = float(mv["value"])
                except (TypeError, ValueError):
                    pass
        if rec:
            rec["online"] = ext_crud.is_online(dev_id)
            nodes_out[nid] = rec

    return {
        "source": topo.get("source", "generated"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": nodes_out,
    }
