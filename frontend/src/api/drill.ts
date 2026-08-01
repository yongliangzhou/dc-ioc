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

// 后端 GET /api/ops/drill 返回 { stats: {year, done, pass, next}, plans: [...] }
// 后端 GET /api/ops/drill/records 返回 { records: [...], total } (真实演练记录)
export async function getDrillPlans(): Promise<DrillPlanView[]> {
  const resp: any = await request.get('/api/ops/drill')
  return resp.plans ?? []
}

export async function getDrillRecords(planId?: number): Promise<DrillRecordView[]> {
  const resp: any = await request.get('/api/ops/drill/records', {
    params: planId != null ? { planId } : {},
  })
  return resp.records ?? []
}

export async function getDrillStats(): Promise<DrillStats> {
  const resp: any = await request.get('/api/ops/drill')
  const s = resp.stats ?? {}
  return {
    totalPlans: (resp.plans ?? []).length,
    totalRecords: 0,
    avgScore: 0,
    passedCount: s.pass ?? 0,
    failedCount: 0,
  }
}
