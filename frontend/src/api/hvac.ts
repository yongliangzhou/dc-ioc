import request from './request'

// ---- 后端返回的真实结构 (与 generator chiller_plant / crac / liquid_cooling 对齐) ----
// chiller_plant(): { chillers:[{id,state,load,evapT,condT,...}], towers, pumps,... }
// crac():          { summary:{total,running,...}, units:[{id,state,supplyT,returnT,rh,...}], ... }
// liquid_cooling():{ primaryCDUs:[...], secondaryCDUs:[...], ... }

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

// ---- 字段映射: 后端原始结构 -> 前端卡片所需结构 ----

function mapChiller(raw: any): ChillerSummary {
  const list: any[] = raw?.chillers ?? []
  const devices: ChillerPlantView[] = list.map((d, i) => ({
    id: i + 1,
    code: d.id ?? `CH-${i + 1}`,
    name: d.id ?? `CH-${i + 1}`,
    roomName: '冷站',
    status: d.state === '运行' ? 'online' : d.state === '检修' ? 'fault' : 'standby',
    coolingCapacity: 3500,
    temperatureIn: Number(d.evapT) || 0,
    temperatureOut: Number(d.condT) || 0,
    loadPercent: Number(d.load) || 0,
    commissionedOn: null,
    healthScore: null,
  }))
  const online = devices.filter((d) => d.status === 'online').length
  const fault = devices.filter((d) => d.status === 'fault').length
  const avgLoad = devices.length ? devices.reduce((s, d) => s + d.loadPercent, 0) / devices.length : 0
  const avgIn = devices.length ? devices.reduce((s, d) => s + d.temperatureIn, 0) / devices.length : 0
  const avgOut = devices.length ? devices.reduce((s, d) => s + d.temperatureOut, 0) / devices.length : 0
  return { total: devices.length, online, avgLoadPercent: avgLoad, avgTemperatureIn: avgIn, avgTemperatureOut: avgOut, devices }
}

function mapCrac(raw: any): CracSummary {
  const list: any[] = raw?.units ?? []
  const devices: CracView[] = list.map((d, i) => ({
    id: i + 1,
    code: d.id ?? `CRAC-${i + 1}`,
    name: d.id ?? `CRAC-${i + 1}`,
    roomName: '包间',
    status: d.state === '运行' ? 'online' : d.state === '故障' ? 'fault' : 'standby',
    temperatureSetpoint: Number(d.setpoints?.supplyT) || Number(d.supplyT) || 0,
    temperatureIn: Number(d.supplyT) || 0,
    temperatureOut: Number(d.returnT) || 0,
    humidityIn: Number(d.supplyRh) || 0,
    humidityOut: Number(d.returnRh) || 0,
    fanSpeed: Number(d.fan) || Number(d.fanHz) || 0,
    commissionedOn: null,
    healthScore: null,
  }))
  const online = devices.filter((d) => d.status === 'online').length
  const avgTIn = devices.length ? devices.reduce((s, d) => s + d.temperatureIn, 0) / devices.length : 0
  const avgTOut = devices.length ? devices.reduce((s, d) => s + d.temperatureOut, 0) / devices.length : 0
  const avgH = devices.length ? devices.reduce((s, d) => s + d.humidityIn, 0) / devices.length : 0
  const avgFan = devices.length ? devices.reduce((s, d) => s + d.fanSpeed, 0) / devices.length : 0
  return { total: devices.length, online, avgTemperatureIn: avgTIn, avgTemperatureOut: avgTOut, avgHumidityIn: avgH, avgFanSpeed: avgFan, devices }
}

function mapLiquid(raw: any): LiquidCoolingSummary {
  const list: any[] = [...(raw?.primaryCDUs ?? []), ...(raw?.secondaryCDUs ?? [])]
  const devices: LiquidCoolingView[] = list.map((d, i) => ({
    id: i + 1,
    code: d.id ?? `CDU-${i + 1}`,
    name: d.name ?? d.id ?? `CDU-${i + 1}`,
    roomName: '液冷间',
    status: d.state === '运行' ? 'online' : d.state === '故障' ? 'fault' : 'standby',
    flowRate: Number(d.flowPri) || Number(d.flowSec) || 0,
    cdiTemperature: Number(d.priInTemp) || 0,
    cdoTemperature: Number(d.priOutTemp) || 0,
    temperatureInCelsius: Number(d.secInTemp) || 0,
    commissionedOn: null,
    healthScore: null,
  }))
  const online = devices.filter((d) => d.status === 'online').length
  const avgFlow = devices.length ? devices.reduce((s, d) => s + d.flowRate, 0) / devices.length : 0
  const avgCdi = devices.length ? devices.reduce((s, d) => s + d.cdiTemperature, 0) / devices.length : 0
  const avgCdo = devices.length ? devices.reduce((s, d) => s + d.cdoTemperature, 0) / devices.length : 0
  return { total: devices.length, online, avgFlowRate: avgFlow, avgCdiTemperature: avgCdi, avgCdoTemperature: avgCdo, devices }
}

// ---- API 调用 ----

function getChillerPlantRaw(): Promise<any> {
  return request.get('/api/hvac/chiller-plant')
}
function getCracRaw(): Promise<any> {
  return request.get('/api/hvac/crac')
}
function getLiquidCoolingRaw(): Promise<any> {
  return request.get('/api/hvac/liquid-cooling')
}

export function getHvacOverview(): Promise<HvacOverview> {
  return Promise.all([getChillerPlantRaw(), getCracRaw(), getLiquidCoolingRaw()]).then(
    ([chillerRaw, cracRaw, liquidRaw]) => {
      const chiller = mapChiller(chillerRaw)
      const crac = mapCrac(cracRaw)
      const liquidCooling = mapLiquid(liquidRaw)
      return {
        totalEquipment: chiller.total + crac.total + liquidCooling.total,
        onlineCount: chiller.online + crac.online + liquidCooling.online,
        faultCount: 0,
        warningCount: 0,
        chiller,
        crac,
        liquidCooling,
      }
    },
  )
}

export function getChillerPlant(): Promise<ChillerSummary> {
  return getChillerPlantRaw().then(mapChiller)
}

export function getCrac(): Promise<CracSummary> {
  return getCracRaw().then(mapCrac)
}

export function getLiquidCooling(): Promise<LiquidCoolingSummary> {
  return getLiquidCoolingRaw().then(mapLiquid)
}
