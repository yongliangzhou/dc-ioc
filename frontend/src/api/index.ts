import request from './request'
import type {
  AlarmCenter,
  AlarmEvent,
  AlarmHistoryQuery,
  AlarmHistoryResponse,
  AlarmRuleDef,
  AssistantAskReq,
  AssistantAskResp,
  AssistantStatusResp,
  AssistantModel,
  Cabinet,
  CabinetMetrics,
  CampusComparisonResponse,
  CampusesResponse,
  FaultImpactReq,
  FaultImpactResp,
  FaultSourceList,
  AnalysisHistory,
  DashboardOverview,
  DeviceActionResponse,
  Drill,
  DrillPlan,
  DrillRecord,
  TenantItem,
  TenantStats,
  DeviceListResponse,
  DeviceRegisterResponse,
  DeviceUpdateRequest,
  Equipment,
  EquipmentMetrics,
  ExternalDevice,
  KnowledgeItem,
  MetricHistoryResponse,
  MetricRealtimeResponse,
  MetricRecordView,
  Paginated,
  RecognizeResp,
  ServerItem,
  ThingModelDef,
  UPositionView,
  Ticket,
  TicketCenter,
  TicketCreateRequest,
  TicketTransitionRequest,
  TicketUpdateRequest,
} from '@/types'

export interface CabinetQuery {
  page?: number
  size?: number
  room?: string
}
/** 机柜分页列表 (支持机房筛选) */

export const getCabinets = (params: CabinetQuery = {}) =>
  request.get<unknown, Paginated<Cabinet>>('/api/cabinets', { params })

/** 设备分页查询参数 */
export interface EquipmentQuery {
  page?: number
  size?: number
  room?: string
  status?: string
  keyword?: string
  [key: string]: unknown
}

/** 审计日志条目 */
export interface AuditLogItem {
  id: number | string
  timestamp?: string
  ts?: string
  method?: string
  action?: string
  resource?: string
  path?: string
  username?: string
  user?: string
  ip?: string
  status_code?: number
  detail?: string
  [key: string]: unknown
}

/** 审计日志查询参数 */
export interface AuditLogQuery {
  page?: number
  size?: number
  action?: string
  user?: string
  [key: string]: unknown
}

/** 工单中心查询参数 */
export interface TicketQuery {
  page?: number
  size?: number
  state?: string
  system?: string
  domain?: string
  [key: string]: unknown
}

/** 机柜近 N 分钟温湿度/功耗曲线 */

export interface EquipmentPageResult {
  items: Equipment[]
  total: number
  page: number
  page_size: number
}

export const listEquipment = (params: EquipmentQuery = {}) =>
  request.get<unknown, EquipmentPageResult>('/api/equipment', { params })

export const getEquipment = (id: number) => request.get<unknown, Equipment>(`/api/equipment/${id}`)

export const createTicket = (data: TicketCreateRequest) =>
  request.post<unknown, Ticket>('/api/tickets', data)

export const updateTicket = (id: string, data: TicketUpdateRequest) =>
  request.put<unknown, Ticket>('/api/tickets/' + encodeURIComponent(id), data)

export const transitionTicket = (id: string, data: TicketTransitionRequest) =>
  request.post<unknown, Ticket>(
    '/api/tickets/' + encodeURIComponent(id) + '/transition/' + encodeURIComponent(data.state),
    { operator: data.operator, note: data.note },
  )

export const deleteTicket = (id: string) =>
  request.delete<unknown, void>('/api/tickets/' + encodeURIComponent(id))

export const askAssistant = (payload: AssistantAskReq) =>
  request.post<unknown, AssistantAskResp>('/api/ops/assistant/ask', payload)

/** 自定义模型列表（含当前激活） */
export const getAssistantModels = () =>
  request.get<unknown, { active: string; models: AssistantModel[] }>('/api/ops/assistant/models')
/** 切换激活模型（admin/operator） */
export const selectAssistantModel = (model: string) =>
  request.post<unknown, { ok: boolean; active: string }>('/api/ops/assistant/models/select', { model })
/** 探测指定模型真实推理可用性 */
export const assistantModelStatus = (model: string) =>
  request.get<unknown, AssistantStatusResp>('/api/ops/assistant/models/status', { params: { model } })

/** 提交 AI 回答反馈 (满意度/纠错) */
export const submitAssistantFeedback = (payload: {
  question: string
  answer: string
  rating: string
  correction?: string
  note?: string
  grounded?: string
  model?: string
}) => request.post<unknown, { ok: boolean; id: number }>('/api/ops/assistant/feedback', payload)
/** 大模型接入状态自查（运维诊断用） */

export const getActiveAlarms = () =>
  request.get<unknown, { total: number; items: AlarmCenter['active'] }>('/api/alarms/active')

/** 确认活跃告警 (真实联动引擎): POST /api/alarms/{id}/ack */

export const ackActiveAlarm = (id: string) =>
  request.post<unknown, { ok: boolean }>(`/api/alarms/${encodeURIComponent(id)}/ack`)
/** 关单活跃告警 (真实联动引擎): POST /api/alarms/{id}/resolve */

export const resolveActiveAlarm = (id: string) =>
  request.post<unknown, { ok: boolean }>(`/api/alarms/${encodeURIComponent(id)}/resolve`)

/** 提交告警处理反馈/经验沉淀 (后端持久化) */
export const submitAlarmFeedback = (payload: {
  alarmId: string
  system: string
  result: string
  note: string
  operator?: string
}) => request.post<unknown, { ok: boolean; id: number }>('/api/alarms/feedback', payload)

/* ================= 告警规则引擎 API ================= */

export const getAlarmRules = () => request.get<unknown, AlarmRuleDef[]>('/api/alarm-rules')

export const createAlarmRule = (data: Partial<AlarmRuleDef>) =>
  request.post<unknown, AlarmRuleDef>('/api/alarm-rules', data)

export const updateAlarmRule = (id: string, data: Partial<AlarmRuleDef>) =>
  request.put<unknown, AlarmRuleDef>(`/api/alarm-rules/${encodeURIComponent(id)}`, data)

export const deleteAlarmRule = (id: string) =>
  request.delete<unknown, void>(`/api/alarm-rules/${encodeURIComponent(id)}`)

export const toggleAlarmRule = (id: string | number, status?: 'enabled' | 'silenced' | 'disabled') => {
  const url = status && status !== 'disabled'
    ? `/api/alarm-rules/${encodeURIComponent(id)}/status`
    : `/api/alarm-rules/${encodeURIComponent(id)}/toggle`
  const body = status && status !== 'disabled' ? { status } : undefined
  return request.patch<unknown, AlarmRuleDef>(url, body)
}

export const getAuditLogs = (params: AuditLogQuery = {}) =>
  request.get<unknown, { items: AuditLogItem[]; total: number; page: number; page_size: number }>(
    '/api/audit-logs',
    { params },
  )

/* ================= 告警持久化 API ================= */

export const getAlarmHistory = (query: AlarmHistoryQuery = {}) =>
  request.get<unknown, AlarmHistoryResponse>('/api/alarm-history', { params: query })

export const acknowledgeAlarm = (eventId: string, operator: string) =>
  request.post<unknown, AlarmEvent>(`/api/alarms/${encodeURIComponent(eventId)}/ack`, {
    note: operator,
  })

export const resolveAlarm = (eventId: string, operator: string, note?: string) =>
  request.post<unknown, AlarmEvent>(`/api/alarms/${encodeURIComponent(eventId)}/resolve`, {
    operator,
    note,
  })

/* ================= 外部设备接入数据契约 (采集器对接) ================= */
/** 设备注册: POST /api/external/devices/register */

export interface DeviceQuery {
  domain?: string
  protocol?: string
  skip?: number
  limit?: number
}

export const getExternalDevices = (params: DeviceQuery = {}) =>
  request.get<unknown, DeviceListResponse>('/api/external/devices', { params })

/** 设备更新: PUT /api/external/devices/{device_id} */

export const updateDevice = (deviceId: string, data: DeviceUpdateRequest) =>
  request.put<unknown, DeviceActionResponse>(
    `/api/external/devices/${encodeURIComponent(deviceId)}`,
    data,
  )

/** 设备删除: DELETE /api/external/devices/{device_id} */

export const deleteDevice = (deviceId: string) =>
  request.delete<unknown, DeviceActionResponse>(
    `/api/external/devices/${encodeURIComponent(deviceId)}`,
  )

/** 物模型列表: GET /api/external/thing-models */

export const getThingModels = () =>
  request.get<unknown, ThingModelDef[]>('/api/external/thing-models')

/** 某设备最近测点: GET /api/external/devices/{device_id}/metrics */

export const getDeviceMetrics = (deviceId: string, limit = 50) =>
  request.get<unknown, MetricRecordView[]>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metrics`,
    { params: { limit } },
  )

/** 某设备实时测点快照: GET /api/external/devices/{device_id}/metrics/realtime */

export const getDeviceRealtime = (deviceId: string) =>
  request.get<unknown, MetricRealtimeResponse>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metrics/realtime`,
  )

// ===== 测点定义 CRUD (前端「测点增删改查」) =====
export interface MetricDef {
  id: number
  deviceId: string
  metricName: string
  label: string
  unit: string
  dataType: string
  description: string
  enabled: boolean
}

export const getMetricDefs = (deviceId: string) =>
  request.get<unknown, MetricDef[]>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metric-defs`,
  )

export const createMetricDef = (deviceId: string, payload: Partial<MetricDef>) =>
  request.post<unknown, MetricDef>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metric-defs`,
    payload,
  )

export const updateMetricDef = (deviceId: string, id: number, payload: Partial<MetricDef>) =>
  request.put<unknown, MetricDef>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metric-defs/${id}`,
    payload,
  )

export const deleteMetricDef = (deviceId: string, id: number) =>
  request.delete<unknown, void>(
    `/api/external/devices/${encodeURIComponent(deviceId)}/metric-defs/${id}`,
  )

/** 某设备历史测点趋势: GET /api/external/devices/{device_id}/metrics/history */

export const getCampuses = () => request.get<unknown, CampusesResponse>('/api/dashboard/campuses')

export const getCampusComparison = () =>
  request.get<unknown, CampusComparisonResponse>('/api/dashboard/campus-comparison')

export const getDashboardOverview = () =>
  request.get<unknown, DashboardOverview>('/api/dashboard/overview')

export const getAlarms = () => request.get<unknown, AlarmCenter>('/api/ops/alarms')

export const getRelatedRunbooks = (
  params: { system?: string; domain?: string; metric?: string } = {},
) => request.get<unknown, KnowledgeItem[]>('/api/runbooks/related', { params })

export const getCabinetMetrics = (
  cabinetId: number | string,
  params: { minutes?: number; step_sec?: number } = {},
) => request.get<unknown, CabinetMetrics>(`/api/cabinets/${cabinetId}/metrics`, { params })

export const getEquipmentMetrics = (
  equipmentId: number | string,
  params: { minutes?: number; step_sec?: number } = {},
) => request.get<unknown, EquipmentMetrics>(`/api/equipment/${equipmentId}/metrics`, { params })

export const getDeviceHistory = (
  deviceId: string,
  params: { metrics?: string; start?: string; end?: string; limit?: number } = {},
) =>
  request.get<unknown, MetricHistoryResponse>(`/api/external/devices/${deviceId}/metrics/history`, {
    params,
  })

export const getTickets = (params: TicketQuery = {}) =>
  request.get<unknown, TicketCenter>('/api/ops/tickets', { params })

export const createTicketFromAlarm = (alarmId: string, data: TicketCreateRequest) =>
  request.post<unknown, Ticket>(`/api/tickets/from-alarm/${encodeURIComponent(alarmId)}`, data)

export const registerDevice = (data: ExternalDevice) =>
  request.post<unknown, DeviceRegisterResponse>('/api/external/devices/register', data)

export const silenceAlarmRule = (id: string, durationMin = 30) =>
  request.patch<unknown, AlarmRuleDef>(`/api/alarm-rules/${encodeURIComponent(id)}/silence`, {
    duration: durationMin,
  })

export const assistantStatus = () =>
  request.get<unknown, AssistantStatusResp>('/api/ops/assistant/status')

/* ================= 自助注册 API (5.4.1) ================= */

export interface UserRegisterRequest {
  username: string
  password: string
  display_name?: string
  email?: string
}

/** 自助注册只读账号: POST /api/auth/register (后端 ALLOW_SELF_REGISTER 开关控制) */
export const registerUser = (data: UserRegisterRequest) =>
  request.post<unknown, { id: number; username: string; roles: string[] }>(
    '/api/auth/register',
    data,
  )

/* ================= U 位识别 API (RFID + 电子工单多源融合) ================= */

export interface CabinetOption {
  id: number
  code: string
  room: string
  row: string
  uTotal: number
}

export interface CabinetListQuery {
  page?: number
  size?: number
  room?: string
}

/** 机柜下拉选项 (来自 /api/cabinets) */
export const getCabinetOptions = (params: CabinetListQuery = {}) =>
  request.get<unknown, { items: CabinetOption[]; total: number }>('/api/cabinets', { params })

/** 机柜内服务器列表 (RFID/资产标签实测) */
export const getServers = (cabinetId: number) =>
  request.get<unknown, ServerItem[]>('/api/servers', { params: { cabinetId } })

/** 机柜 U 位立面图 (含识别冲突) */
export const getUPosition = (cabinetId: number) =>
  request.get<unknown, UPositionView>(`/api/cabinets/${cabinetId}/u-position`)

/** 触发 U 位多源识别 (电子工单 + RFID 融合) */
export const recognizeUPosition = (cabinetId: number) =>
  request.post<unknown, RecognizeResp>(`/api/cabinets/${cabinetId}/u-position/recognize`)

// ---- 故障影响分析 (复用 twin_graph 真实拓扑做链路 BFS 传播) ----
/** 候选故障源: 真实拓扑节点 + 易故障提示 (低健康/已告警/高负载) */
export const getFaultSources = () =>
  request.get<unknown, FaultSourceList>('/api/ops/fault-impact/sources')

/** 故障影响分析: 指定故障源 + 传播范围开关, 沿真实拓扑 BFS 传播 */
export const analyzeFaultImpact = (req: FaultImpactReq) =>
  request.post<unknown, FaultImpactResp>('/api/ops/fault-impact/analyze', req)

/** 影响分析报告历史列表 (存档 + 会签) */
export const getFaultImpactHistory = (limit = 50) =>
  request.get<unknown, AnalysisHistory[]>(`/api/ops/fault-impact/history?limit=${limit}`)

/** 保存影响分析报告 (存档) */
export const saveFaultImpactHistory = (data: Partial<AnalysisHistory>) =>
  request.post<unknown, AnalysisHistory>('/api/ops/fault-impact/history', data)

/** 报告会签 (追加会签人) */
export const signFaultImpactHistory = (id: number, signer: string) =>
  request.post<unknown, AnalysisHistory>(`/api/ops/fault-impact/history/${id}/sign`, { signer })

// ---- 应急演练 (全栈打通真实数据, 持久化到 DB) ----
/** 演练总览: 真实专业域类别建议演练 + DB 计划 (含 steps/level/scope/duration) */
export const getDrills = () => request.get<unknown, Drill>('/api/ops/drill')

/** 新建演练计划 (steps/level/scope/duration 全栈持久化) */
export const createDrill = (data: Partial<DrillPlan>) =>
  request.post<unknown, DrillPlan>('/api/ops/drill', data)

/** 更新演练计划 */
export const updateDrill = (id: number, data: Partial<DrillPlan>) =>
  request.put<unknown, DrillPlan>(`/api/ops/drill/${id}`, data)

/** 删除演练计划 */
export const deleteDrill = (id: number) =>
  request.delete(`/api/ops/drill/${id}`)

/** 演练记录列表 (真实数据, 可过滤 planId) */
export const getDrillRecords = (planId?: number) =>
  request.get<unknown, { records: DrillRecord[]; total: number }>(
    '/api/ops/drill/records' + (planId != null ? `?planId=${planId}` : '')
  )

/** 新建演练记录 */
export const createDrillRecord = (data: Partial<DrillRecord>) =>
  request.post<unknown, DrillRecord>('/api/ops/drill/records', data)

/** 更新演练记录 */
export const updateDrillRecord = (id: number, data: Partial<DrillRecord>) =>
  request.put<unknown, DrillRecord>(`/api/ops/drill/records/${id}`, data)

/** 删除演练记录 */
export const deleteDrillRecord = (id: number) =>
  request.delete(`/api/ops/drill/records/${id}`)

/* ===== 租户管理 (阶段三 A · 资源运营) — 真实数据驱动 ===== */
/** 租户列表 (真实数据, 支持关键字/状态过滤) */
export const getTenants = (kw?: string, status?: string) => {
  const q: string[] = []
  if (kw) q.push(`kw=${encodeURIComponent(kw)}`)
  if (status) q.push(`status=${encodeURIComponent(status)}`)
  const qs = q.length ? '?' + q.join('&') : ''
  return request.get<unknown, { tenants: TenantItem[]; total: number }>(
    `/api/ops/tenants${qs}`
  )
}

/** 租户级统计汇总 (顶部统计卡真实聚合) */
export const getTenantStats = () =>
  request.get<unknown, TenantStats>('/api/ops/tenants/stats')

/** 新建租户 */
export const createTenant = (data: Partial<TenantItem>) =>
  request.post<unknown, TenantItem>('/api/ops/tenants', data)

/** 更新租户 */
export const updateTenant = (id: number, data: Partial<TenantItem>) =>
  request.put<unknown, TenantItem>(`/api/ops/tenants/${id}`, data)

/** 删除租户 */
export const deleteTenant = (id: number) =>
  request.delete(`/api/ops/tenants/${id}`)
