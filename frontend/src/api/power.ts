import request from './request'

// ---- 后端返回的真实结构 (与 generator hv / lv / genset / fuel / battery 对齐) ----
// hv():      { incomers:[{id,src,state,u,i,p,pf,...}], feeders:[...], transformers:[{id,state,load,uLow,...}], ... }
// lv():      { transformers:[{id,state,load,u,i,p,...}], upsGroups:[...], hvdc:[...], branches:[{id,name,loadPct,u,p,...}], ... }
// genset():  { units:[{id,state,u,i,p,rpm,...}], busState, ... }
// fuel():    { mainTanks:[{id,cap,level,t,...}], dayTanks:[...], pumps:[{id,state,mode,...}], ... }
// battery(): { groups:[{id,type,soc,u,i,state,maxT,...}], ... }

export interface PowerDeviceView {
    /** 设备唯一标识，使用后端返回的 device_id 或自定义 code */
    id: string
    /** 兼容旧字段，保留 code 与 id 相同 */
    code: string
    name: string
    /** 机房/区域名称 */
    roomName: string
    /** 新增字段：机房/区域 */
    room: string
    /** 设备编号（在同一机房内的顺序） */
    no: number
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

// ==================== 10KV 中压配电详细类型 ====================

export interface HvIncomerView {
  id: string
  src: string
  state: string
  breaker: string
  ua: number
  ub: number
  uc: number
  u: number
  ia: number
  ib: number
  ic: number
  i: number
  p: number
  q: number
  pf: number
  freq: number
  energy: number
}

export interface HvBusTieView {
  id: string
  state: string
  autoSwitch: string
  mode: string
  iRated: number
  i: number
}

export interface HvBusSectionView {
  id: string
  u: number
  freq: number
  state: string
}

export interface HvAtsView {
  logic: string
  lastTest: string
  switchTime: string
}

export interface HvFeederView {
  id: string
  load: string
  state: string
  breaker: string
  ua: number
  ub: number
  uc: number
  ia: number
  ib: number
  ic: number
  i: number
  p: number
  pf: number
  energy: number
}

export interface HvTransformerSignalView {
  name: string
  value: string
  level: string
}

export interface HvTransformerView {
  id: string
  feeder: string
  state: string
  load: number
  uHigh: number
  iHigh: number
  uLow: number
  iLow: number
  windingT: number
  oilT: number
  ambT: number
  humidity: number
  tap: number
  fan: string
  signals: HvTransformerSignalView[]
}

export interface HvDcPanelAlarmView {
  name: string
  value: string
  level: string
}

export interface HvDcPanelView {
  id: string
  dcBus: number
  dcBusTarget: number
  batteryBank: number
  chargeI: number
  dischargeI: number
  insulationR: number
  ripple: number
  state: string
  alarms: HvDcPanelAlarmView[]
}

export interface HvSwitchgearRowView {
  id: string
  t: number
  h: number
  tev: number
  us: number
  state: string
}

export interface HvSwitchgearEnvView {
  rows: HvSwitchgearRowView[]
  note: string
}

export interface HvProtectionRelayView {
  id: string
  device: string
  state: string
  overcurrent: string
  earthFault: string
  diff: string
  underVoltage: string
  overVoltage: string
  freq: string
  lastTrip: string
  tripCount: number
  comm: string
}

export interface HvArcSuppressionView {
  mode: string
  coilCurrent: number
  coilPosition: number
  neutralV: number
  earthCapacitance: number
  residualCurrent: number
  state: string
  groundingTx: {
    id: string
    state: string
    t: number
    i: number
  }
}

export interface HvMeteringIncomerView {
  energyTotal: number
  energyPeak: number
  energyValley: number
  energyFlat: number
  demand: number
  demandMax: number
}

export interface HvMeteringView {
  incomer1: HvMeteringIncomerView
  incomer2: HvMeteringIncomerView
}

export interface HvQualityDetailView {
  thdU: number
  thdI: number
  unbalance: number
  flicker?: number
}

export interface HvQualityView {
  thdU: number
  thdI: number
  unbalance: number
  incomer1?: HvQualityDetailView
  incomer2?: HvQualityDetailView
}

export interface HvKnowledgeThreshold {
  k: string
  v: string
  note?: string
}

export interface HvKnowledgeArch {
  components: string[]
  design: string
  redundancy: string
}

export interface HvKnowledgeLogicStep {
  step: number
  text: string
  ok?: boolean
}

export interface HvKnowledgeLogic {
  title: string
  steps: HvKnowledgeLogicStep[]
}

export interface HvKnowledgeFault {
  no: number
  fault: string
  lock: string
  action: string
  manualReset: boolean
}

export interface HvKnowledgeView {
  thresholds: HvKnowledgeThreshold[]
  arch?: HvKnowledgeArch
  logic?: HvKnowledgeLogic[]
  faults?: HvKnowledgeFault[]
  note?: string
}

export interface HvSummary {
  scheme: string
  incomers: HvIncomerView[]
  busTie: HvBusTieView
  busSections: HvBusSectionView[]
  ats: HvAtsView
  feeders: HvFeederView[]
  transformers: HvTransformerView[]
  dcPanel: HvDcPanelView
  switchgearEnv: HvSwitchgearEnvView
  protectionRelays: HvProtectionRelayView[]
  arcSuppression: HvArcSuppressionView
  metering: HvMeteringView
  quality: HvQualityView
  knowledge: HvKnowledgeView
  // 向后兼容概览字段
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

// ==================== 0.4KV 低压配电详细类型 ====================

export interface LvTransformerView {
  id: string
  load: number
  t: number
  state: string
  u: number
  i: number
  p: number
  q: number
  pf: number
  freq: number
  energy: number
  thdu: number
  thdi: number
}

export interface LvUpsGroupView {
  id: string
  n: string
  load: number
  uIn: number
  uOut: number
  mode: string
  bypass: string
  state: string
  iIn: number
  iOut: number
  p: number
  pf: number
  freq: number
  energyIn: number
  thdu: number
  thdi: number
}

export interface LvHvdcView {
  id: string
  u: number
  load: number
  modN: number
  modRun: number
  state: string
  i: number
  p: number
  pf: number
  energy: number
  thdi: number
}

export interface LvAtsView {
  id: string
  state: string
  mode: string
  lastSw: string
  uIn: number
  uOut: number
  pf: number
  p: number
}

export interface LvBusbarView {
  id: string
  load: number
  i: number
  state: string
  u: number
  pf: number
  energy: number
  thdu: number
}

export interface LvBranchView {
  id: string
  name: string
  breaker: string
  rated: number
  ua: number
  ub: number
  uc: number
  u: number
  ia: number
  ib: number
  ic: number
  i: number
  freq: number
  p: number
  q: number
  pf: number
  energy: number
  thdu: number
  thdi: number
  loadPct: number
}

export interface LvSpdView {
  id: string
  state: string
  level: string
  leakI: number
  count: number
  status: string
}

/** 低压知识库结构与中压一致, 复用 HvKnowledgeView。 */
export type LvKnowledgeView = HvKnowledgeView

export interface LvSummary {
  transformers: LvTransformerView[]
  upsGroups: LvUpsGroupView[]
  hvdc: LvHvdcView[]
  ats: LvAtsView[]
  busbars: LvBusbarView[]
  branches: LvBranchView[]
  spds: LvSpdView[]
  knowledge: LvKnowledgeView
  // 向后兼容概览字段
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

// ==================== 柴发并机系统详细类型 ====================

export interface GensetFaultView {
  name: string
  value: string
  level: string
}

export interface GensetProtectionView {
  name: string
  state: string
  level: string
}

export interface GensetUnitView {
  id: string
  state: string
  breaker: string
  incomer: string
  ua: number
  ub: number
  uc: number
  u: number
  ia: number
  ib: number
  ic: number
  i: number
  p: number
  q: number
  pf: number
  freq: number
  energy: number
  rpm: number
  waterT: number
  oilP: number
  battU: number
  heater: string
  startCnt: number
  runHrs: number
  faults: GensetFaultView[]
  protections: GensetProtectionView[]
}

export interface GensetLastTestView {
  date: string
  type: string
  result: string
  duration: string
}

/** 柴发知识库结构与中压/低压一致, 复用 HvKnowledgeView。 */
export type GensetKnowledgeView = HvKnowledgeView

export interface GensetSummary {
  scheme: string
  busState: string
  autoMode: string
  units: GensetUnitView[]
  lastTest: GensetLastTestView
  parallelSteps: string[]
  stepActive: number
  knowledge: GensetKnowledgeView
  // 向后兼容概览字段
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

// ==================== 燃油监控系统详细类型 ====================

export interface FuelValveView {
  name: string
  state: string
  level: string
}

export interface FuelSwitchView {
  name: string
  th: string
  state: string
  level: string
}

export interface FuelProtectionView {
  name: string
  state: string
  level: string
}

export interface FuelAlarmView {
  name: string
  value: string
  level: string
}

export interface FuelMainTankView {
  id: string
  cap: number
  level: number
  t: number
  water: string
  leak: string
  valves: FuelValveView[]
  switches: FuelSwitchView[]
  protections: FuelProtectionView[]
}

export interface FuelDayTankView {
  id: string
  cap: number
  level: number
  leak: string
  valve: FuelValveView
  switches: FuelSwitchView[]
  protections: FuelProtectionView[]
}

export interface FuelPumpView {
  id: string
  state: string
  mode: string
  alarms: FuelAlarmView[]
  protections: FuelProtectionView[]
}

export interface FuelPipelineView {
  pressure: number
  state: string
  tracing: string
}

/** 燃油知识库结构与中压/低压/柴发一致, 复用 HvKnowledgeView。 */
export type FuelKnowledgeView = HvKnowledgeView

export interface FuelSummary {
  mainTanks: FuelMainTankView[]
  dayTanks: FuelDayTankView[]
  pumps: FuelPumpView[]
  endurance: number
  contract: string
  pipeline: FuelPipelineView
  knowledge: FuelKnowledgeView
  // 向后兼容概览字段
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

// ==================== 电池监控系统详细类型 ====================

export interface BatteryCellView {
  no: string
  u: number
  t: number
  ir: number
  level: string
}

export interface BatteryGroupView {
  id: string
  type: string
  soc: number
  u: number
  i: number
  cdState: string
  maxT: number
  worstCell: string
  ir: string
  state: string
  cells: BatteryCellView[]
}

export interface BatteryCellAlarmView {
  g: string
  cell: string
  item: string
  lv: string
  ts: string
}

/** 电池知识库结构与各子系统一致, 复用 HvKnowledgeView。 */
export type BatteryKnowledgeView = HvKnowledgeView

export interface BatterySummary {
  groups: BatteryGroupView[]
  backupMin: number
  lastDischarge: string
  cellAlarms: BatteryCellAlarmView[]
  knowledge: BatteryKnowledgeView
  // 向后兼容概览字段
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

// ---- 工具函数 ----

/** 后端中文状态 -> 前端统一状态标识。 */
export function normStatus(state: unknown): string {
  const s = String(state ?? '').trim()
  if (!s) return 'unknown'
  if (s.includes('故障') || s.includes('检修') || s.includes('停机') || s.includes('失电'))
    return 'fault'
  if (s.includes('告警') || s.includes('异常') || s.includes('预警')) return 'warning'
  if (s.includes('待机') || s.includes('备用') || s.includes('热备')) return 'standby'
  if (s.includes('运行') || s.includes('合闸') || s.includes('正常') || s.includes('在线'))
    return 'online'
  return 'standby'
}

export function num(v: unknown): number | null {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** 对非空数值求均值; 全空返回 null (避免把"无数据"显示成 0)。 */
export function avg(list: (number | null)[]): number | null {
  const vals = list.filter((v): v is number => v != null)
  if (!vals.length) return null
  return Number((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1))
}

export interface RawItem {
  [k: string]: unknown
}

/** 通用: 把后端某个设备数组映射为统一的 PowerDeviceView 列表。 */
export function toDevices(
  list: RawItem[],
  room: string,
  prefix: string,
  pick: (d: RawItem) => Partial<PowerDeviceView>,
  offset = 0,
): PowerDeviceView[] {
  return list.map((d, i) => {
    const code = String(d.id ?? `${prefix}-${i + 1}`)
    return {
      id: code,
      code,
      name: String(d.name ?? d.id ?? `${prefix}-${i + 1}`),
      roomName: room,
      room: room,
      no: offset + i + 1,
      status: normStatus(d.state ?? d.breaker),
      voltage: null,
      current: null,
      powerKw: null,
      loadPercent: null,
      powerFactor: null,
      fuelLevel: null,
      fuelConsumption: null,
      commissionedOn: null,
      healthScore: null,
      ...pick(d),
    }
  })
}

function summarize(devices: PowerDeviceView[]): PowerSystemSummary {
  return {
    total: devices.length,
    online: devices.filter((d) => d.status === 'online').length,
    avgLoadPercent: avg(devices.map((d) => d.loadPercent)),
    avgVoltage: avg(devices.map((d) => d.voltage)),
    avgCurrent: avg(devices.map((d) => d.current)),
    devices,
  }
}

// ---- 各子域映射器 ----

/** 10KV 中压: 进线 + 馈线 + 变压器 (中压侧电压单位 kV, 统一换算为 V)。 */
function mapHv(raw: RawItem): PowerSystemSummary {
  const incomers = (raw?.incomers as RawItem[]) ?? []
  const feeders = (raw?.feeders as RawItem[]) ?? []
  const transformers = (raw?.transformers as RawItem[]) ?? []
  const kv = (v: unknown) => {
    const n = num(v)
    return n == null ? null : Number((n * 1000).toFixed(0))
  }
  const devices = [
    ...toDevices(incomers, '10KV 开关站', 'IN', (d) => ({
      voltage: kv(d.u),
      current: num(d.i),
      powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
      powerFactor: num(d.pf),
    })),
    ...toDevices(
      feeders,
      '10KV 开关站',
      'F',
      (d) => ({
        name: String(d.load ?? d.id ?? ''),
        voltage: kv(d.ua),
        current: num(d.i),
        powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
        powerFactor: num(d.pf),
      }),
      incomers.length,
    ),
    ...toDevices(
      transformers,
      '变压器室',
      'T',
      (d) => ({
        voltage: kv(d.uHigh),
        current: num(d.iHigh),
        loadPercent: num(d.load),
      }),
      incomers.length + feeders.length,
    ),
  ]
  return summarize(devices)
}

/** 10KV 中压详细视图: 含全部子系统 (进线/母联/母线/ATS/馈线/变压器/直流屏/开关柜/保护/消弧线圈/计量/质量)。 */
function mapHvDetailed(raw: RawItem): HvSummary {
  const incomers = (raw?.incomers ?? []) as HvIncomerView[]
  const feeders = (raw?.feeders ?? []) as HvFeederView[]
  const transformers = (raw?.transformers ?? []) as HvTransformerView[]
  const kv = (v: unknown) => {
    const n = num(v)
    return n == null ? null : Number((n * 1000).toFixed(0))
  }

  // 为 Dashboard 向后兼容生成 PowerDeviceView 列表
  const devices: PowerDeviceView[] = [
    ...toDevices(incomers as unknown as RawItem[], '10KV 开关站', 'IN', (d) => ({
      voltage: kv(d.u),
      current: num(d.i),
      powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
      powerFactor: num(d.pf),
    })),
    ...toDevices(
      feeders as unknown as RawItem[],
      '10KV 开关站',
      'F',
      (d) => ({
        name: String(d.load ?? d.id ?? ''),
        voltage: kv(d.ua),
        current: num(d.i),
        powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
        powerFactor: num(d.pf),
      }),
      incomers.length,
    ),
    ...toDevices(
      transformers as unknown as RawItem[],
      '变压器室',
      'T',
      (d) => ({
        voltage: kv(d.uHigh),
        current: num(d.iHigh),
        loadPercent: num(d.load),
      }),
      incomers.length + feeders.length,
    ),
  ]

  const online = devices.filter((d) => d.status === 'online').length

  return {
    scheme: String(raw?.scheme ?? ''),
    incomers,
    busTie: (raw?.busTie ?? {
      id: '',
      state: '',
      autoSwitch: '',
      mode: '',
      iRated: 0,
      i: 0,
    }) as HvBusTieView,
    busSections: (raw?.busSections ?? []) as HvBusSectionView[],
    ats: (raw?.ats ?? { logic: '', lastTest: '', switchTime: '' }) as HvAtsView,
    feeders,
    transformers,
    dcPanel: (raw?.dcPanel ?? {
      id: '',
      dcBus: 0,
      dcBusTarget: 0,
      batteryBank: 0,
      chargeI: 0,
      dischargeI: 0,
      insulationR: 0,
      ripple: 0,
      state: '',
      alarms: [],
    }) as HvDcPanelView,
    switchgearEnv: (raw?.switchgearEnv ?? { rows: [], note: '' }) as HvSwitchgearEnvView,
    protectionRelays: (raw?.protectionRelays ?? []) as HvProtectionRelayView[],
    arcSuppression: (raw?.arcSuppression ?? {
      mode: '',
      coilCurrent: 0,
      coilPosition: 0,
      neutralV: 0,
      earthCapacitance: 0,
      residualCurrent: 0,
      state: '',
      groundingTx: { id: '', state: '', t: 0, i: 0 },
    }) as HvArcSuppressionView,
    metering: (raw?.metering ?? {
      incomer1: {
        energyTotal: 0,
        energyPeak: 0,
        energyValley: 0,
        energyFlat: 0,
        demand: 0,
        demandMax: 0,
      },
      incomer2: {
        energyTotal: 0,
        energyPeak: 0,
        energyValley: 0,
        energyFlat: 0,
        demand: 0,
        demandMax: 0,
      },
    }) as HvMeteringView,
    quality: (raw?.quality ?? { thdU: 0, thdI: 0, unbalance: 0 }) as HvQualityView,
    knowledge: (raw?.knowledge ?? { thresholds: [] }) as HvKnowledgeView,
    total: devices.length,
    online,
    avgLoadPercent: avg(devices.map((d) => d.loadPercent)),
    avgVoltage: avg(devices.map((d) => d.voltage)),
    avgCurrent: avg(devices.map((d) => d.current)),
    devices,
  }
}

/** 0.4KV 低压: 变压器 + UPS + HVDC + 出线回路。 */
function mapLv(raw: RawItem): PowerSystemSummary {
  const transformers = (raw?.transformers as RawItem[]) ?? []
  const ups = (raw?.upsGroups as RawItem[]) ?? []
  const hvdc = (raw?.hvdc as RawItem[]) ?? []
  const branches = (raw?.branches as RawItem[]) ?? []
  let off = 0
  const t = toDevices(
    transformers,
    '变压器室',
    'T',
    (d) => ({
      voltage: num(d.u) != null ? Number((num(d.u)! * 1000).toFixed(0)) : null,
      current: num(d.i),
      powerKw: num(d.p),
      loadPercent: num(d.load),
      powerFactor: num(d.pf),
    }),
    off,
  )
  off += t.length
  const u = toDevices(
    ups,
    'UPS 电力室',
    'UPS',
    (d) => ({
      voltage: num(d.uOut),
      current: num(d.iOut),
      powerKw: num(d.p),
      loadPercent: num(d.load),
      powerFactor: num(d.pf),
    }),
    off,
  )
  off += u.length
  const h = toDevices(
    hvdc,
    'HVDC 电力室',
    'HVDC',
    (d) => ({
      voltage: num(d.u),
      current: num(d.i),
      powerKw: num(d.p),
      loadPercent: num(d.load),
      powerFactor: num(d.pf),
    }),
    off,
  )
  off += h.length
  const b = toDevices(
    branches,
    '低压配电室',
    'LP',
    (d) => ({
      status: normStatus(d.breaker),
      voltage: num(d.u),
      current: num(d.i),
      powerKw: num(d.p),
      loadPercent: num(d.loadPct),
      powerFactor: num(d.pf),
    }),
    off,
  )
  return summarize([...t, ...u, ...h, ...b])
}

/** 0.4KV 低压详细视图: 含全部子系统 (变压器/UPS/HVDC/ATS/母排/馈线/防雷/知识库)。 */
function mapLvDetailed(raw: RawItem): LvSummary {
  const transformers = (raw?.transformers ?? []) as LvTransformerView[]
  const ups = (raw?.upsGroups ?? []) as LvUpsGroupView[]
  const hvdc = (raw?.hvdc ?? []) as LvHvdcView[]
  const ats = (raw?.ats ?? []) as LvAtsView[]
  const busbars = (raw?.busbars ?? []) as LvBusbarView[]
  const branches = (raw?.branches ?? []) as LvBranchView[]

  // 为向后兼容复用 mapLv 的 PowerDeviceView 映射
  const summary = mapLv(raw)

  return {
    transformers,
    upsGroups: ups,
    hvdc,
    ats,
    busbars,
    branches,
    spds: (raw?.spds ?? []) as LvSpdView[],
    knowledge: (raw?.knowledge ?? { thresholds: [] }) as LvKnowledgeView,
    total: summary.total,
    online: summary.online,
    avgLoadPercent: summary.avgLoadPercent,
    avgVoltage: summary.avgVoltage,
    avgCurrent: summary.avgCurrent,
    devices: summary.devices,
  }
}

/** 柴发并机: units (中压机组, 电压单位 kV)。 */
function mapGenset(raw: RawItem): PowerSystemSummary {
  const units = (raw?.units as RawItem[]) ?? []
  const devices = toDevices(units, '柴发机房', 'DG', (d) => {
    const p = num(d.p)
    return {
      voltage: num(d.u) != null ? Number((num(d.u)! * 1000).toFixed(0)) : null,
      current: num(d.i),
      powerKw: p,
      // 机组额定按 2500kW 估算负载率, 仅在有功率读数时计算
      loadPercent: p != null ? Number(((p / 2500) * 100).toFixed(1)) : null,
      powerFactor: num(d.pf),
    }
  })
  return summarize(devices)
}

/** 柴发并机详细视图: 含全部子系统 (机组电参量/开关状态/故障/保护装置/并机流程/知识库)。 */
function mapGensetDetailed(raw: RawItem): GensetSummary {
  const units = (raw?.units ?? []) as GensetUnitView[]
  const summary = mapGenset(raw)
  return {
    scheme: String(raw?.scheme ?? ''),
    busState: String(raw?.busState ?? ''),
    autoMode: String(raw?.autoMode ?? ''),
    units,
    lastTest: (raw?.lastTest ?? {
      date: '',
      type: '',
      result: '',
      duration: '',
    }) as GensetLastTestView,
    parallelSteps: (raw?.parallelSteps ?? []) as string[],
    stepActive: Number(raw?.stepActive ?? 0),
    knowledge: (raw?.knowledge ?? { thresholds: [] }) as GensetKnowledgeView,
    total: summary.total,
    online: summary.online,
    avgLoadPercent: summary.avgLoadPercent,
    avgVoltage: summary.avgVoltage,
    avgCurrent: summary.avgCurrent,
    devices: summary.devices,
  }
}

/** 燃油: 主油罐 + 日用油箱 + 油泵 (以油位作为负载率维度)。 */
function mapFuel(raw: RawItem): PowerSystemSummary {
  const main = (raw?.mainTanks as RawItem[]) ?? []
  const day = (raw?.dayTanks as RawItem[]) ?? []
  const pumps = (raw?.pumps as RawItem[]) ?? []
  const m = toDevices(main, '室外油库', 'MT', (d) => ({
    status: normStatus(d.leak === '正常' ? '运行' : d.leak),
    fuelLevel: num(d.level),
    loadPercent: num(d.level),
  }))
  const dt = toDevices(
    day,
    '日用油间',
    'DT',
    (d) => ({
      status: normStatus(d.leak === '正常' ? '运行' : d.leak),
      fuelLevel: num(d.level),
      loadPercent: num(d.level),
    }),
    m.length,
  )
  const p = toDevices(
    pumps,
    '油泵房',
    'P',
    (d) => ({
      status: normStatus(d.state),
    }),
    m.length + dt.length,
  )
  return summarize([...m, ...dt, ...p])
}

/** 燃油详细视图: 含全部子系统 (主油罐/日用油箱/油泵/管道/知识库)。 */
function mapFuelDetailed(raw: RawItem): FuelSummary {
  const summary = mapFuel(raw)
  return {
    mainTanks: (raw?.mainTanks ?? []) as FuelMainTankView[],
    dayTanks: (raw?.dayTanks ?? []) as FuelDayTankView[],
    pumps: (raw?.pumps ?? []) as FuelPumpView[],
    endurance: Number(raw?.endurance ?? 0),
    contract: String(raw?.contract ?? ''),
    pipeline: (raw?.pipeline ?? { pressure: 0, state: '', tracing: '' }) as FuelPipelineView,
    knowledge: (raw?.knowledge ?? { thresholds: [] }) as FuelKnowledgeView,
    total: summary.total,
    online: summary.online,
    avgLoadPercent: summary.avgLoadPercent,
    avgVoltage: summary.avgVoltage,
    avgCurrent: summary.avgCurrent,
    devices: summary.devices,
  }
}

/** 电池: groups (以 SOC 作为负载率维度)。 */
function mapBattery(raw: RawItem): PowerSystemSummary {
  const groups = (raw?.groups as RawItem[]) ?? []
  const devices = toDevices(groups, '电池室', 'BAT', (d) => ({
    name: String(d.id ?? ''),
    voltage: num(d.u),
    current: num(d.i),
    loadPercent: num(d.soc),
  }))
  return summarize(devices)
}

/** 电池详细视图: 含全部子系统 (电池组/单体电压温度内阻/告警/知识库)。 */
function mapBatteryDetailed(raw: RawItem): BatterySummary {
  const summary = mapBattery(raw)
  return {
    groups: (raw?.groups ?? []) as BatteryGroupView[],
    backupMin: Number(raw?.backupMin ?? 0),
    lastDischarge: String(raw?.lastDischarge ?? ''),
    cellAlarms: (raw?.cellAlarms ?? []) as BatteryCellAlarmView[],
    knowledge: (raw?.knowledge ?? { thresholds: [] }) as BatteryKnowledgeView,
    total: summary.total,
    online: summary.online,
    avgLoadPercent: summary.avgLoadPercent,
    avgVoltage: summary.avgVoltage,
    avgCurrent: summary.avgCurrent,
    devices: summary.devices,
  }
}

// ---- API 调用 ----

function emptySummary(): PowerSystemSummary {
  return {
    total: 0,
    online: 0,
    avgLoadPercent: null,
    avgVoltage: null,
    avgCurrent: null,
    devices: [],
  }
}

function fetchMapped(
  url: string,
  mapper: (raw: RawItem) => PowerSystemSummary,
): Promise<PowerSystemSummary> {
  return request
    .get<unknown, RawItem>(url)
    .then((raw) => mapper(raw ?? {}))
    .catch(() => emptySummary())
}

function fetchHvDetailed(): Promise<HvSummary> {
  return request
    .get<unknown, RawItem>('/api/power/hv')
    .then((raw) => mapHvDetailed(raw ?? {}))
    .catch(() => {
      console.error('Failed to load HV detailed data')
      return mapHvDetailed({})
    })
}

export function getPowerHv(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/hv', mapHv)
}

export function getPowerHvDetailed(): Promise<HvSummary> {
  return fetchHvDetailed()
}

export function getPowerLv(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/lv', mapLv)
}

export function getPowerLvDetailed(): Promise<LvSummary> {
  return request
    .get<unknown, RawItem>('/api/power/lv')
    .then((raw) => mapLvDetailed(raw ?? {}))
    .catch(() => {
      console.error('Failed to load LV detailed data')
      return mapLvDetailed({})
    })
}

export function getPowerGenset(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/genset', mapGenset)
}

export function getPowerGensetDetailed(): Promise<GensetSummary> {
  return request
    .get<unknown, RawItem>('/api/power/genset')
    .then((raw) => mapGensetDetailed(raw ?? {}))
    .catch(() => {
      console.error('Failed to load Genset detailed data')
      return mapGensetDetailed({})
    })
}

export function getPowerFuel(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/fuel', mapFuel)
}

export function getPowerFuelDetailed(): Promise<FuelSummary> {
  return request
    .get<unknown, RawItem>('/api/power/fuel')
    .then((raw) => mapFuelDetailed(raw ?? {}))
    .catch(() => {
      console.error('Failed to load Fuel detailed data')
      return mapFuelDetailed({})
    })
}

export function getPowerBattery(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/battery', mapBattery)
}

export function getPowerBatteryDetailed(): Promise<BatterySummary> {
  return request
    .get<unknown, RawItem>('/api/power/battery')
    .then((raw) => mapBatteryDetailed(raw ?? {}))
    .catch(() => {
      console.error('Failed to load Battery detailed data')
      return mapBatteryDetailed({})
    })
}

export function getPowerOverview(): Promise<PowerOverview> {
  return Promise.all([
    getPowerHv(),
    getPowerLv(),
    getPowerGenset(),
    getPowerFuel(),
    getPowerBattery(),
  ]).then(([hv, lv, genset, fuel, battery]) => {
    const all = [hv, lv, genset, fuel, battery]
    const devices = all.flatMap((s) => s.devices)
    return {
      totalEquipment: all.reduce((s, x) => s + x.total, 0),
      onlineCount: all.reduce((s, x) => s + x.online, 0),
      faultCount: devices.filter((d) => d.status === 'fault').length,
      warningCount: devices.filter((d) => d.status === 'warning').length,
      hv,
      lv,
      genset,
      fuel,
      battery,
    }
  })
}
