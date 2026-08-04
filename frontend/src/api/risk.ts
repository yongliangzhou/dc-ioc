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
