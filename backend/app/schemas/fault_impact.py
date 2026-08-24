"""故障影响分析 schema: 候选故障源 / 链路影响传播 / 严重度评估。

数据底座: 复用 twin_graph.build_topology_graph() 真实设备拓扑 (供电/制冷链路节点+边),
叠加 twin_graph.build_twin_graph() 的 IT 包间内设备, 做故障传播 BFS; 结合 equipment_health
健康分与告警状态初始化易故障节点; 并内建业务域映射以识别受影响业务/SLA 风险。
"""
from __future__ import annotations

from pydantic import BaseModel


class FaultSourceNode(BaseModel):
    """候选故障源 (来自真实设备台账的拓扑节点)。"""

    id: int
    label: str
    kind: str
    domain: str
    category: str
    status: str | None = None
    health: float = 100.0
    loadPct: float = 0.0
    redundancy: str | None = None
    roomCode: str | None = None
    riskHint: str | None = None  # 易故障提示 (低健康/已告警/高负载)


class FaultSourceList(BaseModel):
    """候选故障源列表 + 拓扑边 (前端离线构图用)。"""

    generatedAt: str
    source: str
    nodes: list[FaultSourceNode]
    edges: list[dict]


class FaultImpactReq(BaseModel):
    """影响分析请求: 指定故障源 + 传播范围开关。"""

    faultIds: list[int]
    scope: dict | None = None  # {power:true, cool:true, network:true, business:true}


class FaultImpactNode(BaseModel):
    """影响链路中的节点 (含传播元信息)。"""

    id: int
    label: str
    kind: str
    domain: str
    category: str
    status: str | None = None
    health: float = 100.0
    roomCode: str | None = None
    state: str  # fault | affected | normal
    hop: int = 0  # 距故障源的跳数
    critical: bool = False  # 是否关键设备 (冗余/供电/制冷前端)
    business: str | None = None  # 承载业务域 (IT 设备)
    slaRisk: str | None = None  # low | medium | high | critical


class FaultImpactEdge(BaseModel):
    source: int
    target: int
    type: str
    label: str | None = None


class AffectedBusiness(BaseModel):
    """受影响的业务域 / SLA 风险项。"""

    business: str
    criticalDevices: int
    affectedDevices: int
    severity: str  # low | medium | high | critical
    sla: str | None = None  # SLA 目标描述
    note: str | None = None


class Mitigation(BaseModel):
    """处置缓解措施 (按关键链路/受影响业务域生成的动作清单)。"""

    seq: int
    action: str  # 动作类型: 冗余切换/容灾/限流/隔离/巡检...
    target: str  # 作用对象 (关键设备/业务域)
    priority: str  # P0/P1/P2
    detail: str  # 具体操作描述


class FaultImpactResp(BaseModel):
    """影响分析结果。"""

    faultIds: list[int]
    generatedAt: str
    nodes: list[FaultImpactNode]
    edges: list[FaultImpactEdge]
    affectedIds: list[int]
    summary: dict  # severity/criticalPaths/affectedCount/slaRisk...
    businesses: list[AffectedBusiness]
    suggestion: str  # 处置建议 (摘要)
    mitigations: list[Mitigation] = []  # 结构化处置缓解措施清单
