import request from '@/api/request'

/** CMDB 关系层 API (阶段二)。所有读写统一走 axios 实例 (Bearer 注入 / 401 刷新)。 */
const BASE = '/api/ops/ci-relations'

export type RelationType = 'connects_to' | 'powers' | 'cools' | 'depends_on' | 'hosts'

export interface CiRelationRow {
  id: number
  source_ci: string
  target_ci: string
  source_name: string
  target_name: string
  relation_type: RelationType | string
  description: string
  created_by: string
  created_at: string | null
  tenant_id: number | null
}

export interface CiOption {
  ci: string
  name: string
  kind: string
}

export interface CiGraph {
  nodes: Array<{ id: string; name: string }>
  edges: Array<{ id: number; source: string; target: string; type: string }>
  total: number
  topology_source: 'real' | 'fallback'
}

export interface CiImpactItem {
  ci: string
  name: string
  hop: number
  via: string
  path: string[]
}

export interface CiImpact {
  source_ci: string
  depth: number
  topology_source: 'real' | 'fallback'
  impacted: CiImpactItem[]
  total: number
  has_cycle: boolean
}

export interface CiRelationPayload {
  source_ci: string
  target_ci: string
  source_name?: string
  target_name?: string
  relation_type: RelationType
  description?: string
}

export const ciRelationApi = {
  list: (params: Record<string, unknown> = {}) =>
    request.get<CiRelationRow[]>(BASE, { params }).then((r) => r.data),
  create: (payload: CiRelationPayload) =>
    request.post<CiRelationRow>(BASE, payload).then((r) => r.data),
  remove: (id: number) => request.delete(`${BASE}/${id}`).then((r) => r.data),
  graph: () => request.get<CiGraph>(`${BASE}/graph`).then((r) => r.data),
  options: () => request.get<CiOption[]>(`${BASE}/options`).then((r) => r.data),
  impact: (ci: string, depth = 3) =>
    request
      .get<CiImpact>(`${BASE}/impact/${encodeURIComponent(ci)}`, {
        params: { depth },
      })
      .then((r) => r.data),
}

/** 故障影响分析响应里的真实关系标记 (阶段二新增, 旧版响应无此字段)。 */
export interface FaultImpactTopology {
  topologySource?: 'real+legacy' | 'legacy'
  realRelations?: Array<Record<string, unknown>>
}
