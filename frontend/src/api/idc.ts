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
