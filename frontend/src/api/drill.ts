import request from './request'
export interface DrillPlanView { id: number; code: string; name: string; scenario: string; description: string | null; participants: string | null }
export interface DrillRecordView { id: number; planId: number | null; planName: string | null; executedBy: string; startedAt: string | null; completedAt: string | null; score: number | null; result: string | null; notes: string | null }
export interface DrillStats { totalPlans: number; totalRecords: number; avgScore: number; passedCount: number; failedCount: number }
export function getDrillPlans(): Promise<DrillPlanView[]> { return request.get('/api/drill/plans') }
export function getDrillRecords(planId?: number): Promise<DrillRecordView[]> { return request.get('/api/drill/records', { params: planId ? { planId } : {} }) }
export function getDrillStats(): Promise<DrillStats> { return request.get('/api/drill/stats') }
