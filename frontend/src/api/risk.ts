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

// 后端 GET /api/ops/risk 返回 { stats: {high, mid, low, closed}, matrix: [...] }
export async function getRisks(): Promise<RiskView[]> {
  const resp: any = await request.get('/api/ops/risk')
  return resp.matrix ?? []
}

export async function getRiskStats(): Promise<RiskStats> {
  const resp: any = await request.get('/api/ops/risk')
  const s = resp.stats ?? {}
  const high = s.high ?? 0
  const mid = s.mid ?? 0
  const low = s.low ?? 0
  const closed = s.closed ?? 0
  const total = high + mid + low
  return {
    total,
    open: total - closed,
    mitigated: closed,
    critical: high,
    high,
  }
}
