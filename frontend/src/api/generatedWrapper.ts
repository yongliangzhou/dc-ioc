/**
 * Bridge layer: wraps orval-generated fetch-based API calls with our
 * existing axios instance (auth interceptors, token refresh, mock fallback).
 *
 * Usage:
 *   import { api } from '@/api/generatedWrapper'
 *   const res = await api.getApiAlarmsActive()
 *   // res.data has the typed response body
 */

import request from './request'

type FetchConfig = {
  method: string
  params?: Record<string, unknown>
  data?: unknown
  headers?: Record<string, string>
}

/**
 * Adapts axios to the { data, status, headers } shape that orval
 * generated code expects, so callers only deal with `.data`.
 */
async function axiosFetch<T>(url: string, config: FetchConfig): Promise<{ data: T; status: number; headers: Headers }> {
  const method = config.method?.toLowerCase() || 'get'

  const resp = await request({
    url,
    method,
    params: config.params,
    data: config.data,
    headers: config.headers,
  })

  // The axios response interceptor already extracts res.data,
  // so `resp` here is already the parsed body.
  return {
    data: resp as T,
    status: 200,
    headers: new Headers(),
  }
}

// Re-export all generated type exports for convenience
export * from './generated/index'

// ─── Typed API helpers (replace generated fetch calls with axios) ───

import type {
  AlarmRuleDef,
  Cabinet,
  Equipment,
  Ticket,
  DashboardOverview,
  GetApiCabinetsParams,
  GetApiCabinetsCabinetIdMetricsParams,
  GetApiCabinetsCabinetIdMetrics200,
  GetApiEquipmentParams,
  GetApiEquipment200,
  GetApiEquipmentEquipmentIdMetricsParams,
  GetApiEquipmentEquipmentIdMetrics200,
  GetApiTicketsParams,
  GetApiTickets200,
  PostApiTicketsBody,
  PutApiTicketsIdBody,
  PostApiTicketsIdTransitionStateBody,
  PostApiTicketsFromAlarmAlarmIdBody,
  PostApiOpsAssistantAskBody,
  PostApiOpsAssistantAsk200,
  GetApiOpsAssistantStatus200,
  GetApiAlarmsActive200,
  PostApiAlarmsActiveIdAck200,
  PostApiAlarmsActiveIdResolve200,
  PatchApiAlarmRulesIdStatusBody,
  PatchApiAlarmRulesIdToggleBody,
  GetApiExternalDevicesParams,
  GetApiExternalDevices200,
  GetApiExternalThingModels200Item,
  GetApiExternalDevicesDeviceIdMetricsRealtime200,
  GetApiExternalDevicesDeviceIdMetricsHistoryParams,
  GetApiExternalDevicesDeviceIdMetricsHistory200,
  PostApiAuthLoginBody,
  PostApiAuthLogin200,
  PostApiAuthRegisterBody,
  PostApiAuthRegister200,
  PostApiAuthRefreshBody,
  PostApiAuthRefresh200,
  GetApiAuditLogsParams,
  GetApiAuditLogs200,
  GetApiKnowledgeParams,
  GetApiKnowledge200Item,
  PostApiKnowledgeImportBody,
  PostApiKnowledgeImport200,
} from './generated/index'

/** Typed API callers — use these instead of the raw generated fetch functions */

export const api = {
  // ── Cabinets ──
  getCabinets(params?: GetApiCabinetsParams) {
    return axiosFetch<Cabinet[]>(`/api/cabinets`, { method: 'GET', params: params as Record<string, unknown> })
  },
  getCabinetMetrics(cabinetId: number, params?: GetApiCabinetsCabinetIdMetricsParams) {
    return axiosFetch<GetApiCabinetsCabinetIdMetrics200>(`/api/cabinets/${cabinetId}/metrics`, { method: 'GET', params: params as Record<string, unknown> })
  },

  // ── Equipment ──
  getEquipment(params?: GetApiEquipmentParams) {
    return axiosFetch<GetApiEquipment200>(`/api/equipment`, { method: 'GET', params: params as Record<string, unknown> })
  },
  getEquipmentDetail(id: number) {
    return axiosFetch<Equipment>(`/api/equipment/${id}`, { method: 'GET' })
  },
  getEquipmentMetrics(equipmentId: number, params?: GetApiEquipmentEquipmentIdMetricsParams) {
    return axiosFetch<GetApiEquipmentEquipmentIdMetrics200>(`/api/equipment/${equipmentId}/metrics`, { method: 'GET', params: params as Record<string, unknown> })
  },

  // ── Tickets ──
  getTickets(params?: GetApiTicketsParams) {
    return axiosFetch<GetApiTickets200>(`/api/tickets`, { method: 'GET', params: params as Record<string, unknown> })
  },
  createTicket(body: PostApiTicketsBody) {
    return axiosFetch<Ticket>(`/api/tickets`, { method: 'POST', data: body })
  },
  getTicket(id: string) {
    return axiosFetch<Ticket>(`/api/tickets/${id}`, { method: 'GET' })
  },
  updateTicket(id: string, body: PutApiTicketsIdBody) {
    return axiosFetch<Ticket>(`/api/tickets/${id}`, { method: 'PUT', data: body })
  },
  deleteTicket(id: string) {
    return axiosFetch<void>(`/api/tickets/${id}`, { method: 'DELETE' })
  },
  transitionTicket(id: string, state: string, body: PostApiTicketsIdTransitionStateBody) {
    return axiosFetch<Ticket>(`/api/tickets/${id}/transition/${state}`, { method: 'POST', data: body })
  },
  ticketFromAlarm(alarmId: string, body: PostApiTicketsFromAlarmAlarmIdBody) {
    return axiosFetch<Ticket>(`/api/tickets/from-alarm/${alarmId}`, { method: 'POST', data: body })
  },

  // ── AI Assistant ──
  askAssistant(body: PostApiOpsAssistantAskBody) {
    return axiosFetch<PostApiOpsAssistantAsk200>(`/api/ops/assistant/ask`, { method: 'POST', data: body })
  },
  getAssistantStatus() {
    return axiosFetch<GetApiOpsAssistantStatus200>(`/api/ops/assistant/status`, { method: 'GET' })
  },

  // ── Alarms ──
  getActiveAlarms() {
    return axiosFetch<GetApiAlarmsActive200>(`/api/alarms/active`, { method: 'GET' })
  },
  ackAlarm(id: string) {
    return axiosFetch<PostApiAlarmsActiveIdAck200>(`/api/alarms/active/${id}/ack`, { method: 'POST' })
  },
  resolveAlarm(id: string) {
    return axiosFetch<PostApiAlarmsActiveIdResolve200>(`/api/alarms/active/${id}/resolve`, { method: 'POST' })
  },

  // ── Alarm Rules ──
  getAlarmRules() {
    return axiosFetch<AlarmRuleDef[]>(`/api/alarm-rules`, { method: 'GET' })
  },
  createAlarmRule(body: AlarmRuleDef) {
    return axiosFetch<AlarmRuleDef>(`/api/alarm-rules`, { method: 'POST', data: body })
  },
  updateAlarmRule(id: string, body: AlarmRuleDef) {
    return axiosFetch<AlarmRuleDef>(`/api/alarm-rules/${id}`, { method: 'PUT', data: body })
  },
  deleteAlarmRule(id: string) {
    return axiosFetch<void>(`/api/alarm-rules/${id}`, { method: 'DELETE' })
  },
  patchAlarmRuleStatus(id: string, body: PatchApiAlarmRulesIdStatusBody) {
    return axiosFetch<AlarmRuleDef>(`/api/alarm-rules/${id}/status`, { method: 'PATCH', data: body })
  },
  patchAlarmRuleToggle(id: string, body: PatchApiAlarmRulesIdToggleBody) {
    return axiosFetch<AlarmRuleDef>(`/api/alarm-rules/${id}/toggle`, { method: 'PATCH', data: body })
  },

  // ── Dashboard ──
  getDashboardOverview() {
    return axiosFetch<DashboardOverview>(`/api/dashboard/overview`, { method: 'GET' })
  },

  // ── External Devices ──
  getExternalDevices(params?: GetApiExternalDevicesParams) {
    return axiosFetch<GetApiExternalDevices200>(`/api/external/devices`, { method: 'GET', params: params as Record<string, unknown> })
  },
  getExternalThingModels() {
    return axiosFetch<GetApiExternalThingModels200Item[]>(`/api/external/thing-models`, { method: 'GET' })
  },
  getDeviceRealtime(deviceId: string) {
    return axiosFetch<GetApiExternalDevicesDeviceIdMetricsRealtime200>(`/api/external/devices/${deviceId}/metrics/realtime`, { method: 'GET' })
  },
  getDeviceHistory(deviceId: string, params?: GetApiExternalDevicesDeviceIdMetricsHistoryParams) {
    return axiosFetch<GetApiExternalDevicesDeviceIdMetricsHistory200>(`/api/external/devices/${deviceId}/metrics/history`, { method: 'GET', params: params as Record<string, unknown> })
  },

  // ── Auth ──
  login(body: PostApiAuthLoginBody) {
    return axiosFetch<PostApiAuthLogin200>(`/api/auth/login`, { method: 'POST', data: body })
  },
  register(body: PostApiAuthRegisterBody) {
    return axiosFetch<PostApiAuthRegister200>(`/api/auth/register`, { method: 'POST', data: body })
  },
  refresh(body: PostApiAuthRefreshBody) {
    return axiosFetch<PostApiAuthRefresh200>(`/api/auth/refresh`, { method: 'POST', data: body })
  },

  // ── Audit ──
  getAuditLogs(params?: GetApiAuditLogsParams) {
    return axiosFetch<GetApiAuditLogs200>(`/api/audit/logs`, { method: 'GET', params: params as Record<string, unknown> })
  },

  // ── Knowledge ──
  getKnowledge(params?: GetApiKnowledgeParams) {
    return axiosFetch<GetApiKnowledge200Item[]>(`/api/knowledge`, { method: 'GET', params: params as Record<string, unknown> })
  },
  importKnowledge(body: PostApiKnowledgeImportBody) {
    return axiosFetch<PostApiKnowledgeImport200>(`/api/knowledge/import`, { method: 'POST', data: body })
  },
}
