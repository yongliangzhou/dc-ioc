import request from './request'

// ---- 后端类型 (从 Java MonitorDtos 映射) ----

export interface SecurityDeviceView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  lastEvent: string | null
  lastEventTime: string | null
  commissionedOn: string | null
  healthScore: number | null
}

export interface SecuritySystemSummary {
  total: number
  online: number
  eventsToday: number
  alertsToday: number
  devices: SecurityDeviceView[]
}

export interface SecurityOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  cctv: SecuritySystemSummary
  acs: SecuritySystemSummary
  ids: SecuritySystemSummary
  fire: SecuritySystemSummary
}

// ---- API 调用 ----

export function getSecurityOverview(): Promise<SecurityOverview> {
  return request.get('/api/monitor/security/overview')
}

export function getSecurityCctv(): Promise<SecuritySystemSummary> {
  return request.get('/api/monitor/security/cctv')
}

export function getSecurityAcs(): Promise<SecuritySystemSummary> {
  return request.get('/api/monitor/security/acs')
}

export function getSecurityIds(): Promise<SecuritySystemSummary> {
  return request.get('/api/monitor/security/ids')
}

export function getSecurityFire(): Promise<SecuritySystemSummary> {
  return request.get('/api/monitor/security/fire')
}
