import request from './request'

// ---- 后端类型 ----

export interface RouteView {
  id: number
  code: string
  name: string
  description: string | null
  freq: string
  state: string
  frequency?: string
  status?: string
  note?: string
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

// 巡检发现 (findings) —— 即页面中的"巡检记录"
export interface FindingView {
  id: number
  route: string
  item: string
  ts: string
  lv: string
  action: string
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
  return request.get('/api/ops/inspection/routes')
}

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 Number()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

// 后端 GET /api/ops/inspection/findings 返回巡检发现列表 (对应原 records 概念)
export function getInspectionRecords(routeId?: number): Promise<FindingView[]> {
  return request.get<unknown, FindingView[]>('/api/ops/inspection/findings', {
    params: routeId ? { routeId } : {},
  })
}

// 后端已补 GET /api/ops/inspection/findings/{fid} 详情端点
export function getInspectionRecordDetail(recordId: number): Promise<RecordView> {
  return request.get<unknown, RecordView>(`/api/ops/inspection/findings/${recordId}`)
}

// 后端 finding 模型无 items 子表概念, 降级返回空数组 (产品确认无需独立 items 端点)
export function getInspectionItems(recordId: number): Promise<ItemView[]> {
  void recordId
  return Promise.resolve([])
}

// ---- 路线写操作 ----
export interface RouteCreatePayload {
  code?: string
  name?: string
  description?: string
  freq: string
  items?: number
  last?: string
  next?: string
  state?: string
  note?: string
}
export function createInspectionRoute(payload: RouteCreatePayload): Promise<unknown> {
  return request.post('/api/ops/inspection/routes', payload)
}
export function updateInspectionRoute(
  id: number,
  payload: Partial<RouteCreatePayload>,
): Promise<unknown> {
  return request.put(`/api/ops/inspection/routes/${id}`, payload)
}
export function deleteInspectionRoute(id: number): Promise<unknown> {
  return request.delete(`/api/ops/inspection/routes/${id}`)
}

// ---- 发现写操作 ----
export interface FindingCreatePayload {
  route: string
  item: string
  ts?: string
  lv?: string
  action?: string
}
export function createInspectionFinding(payload: FindingCreatePayload): Promise<unknown> {
  return request.post('/api/ops/inspection/findings', payload)
}
export function updateInspectionFinding(
  id: number,
  payload: Partial<FindingCreatePayload>,
): Promise<unknown> {
  return request.put(`/api/ops/inspection/findings/${id}`, payload)
}
export function deleteInspectionFinding(id: number): Promise<unknown> {
  return request.delete(`/api/ops/inspection/findings/${id}`)
}

// 后端 GET /api/ops/inspection 返回 { today: {...}, robot: {...}, routes, findings }
// 统计从 today 字段派生
export async function getInspectionStats(): Promise<InspectionStats> {
  const resp = await request.get<unknown, RawItem>('/api/ops/inspection')
  const today = (resp.today as RawItem) ?? {}
  const active = Number(today.active) || 0
  const abnormal = Number(today.abnormal) || 0
  const rate = Number(today.rate) || 0
  return {
    totalRoutes: Array.isArray(resp.routes) ? resp.routes.length : 0,
    activeRoutes: active,
    todayRecords: abnormal,
    completedRecords: abnormal,
    passRecords: abnormal,
    failRecords: 0,
    completionRate: rate,
    passRate: rate,
  }
}
