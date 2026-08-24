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
  owner?: string
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

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 Number()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

// 将 unknown 收窄为 RawItem 数组
function asRawList(v: unknown): RawItem[] {
  return Array.isArray(v) ? (v as RawItem[]) : []
}

// 后端 GET /api/ops/maintain 返回 { stats: {plan, done, overdue, thisWeek}, plans: [...], spares: [...] }
// 后端 GET /api/ops/maintain/records 返回 { records: [...], total } (真实维保记录)
export async function getMaintenancePlans(): Promise<PlanView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/maintain')
  return asRawList(resp.plans).map((p) => ({
    id: (p.id as number | string) ?? '',
    code: String(p.code ?? ''),
    name: String(p.name ?? p.equip ?? ''),
    equipmentCode: String(p.equip ?? ''),
    description: (p.vendor as string | null) ?? null,
    frequency: String(p.cycle ?? ''),
    nextDueDate: (p.next as string | null) ?? null,
    status: String(p.state ?? '正常'),
    overdue: p.state === '逾期' ? 1 : 0,
  }))
}

export async function getMaintenanceRecords(planId?: number | string): Promise<RecordView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/maintain/records', {
    params: planId != null ? { planId } : {},
  })
  return (resp.records as RecordView[]) ?? []
}

// ---- 执行记录写操作 ----
export interface RecordCreate {
  planCode?: string
  planName?: string
  equipmentCode?: string
  maintainedBy?: string
  startedAt?: string
  completedAt?: string
  status?: string
  result?: string
  actionDescription?: string
  notes?: string
}
export function createMaintenanceRecord(payload: RecordCreate): Promise<unknown> {
  return request.post('/api/ops/maintain/records', payload)
}
export function updateMaintenanceRecord(id: number, payload: Partial<RecordCreate>): Promise<unknown> {
  return request.put(`/api/ops/maintain/records/${id}`, payload)
}
export function deleteMaintenanceRecord(id: number): Promise<unknown> {
  return request.delete(`/api/ops/maintain/records/${id}`)
}

export async function getMaintenanceStats(): Promise<MaintenanceStats> {
  const resp = await request.get<unknown, RawItem>('/api/ops/maintain')
  const s = (resp.stats as RawItem) ?? {}
  const plan = Number(s.plan) || 0
  const done = Number(s.done) || 0
  return {
    totalPlans: plan,
    activePlans: plan - (Number(s.overdue) || 0),
    overduePlans: Number(s.overdue) || 0,
    totalRecords: done,
    completedRecords: done,
  }
}

// ---- 维保计划读写 (批次补强, 区别于聚合器动态计划) ----
export interface PlanCreate {
  code?: string
  name?: string
  equipmentCode?: string
  description?: string
  frequency?: string
  nextDueDate?: string
  status?: string
  owner?: string
}
export async function getMaintenancePlanList(status?: string): Promise<PlanView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/maintain/plans', {
    params: status ? { status } : {},
  })
  const list = (resp.plans as PlanView[]) ?? []
  return list.map((p) => ({
    ...p,
    id: Number(p.id),
    overdue:
      p.status === 'done'
        ? 0
        : p.nextDueDate && new Date(p.nextDueDate) < new Date()
          ? 1
          : 0,
  }))
}
export function createMaintenancePlan(payload: PlanCreate): Promise<unknown> {
  return request.post('/api/ops/maintain/plans', payload)
}
export function updateMaintenancePlan(id: number, payload: Partial<PlanCreate>): Promise<unknown> {
  return request.put(`/api/ops/maintain/plans/${id}`, payload)
}
export function deleteMaintenancePlan(id: number): Promise<unknown> {
  return request.delete(`/api/ops/maintain/plans/${id}`)
}
