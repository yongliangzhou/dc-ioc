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
  return Promise.all([
    getSecurityCctv(),
    getSecurityAcs(),
    getSecurityIds(),
    getSecurityFire(),
  ]).then(([cctv, acs, ids, fire]) => ({
    totalEquipment: cctv.total + acs.total + ids.total + fire.total,
    onlineCount: cctv.online + acs.online + ids.online + fire.online,
    faultCount: 0,
    warningCount: 0,
    cctv,
    acs,
    ids,
    fire,
  }))
}

export function getSecurityCctv(): Promise<SecuritySystemSummary> {
  return request.get('/api/security/cctv')
}

export function getSecurityAcs(): Promise<SecuritySystemSummary> {
  return request.get('/api/security/acs')
}

export function getSecurityIds(): Promise<SecuritySystemSummary> {
  return request.get('/api/security/ids')
}

export function getSecurityFire(): Promise<SecuritySystemSummary> {
  return request.get('/api/security/fire')
}

