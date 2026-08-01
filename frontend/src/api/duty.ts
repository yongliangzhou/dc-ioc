import request from './request'
export interface ShiftView { id: number; code: string; name: string; shiftDate: string; shiftType: string; onDuty: string; backupDuty: string | null; handoverNotes: string | null }
export interface DutyStats { totalShifts: number; todayShifts: number }
export function getDutyShifts(from?: string, to?: string): Promise<ShiftView[]> { return request.get('/api/duty', { params: { from, to } }) }
export function getDutyStats(): Promise<DutyStats> { return request.get('/duty/stats') }
