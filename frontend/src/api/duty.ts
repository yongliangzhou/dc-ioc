import request from './request'

export interface ShiftView {
  id: number
  code: string
  name: string
  shiftDate: string
  shiftType: string
  onDuty: string
  backupDuty: string | null
  handoverNotes: string | null
}

export interface DutyStats {
  totalShifts: number
  todayShifts: number
}

export function getDutyShifts(from?: string, to?: string): Promise<ShiftView[]> {
  return request.get('/api/ops/shift', { params: { start: from, end: to } })
}

// 后端 shift.py 无统计端点, 基于 /api/ops/shift 列表本地聚合
export async function getDutyStats(): Promise<DutyStats> {
  const shifts: ShiftView[] = await request.get('/api/ops/shift')
  const today = new Date().toISOString().slice(0, 10)
  const todayShifts = shifts.filter((s) => (s.shiftDate || '').slice(0, 10) === today).length
  return { totalShifts: shifts.length, todayShifts }
}
