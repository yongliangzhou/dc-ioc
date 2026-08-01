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
  return request.get('/api/ops/inspection/routes')
}

// 后端 GET /api/ops/inspection/findings 返回巡检发现列表 (对应原 records 概念)
export function getInspectionRecords(routeId?: number): Promise<RecordView[]> {
  return request
    .get('/api/ops/inspection/findings', { params: routeId ? { routeId } : {} })
    .then((r: any) => r)
}

// 后端已补 GET /api/ops/inspection/findings/{fid} 详情端点
export function getInspectionRecordDetail(recordId: number): Promise<RecordView> {
  return request.get(`/api/ops/inspection/findings/${recordId}`).then((r: any) => r)
}

// 后端 finding 模型无 items 子表概念, 降级返回空数组 (产品确认无需独立 items 端点)
export function getInspectionItems(recordId: number): Promise<ItemView[]> {
  void recordId
  return Promise.resolve([])
}

// 后端 GET /api/ops/inspection 返回 { today: {...}, robot: {...}, routes, findings }
// 统计从 today 字段派生
export async function getInspectionStats(): Promise<InspectionStats> {
  const resp: any = await request.get('/api/ops/inspection')
  const today = resp.today ?? {}
  const plan = today.plan ?? 0
  const done = today.done ?? 0
  const rate = today.rate ?? 0
  return {
    totalRoutes: (resp.routes ?? []).length,
    activeRoutes: plan,
    todayRecords: done,
    completedRecords: done,
    passRecords: done,
    failRecords: 0,
    completionRate: rate,
    passRate: rate,
  }
}
