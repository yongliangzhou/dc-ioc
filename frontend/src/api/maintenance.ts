import request from './request'

export interface PlanView {
  id: number; code: string; name: string; equipmentCode: string
  description: string | null; frequency: string; nextDueDate: string | null
  status: string; overdue: number
}
export interface RecordView {
  id: number; planId: number | null; planName: string | null
  maintainedBy: string; startedAt: string | null; completedAt: string | null
  status: string; result: string | null; actionDescription: string | null; notes: string | null
}
export interface MaintenanceStats {
  totalPlans: number; activePlans: number; overduePlans: number
  totalRecords: number; completedRecords: number
}

export function getMaintenancePlans(): Promise<PlanView[]> { return request.get('/api/maintenance/plans') }
export function getMaintenanceRecords(planId?: number): Promise<RecordView[]> {
  return request.get('/api/maintenance/records', { params: planId ? { planId } : {} })
}
export function getMaintenanceStats(): Promise<MaintenanceStats> { return request.get('/api/maintenance/stats') }
