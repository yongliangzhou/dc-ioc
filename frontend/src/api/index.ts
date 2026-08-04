import request from './request'
import type {
  AlarmCenter,
  AlarmEvent,
  AlarmHistoryQuery,
  AlarmHistoryResponse,
  AlarmRuleDef,
  AlarmRuleStatus,
  AssistantAskReq,
  AssistantAskResp,
  AssistantStatusResp,
  Cabinet,
  CabinetMetrics,
  CampusComparisonResponse,
  CampusesResponse,
  DashboardOverview,
  DeviceActionResponse,
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
  ThingModelDef,
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
  action?: string
  user?: string
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
/** 大模型接入状态自查（运维诊断用） */

export const getActiveAlarms = () =>
  request.get<unknown, { total: number; items: AlarmCenter['active'] }>('/api/alarms/active')

/** 确认活跃告警 (真实联动引擎): POST /api/alarms/{id}/ack */

export const ackActiveAlarm = (id: string) =>
  request.post<unknown, { ok: boolean }>(`/api/alarms/${encodeURIComponent(id)}/ack`)
/** 关单活跃告警 (真实联动引擎): POST /api/alarms/{id}/resolve */

export const resolveActiveAlarm = (id: string) =>
  request.post<unknown, { ok: boolean }>(`/api/alarms/${encodeURIComponent(id)}/resolve`)

/* ================= 告警规则引擎 API ================= */

export const getAlarmRules = () => request.get<unknown, AlarmRuleDef[]>('/api/alarm-rules')

export const createAlarmRule = (data: Partial<AlarmRuleDef>) =>
  request.post<unknown, AlarmRuleDef>('/api/alarm-rules', data)

export const updateAlarmRule = (id: string, data: Partial<AlarmRuleDef>) =>
  request.put<unknown, AlarmRuleDef>(`/api/alarm-rules/${encodeURIComponent(id)}`, data)

export const deleteAlarmRule = (id: string) =>
  request.delete<unknown, void>(`/api/alarm-rules/${encodeURIComponent(id)}`)

export const toggleAlarmRule = (id: string, status: AlarmRuleStatus) =>
  request.patch<unknown, AlarmRuleDef>(`/api/alarm-rules/${encodeURIComponent(id)}/status`, {
    status,
  })

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
