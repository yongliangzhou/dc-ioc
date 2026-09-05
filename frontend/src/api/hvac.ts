import request from './request'

// ============================================================
//  派生指标计算 (COP / SHR)
//
//  这些指标后端只给到单机原始测点，聚合值此前缺失，
//  导致驾驶舱"冷源 COP""空调 SHR"两张卡永远显示 '--'。
//  在此统一派生，保证所有消费方拿到同一口径。
// ============================================================

/** 多台设备的加权/算术均值；无有效样本时返回 null（宁可显示"无数据"，也不填假值） */
function meanOf(values: number[]): number | null {
  const valid = values.filter((v) => Number.isFinite(v) && v > 0)
  if (!valid.length) return null
  return valid.reduce((a, b) => a + b, 0) / valid.length
}

/** 饱和水蒸气压 (Pa)，T 单位 ℃ —— Magnus 公式 */
function saturationVaporPressure(tC: number): number {
  return 610.78 * Math.exp((17.27 * tC) / (tC + 237.3))
}

/** 含湿量 (kg/kg 干空气) */
function humidityRatio(tC: number, rhPct: number, pPa = 101325): number {
  const pv = (rhPct / 100) * saturationVaporPressure(tC)
  return (0.622 * pv) / Math.max(1, pPa - pv)
}

/** 湿空气比焓 (kJ/kg 干空气) */
function enthalpy(tC: number, rhPct: number): number {
  const w = humidityRatio(tC, rhPct)
  return 1.006 * tC + w * (2501 + 1.86 * tC)
}

/**
 * 显热比 SHR = 显热负荷 / 总热负荷（ASHRAE 简化式）。
 * 由回风与送风的干球温度差、比焓差求得；
 * 数据不合理（无温升 / 无焓差 / 结果越界）时返回 null。
 */
export function shrOf(
  returnT: number,
  supplyT: number,
  returnRh: number,
  supplyRh: number,
): number | null {
  if (![returnT, supplyT, returnRh, supplyRh].every(Number.isFinite)) return null
  const dT = returnT - supplyT
  const dh = enthalpy(returnT, returnRh) - enthalpy(supplyT, supplyRh)
  if (dT <= 0 || dh <= 0.01) return null
  const shr = (1.006 * dT) / dh
  if (!Number.isFinite(shr) || shr <= 0 || shr > 1) return null
  return shr
}

// ============================================================
//  冷源系统 — 全量类型定义 (对齐 dc_ioc_data.chiller_plant)
// ============================================================

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

// ---- 新增：水系统设备 ----
export interface PumpView {
  code: string
  state: string
  hz: number
  kw: number
  flow: number
  inPressure: number // 入口压力 bar
  outPressure: number // 出口压力 bar
}

export interface TowerView {
  code: string
  state: string
  fanHz: number
  outTemp: number | string
}

export interface HexView {
  code: string
  state: string
  eff: number
  priIn: number | string
  priOut: number | string
  secIn: number | string
  secOut: number | string
}

export interface ValveView {
  code: string
  name: string
  position: number
  state: string
  type: string
}

export interface StorageTankView {
  level: number
  dischargeMin: number
  mode: string
  capacity: number
  topTemp: number
  botTemp: number
  flow: number
  power: number
}

export interface MakeupDeviceView {
  id: string
  state: string
  mode: string
  supplyPressure: number
  setpointPressure: number
  tankLevel: number
  waterTemp: number
  pumpHz: number
  makeupFlow: number
}

export interface BypassFilterView {
  id: string
  state: string
  mode: string
  flow: number
  inletPressure: number
  outletPressure: number
  diffPressure: number
  turbidity: number
  backwashInterval: number
  lastBackwash: string
  filterHealth: number
}

export interface PipePressureView {
  supplyHeader: number
  returnHeader: number
  secSupplyHeader: number
  secReturnHeader: number
  condenserSupply: number
  condenserReturn: number
  makeupSupply: number
  makeupReturn: number
}

// ---- 完整冷源摘要 ----
export interface ChillerSummary {
  // 系统总览
  mode: string
  supplyTemp: number
  returnTemp: number
  targetSupplyTemp: number
  flow: number
  coolingCap: number
  plr: number
  outdoorTemp: number
  outdoorRH: number
  wetBulb: number

  // 设备统计
  total: number
  online: number
  avgLoadPercent: number
  avgTemperatureIn: number
  avgTemperatureOut: number

  /**
   * 系统级 COP：运行中机组的平均性能系数（由单机 cop 派生）。
   * 注意：后端 chiller_plant() 只返回 chillers，没有 chillerGroups，
   * 所以 chillerGroups 恒为空 —— 早期驾驶舱从这里取 COP，导致永远算不出来。
   * 无有效样本时为 null，由调用方决定如何呈现。
   */
  systemCop: number | null

  // 各子系统
  chillers: ChillerPlantView[]
  towers: TowerView[]
  pumpsChw: PumpView[] // 一次冷冻水泵
  pumpsCw: PumpView[] // 冷却水泵
  pumpsSec: PumpView[] // 二次冷冻水泵
  hexs: HexView[]
  valves: ValveView[]
  storageTank: StorageTankView
  makeupDevice: MakeupDeviceView
  bypassFilter: BypassFilterView
  pipePressure: PipePressureView
  // 制冷机组×水泵×蓄冷罐分组
  chillerGroups: ChillerGroupView[]
}

// ---- 精密空调单机 ----
export interface CracView {
  id: number
  code: string
  name: string
  roomName: string
  type: string
  status: string

  // 送回风温度
  supplyT: number | string // 送风温度 °C
  returnT: number | string // 回风温度 °C
  supplyRh: number | string // 送风湿度 %
  returnRh: number | string // 回风湿度 %

  // 供回水水温
  chilledWaterT: number | string
  returnWaterT: number | string

  // 运行参数
  fanSpeed: number // 风机 %
  valve: number // 风阀开度 %
  waterValve: number // 水阀开度 %
  power: number // 功率 kW
  dp: number | string // 压差 Pa
  filter: string // 滤网状态

  /** 单机显热比，后端 dc_ioc_data.crac 直接提供；缺失时为 null（由 systemShr 走温湿度推导兜底） */
  shr: number | null

  // 控制点位
  fanEnable: boolean
  fanSpeedSet: number
  waterValveSet: number
  coolingMode: string
  humidOn: boolean

  // 整定值
  supplyTSet: number
  rhSet: number
  roomTSet: number
  highTempAlarm: number
  lowTempAlarm: number
  highRhAlarm: number

  commissionedOn: string | null
  healthScore: number | null
}

// ---- 包间环境 ----
export interface RoomView {
  id: string
  name: string
  avgTemp: number
  avgRh: number
  hotAisle: number // 热通道温度
  hotRh: number // 热通道湿度
  coldAisle: number // 冷通道温度
  coldRh: number // 冷通道湿度
  inOutDiff: number // 室内外压差
  dewPoint: number // 露点
  cracRun: number
  cracN: number
  state: string
  leak: { status: string; level: string; position: number | null; zone: number }
}

// ---- 定位式漏水检测 ----
export interface LeakDeviceView {
  id: string
  location: string
  zone: number
  status: string
  position: number | null
  cableLength: number
  cableStatus: string
}

// ---- 新风机组 ----
export interface FreshAirView {
  id: string
  state: string
  supplyT: number | string
  rh: number | string
  co2: number | string
  filterDp: number // 过滤器压差
}

// ---- 恒湿机 ----
export interface HumidifierView {
  id: string
  name: string
  state: string
  rh: number | string
  mode: string
}

// ---- 功能房间 ----
export interface FuncRoomView {
  id: string
  t: number
  rh: number
}

// ---- 控制策略 ----
export interface CracCtrlView {
  humId: { rhLowOn: number; rhHighOff: number; desc: string }
  positivePressure: { min: number; max: number; unit: string; desc: string }
  secPump: {
    diffTarget: number
    diffUnit: string
    addHz: number
    addDelayMin: number
    reduceHz: number
    reduceDelayMin: number
    minRun: number
    desc: string
  }
}

export interface CracSummary {
  // 汇总
  total: number
  online: number
  standby: number
  fault: number
  outdoorRef: number // 室外参考温度

  // 均值指标
  avgSupplyT: number
  avgReturnT: number
  avgSupplyWaterT: number
  avgReturnWaterT: number
  avgInOutDiff: number // 平均室内外压差

  // 漏水
  leakAlarm: number
  leakTotal: number

  // 子系统
  devices: CracView[]
  rooms: RoomView[]
  leakDevices: LeakDeviceView[]
  freshAir: FreshAirView[]
  humidifiers: HumidifierView[]
  funcRooms: FuncRoomView[]
  ctrl: CracCtrlView

  // backward compat (HvacDashboard)
  avgTemperatureIn: number
  avgTemperatureOut: number
  avgHumidityIn: number
  avgFanSpeed: number

  /**
   * 系统级显热比 SHR：运行机组的平均显热比。
   * 由送/回风干球温度与相对湿度按 ASHRAE 简化式派生（见 shrOf）。
   * 无有效样本时为 null。
   */
  systemShr: number | null
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

// ======== 液冷系统完整类型 ========

export interface LiquidCDUView {
  id: string
  name: string
  state: string
  heatExEff: number
  priInTemp: number
  priOutTemp: number
  secInTemp: number
  secOutTemp: number
  flowPri: number
  flowSec: number
  dpPri: number
  dpSec: number
  pumpSpeed: number
  pumpKw: number
  valve: number
  leakStatus: string
  runHrs: number
}

export interface LiquidSecCDUView {
  id: string
  name: string
  rackGroup: string
  state: string
  supplyTemp: number | string
  returnTemp: number | string
  flow: number
  dp: number
  pumpSpeed: number
  pumpKw: number
  leakStatus: string
  coldPlateCount: number
  coldPlateOnline: number
}

export interface ColdPlateGPUView {
  rackId: string
  nodeType: string
  inletTemp: number
  outletTemp: number
  flow: number
  dp: number
  gpuTemp: number[]
  state: string
}

export interface ManifoldNodeView {
  id: string
  zone: string
  temp: number
  pressure: number
  flow: number
  valvesOpen?: number
  branchCount?: number
}

export interface LeakRopeView {
  id: string
  location: string
  status: string
  length: number
  coverage: number
}

export interface LeakPointView {
  id: string
  zone: string
  count: number
  alarmCount: number
}

export interface CoolantQualityView {
  type: string
  conductivity: number
  ph: number
  corrosionInhibitor: number
  glycolConcentration: number
  particleCount: number
  lastTested: string
  nextTest: string
  status: string
}

export interface RejectionTowerView {
  id: string
  state: string
  fanHz: number
  outletTemp: number | string
  approach: number | string
}

export interface DryCoolerView {
  id: string
  state: string
  fanHz: number
  ambientT: number
}

export interface RejectionPumpView {
  id: string
  state: string
  hz: number
  kw: number
}

export interface HeatRecoveryView {
  enabled: boolean
  recoveryRate: number
  recoveryTemp: number
  returnTemp: number
  flow: number
  usageType: string
  co2Reduction: number
  annualSaving: number
}

export interface LiquidControlView {
  primarySupplySetpoint: number
  secondarySupplySetpoint: number
  approachTarget: number
  glycolMin: number
  conductivityMax: number
  leakResponseTime: number
  pumpRedundancy: string
  cdurRedundancy: string
  description: string
}

export interface LiquidCoolingSummary {
  // 全局 KPI
  systemMode: string
  outdoorT: number
  outdoorRH: number
  totalCoolingCap: number
  coolingCapUsed: number
  capRate: number

  // 一次侧
  primarySupplyTemp: number
  primaryReturnTemp: number
  primaryFlow: number
  primaryPressure: number

  // 二次侧
  secSupplyTemp: number
  secReturnTemp: number
  secFlow: number
  secPressure: number
  deltaT: number

  // 效率指标
  pueContribution: number
  freeCoolingHours: number
  heatRecoveryMW: number

  // 传统汇总
  total: number
  online: number
  avgFlowRate: number
  avgCdiTemperature: number
  avgCdoTemperature: number

  // 子系统
  devices: LiquidCoolingView[]
  primaryCDUs: LiquidCDUView[]
  secondaryCDUs: LiquidSecCDUView[]
  coldPlates: ColdPlateGPUView[]
  manifoldsSupply: ManifoldNodeView[]
  manifoldsReturn: ManifoldNodeView[]
  leakRope: LeakRopeView[]
  leakPoint: LeakPointView[]
  leakTotalSensors: number
  leakAlarmCount: number
  leakWarningCount: number
  coolantQuality: CoolantQualityView
  towerFans: RejectionTowerView[]
  dryCoolers: DryCoolerView[]
  rejectionPumps: RejectionPumpView[]
  totalHeatRejected: number
  approachTemp: number
  freeCoolingAvailable: boolean
  heatRecovery: HeatRecoveryView
  control: LiquidControlView
  supplyTrend: number[]
  returnTrend: number[]
  flowTrend: number[]
  deltaTTrend: number[]
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

// ============================================================
//  字段映射
// ============================================================

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 num()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

// 将 unknown 索引值收窄为 RawItem 数组 (后端数组字段)
function asRawList(v: unknown): RawItem[] {
  return Array.isArray(v) ? (v as RawItem[]) : []
}

function mapChiller(raw: RawItem): ChillerSummary {
  const list = asRawList(raw?.chillers)
  const devices: ChillerPlantView[] = list.map((d, i) => ({
    id: i + 1,
    code: String(d.id ?? `CH-${i + 1}`),
    name: String(d.id ?? `CH-${i + 1}`),
    roomName: '冷站',
    status: d.state === '运行' ? 'online' : d.state === '检修' ? 'fault' : 'standby',
    coolingCapacity: 3500,
    temperatureIn: Number(d.evapT) || 0,
    temperatureOut: Number(d.condT) || 0,
    loadPercent: Number(d.load) || 0,
    commissionedOn: null,
    healthScore: null,
  }))
  const chillerOnline = devices.filter((d) => d.status === 'online').length
  const avgLoad = devices.length
    ? devices.reduce((s, d) => s + d.loadPercent, 0) / devices.length
    : 0
  const avgIn = devices.length
    ? devices.reduce((s, d) => s + d.temperatureIn, 0) / devices.length
    : 0
  const avgOut = devices.length
    ? devices.reduce((s, d) => s + d.temperatureOut, 0) / devices.length
    : 0

  // 系统 COP: 只统计"运行中"的机组, 待机/检修机的 cop=0 会把它拉成假的低值
  const systemCop = meanOf(list.filter((d) => d.state === '运行').map((d) => Number(d.cop) || 0))

  // 泵组映射
  const mapPump = (p: RawItem): PumpView => ({
    code: String(p.id ?? ''),
    state: String(p.state ?? ''),
    hz: Number(p.hz) || 0,
    kw: Number(p.kw) || 0,
    flow: Number(p.flow) || 0,
    inPressure: Number(p.inP) || 0,
    outPressure: Number(p.outP) || 0,
  })
  const pumpsChw: PumpView[] = asRawList(raw?.pumps && (raw.pumps as RawItem).chw).map(mapPump)
  const pumpsCw: PumpView[] = asRawList(raw?.pumps && (raw.pumps as RawItem).cw).map(mapPump)
  const pumpsSec: PumpView[] = asRawList(raw?.pumps && (raw.pumps as RawItem).sec).map(mapPump)

  // 冷却塔映射
  const towers: TowerView[] = asRawList(raw?.towers).map((t) => ({
    code: String(t.id ?? ''),
    state: String(t.state ?? ''),
    fanHz: Number(t.fanHz) || 0,
    outTemp: t.outT === '-' ? '-' : Number(t.outT) || 0,
  }))

  // 板换映射
  const hexs: HexView[] = asRawList(raw?.hex).map((h) => ({
    code: String(h.id ?? ''),
    state: String(h.state ?? ''),
    eff: Number(h.eff) || 0,
    priIn: h.priIn === '-' ? '-' : Number(h.priIn) || 0,
    priOut: h.priOut === '-' ? '-' : Number(h.priOut) || 0,
    secIn: h.secIn === '-' ? '-' : Number(h.secIn) || 0,
    secOut: h.secOut === '-' ? '-' : Number(h.secOut) || 0,
  }))

  // 阀门映射
  const valves: ValveView[] = asRawList(raw?.valves).map((v) => ({
    code: String(v.id ?? ''),
    name: String(v.name ?? ''),
    position: Number(v.pos) || 0,
    state: String(v.state ?? ''),
    type: String(v.type ?? '电动阀'),
  }))

  // 蓄冷罐
  const st = (raw?.storageTank as RawItem) ?? {}
  const storageTank: StorageTankView = {
    level: Number(st.level) || 0,
    dischargeMin: Number(st.dischargeMin) || 0,
    mode: String(st.mode ?? ''),
    capacity: Number(st.capacity) || 0,
    topTemp: Number(st.topTemp) || 0,
    botTemp: Number(st.botTemp) || 0,
    flow: Number(st.flow) || 0,
    power: Number(st.power) || 0,
  }

  // 定压补水
  const mu = (raw?.makeupDevice as RawItem) ?? {}
  const makeupDevice: MakeupDeviceView = {
    id: String(mu.id ?? ''),
    state: String(mu.state ?? ''),
    mode: String(mu.mode ?? ''),
    supplyPressure: Number(mu.supplyP) || 0,
    setpointPressure: Number(mu.setpointP) || 0,
    tankLevel: Number(mu.tankLevel) || 0,
    waterTemp: Number(mu.waterTemp) || 0,
    pumpHz: Number(mu.pumpHz) || 0,
    makeupFlow: Number(mu.makeupFlow) || 0,
  }

  // 旁滤装置
  const bf = (raw?.bypassFilter as RawItem) ?? {}
  const bypassFilter: BypassFilterView = {
    id: String(bf.id ?? ''),
    state: String(bf.state ?? ''),
    mode: String(bf.mode ?? ''),
    flow: Number(bf.flow) || 0,
    inletPressure: Number(bf.inP) || 0,
    outletPressure: Number(bf.outP) || 0,
    diffPressure: Number(bf.diffP) || 0,
    turbidity: Number(bf.turbidity) || 0,
    backwashInterval: Number(bf.backwashInterval) || 0,
    lastBackwash: String(bf.lastBackwash ?? ''),
    filterHealth: Number(bf.filterHealth) || 0,
  }

  // 管路压力
  const pp = (raw?.pipePressure as RawItem) ?? {}
  const pipePressure: PipePressureView = {
    supplyHeader: Number(pp.supplyHeader) || 0,
    returnHeader: Number(pp.returnHeader) || 0,
    secSupplyHeader: Number(pp.secSupplyHeader) || 0,
    secReturnHeader: Number(pp.secReturnHeader) || 0,
    condenserSupply: Number(pp.condenserSupply) || 0,
    condenserReturn: Number(pp.condenserReturn) || 0,
    makeupSupply: Number(pp.makeupSupply) || 0,
    makeupReturn: Number(pp.makeupReturn) || 0,
  }

  const total =
    devices.length +
    towers.length +
    pumpsChw.length +
    pumpsCw.length +
    pumpsSec.length +
    hexs.length +
    valves.length +
    2 // makeup + bypass filter

  return {
    mode: String(raw?.mode ?? ''),
    supplyTemp: Number(raw?.supplyT) || 0,
    returnTemp: Number(raw?.returnT) || 0,
    targetSupplyTemp: Number(raw?.targetSupplyT) || 0,
    flow: Number(raw?.flow) || 0,
    coolingCap: Number(raw?.coolingCap) || 0,
    plr: Number(raw?.plr) || 0,
    outdoorTemp: Number(raw?.outdoorT) || 0,
    outdoorRH: Number(raw?.outdoorRH) || 0,
    wetBulb: Number(raw?.wetBulb) || 0,
    total,
    online: chillerOnline,
    avgLoadPercent: avgLoad,
    avgTemperatureIn: avgIn,
    avgTemperatureOut: avgOut,
    systemCop,
    chillers: devices,
    towers,
    pumpsChw,
    pumpsCw,
    pumpsSec,
    hexs,
    valves,
    storageTank,
    makeupDevice,
    bypassFilter,
    pipePressure,
    chillerGroups: asRawList(raw?.chillerGroups).map((g) => {
      const c = (g?.chiller as RawItem) ?? {}
      const chw = g?.chwPump as RawItem | undefined
      const cw = g?.cwPump as RawItem | undefined
      return {
        chiller: {
          id: String(c.id ?? ''),
          state: String(c.state ?? ''),
          load: Number(c.load) || 0,
          cop: Number(c.cop) || 0,
          evapT: (c.evapT as number | string) ?? '-',
          condT: (c.condT as number | string) ?? '-',
          current: Number(c.current) || 0,
          runHrs: Number(c.runHrs) || 0,
        },
        chwPump: chw
          ? {
              id: String(chw.id ?? ''),
              state: String(chw.state ?? ''),
              hz: Number(chw.hz) || 0,
              kw: Number(chw.kw) || 0,
              flow: Number(chw.flow) || 0,
              inP: Number(chw.inP) || 0,
              outP: Number(chw.outP) || 0,
            }
          : null,
        cwPump: cw
          ? {
              id: String(cw.id ?? ''),
              state: String(cw.state ?? ''),
              hz: Number(cw.hz) || 0,
              kw: Number(cw.kw) || 0,
              flow: Number(cw.flow) || 0,
              inP: Number(cw.inP) || 0,
              outP: Number(cw.outP) || 0,
            }
          : null,
        tankConnected: Boolean(g?.tankConnected),
        tankFlow: Number(g?.tankFlow) || 0,
      }
    }),
  }
}

function mapCrac(raw: RawItem): CracSummary {
  // ---- 精密空调机组 ----
  const list = asRawList(raw?.units)
  const devices: CracView[] = list.map((d, i) => ({
    id: i + 1,
    code: String(d.id ?? `CRAC-${i + 1}`),
    name: String(d.id ?? `CRAC-${i + 1}`),
    roomName: String(d.room ?? '包间'),
    type: String(d.type ?? '精密空调'),
    status: d.state === '运行' ? 'online' : d.state === '故障' ? 'fault' : 'standby',
    supplyT: d.supplyT === '-' ? '-' : Number(d.supplyT) || 0,
    returnT: d.returnT === '-' ? '-' : Number(d.returnT) || 0,
    supplyRh: d.supplyRh === '-' ? '-' : Number(d.supplyRh) || 0,
    returnRh: d.returnRh === '-' ? '-' : Number(d.returnRh) || 0,
    chilledWaterT: d.chilledWaterT === '-' ? '-' : Number(d.chilledWaterT) || 0,
    returnWaterT: d.returnWaterT === '-' ? '-' : Number(d.returnWaterT) || 0,
    fanSpeed: Number(d.fan) || 0,
    valve: Number(d.valve) || 0,
    waterValve: Number(d.waterValve) || 0,
    power: Number(d.power) || 0,
    dp: d.dp === '-' ? '-' : Number(d.dp) || 0,
    shr: d.shr === '-' || d.shr == null ? null : Number(d.shr) || null,
    filter: String(d.filter ?? '正常'),
    fanEnable: Boolean((d.control as RawItem | undefined)?.fanEnable ?? true),
    fanSpeedSet: Number((d.control as RawItem | undefined)?.fanSpeedSet) || 0,
    waterValveSet: Number((d.control as RawItem | undefined)?.waterValveSet) || 0,
    coolingMode: String((d.control as RawItem | undefined)?.coolingMode ?? '制冷'),
    humidOn: Boolean((d.control as RawItem | undefined)?.humidOn ?? false),
    supplyTSet: Number(d.setpoints && (d.setpoints as RawItem).supplyTSet) || 0,
    rhSet: Number(d.setpoints && (d.setpoints as RawItem).rhSet) || 0,
    roomTSet: Number(d.setpoints && (d.setpoints as RawItem).roomTSet) || 0,
    highTempAlarm: Number(d.setpoints && (d.setpoints as RawItem).highTempAlarm) || 0,
    lowTempAlarm: Number(d.setpoints && (d.setpoints as RawItem).lowTempAlarm) || 0,
    highRhAlarm: Number(d.setpoints && (d.setpoints as RawItem).highRhAlarm) || 0,
    commissionedOn: null,
    healthScore: null,
  }))

  const onlineCount = devices.filter((d) => d.status === 'online').length

  // 系统 SHR: 优先取后端单机 shr；缺失时按送/回风干球温度 + 相对湿度用 ASHRAE 简化式推导
  const systemShr = meanOf(
    devices
      .filter((d) => d.status === 'online')
      .map(
        (d) =>
          d.shr ??
          shrOf(Number(d.returnT), Number(d.supplyT), Number(d.returnRh), Number(d.supplyRh)),
      )
      .filter((v): v is number => v !== null),
  )

  // ---- 包间环境 ----
  const rooms: RoomView[] = asRawList(raw?.rooms).map((r) => ({
    id: String(r.id ?? ''),
    name: String(r.name ?? ''),
    avgTemp: Number(r.avgTemp) || 0,
    avgRh: Number(r.avgRh) || 0,
    hotAisle: Number(r.hotAisle) || 0,
    hotRh: Number(r.hotRh) || 0,
    coldAisle: Number(r.coldAisle) || 0,
    coldRh: Number(r.coldRh) || 0,
    inOutDiff: Number(r.inOutDiff) || 0,
    dewPoint: Number(r.dewPoint) || 0,
    cracRun: Number(r.cracRun) || 0,
    cracN: Number(r.cracN) || 0,
    state: String(r.state ?? '正常'),
    leak: (r.leak as RoomView['leak']) ?? {
      status: '正常',
      level: '正常',
      position: null,
      zone: 0,
    },
  }))

  // ---- 定位式漏水检测 ----
  const leakDevices: LeakDeviceView[] = asRawList(raw?.leak && (raw.leak as RawItem).devices).map(
    (l) => ({
      id: String(l.id ?? ''),
      location: String(l.location ?? ''),
      zone: Number(l.zone) || 0,
      status: String(l.status ?? '正常'),
      position: (l.position as number | null) ?? null,
      cableLength: Number(l.cableLength) || 0,
      cableStatus: String(l.cableStatus ?? '正常'),
    }),
  )

  // ---- 新风机组 ----
  const freshAir: FreshAirView[] = asRawList(raw?.fresh).map((f) => ({
    id: String(f.id ?? ''),
    state: String(f.state ?? ''),
    supplyT: f.supplyT === '-' ? '-' : Number(f.supplyT) || 0,
    rh: f.rh === '-' ? '-' : Number(f.rh) || 0,
    co2: f.co2 === '-' ? '-' : Number(f.co2) || 0,
    filterDp: Number(f.filterDp) || 0,
  }))

  // ---- 恒湿机 ----
  const humidifiers: HumidifierView[] = asRawList(raw?.humid).map((h) => ({
    id: String(h.id ?? ''),
    name: String(h.name ?? ''),
    state: String(h.state ?? ''),
    rh: h.rh === '-' ? '-' : Number(h.rh) || 0,
    mode: String(h.mode ?? ''),
  }))

  // ---- 功能房间 ----
  const funcRooms: FuncRoomView[] = asRawList(raw?.funcRooms).map((f) => ({
    id: String(f.id ?? ''),
    t: Number(f.t) || 0,
    rh: Number(f.rh) || 0,
  }))

  // ---- 控制策略 ----
  const ctrlRaw = (raw?.ctrl as RawItem) ?? {}
  const ctrl: CracCtrlView = {
    humId: (ctrlRaw.humId as CracCtrlView['humId']) ?? { rhLowOn: 30, rhHighOff: 65, desc: '' },
    positivePressure: (ctrlRaw.positivePressure as CracCtrlView['positivePressure']) ?? {
      min: 5,
      max: 10,
      unit: 'Pa',
      desc: '',
    },
    secPump: (ctrlRaw.secPump as CracCtrlView['secPump']) ?? {
      diffTarget: 0.1,
      diffUnit: 'MPa',
      addHz: 50,
      addDelayMin: 5,
      reduceHz: 35,
      reduceDelayMin: 5,
      minRun: 1,
      desc: '',
    },
  }

  const s = (raw?.summary as RawItem) ?? {}

  // backward compat: compute old dashboard fields from device list
  const dashAvgSupply = devices.length
    ? devices
        .filter((d) => typeof d.supplyT === 'number')
        .reduce((sum, d) => sum + Number(d.supplyT), 0) / devices.length
    : 0
  const dashAvgReturn = devices.length
    ? devices
        .filter((d) => typeof d.returnT === 'number')
        .reduce((sum, d) => sum + Number(d.returnT), 0) / devices.length
    : 0
  const dashAvgRh = devices.length
    ? devices
        .filter((d) => typeof d.supplyRh === 'number')
        .reduce((sum, d) => sum + Number(d.supplyRh), 0) / devices.length
    : 0
  const dashAvgFan = devices.length
    ? devices.reduce((sum, d) => sum + d.fanSpeed, 0) / devices.length
    : 0

  return {
    total: Number(s.total) || devices.length,
    online: onlineCount,
    standby: Number(s.standby) || 0,
    fault: Number(s.fault) || 0,
    outdoorRef: Number(s.outdoorRef) || 0,
    avgSupplyT: Number(s.avgSupply) || 0,
    avgReturnT: Number(s.avgReturn) || 0,
    avgSupplyWaterT: Number(s.avgSupplyWater) || 0,
    avgReturnWaterT: Number(s.avgReturnWater) || 0,
    avgInOutDiff: Number(s.avgInOutDiff) || 0,
    leakAlarm: Number(s.leakAlarm) || 0,
    leakTotal: Number(s.leakTotal) || leakDevices.length,
    devices,
    rooms,
    leakDevices,
    freshAir,
    humidifiers,
    funcRooms,
    ctrl,
    avgTemperatureIn: dashAvgReturn,
    avgTemperatureOut: dashAvgSupply,
    avgHumidityIn: dashAvgRh,
    avgFanSpeed: dashAvgFan,
    systemShr,
  }
}

function mapLiquid(raw: RawItem): LiquidCoolingSummary {
  // 传统 device 列表 (一次 + 二次 CDU 扁平化为兼容视图)
  const list = [...asRawList(raw?.primaryCDUs), ...asRawList(raw?.secondaryCDUs)]
  const devices: LiquidCoolingView[] = list.map((d, i) => ({
    id: i + 1,
    code: String(d.id ?? `CDU-${i + 1}`),
    name: String(d.name ?? d.id ?? `CDU-${i + 1}`),
    roomName: String(d.rackGroup ?? d.id ?? '液冷间'),
    status: d.state === '运行' ? 'online' : d.state === '故障' ? 'fault' : 'standby',
    flowRate: Number(d.flowPri) || Number(d.flowSec) || Number(d.flow) || 0,
    cdiTemperature: Number(d.priInTemp) || Number(d.secInTemp) || Number(d.supplyTemp) || 0,
    cdoTemperature: Number(d.priOutTemp) || Number(d.secOutTemp) || Number(d.returnTemp) || 0,
    temperatureInCelsius: Number(d.secInTemp) || Number(d.supplyTemp) || 0,
    commissionedOn: null,
    healthScore: null,
  }))
  const online = devices.filter((d) => d.status === 'online').length
  const avgFlow = devices.length ? devices.reduce((s, d) => s + d.flowRate, 0) / devices.length : 0
  const avgCdi = devices.length
    ? devices.reduce((s, d) => s + d.cdiTemperature, 0) / devices.length
    : 0
  const avgCdo = devices.length
    ? devices.reduce((s, d) => s + d.cdoTemperature, 0) / devices.length
    : 0

  // 一次侧 CDU
  const primaryCDUs: LiquidCDUView[] = asRawList(raw?.primaryCDUs).map((d) => ({
    id: String(d.id ?? ''),
    name: String(d.name ?? ''),
    state: String(d.state ?? ''),
    heatExEff: Number(d.heatExEff) || 0,
    priInTemp: Number(d.priInTemp) || 0,
    priOutTemp: Number(d.priOutTemp) || 0,
    secInTemp: Number(d.secInTemp) || 0,
    secOutTemp: Number(d.secOutTemp) || 0,
    flowPri: Number(d.flowPri) || 0,
    flowSec: Number(d.flowSec) || 0,
    dpPri: Number(d.dpPri) || 0,
    dpSec: Number(d.dpSec) || 0,
    pumpSpeed: Number(d.pumpSpeed) || 0,
    pumpKw: Number(d.pumpKw) || 0,
    valve: Number(d.valve) || 0,
    leakStatus: String(d.leakStatus ?? '正常'),
    runHrs: Number(d.runHrs) || 0,
  }))

  // 二次侧 CDU
  const secondaryCDUs: LiquidSecCDUView[] = asRawList(raw?.secondaryCDUs).map((d) => ({
    id: String(d.id ?? ''),
    name: String(d.name ?? ''),
    rackGroup: String(d.rackGroup ?? ''),
    state: String(d.state ?? ''),
    supplyTemp: d.supplyTemp === '-' ? '-' : Number(d.supplyTemp) || 0,
    returnTemp: d.returnTemp === '-' ? '-' : Number(d.returnTemp) || 0,
    flow: Number(d.flow) || 0,
    dp: Number(d.dp) || 0,
    pumpSpeed: Number(d.pumpSpeed) || 0,
    pumpKw: Number(d.pumpKw) || 0,
    leakStatus: String(d.leakStatus ?? '正常'),
    coldPlateCount: Number(d.coldPlateCount) || 0,
    coldPlateOnline: Number(d.coldPlateOnline) || 0,
  }))

  // 冷板 GPU 温度
  const coldPlates: ColdPlateGPUView[] = asRawList(raw?.coldPlateMonitoring).map((p) => ({
    rackId: String(p.rackId ?? ''),
    nodeType: String(p.nodeType ?? ''),
    inletTemp: Number(p.inletTemp) || 0,
    outletTemp: Number(p.outletTemp) || 0,
    flow: Number(p.flow) || 0,
    dp: Number(p.dp) || 0,
    gpuTemp: asRawList(p.gpuTemp).map((t) => Number(t) || 0),
    state: String(p.state ?? '正常'),
  }))

  // 分集液管路
  const manifoldsSupply: ManifoldNodeView[] = asRawList(
    raw?.manifolds && (raw.manifolds as RawItem).supply,
  ).map((m) => ({
    id: String(m.id ?? ''),
    zone: String(m.zone ?? ''),
    temp: Number(m.temp) || 0,
    pressure: Number(m.pressure) || 0,
    flow: Number(m.flow) || 0,
    valvesOpen: (m.valvesOpen as number | undefined) ?? undefined,
    branchCount: (m.branchCount as number | undefined) ?? undefined,
  }))
  const manifoldsReturn: ManifoldNodeView[] = asRawList(
    raw?.manifolds && (raw.manifolds as RawItem).return,
  ).map((m) => ({
    id: String(m.id ?? ''),
    zone: String(m.zone ?? ''),
    temp: Number(m.temp) || 0,
    pressure: Number(m.pressure) || 0,
    flow: Number(m.flow) || 0,
  }))

  // 漏液检测
  const ld = (raw?.leakDetection as RawItem) ?? {}
  const leakRope: LeakRopeView[] = asRawList(ld.ropeLeak).map((lr) => ({
    id: String(lr.id ?? ''),
    location: String(lr.location ?? ''),
    status: String(lr.status ?? '正常'),
    length: Number(lr.length) || 0,
    coverage: Number(lr.coverage) || 0,
  }))
  const leakPoint: LeakPointView[] = asRawList(ld.pointLeak).map((lp) => ({
    id: String(lp.id ?? ''),
    zone: String(lp.zone ?? ''),
    count: Number(lp.count) || 0,
    alarmCount: Number(lp.alarmCount) || 0,
  }))

  // 冷却液品质
  const cq = (raw?.coolantQuality as RawItem) ?? {}
  const coolantQuality: CoolantQualityView = {
    type: String(cq.type ?? ''),
    conductivity: Number(cq.conductivity) || 0,
    ph: Number(cq.ph) || 0,
    corrosionInhibitor: Number(cq.corrosionInhibitor) || 0,
    glycolConcentration: Number(cq.glycolConcentration) || 0,
    particleCount: Number(cq.particleCount) || 0,
    lastTested: String(cq.lastTested ?? ''),
    nextTest: String(cq.nextTest ?? ''),
    status: String(cq.status ?? '正常'),
  }

  // 热排放
  const hr = (raw?.heatRejection as RawItem) ?? {}
  const towerFans: RejectionTowerView[] = asRawList(hr.towerFans).map((f) => ({
    id: String(f.id ?? ''),
    state: String(f.state ?? ''),
    fanHz: Number(f.fanHz) || 0,
    outletTemp: f.outletTemp === '-' ? '-' : Number(f.outletTemp) || 0,
    approach: f.approach === '-' ? '-' : Number(f.approach) || 0,
  }))
  const dryCoolers: DryCoolerView[] = asRawList(hr.dryCoolers).map((dc) => ({
    id: String(dc.id ?? ''),
    state: String(dc.state ?? ''),
    fanHz: Number(dc.fanHz) || 0,
    ambientT: Number(dc.ambientT) || 0,
  }))
  const rejectionPumps: RejectionPumpView[] = asRawList(hr.rejectionPumps).map((rp) => ({
    id: String(rp.id ?? ''),
    state: String(rp.state ?? ''),
    hz: Number(rp.hz) || 0,
    kw: Number(rp.kw) || 0,
  }))

  // 余热回收
  const rh = (raw?.heatRecoveryDetail as RawItem) ?? {}
  const heatRecovery: HeatRecoveryView = {
    enabled: Boolean(rh.enabled ?? false),
    recoveryRate: Number(rh.recoveryRate) || 0,
    recoveryTemp: Number(rh.recoveryTemp) || 0,
    returnTemp: Number(rh.returnTemp) || 0,
    flow: Number(rh.flow) || 0,
    usageType: String(rh.usageType ?? ''),
    co2Reduction: Number(rh.co2Reduction) || 0,
    annualSaving: Number(rh.annualSaving) || 0,
  }

  // 控制策略
  const cs = (raw?.controlStrategy as RawItem) ?? {}
  const control: LiquidControlView = {
    primarySupplySetpoint: Number(cs.primarySupplySetpoint) || 0,
    secondarySupplySetpoint: Number(cs.secondarySupplySetpoint) || 0,
    approachTarget: Number(cs.approachTarget) || 0,
    glycolMin: Number(cs.glycolMin) || 0,
    conductivityMax: Number(cs.conductivityMax) || 0,
    leakResponseTime: Number(cs.leakResponseTime) || 0,
    pumpRedundancy: String(cs.pumpRedundancy ?? ''),
    cdurRedundancy: String(cs.cdurRedundancy ?? ''),
    description: String(cs.description ?? ''),
  }

  return {
    systemMode: String(raw?.systemMode ?? ''),
    outdoorT: Number(raw?.outdoorT) || 0,
    outdoorRH: Number(raw?.outdoorRH) || 0,
    totalCoolingCap: Number(raw?.totalCoolingCap) || 0,
    coolingCapUsed: Number(raw?.coolingCapUsed) || 0,
    capRate: Number(raw?.capRate) || 0,
    primarySupplyTemp: Number(raw?.supplyTemp) || 0,
    primaryReturnTemp: Number(raw?.returnTemp) || 0,
    primaryFlow: Number(raw?.primaryFlow) || 0,
    primaryPressure: Number(raw?.primaryPressure) || 0,
    secSupplyTemp: Number(raw?.secSupplyTemp) || 0,
    secReturnTemp: Number(raw?.secReturnTemp) || 0,
    secFlow: Number(raw?.secFlow) || 0,
    secPressure: Number(raw?.secPressure) || 0,
    deltaT: Number(raw?.deltaT) || 0,
    pueContribution: Number(raw?.pueContribution) || 0,
    freeCoolingHours: Number(raw?.freeCoolingHours) || 0,
    heatRecoveryMW: Number(raw?.heatRecovery) || 0,
    total: devices.length,
    online,
    avgFlowRate: avgFlow,
    avgCdiTemperature: avgCdi,
    avgCdoTemperature: avgCdo,
    devices,
    primaryCDUs,
    secondaryCDUs,
    coldPlates,
    manifoldsSupply,
    manifoldsReturn,
    leakRope,
    leakPoint,
    leakTotalSensors: Number(ld.totalSensors) || 0,
    leakAlarmCount: Number(ld.alarmCount) || 0,
    leakWarningCount: Number(ld.warningCount) || 0,
    coolantQuality,
    towerFans,
    dryCoolers,
    rejectionPumps,
    totalHeatRejected: Number(hr.totalHeatRejected) || 0,
    approachTemp: Number(hr.approachTemp) || 0,
    freeCoolingAvailable: Boolean(hr.freeCoolingAvailable ?? false),
    heatRecovery,
    control,
    supplyTrend: asRawList(raw?.supplyTempTrend).map((t) => Number(t)),
    returnTrend: asRawList(raw?.returnTempTrend).map((t) => Number(t)),
    flowTrend: asRawList(raw?.flowTrend).map((t) => Number(t)),
    deltaTTrend: asRawList(raw?.deltaTTrend).map((t) => Number(t)),
  }
}

// ============================================================
//  API 调用
// ============================================================

function getChillerPlantRaw(): Promise<RawItem> {
  return request.get<unknown, RawItem>('/api/hvac/chiller-plant')
}
function getCracRaw(): Promise<RawItem> {
  return request.get<unknown, RawItem>('/api/hvac/crac')
}
function getLiquidCoolingRaw(): Promise<RawItem> {
  return request.get<unknown, RawItem>('/api/hvac/liquid-cooling')
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
        faultCount: crac.fault,
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

// ---- D6: 冷机机组控制指令 (后端已落地 /chiller-control) ----
export interface ChillerControlResult {
  status: string
  chiller_id: string
  action: string
  value: number | null
  operator: string
  accepted_at: string
  log_id: number
}

export function controlChiller(
  chillerId: string,
  action: 'start' | 'stop' | 'mode' | 'temp',
  value?: number,
): Promise<ChillerControlResult> {
  return request.post<unknown, ChillerControlResult>('/api/hvac/chiller-control', {
    chiller_id: chillerId,
    action,
    value,
  })
}

export function getCrac(): Promise<CracSummary> {
  return getCracRaw().then(mapCrac)
}

export function getLiquidCooling(): Promise<LiquidCoolingSummary> {
  return getLiquidCoolingRaw().then(mapLiquid)
}

// ============================================================
//  冷源趋势数据 & 机组分组
// ============================================================

export interface ChillerGroupView {
  chiller: {
    id: string
    state: string
    load: number
    cop: number
    evapT: number | string
    condT: number | string
    current: number
    runHrs: number
  }
  chwPump: {
    id: string
    state: string
    hz: number
    kw: number
    flow: number
    inP: number
    outP: number
  } | null
  cwPump: {
    id: string
    state: string
    hz: number
    kw: number
    flow: number
    inP: number
    outP: number
  } | null
  tankConnected: boolean
  tankFlow: number
}

export interface FreezeTrendItem {
  timestamps: string[]
  supplyTemp: number[]
  wetBulb: number[]
  loadPct: number[]
}

export interface CopRlaPoint {
  chiller: string
  rla: number
  cop: number
  ts: string
}

export interface CondCoolDiffItem {
  timestamps: string[]
  condTemp: number[]
  coolTemp: number[]
  diff: number[]
}

export interface PumpFreqFlowItem {
  chwPump: { hz: number; flow: number }[]
  cwPump: { hz: number; flow: number }[]
}

export interface TankGradientItem {
  timestamps: string[]
  levels: string[]
  data: number[][] // [level][time]
}

export interface CoolingFreecoolingMonthly {
  days: string[]
  coolingLoad: number[]
  freeCoolingPct: number[]
  unit: string
}

export interface DeltaTBypass1h {
  timestamps: string[]
  deltaT: number[]
  bypassValve: number[]
  deltaTDesign: number
  bypassHighAlarm: number
}

export interface ChillerTrends {
  freezeTrend: Record<string, FreezeTrendItem>
  copRlaScatter: Record<string, CopRlaPoint[]>
  condCoolDiff: Record<string, CondCoolDiffItem>
  pumpFreqFlow: Record<string, PumpFreqFlowItem>
  tankGradient: Record<string, TankGradientItem>
  coolingFreecoolingMonthly: CoolingFreecoolingMonthly
  deltaTBypass1h: DeltaTBypass1h
}

export function getChillerTrends(): Promise<ChillerTrends> {
  return request
    .get<unknown, RawItem>('/api/hvac/chiller-trends')
    .then((r) => r as unknown as ChillerTrends)
}

// ============================================================
//  空调末端 按包间分组视图
// ============================================================

export interface CracEnvSensors {
  avgTemp: number
  avgRh: number
  hotAisleTemp: number
  hotAisleRh: number
  coldAisleTemp: number
  coldAisleRh: number
  dewPoint: number
  inOutDiff: number
  supplyStaticPressure: number // Pa 架空地板下静压
}

export interface CracRoomGroupView {
  roomId: string
  roomName: string
  status: string
  cracRun: number
  cracN: number
  envSensors: CracEnvSensors
  roomCracs: CracView[]
  inRowCracs: CracView[]
  fau: FreshAirView | null
  humidifier: HumidifierView | null
  leak: { status: string; level: string; position: number | null; zone: number }
}

export function mapCracRoomGroups(summary: CracSummary): CracRoomGroupView[] {
  // 真实数据源: 已映射的 CracSummary.rooms (包间环境) + .devices (按 roomName 归集到每间)。
  // 旧实现读取后端原始 raw.roomGroups, 但当前后端契约 (见 mapCrac) 已扁平为 rooms/units,
  // 不存在 roomGroups 字段 —— 旧实现恒返回 [], 导致机房热力图与"包间设备归集"长期空白。
  // 注意: 当前扁平模型未提供逐间 FAU / 恒湿机 / 列间空调关联。
  // 方案 2: 若全场仅单台 FAU / 单台恒湿机 (全局唯一), 作为兜底挂到各包间透出;
  // 多台则不归属 (置 null), 避免把 A 间设备误标到 B 间。inRowCracs 始终置 [] (无列间数据)。
  // 调用方 slot 均以 v-if 保护, 不会访问 null 而崩溃。
  const globalFau = summary.freshAir.length === 1 ? summary.freshAir[0] : null
  const globalHum = summary.humidifiers.length === 1 ? summary.humidifiers[0] : null
  return summary.rooms.map((room) => ({
    roomId: room.id,
    roomName: room.name,
    status: room.state,
    cracRun: room.cracRun,
    cracN: room.cracN,
    envSensors: {
      avgTemp: room.avgTemp,
      avgRh: room.avgRh,
      hotAisleTemp: room.hotAisle,
      hotAisleRh: room.hotRh,
      coldAisleTemp: room.coldAisle,
      coldAisleRh: room.coldRh,
      dewPoint: room.dewPoint,
      inOutDiff: room.inOutDiff,
      supplyStaticPressure: 0,
    },
    roomCracs: summary.devices.filter((d) => d.roomName === room.name),
    inRowCracs: [],
    fau: globalFau,
    humidifier: globalHum,
    leak: room.leak,
  }))
}

// ============================================================
//  空调末端趋势诊断 (7类趋势图)
// ============================================================

export interface DeltaTIntegralSeries {
  unitId: string
  label: string
  data: number[]
}

export interface DeltaTIntegralRoom {
  roomId: string
  roomName: string
  series: DeltaTIntegralSeries[]
}

export interface FilterDpPoint {
  date: string
  value: number
}

export interface FilterDpUnit {
  unitId: string
  label: string
  roomName: string
  raw: FilterDpPoint[]
  slope: FilterDpPoint[]
  trend: string
}

export interface ShrWeeklyPoint {
  week: string
  value: number
}

export interface ShrTrendUnit {
  unitId: string
  label: string
  roomName: string
  data: ShrWeeklyPoint[]
}

export interface SupplyVsCabinetPeriod {
  timestamps: string[]
  supplyTemp: number[]
  cabinetInletTemp: number[]
  deltaT: number[]
}

export interface SupplyVsCabinetRoom {
  roomId: string
  roomName: string
  periods: Record<string, SupplyVsCabinetPeriod>
}

export interface DailyCorr {
  day: string
  correlation: number
  bestLag: number
}

export interface FanStaticUnit {
  unitId: string
  label: string
  roomName: string
  timestamps: string[]
  fanSpeed: number[]
  staticPressure: number[]
  dailyCorrelation: DailyCorr[]
}

export interface ValveDtUnit {
  unitId: string
  label: string
  roomName: string
  timestamps: string[]
  valveOpening: number[]
  waterDeltaT: number[]
}

export interface SuperheatUnit {
  unitId: string
  label: string
  roomName: string
  timestamps: string[]
  suctionSuperheat: number[]
  dischargeSuperheat: number[]
}

export interface CracTrends {
  deltaTIntegral: { title: string; unit: string; period: string; rooms: DeltaTIntegralRoom[] }
  filterDpSlope: { title: string; unit: string; period: string; units: FilterDpUnit[] }
  shrTrend: { title: string; unit: string; period: string; units: ShrTrendUnit[] }
  supplyVsCabinet: { title: string; unit: string; periods: string[]; rooms: SupplyVsCabinetRoom[] }
  fanVsStaticPressure: { title: string; unit: string; period: string; units: FanStaticUnit[] }
  valveDeltaT: { title: string; unit: string; period: string; units: ValveDtUnit[] }
  superheatTrend: { title: string; unit: string; period: string; units: SuperheatUnit[] }
}

export function getCracTrends(): Promise<CracTrends> {
  return request
    .get<unknown, RawItem>('/api/hvac/crac-trends')
    .then((r) => r as unknown as CracTrends)
}
