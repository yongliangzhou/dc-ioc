import request from './request'

// ---- 后端类型 (从 Java MonitorDtos 映射) ----

export interface PowerDeviceView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  voltage: number | null
  current: number | null
  powerKw: number | null
  loadPercent: number | null
  powerFactor: number | null
  fuelLevel: number | null
  fuelConsumption: number | null
  commissionedOn: string | null
  healthScore: number | null
}

export interface PowerSystemSummary {
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

export interface PowerOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  hv: PowerSystemSummary
  lv: PowerSystemSummary
  genset: PowerSystemSummary
  fuel: PowerSystemSummary
  battery: PowerSystemSummary
}

// ---- API 调用 ----

export function getPowerOverview(): Promise<PowerOverview> {
  return request.get('/api/monitor/power/overview')
}

export function getPowerHv(): Promise<PowerSystemSummary> {
  return request.get('/api/monitor/power/hv')
}

export function getPowerLv(): Promise<PowerSystemSummary> {
  return request.get('/api/monitor/power/lv')
}

export function getPowerGenset(): Promise<PowerSystemSummary> {
  return request.get('/api/monitor/power/genset')
}

export function getPowerFuel(): Promise<PowerSystemSummary> {
  return request.get('/api/monitor/power/fuel')
}

export function getPowerBattery(): Promise<PowerSystemSummary> {
  return request.get('/api/monitor/power/battery')
}
