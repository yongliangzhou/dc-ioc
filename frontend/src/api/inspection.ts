import request from './request'

// ---- 后端类型 ----

export interface RouteView {
  id: number
  code: string
  name: string
  description: string | null
  frequency: string
  status: string
}

export interface RecordView {
  id: number
  routeId: number | null
  routeName: string | null
  inspectorName: string
  startedAt: string | null
  completedAt: string | null
  status: string
  result: string | null
  notes: string | null
  itemTotal: number
  itemPassed: number
  itemFailed: number
  itemWarned: number
}

export interface ItemView {
  id: number
  equipmentCode: string
  itemName: string
  checked: boolean
  result: string | null
  remark: string | null
}

export interface InspectionStats {
  totalRoutes: number
  activeRoutes: number
  todayRecords: number
  completedRecords: number
  passRecords: number
  failRecords: number
  completionRate: number
  passRate: number
}

// ---- API ----

export function getInspectionRoutes(): Promise<RouteView[]> {
  return request.get('/api/inspection/routes')
}

export function getInspectionRecords(routeId?: number): Promise<RecordView[]> {
  return request.get('/api/inspection/records', { params: routeId ? { routeId } : {} })
}

export function getInspectionRecordDetail(recordId: number): Promise<RecordView> {
  return request.get(`/inspection/records/${recordId}`)
}

export function getInspectionItems(recordId: number): Promise<ItemView[]> {
  return request.get(`/inspection/records/${recordId}/items`)
}

export function getInspectionStats(): Promise<InspectionStats> {
  return request.get('/api/inspection/stats')
}
