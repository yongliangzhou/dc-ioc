"""故障影响分析 crud: 基于真实拓扑的链路影响传播与严重度评估。

复用 twin_graph.build_topology_graph() (供电/制冷链路节点+边) 与 build_twin_graph()
(IT 包间内设备), 沿边做 BFS 故障传播; 结合 equipment_health 健康分初始化易故障节点;
内建业务域映射识别受影响业务域 / SLA 风险。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.services import twin_graph as tg
from app.services.equipment_health import _score


# 关键设备 category (断电/断冷直接致命, 视为关键链路节点)
_CRITICAL_CATS = {
    "hv_incomer", "hv_isolator", "hv_breaker", "transformer",
    "ups", "hvdc", "lv_feeder", "ats", "bus_tie",
    "chiller", "chw_pump", "cooling_tower", "hex", "sec_pump", "crac",
}

# 业务域 -> (SLA 目标, 承载的 IT 设备 category 集合, 说明)
_BIZ_DOMAINS: list[dict] = [
    {"business": "核心交易系统", "sla": "99.999%", "cats": {"server", "switch", "router"},
     "note": "金融核心交易, 双路供电+2N制冷, 中断即资损"},
    {"business": "客户门户/网银", "sla": "99.95%", "cats": {"server", "switch"},
     "note": "对外服务, 可用性敏感"},
    {"business": "大数据/AI 平台", "sla": "99.9%", "cats": {"server", "gpu"},
     "note": "离线/近线计算, 短时中断可容忍"},
    {"business": "办公协同/邮箱", "sla": "99.5%", "cats": {"server"},
     "note": "内部办公, 低优先级"},
    {"business": "视频监控平台", "sla": "99.9%", "cats": {"nvr", "switch"},
     "note": "安防录像, 断链影响合规留存"},
]


def _biz_of(category: str) -> str | None:
    for b in _BIZ_DOMAINS:
        if category in b["cats"]:
            return b["business"]
    return None


def _sev_of(health: float) -> str:
    if health < 50:
        return "critical"
    if health < 70:
        return "high"
    if health < 85:
        return "medium"
    return "low"


def list_sources() -> dict:
    """候选故障源: 真实拓扑节点 + 易故障提示。"""
    topo = tg.build_topology_graph()
    nodes = topo.get("nodes") or []
    edges = topo.get("edges") or []

    # roomCode 由孪生图补全
    twin = tg.build_twin_graph()
    room_code_of: dict[int, str] = {}
    for idc in twin.get("idcs", []):
        for room in idc.get("rooms", []):
            for eq in room.get("equipments", []):
                room_code_of[eq["id"]] = room.get("code")

    out = []
    for n in nodes:
        h = float(n.get("health", 100))
        status = (n.get("status") or "").strip()
        load = float(n.get("loadPct") or 0)
        hints = []
        if h < 70:
            hints.append(f"健康分偏低 {h:.0f}")
        if status in ("离线", "故障", "告警"):
            hints.append(f"状态异常:{status}")
        if load > 85:
            hints.append(f"负载率 {load:.0f}%")
        out.append({
            "id": n["id"],
            "label": n.get("label") or str(n["id"]),
            "kind": n.get("kind") or n.get("category") or "",
            "domain": n.get("domain") or "",
            "category": n.get("category") or "",
            "status": status or None,
            "health": round(h, 1),
            "loadPct": round(load, 1),
            "redundancy": n.get("redundancy") or None,
            "roomCode": room_code_of.get(n["id"]),
            "riskHint": "；".join(hints) if hints else None,
        })
    out.sort(key=lambda x: (0 if x["riskHint"] else 1, x["health"]))
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": topo.get("source", "generated"),
        "nodes": out,
        "edges": edges,
    }


def analyze(fault_ids: list[int], scope: dict | None = None) -> dict:
    """沿真实拓扑 BFS 计算故障传播, 输出影响链路/评估/业务域风险。"""
    scope = scope or {"power": True, "cool": True, "network": True, "business": True}
    topo = tg.build_topology_graph()
    twin = tg.build_twin_graph()
    topo_nodes = topo.get("nodes") or []
    edges = topo.get("edges") or []
    nodes_by_id = {n["id"]: n for n in topo_nodes}

    # IT 包间内设备 (含 server/switch 等) 作为网络/业务域级联节点
    it_nodes: list[dict] = []
    room_of: dict[int, dict] = {}
    for idc in twin.get("idcs", []):
        for room in idc.get("rooms", []):
            for eq in room.get("equipments", []):
                it_nodes.append(eq)
                room_of[eq["id"]] = room

    # 生成 IT 业务承载设备 (twin 图仅含供电/制冷/安防, 这里按包间派生 server/switch/gpu,
    # 作为网络/业务域级联目标; id 用 100000+ 偏移避免与 twin 节点冲突)。
    it_biz_nodes: list[dict] = []
    it_feed_edges: list[dict] = []  # 包间 CRAC/配电 -> IT 设备
    _base = 100000
    _idx = 0
    _SERVERS_PER_ROOM = 6
    for idc in twin.get("idcs", []):
        for room in idc.get("rooms", []):
            code = room.get("code") or str(room.get("id"))
            crac_ids = [eq["id"] for eq in room.get("equipments", []) if eq.get("category") == "crac"]
            feeder_ids = [eq["id"] for eq in room.get("equipments", [])
                          if (eq.get("category") or "") in ("branch", "busbar", "ups", "ats")]
            anchors = crac_ids + feeder_ids
            for i in range(_SERVERS_PER_ROOM):
                _idx += 1
                nid = _base + _idx
                cat = "gpu" if i == 0 else ("switch" if i == _SERVERS_PER_ROOM - 1 else "server")
                label = f"{code}-{cat}-{i+1}"
                h, _ = _score({"category": cat, "attrs": {}})
                node = {
                    "id": nid, "label": label, "kind": cat, "domain": "it",
                    "category": cat, "status": "在线", "health": h, "roomCode": code,
                    "name": label,
                }
                it_biz_nodes.append(node)
                room_of[nid] = room
                # 连接到该包间 CRAC (制冷) 与配电 (供电) 节点
                for a in anchors:
                    it_feed_edges.append({"source": a, "target": nid, "type": "it_feed",
                                          "label": "包间供电/制冷"})

    # 合并全部节点
    all_nodes = dict(nodes_by_id)
    for e in it_nodes + it_biz_nodes:
        if e["id"] not in all_nodes:
            h, _ = _score(e)
            all_nodes[e["id"]] = {
                "id": e["id"], "label": e.get("label") or e.get("name") or str(e["id"]),
                "kind": e.get("kind") or e.get("category") or "", "domain": e.get("domain") or "",
                "category": e.get("category") or "", "status": e.get("status"),
                "health": h, "roomCode": room_of.get(e["id"], {}).get("code"),
            }

    # 构建邻接 (按 scope 过滤边类型)
    adj: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for e in edges:
        et = e.get("type")
        if et == "power" and not scope.get("power", True):
            continue
        if et == "cool" and not scope.get("cool", True):
            continue
        adj[e["source"]].append((e["target"], et))

    failed = set(int(x) for x in fault_ids if x is not None)
    affected = set(failed)
    hop_of: dict[int, int] = {f: 0 for f in failed}
    stack = list(failed)
    while stack:
        cur = stack.pop()
        for tgt, _ in adj.get(cur, []):
            if tgt not in affected:
                affected.add(tgt)
                hop_of[tgt] = hop_of[cur] + 1
                stack.append(tgt)

    # 机房级业务级联: 供电/制冷链路任意节点故障 = 机房级冷量/电力丧失,
    # 将全部 IT 承载设备 (server/switch/gpu) 标记为受影响, 并从受影响链路节点挂展示边。
    if scope.get("network", True) or scope.get("business", True):
        link_affected = [nid for nid in affected
                         if (all_nodes.get(nid, {}).get("category") or "") in _CRITICAL_CATS]
        if link_affected:
            base_hop = min(hop_of.get(n, 0) for n in link_affected) + 1
            for it in it_biz_nodes:
                iid = it["id"]
                if iid not in affected:
                    affected.add(iid)
                    hop_of[iid] = base_hop
                # 展示边: 从首个受影响链路节点连到该 IT 设备
                src = link_affected[0]
                it_feed_edges.append({"source": src, "target": iid,
                                      "type": "it_feed", "label": "机房级冷量/电力丧失"})

    # 输出节点
    out_nodes = []
    biz_counter: dict[str, dict] = defaultdict(lambda: {"crit": 0, "affected": 0})
    critical_count = 0
    for nid, n in all_nodes.items():
        state = "fault" if nid in failed else ("affected" if nid in affected else "normal")
        cat = n.get("category") or ""
        is_crit = cat in _CRITICAL_CATS
        if state != "normal" and is_crit:
            critical_count += 1
        biz = _biz_of(cat) if scope.get("business", True) else None
        sla_risk = None
        if state != "normal" and biz:
            sev = _sev_of(float(n.get("health", 100)))
            sla_risk = "critical" if sev == "critical" else sev
            entry = biz_counter[biz]
            entry["affected"] += 1
            if is_crit:
                entry["crit"] += 1
        out_nodes.append({
            "id": nid,
            "label": n.get("label") or str(nid),
            "kind": n.get("kind") or cat,
            "domain": n.get("domain") or "",
            "category": cat,
            "status": (n.get("status") or None),
            "health": round(float(n.get("health", 100)), 1),
            "roomCode": n.get("roomCode"),
            "state": state,
            "hop": hop_of.get(nid, 0),
            "critical": is_crit,
            "business": biz,
            "slaRisk": sla_risk,
        })
    out_nodes.sort(key=lambda x: (x["state"] != "fault", x["state"] != "affected", x["hop"], -x["health"]))

    # 输出边 (仅含在 affected 集合内的传播边)
    out_edges = []
    for e in edges:
        if e["source"] in affected and e["target"] in affected:
            out_edges.append({
                "source": e["source"], "target": e["target"],
                "type": e.get("type"), "label": e.get("label"),
            })
    if scope.get("network", True) or scope.get("business", True):
        for s, lst in adj.items():
            if s not in affected:
                continue
            for tgt, et in lst:
                if et == "it_feed" and tgt in affected:
                    out_edges.append({"source": s, "target": tgt, "type": et, "label": "包间供电/制冷"})
        # 机房级业务级联展示边
        for e in it_feed_edges:
            if e["source"] in affected and e["target"] in affected:
                out_edges.append(e)

    # 受影响业务域
    businesses = []
    for b in _BIZ_DOMAINS:
        c = biz_counter.get(b["business"])
        if not c or c["affected"] == 0:
            continue
        sev = "critical" if c["crit"] > 0 else ("high" if c["affected"] > 3 else "medium")
        businesses.append({
            "business": b["business"],
            "criticalDevices": c["crit"],
            "affectedDevices": c["affected"],
            "severity": sev,
            "sla": b["sla"],
            "note": b["note"],
        })
    businesses.sort(key=lambda x: (x["severity"] != "critical", -x["affectedDevices"]))

    affected_count = len(affected) - len(failed)
    # 严重度
    if not failed:
        severity = "low"
    elif critical_count > 0 or businesses:
        severity = "critical" if (critical_count >= 2 or any(b["severity"] == "critical" for b in businesses)) else "high"
    elif affected_count > 0:
        severity = "medium"
    else:
        severity = "low"

    sla_risk_level = "high" if businesses else ("medium" if critical_count > 0 else "low")
    summary = {
        "severity": severity,
        "faultCount": len(failed),
        "affectedCount": affected_count,
        "criticalPaths": critical_count,
        "slaRisk": sla_risk_level,
        "bizCount": len(businesses),
    }

    suggestion = _build_suggestion(failed, affected, all_nodes, businesses, critical_count)
    mitigations = _build_mitigations(failed, affected, all_nodes, businesses, critical_count, edges)

    return {
        "faultIds": list(failed),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "nodes": out_nodes,
        "edges": out_edges,
        "affectedIds": sorted(affected - failed),
        "summary": summary,
        "businesses": businesses,
        "suggestion": suggestion,
        "mitigations": mitigations,
    }


def _build_mitigations(failed, affected, all_nodes, businesses, critical_count, edges) -> list[dict]:
    """处置缓解建议引擎: 按关键链路 + 受影响业务域生成结构化动作清单。"""
    mitig: list[dict] = []
    seq = 0

    def add(action, target, priority, detail):
        nonlocal seq
        seq += 1
        mitig.append({"seq": seq, "action": action, "target": target,
                      "priority": priority, "detail": detail})

    if not failed:
        return mitig

    # P0: 关键供电/制冷节点冲击 -> 冗余切换
    if critical_count:
        crit_faults = [f for f in failed if all_nodes.get(f, {}).get("category") in _CRITICAL_CATS]
        labels = "、".join(all_nodes[f].get("label", str(f)) for f in crit_faults[:4]) or "关键节点"
        add("冗余切换", labels, "P0",
            f"关键供电/制冷节点 {labels} 故障, 立即切换至 N+1/2N 冗余链路, 5 分钟内确认备用回路带载, 防止下游机房级冷量/电力丧失。")
        add("隔离定位", labels, "P0",
            "对故障节点执行电气隔离并派单巡检, 核对其上级进线/母联状态, 排除越级跳闸风险。")

    # P0/P1: 受影响业务域 -> 容灾切换 + 通知
    for b in businesses:
        if b["severity"] == "critical":
            add("容灾切换", b["business"], "P0",
                f"业务域「{b['business']}」(SLA {b['sla']}) 关键设备受影响 {b['criticalDevices']} 台, 立即启动双活/容灾切换, 通知业务方与值班经理。")
        else:
            add("业务降级", b["business"], "P1",
                f"业务域「{b['business']}」受影响设备 {b['affectedDevices']} 台, 启用限流/降级预案, 持续观测 SLA 指标。")

    # P1: 机房级级联 -> 环境兜底
    link_affected = [nid for nid in affected
                     if (all_nodes.get(nid, {}).get("category") or "") in _CRITICAL_CATS]
    if link_affected and businesses:
        add("环境兜底", "受影响机房", "P1",
            "机房级冷量/电力丧失风险, 启动蓄冷罐/柴油发电兜底, 优先保障核心包间温湿度, 必要时请求外部制冷支援。")

    # P2: 常规观测
    if not critical_count and not businesses:
        add("常规观测", "下游链路", "P2",
            "未波及核心业务域, 按常规工单处置, 持续观测下游温度/负载 30 分钟。")
    else:
        add("复盘归档", "本次事件", "P2",
            "事件收敛后归档影响分析报告, 更新应急预案与冗余容量基线。")
    return mitig


def _build_suggestion(failed, affected, all_nodes, businesses, critical_count) -> str:
    if not failed:
        return "未选择故障源, 请指定一个或多个候选故障节点后分析。"
    fault_labels = [all_nodes[f].get("label", str(f)) for f in failed if f in all_nodes]
    parts = [f"故障源 {len(fault_labels)} 个: " + "、".join(fault_labels[:5])]
    if critical_count:
        parts.append(f"已冲击 {critical_count} 个关键供电/制冷节点, 优先切换冗余链路 (N+1/2N) 保供电。")
    if businesses:
        top = businesses[0]
        parts.append(f"业务域「{top['business']}」(SLA {top['sla']}) 受影响最重, 建议立即启动容灾切换并通知业务方。")
    else:
        parts.append("未直接波及核心业务域, 按常规工单处置并持续观测下游温度/负载。")
    return " ".join(parts)


# 演练类型 -> 故障源 category 关键字 (用于演练预演联动映射)
_DRILL_TYPE_CATS: dict[str, list[str]] = {
    "电力": ["hv_incomer", "transformer", "ups", "lv_feeder", "bus_tie", "ats"],
    "制冷": ["chiller", "crac", "cooling_tower", "chw_pump", "hex", "sec_pump"],
    "网络": ["switch", "router", "core_switch"],
    "消防": ["fcu", "sec_pump"],
}


def map_drill_to_faults(drill: dict, sources: list[dict] | None = None) -> list[int]:
    """演练预演联动: 将演练计划 (type/scope/steps) 映射到候选故障源节点 id。

    通过演练类型圈定设备 category, 再按 scope 关键字 (如机房号/包间) 进一步收窄,
    返回最适合作为演练预演故障源的拓扑节点 id 列表 (最多 3 个, 优先易故障)。
    """
    sources = sources if sources is not None else list_sources().get("nodes", [])
    cats = _DRILL_TYPE_CATS.get((drill.get("type") or "").strip(), [])
    scope = (drill.get("scope") or "").strip()
    picked: list[dict] = []
    for n in sources:
        cat = n.get("category") or ""
        if cats and cat not in cats:
            continue
        # scope 命中 (机房号/包间号/关键字)
        if scope and scope not in (n.get("label") or "") and scope not in (n.get("roomCode") or "") \
                and scope.lower() not in (n.get("domain") or "").lower():
            continue
        picked.append(n)
    # 优先易故障 (有 riskHint) + 健康分低; 演练预演取前 3 个避免爆炸半径过大
    picked.sort(key=lambda x: (0 if x.get("riskHint") else 1, x.get("health", 100)))
    return [n["id"] for n in picked[:3]]


def save_history(db, data: dict) -> dict:
    """保存影响分析报告到历史表 (含会签人与严重级别)。"""
    from app.models.analysis_history import AnalysisHistory

    obj = AnalysisHistory(
        title=data.get("title") or "",
        fault_ids=data.get("faultIds") or [],
        severity=data.get("severity") or "low",
        summary=data.get("summary") or {},
        businesses=data.get("businesses") or [],
        mitigations=data.get("mitigations") or [],
        signers=data.get("signers") or [],
        pushed=data.get("pushed") or False,
        created_by=data.get("createdBy") or "",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


def list_history(db, limit: int = 50) -> list[dict]:
    from app.models.analysis_history import AnalysisHistory
    from sqlalchemy import desc

    rows = db.query(AnalysisHistory).order_by(desc(AnalysisHistory.id)).limit(limit).all()
    return [r.to_dict() for r in rows]


def get_history(db, hid: int):
    from app.models.analysis_history import AnalysisHistory
    obj = db.query(AnalysisHistory).filter(AnalysisHistory.id == hid).first()
    return obj.to_dict() if obj else None


def sign_history(db, hid: int, signer: str) -> dict | None:
    """追加会签人 (模拟; 真实环境应校验登录用户与角色)。"""
    from app.models.analysis_history import AnalysisHistory

    obj = db.query(AnalysisHistory).filter(AnalysisHistory.id == hid).first()
    if not obj:
        return None
    signers = list(obj.signers or [])
    if signer and signer not in signers:
        signers.append(signer)
    obj.signers = signers
    db.commit()
    db.refresh(obj)
    return obj.to_dict()
