import request from './request'

export interface PlanView {
  id: number | string
  code: string
  name: string
  equipmentCode: string
  description: string | null
  frequency: string
  nextDueDate: string | null
  status: string
  overdue: number
}

export interface RecordView {
  id: number
  planId: number | null
  planName: string | null
  maintainedBy: string
  startedAt: string | null
  completedAt: string | null
  status: string
  result: string | null
  actionDescription: string | null
  notes: string | null
}

export interface MaintenanceStats {
  totalPlans: number
  activePlans: number
  overduePlans: number
  totalRecords: number
  completedRecords: number
}

// 后端 GET /api/ops/maintain 返回 { stats: {plan, done, overdue, thisWeek}, plans: [...], spares: [...] }
// 后端 GET /api/ops/maintain/records 返回 { records: [...], total } (真实维保记录)
export async function getMaintenancePlans(): Promise<PlanView[]> {
  const resp: any = await request.get('/api/ops/maintain')
  return (resp.plans ?? []).map((p: any) => ({
    id: p.id,
    code: p.code ?? '',
    name: p.name ?? p.equip ?? '',
    equipmentCode: p.equip ?? '',
    description: p.vendor ?? null,
    frequency: p.cycle ?? '',
    nextDueDate: p.next ?? null,
    status: p.state ?? '正常',
    overdue: p.state === '逾期' ? 1 : 0,
  }))
}

export async function getMaintenanceRecords(planId?: number): Promise<RecordView[]> {
  const resp: any = await request.get('/api/ops/maintain/records', {
    params: planId != null ? { planId } : {},
  })
  return resp.records ?? []
}

export async function getMaintenanceStats(): Promise<MaintenanceStats> {
  const resp: any = await request.get('/api/ops/maintain')
  const s = resp.stats ?? {}
  const plan = s.plan ?? 0
  const done = s.done ?? 0
  return {
    totalPlans: plan,
    activePlans: plan - (s.overdue ?? 0),
    overduePlans: s.overdue ?? 0,
    totalRecords: done,
    completedRecords: done,
  }
}
