import request from './request'

export interface DrillPlanView {
  id: number
  code: string
  name: string
  scenario: string
  description: string | null
  participants: string | null
}

export interface DrillRecordView {
  id: number
  planId: number | null
  planName: string | null
  executedBy: string
  startedAt: string | null
  completedAt: string | null
  score: number | null
  result: string | null
  notes: string | null
}

export interface DrillStats {
  totalPlans: number
  totalRecords: number
  avgScore: number
  passedCount: number
  failedCount: number
}

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 Number()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

// 后端 GET /api/ops/drill 返回 { stats: {year, done, pass, next}, plans: [...] }
// 后端 GET /api/ops/drill/records 返回 { records: [...], total } (真实演练记录)
export async function getDrillPlans(): Promise<DrillPlanView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/drill')
  return (resp.plans as DrillPlanView[]) ?? []
}

export async function getDrillRecords(planId?: number): Promise<DrillRecordView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/drill/records', {
    params: planId != null ? { planId } : {},
  })
  return (resp.records as DrillRecordView[]) ?? []
}

export async function getDrillStats(): Promise<DrillStats> {
  const resp = await request.get<unknown, RawItem>('/api/ops/drill')
  const s = (resp.stats as RawItem) ?? {}
  return {
    totalPlans: Array.isArray(resp.plans) ? resp.plans.length : 0,
    totalRecords: 0,
    avgScore: 0,
    passedCount: Number(s.pass) || 0,
    failedCount: 0,
  }
}
