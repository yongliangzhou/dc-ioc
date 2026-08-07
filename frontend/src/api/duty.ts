import request from './request'

export interface ShiftMember {
  name: string
  role?: string
  phone?: string
}
export interface ShiftView {
  id: number
  date: string
  shift: string // day / night
  members: ShiftMember[] // [{name, role, phone}]
  leader: string
  note: string
  createdAt?: string
  updatedAt?: string
}

export interface DutyStats {
  totalShifts: number
  todayShifts: number
}

// ===== 排班 CRUD =====
export interface ShiftCreate {
  date: string
  shift?: string
  members?: ShiftMember[] // 成员数组 [{name, role, phone}]
  leader?: string
  note?: string
}

export function getDutyShifts(from?: string, to?: string): Promise<ShiftView[]> {
  return request.get('/api/ops/shift', { params: { start: from, end: to } })
}

export async function getDutyStats(): Promise<DutyStats> {
  const shifts: ShiftView[] = await request.get('/api/ops/shift')
  const today = new Date().toISOString().slice(0, 10)
  const todayShifts = shifts.filter((s) => (s.date || '').slice(0, 10) === today).length
  return { totalShifts: shifts.length, todayShifts }
}

export function createDutyShift(payload: ShiftCreate): Promise<ShiftView> {
  return request.post('/api/ops/shift', payload)
}
export function updateDutyShift(id: number, payload: Partial<ShiftCreate>): Promise<ShiftView> {
  return request.put(`/api/ops/shift/${id}`, payload)
}
export function deleteDutyShift(id: number): Promise<void> {
  return request.delete(`/api/ops/shift/${id}`)
}

// ===== 交接班 =====
export interface HandoverItem {
  level?: string // normal / warn / critical
  text: string
}
export interface HandoverView {
  id: number
  shiftDate: string
  shiftType: string
  fromUser: string
  toUser: string
  items: string // JSON 串
  note: string
  status: string
  createdAt?: string
  updatedAt?: string
}
export interface HandoverCreate {
  shiftDate?: string
  shiftType?: string
  fromUser?: string
  toUser?: string
  items?: string // JSON 串
  note?: string
  status?: string
}

export function getHandovers(shiftDate?: string, status?: string): Promise<{ items: HandoverView[]; total: number }> {
  return request.get('/api/ops/shift/handover', { params: { shiftDate, status } })
}
export function createHandover(payload: HandoverCreate): Promise<HandoverView> {
  return request.post('/api/ops/shift/handover', payload)
}
export function updateHandover(id: number, payload: Partial<HandoverCreate>): Promise<HandoverView> {
  return request.put(`/api/ops/shift/handover/${id}`, payload)
}
export function deleteHandover(id: number): Promise<void> {
  return request.delete(`/api/ops/shift/handover/${id}`)
}
