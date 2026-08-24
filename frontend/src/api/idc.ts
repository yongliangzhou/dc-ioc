import request from './request'

export interface Idc {
  id: number
  code: string
  name: string
  region: string
  address: string
  powerCapacityMw: number
  coolingCapacityMw: number
  rackCapacity: number
  rooms: number
  status: string
  capacityKw: number
  description: string
  isCurrent: boolean
  createdAt?: string
  updatedAt?: string
}

export interface IdcCreate {
  code: string
  name: string
  region: string
  address: string
  powerCapacityMw: number
  coolingCapacityMw: number
  rackCapacity: number
  rooms: number
  status: string
  capacityKw: number
  description: string
}

export interface IdcCompareItem {
  id: number
  code: string
  name: string
  region: string
  status: string
  powerCapacityMw: number
  coolingCapacityMw: number
  rackCapacity: number
  rackUsed: number
  deviceCount: number
  onlineCount: number
  activeAlarmCount: number
}

export interface IdcCompare {
  centers: IdcCompareItem[]
  currentIdcId: number | null
}

export interface IdcAlarm {
  idcId: number
  idcName: string
  idcCode: string
  alarmId?: string
  deviceId?: string
  category?: string
  metricName?: string
  level?: string
  value?: number
  unit?: string
  desc?: string
  state?: string
  ts?: number
}

export interface IdcAlarmResp {
  total: number
  items: IdcAlarm[]
  byIdc: Record<string, number>
}

export interface IdcRelatedService {
  key: string
  name: string
  deviceCount: number
  onlineCount: number
  alarmCount: number
}

export interface IdcServicesResp {
  idcId: number
  idcName: string
  services: IdcRelatedService[]
  totalDevices: number
  onlineDevices: number
}

export interface IdcOpLog {
  id: number
  ts: string
  action: string
  target: string
  operator: string
  detail: string
}

export interface IdcOpLogsResp {
  total: number
  items: IdcOpLog[]
}

export interface IdcBatchDeleteResp {
  deleted: number
  skipped: number[]
}

export interface IdcToggleStatusResp {
  id: number
  status: string
  isCurrent: boolean
}

export const listIdcs = (params: { region?: string; status?: string } = {}) =>
  request.get<unknown, Idc[]>('/api/idc', { params })

export const getCurrentIdc = () => request.get<unknown, Idc>('/api/idc/current')

export const setIdcCurrent = (id: number) =>
  request.put<unknown, Idc>(`/api/idc/current?idcId=${id}`, {})

export const compareIdcs = () => request.get<unknown, IdcCompare>('/api/idc/compare')

export const unifiedAlarms = () => request.get<unknown, IdcAlarmResp>('/api/idc/alarms')

export const createIdc = (data: IdcCreate) =>
  request.post<unknown, Idc>('/api/idc', data)

export const updateIdc = (id: number, data: Partial<IdcCreate>) =>
  request.put<unknown, Idc>(`/api/idc/${id}`, data)

export const deleteIdc = (id: number) => request.delete(`/api/idc/${id}`)

export const batchDeleteIdcs = (ids: number[]) =>
  request.post<unknown, IdcBatchDeleteResp>('/api/idc/batch-delete', { ids })

export const toggleIdcStatus = (id: number) =>
  request.put<unknown, IdcToggleStatusResp>(`/api/idc/${id}/toggle-status`, {})

export const getIdcServices = (id: number) =>
  request.get<unknown, IdcServicesResp>(`/api/idc/${id}/services`)

export const getIdcOpLogs = (limit = 50) =>
  request.get<unknown, IdcOpLogsResp>('/api/idc/op-logs', { params: { limit } })
