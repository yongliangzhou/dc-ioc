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

export function getTwinOverview(): Promise<TwinOverview> {
  return request.get('/api/ops/twin').then((r: any) => r.data)
}

export function getTwinTopology(modelId: number): Promise<TwinTopology> {
  return request.get(`/api/ops/twin/topology`).then((r: any) => r.data)
}
