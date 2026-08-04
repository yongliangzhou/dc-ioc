import request from './request'

// ===== Twin 数字孪生 =====

export interface TwinModelView {
  id: number
  name: string
  description: string
  status: string
  nodeCount: number
  edgeCount: number
}

export interface TwinOverview {
  modelCount: number
  activeModelCount: number
  totalNodes: number
  totalEdges: number
  models: TwinModelView[]
}

export interface TopoNode {
  id: string
  label: string
  kind: string
  lane: string
  x: number
  y: number
  load: number
  health: number
  redundancy: string | null
}

export interface TopoEdge {
  id: string
  from: string
  to: string
  type: string
  label: string | null
}

export interface TwinTopology {
  name: string
  description: string
  source: string
  nodes: TopoNode[]
  edges: TopoEdge[]
}

// ---- 后端原始结构: generated.twin() ----
interface RawTwin {
  platform?: string
  coverage?: { points?: number; mapped?: number; models?: number; refreshMs?: number }
  layers?: string[]
  scenes?: { id: string; state?: string; last?: string }[]
  autoOps?: { id: string; state?: string; saving?: string }[]
  knowledge?: unknown
}

function mapTwin(raw: RawTwin): TwinOverview {
  const scenes = raw.scenes ?? []
  const models: TwinModelView[] = scenes.map((s, i) => ({
    id: i + 1,
    name: s.id,
    description: s.state ?? '',
    status: s.state ?? '已编排',
    nodeCount: 0,
    edgeCount: 0,
  }))
  // 若没有 scenes, 用平台信息构造一个默认模型, 避免界面完全空白
  if (models.length === 0) {
    models.push({
      id: 1,
      name: raw.platform || '数字孪生平台',
      description: 'Raptor / 方舟自动化运营平台',
      status: '在线',
      nodeCount: 0,
      edgeCount: 0,
    })
  }
  return {
    modelCount: models.length,
    activeModelCount: models.filter((m) => m.status !== '离线').length,
    totalNodes: raw.coverage?.points ?? 0,
    totalEdges: raw.coverage?.mapped ?? 0,
    models,
  }
}

// ---- 后端原始结构: agg.twin_topology() -> { twinGraph, topology, summary } ----
interface RawTopoNode {
  id?: string | number
  label?: string
  name?: string
  kind?: string
  category?: string
  lane?: string
  x?: number
  y?: number
  load?: number
  health?: number
  redundancy?: string | null
}
interface RawTopoEdge {
  id?: string | number
  from?: string | number
  to?: string | number
  source?: string | number
  target?: string | number
  type?: string
  label?: string | null
}
interface RawTopoContainer {
  nodes?: RawTopoNode[]
  edges?: RawTopoEdge[]
  source?: string
  name?: string
  description?: string
}
interface RawTopology {
  name?: string
  description?: string
  source?: string
  topology?: RawTopoContainer
  twinGraph?: unknown
  summary?: { source?: string }
}

function mapTopology(raw: RawTopology): TwinTopology {
  const topo: RawTopoContainer = raw.topology ?? (raw as unknown as RawTopoContainer)
  const nodes = (topo.nodes ?? []).map((n): TopoNode => ({
    id: String(n.id ?? n.label ?? Math.random()),
    label: n.label ?? n.name ?? String(n.id ?? ''),
    kind: n.kind ?? n.category ?? 'device',
    lane: n.lane ?? (n.category === 'power' ? 'power' : n.category === 'cool' ? 'cool' : 'other'),
    x: n.x ?? 0,
    y: n.y ?? 0,
    load: n.load ?? 0,
    health: n.health ?? 0,
    redundancy: n.redundancy ?? null,
  }))
  const edges = (topo.edges ?? []).map((e): TopoEdge => ({
    id: String(e.id ?? `${e.from}-${e.to}`),
    from: String(e.from ?? e.source ?? ''),
    to: String(e.to ?? e.target ?? ''),
    type: e.type ?? 'power',
    label: e.label ?? null,
  }))
  return {
    name: raw.name ?? '数字孪生拓扑',
    description: raw.description ?? '',
    source: raw.source ?? topo.source ?? raw.summary?.source ?? 'generated',
    nodes,
    edges,
  }
}

export function getTwinOverview(): Promise<TwinOverview> {
  return request.get<unknown, RawTwin>('/api/ops/twin').then(mapTwin)
}

export function getTwinTopology(): Promise<TwinTopology> {
  return request.get<unknown, RawTopology>('/api/ops/twin/topology').then(mapTopology)
}
