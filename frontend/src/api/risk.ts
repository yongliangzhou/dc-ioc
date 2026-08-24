import request from './request'

export interface RiskView {
  id: number
  code: string
  title: string
  category: string
  severity: string
  probability: string
  description: string | null
  mitigation: string | null
  status: string
}

export interface RiskStats {
  total: number
  open: number
  mitigated: number
  critical: number
  high: number
}

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 Number()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

// 后端 GET /api/ops/risk 返回 { stats: {high, mid, low, closed}, matrix: [...] }
export async function getRisks(): Promise<RiskView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/risk')
  return (resp.matrix as RiskView[]) ?? []
}

// ---- 风险项写操作 ----
export interface RiskCreate {
  risk: string
  cat?: string
  prob?: number
  impact?: number
  ctrl?: string
  owner?: string
  code?: string
  closed?: number
}
export function createRisk(payload: RiskCreate): Promise<unknown> {
  return request.post('/api/ops/risk', payload)
}
export function updateRisk(id: number, payload: Partial<RiskCreate>): Promise<unknown> {
  return request.put(`/api/ops/risk/${id}`, payload)
}
export function deleteRisk(id: number): Promise<unknown> {
  return request.delete(`/api/ops/risk/${id}`)
}

// 基于采集数据 + 活跃告警自动分析生成风险提示 (草稿)
export function analyzeRisk(): Promise<unknown> {
  return request.post('/api/ops/risk/analyze', {})
}

export async function getRiskStats(): Promise<RiskStats> {
  const resp = await request.get<unknown, RawItem>('/api/ops/risk')
  const s = (resp.stats as RawItem) ?? {}
  const high = Number(s.high) || 0
  const mid = Number(s.mid) || 0
  const low = Number(s.low) || 0
  const closed = Number(s.closed) || 0
  const total = high + mid + low
  return {
    total,
    open: total - closed,
    mitigated: closed,
    critical: high,
    high,
  }
}
