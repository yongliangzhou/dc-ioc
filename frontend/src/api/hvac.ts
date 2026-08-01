import request from './request'

// ---- 后端类型 (从 Java MonitorDtos 映射) ----

export interface ChillerPlantView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  coolingCapacity: number
  temperatureIn: number
  temperatureOut: number
  loadPercent: number
  commissionedOn: string | null
  healthScore: number | null
}

export interface CracView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  temperatureSetpoint: number
  temperatureIn: number
  temperatureOut: number
  humidityIn: number
  humidityOut: number
  fanSpeed: number
  commissionedOn: string | null
  healthScore: number | null
}

export interface LiquidCoolingView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  flowRate: number
  cdiTemperature: number
  cdoTemperature: number
  temperatureInCelsius: number
  commissionedOn: string | null
  healthScore: number | null
}

export interface ChillerSummary {
  total: number
  online: number
  avgLoadPercent: number
  avgTemperatureIn: number
  avgTemperatureOut: number
  devices: ChillerPlantView[]
}

export interface CracSummary {
  total: number
  online: number
  avgTemperatureIn: number
  avgTemperatureOut: number
  avgHumidityIn: number
  avgFanSpeed: number
  devices: CracView[]
}

export interface LiquidCoolingSummary {
  total: number
  online: number
  avgFlowRate: number
  avgCdiTemperature: number
  avgCdoTemperature: number
  devices: LiquidCoolingView[]
}

export interface HvacOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  chiller: ChillerSummary
  crac: CracSummary
  liquidCooling: LiquidCoolingSummary
}

// ---- API 调用 ----

export function getHvacOverview(): Promise<HvacOverview> {
  return Promise.all([getChillerPlant(), getCrac(), getLiquidCooling()]).then(
    ([chiller, crac, liquidCooling]) => ({
      totalEquipment: chiller.total + crac.total + liquidCooling.total,
      onlineCount: chiller.online + crac.online + liquidCooling.online,
      faultCount: 0,
      warningCount: 0,
      chiller,
      crac,
      liquidCooling,
    }),
  )
}

export function getChillerPlant(): Promise<ChillerSummary> {
  return request.get('/api/hvac/chiller-plant')
}

export function getCrac(): Promise<CracSummary> {
  return request.get('/api/hvac/crac')
}

export function getLiquidCooling(): Promise<LiquidCoolingSummary> {
  return request.get('/api/hvac/liquid-cooling')
}
