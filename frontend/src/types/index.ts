/* ===== 通用 ===== */
export interface Paginated<T> {
  total: number
  page: number
  size: number
  items: T[]
}

/* ===== 专业域设备 (B5: 真实 external_devices 为骨架 + 物模型指标) ===== */
/* ===== 认证 ===== */
export interface LoginRequest {
  username: string
  password: string
}
export interface UserInfo {
  id: number
  username: string
  display_name: string
  email?: string | null
  department: string
  is_superuser: boolean
  roles: string[]
  permissions: string[]
}
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

/* ===== 驾驶舱总览 ===== */
export interface AlarmCount {
  crit: number
  warn: number
  info: number
}
export interface DashboardOverview {
  total_devices: number
  online_devices: number
  online_rate: number // 0-100
  today_alarms: number
  pue: number
  wue?: number
  it_load_mw?: number
  total_load_mw?: number
  cool_load_mw?: number
  availability?: number
  free_cool_hours?: number
  alarms?: AlarmCount
}

/* ===== 机柜 ===== */
export interface Cabinet {
  id: number
  idc_id: number
  code: string
  room: string
  row: string
  u_total: number
  u_used: number
  rated_power_kw: number
  current_power_kw: number
  status: string
}

/* ===== 机柜时序指标 ===== */
export interface CabinetMetricPoint {
  ts: string // ISO8601
  value: number
}
export interface CabinetMetrics {
  cabinet_id: number
  code: string
  range_minutes: number
  temperature: CabinetMetricPoint[]
  humidity: CabinetMetricPoint[]
  power_kw: CabinetMetricPoint[]
}

/* ===== 统一设备台账 ===== */
export interface Equipment {
  id: number
  idc_id: number
  room_id: number | null
  code: string
  name: string
  domain: string
  category: string
  vendor: string
  model: string
  status: string
  load_pct: number
  run_hours: number
  redundancy: string
  attrs: Record<string, unknown>
}

/* ===== 设备健康评分 (阶段三 D/E) ===== */
export interface EquipmentHealthItem {
  id: string
  code: string
  name: string
  domain: string
  category: string
  status: string
  loadPct: number
  health: number
  grade: string // 优/良/中/差
  issues: string[]
}
export interface EquipmentHealthDomain {
  domain: string
  label: string
  avgHealth: number
  count: number
  grade: string
}
export interface EquipmentHealthSummary {
  优: number
  良: number
  中: number
  差: number
}
export interface EquipmentHealth {
  generatedAt: string
  count: number
  avgHealth: number
  byDomain: EquipmentHealthDomain[]
  byEquipment: EquipmentHealthItem[]
  worst: EquipmentHealthItem[]
  summary: EquipmentHealthSummary
}
export interface EquipmentMetrics {
  equipment_id: number
  code: string
  range_minutes: number
  metrics: string[]
  series: Record<string, CabinetMetricPoint[]>
}

/* ===== 告警 ===== */
export interface Alarm {
  id?: string
  lv: 'crit' | 'warn' | 'info'
  sys: string
  desc: string
  state: string
  ts?: string
  owner?: string
}
export interface AlarmCenter {
  convergence: { raw: number; converged: number; rate: number }
  rules: string[]
  trend: { id: string; pred: string; conf: number; sug: string }[]
  active: Alarm[]
  sla: { mttaMin: number; mttrMin: number; autoCloseRate: number }
  /** 运维知识面板：事件→问题→风险 闭环 / 智能趋势告警 */
  knowledge?: PowerKnowledge
}

/* ===== 告警规则引擎 ===== */
/** 规则状态 */
export type AlarmRuleStatus = 'enabled' | 'disabled' | 'silenced'

/** 告警规则定义 — 与后端 AlarmRuleView 对齐 (阈值带模型) */
export interface AlarmRuleDef {
  id: number
  ruleCode?: string // 规则编码 (category+metric 生成)
  category: string // 业务系统 / 类别
  metric: string // 测点名
  warnLo?: number | null // 预警下限
  warnHi?: number | null // 预警上限
  critLo?: number | null // 严重下限
  critHi?: number | null // 严重上限
  unit?: string
  enabled: boolean // 是否启用
  source?: string // 来源 (DEFAULT / CUSTOM)
  status: AlarmRuleStatus
  created?: string
  updated?: string
}

/** 规则引擎运行状态 (由规则列表本地计算, 后端无 /state 端点) */
export interface AlarmEngineState {
  totalRules: number
  enabledCount: number
  triggeredCount: number
  silencedCount: number
}

/* ===== 告警持久化 ===== */
/** 告警事件 — 规则触发后的生命周期记录 */
export interface AlarmEvent {
  id: string
  ruleId: string
  ruleName: string
  metric: string
  sys: string
  lv: 'crit' | 'warn' | 'info'
  desc: string
  value: number
  threshold: number
  unit?: string
  state: 'active' | 'acknowledged' | 'resolved' | 'suppressed'
  triggeredAt: string
  acknowledgedAt?: string
  acknowledgedBy?: string
  resolvedAt?: string
  resolvedBy?: string
  note?: string
  autoResolved: boolean
  escalationCount: number // 升级次数
}

/** 告警历史查询参数 */
export interface AlarmHistoryQuery {
  sys?: string
  lv?: string
  state?: string
  from?: string
  to?: string
  page?: number
  limit?: number
}

/** 告警历史查询响应 */
export interface AlarmHistoryResponse {
  items: AlarmEvent[]
  total: number
  page: number
  limit: number
  stats: {
    total24h: number
    active24h: number
    resolved24h: number
    mttaMin: number
    mttrMin: number
    bySystem: Record<string, number>
    byLevel: { crit: number; warn: number; info: number }
  }
}

/* ===== 暖通·冷源 / 末端 ===== */
export interface ChillerPlant {
  mode: string
  modes?: string[]
  outdoorT: number
  outdoorRH: number
  wetBulb: number
  supplyT: number
  returnT: number
  targetSupplyT: number
  flow: number
  coolingCap: number
  plr: number
  storageTank: {
    level: number
    dischargeMin: number
    mode: string
    capacity: number
    topTemp: number
    botTemp: number
    flow: number
    power: number
  }
  chillers: {
    id: string
    state: string
    load: number
    cop: number
    evapT: number | string
    condT: number | string
    current: number
    runHrs: number
  }[]
  towers: { id: string; state: string; fanHz: number; outT: number | string }[]
  pumps: {
    chw: { id: string; state: string; hz: number; kw: number }[]
    cw: { id: string; state: string; hz: number; kw: number }[]
    sec: { id: string; state: string; hz: number; kw: number; flow: number; pressure?: number }[]
  }
  ambient: {
    outdoorTemp: number
    outdoorRH: number
    wetBulb: number
    indoorTemp: number
    indoorRH: number
    freeCooling: string
  }
  hex: {
    id: string
    state: string
    eff: number
    priIn: number
    priOut: number
    secIn: number
    secOut: number
  }[]
  valves: { id: string; name: string; pos: number; state: string }[]
  staging: { rule: string; lastAction: string; next: string }
  tempTrend: number[]
  loadTrend: number[]
  /** 冷却水回水温度（℃） */
  cwReturnT?: number
  /** 设计阈值（依据《阿里云数据中心弱电手册》） */
  thresholds?: Record<string, number>
  /** 运行模式切换判据（手册） */
  modeLogic?: {
    current: string
    modes: { name: string; desc: string }[]
    transitions: { from: string; to: string; conditions: { label: string; ok: boolean }[] }[]
  }
  /** 冷源故障锁定知识库（手册 §制冷单元故障切换） */
  faults?: { no: number; fault: string; lock: string; action: string; manualReset: boolean }[]
}
export interface CracRoomLeak {
  status: string
  level: string
  position: number | null
  zone: number
}
export interface CracRoom {
  id: string
  name: string
  avgTemp: number
  avgRh: number
  hotAisle: number
  hotRh: number
  coldAisle: number
  coldRh: number
  inOutDiff: number
  dewPoint: number
  cracRun: number
  cracN: number
  state: string
  leak: CracRoomLeak
}
export interface CracUnitControl {
  fanEnable: boolean
  fanSpeedSet: number
  waterValveSet: number
  coolingMode: string
  humidOn: boolean
}
export interface CracUnitSetpoints {
  supplyTSet: number
  rhSet: number
  roomTSet: number
  highTempAlarm: number
  lowTempAlarm: number
  highRhAlarm: number
}
export interface CracUnit {
  id: string
  room: string
  type: string
  state: string
  supplyT: number | string
  returnT: number | string
  supplyRh: number | string
  returnRh: number | string
  chilledWaterT: number | string
  returnWaterT: number | string
  fan: number
  valve: number
  waterValve: number
  power: number | string
  dp: number | string
  filter: string
  control: CracUnitControl
  setpoints: CracUnitSetpoints
}
export interface CracLeakDevice {
  id: string
  location: string
  zone: number
  status: string
  position: number | null
  cableLength: number
  cableStatus: string
}
export interface CracLeak {
  total: number
  alarm: number
  devices: CracLeakDevice[]
}
export interface CracSummary {
  total: number
  running: number
  standby: number
  fault: number
  maint: number
  avgSupply: number | string
  avgReturn: number | string
  avgSupplyWater: number | string
  avgReturnWater: number | string
  outdoorRef: number
  avgInOutDiff: number
  leakAlarm: number
  leakTotal: number
}
export interface Crac {
  summary: CracSummary
  rooms: CracRoom[]
  units: CracUnit[]
  leak: CracLeak
  fresh: {
    id: string
    state: string
    supplyT: number | string
    rh: number | string
    co2: number | string
    filterDp: number | string
  }[]
  humid: { id: string; name: string; state: string; rh: number | string; mode: string }[]
  funcRooms: { id: string; t: number; rh: number }[]
  /** 末端控制策略（依据《阿里云数据中心弱电手册》） */
  ctrl?: {
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
  /** 运维知识面板：设计阈值/系统架构/控制逻辑/故障知识库 */
  knowledge?: PowerKnowledge
}

/* ===== 暖通·液冷系统 ===== */
export interface LiquidCoolingPrimaryCDU {
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
export interface LiquidCoolingSecondaryCDU {
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
export interface LiquidCoolingColdPlate {
  rackId: string
  nodeType: string
  inletTemp: number
  outletTemp: number
  flow: number
  dp: number
  gpuTemp: number[]
  state: string
}
export interface LiquidCoolingManifoldNode {
  id: string
  zone: string
  temp: number
  pressure: number
  flow: number
  valvesOpen?: number
  branchCount?: number
}
export interface LiquidCoolingLeakRope {
  id: string
  location: string
  status: string
  length: number
  coverage: number
}
export interface LiquidCoolingLeakPoint {
  id: string
  zone: string
  count: number
  alarmCount: number
}
export interface LiquidCoolingCoolantQuality {
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
export interface LiquidCoolingTowerFan {
  id: string
  state: string
  fanHz: number
  outletTemp: number | string
  approach: number | string
}
export interface LiquidCoolingDryCooler {
  id: string
  state: string
  fanHz: number
  ambientT: number
}
export interface LiquidCoolingRejectionPump {
  id: string
  state: string
  hz: number
  kw: number
}
export interface LiquidCoolingHeatRecovery {
  enabled: boolean
  recoveryRate: number
  recoveryTemp: number
  returnTemp: number
  flow: number
  usageType: string
  co2Reduction: number
  annualSaving: number
}
export interface LiquidCoolingControl {
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
export interface LiquidCooling {
  systemMode: string
  outdoorT: number
  outdoorRH: number
  totalCoolingCap: number
  coolingCapUsed: number
  capRate: number
  supplyTemp: number
  returnTemp: number
  primaryFlow: number
  primaryPressure: number
  secSupplyTemp: number
  secReturnTemp: number
  secFlow: number
  secPressure: number
  deltaT: number
  pueContribution: number
  freeCoolingHours: number
  heatRecovery: number
  primaryCDUs: LiquidCoolingPrimaryCDU[]
  secondaryCDUs: LiquidCoolingSecondaryCDU[]
  coldPlateMonitoring: LiquidCoolingColdPlate[]
  manifolds: { supply: LiquidCoolingManifoldNode[]; return: LiquidCoolingManifoldNode[] }
  leakDetection: {
    totalSensors: number
    alarmCount: number
    warningCount: number
    ropeLeak: LiquidCoolingLeakRope[]
    pointLeak: LiquidCoolingLeakPoint[]
  }
  coolantQuality: LiquidCoolingCoolantQuality
  heatRejection: {
    type: string
    towerFans: LiquidCoolingTowerFan[]
    dryCoolers: LiquidCoolingDryCooler[]
    rejectionPumps: LiquidCoolingRejectionPump[]
    totalHeatRejected: number
    approachTemp: number
    freeCoolingAvailable: boolean
  }
  heatRecoveryDetail: LiquidCoolingHeatRecovery
  controlStrategy: LiquidCoolingControl
  supplyTempTrend: number[]
  returnTempTrend: number[]
  flowTrend: number[]
  deltaTTrend: number[]
  knowledge?: PowerKnowledge
}

/* ===== 电力 ===== */
/** 三相电压/电流 */
export interface HvPhase {
  ua: number
  ub: number
  uc: number // 三相线电压 kV
  ia: number
  ib: number
  ic: number // 三相电流 A
}
/** 10KV 进线柜 (双路市电) */
export interface HvIncomer {
  id: string
  src: string
  state: string
  breaker: string // state=断路器分合
  ua: number
  ub: number
  uc: number
  u: number // 三相+平均线电压 kV
  ia: number
  ib: number
  ic: number
  i: number // 三相+平均电流 A
  p: number
  q: number
  pf: number
  freq: number // 有功MW/无功Mvar/功率因数/频率
  energy: number // 当日有功电度 kWh
}
/** 10KV 出线馈线柜 */
export interface HvFeeder {
  id: string
  load: string
  state: string
  breaker: string // load=所带负荷名称
  ua: number
  ub: number
  uc: number // 三相线电压 kV
  ia: number
  ib: number
  ic: number // 三相电流 A
  p: number
  pf: number
  energy: number // 功率MW/功率因数/累计电度 kWh
}
/** 遥信量 (开关量) */
export interface HvSignal {
  name: string
  value: string
  level: 'g' | 'a' | 'r' | 'b'
}
/** 10KV/0.4KV 配电变压器 (由出线供电) */
export interface HvTransformer {
  id: string
  feeder: string
  state: string
  load: number // 负载率 %
  uHigh: number
  iHigh: number // 高压侧 线电压kV/电流A
  uLow: number
  iLow: number // 低压侧 线电压kV/电流A
  windingT: number
  oilT: number // 绕组温度/油温 ℃
  ambT: number
  humidity: number // 环境温度℃/湿度 %
  tap: number
  fan: string // 有载分接档位/冷却风机
  signals: HvSignal[] // 遥信量 (运行状态/保护告警/断路器位置等)
}
export interface HvBusTie {
  id: string
  state: string
  autoSwitch: string
  mode: string
}
export interface HvAts {
  logic: string
  lastTest: string
  switchTime: string
}
export interface HvQuality {
  thdU: number
  thdI: number
  unbalance: number
}
export interface PowerHv {
  scheme: string
  incomers: HvIncomer[]
  busTie: HvBusTie
  ats: HvAts
  feeders: HvFeeder[]
  transformers: HvTransformer[]
  quality: HvQuality
  knowledge?: PowerKnowledge
}
/** 低压馈线回路 (出线/断路器柜) — 含断路器分合与全电参量 */
export interface LvBranch {
  id: string // 回路编号，如 LP-A01
  name: string // 所带负荷
  breaker: string // 断路器分合状态：合闸/分闸
  rated: number // 额定电流 A
  ua: number
  ub: number
  uc: number
  u: number // 三相相电压 V + 平均
  ia: number
  ib: number
  ic: number
  i: number // 三相电流 A + 平均
  freq: number // 频率 Hz
  p: number // 有功功率 kW
  q: number // 无功功率 kvar
  pf: number // 功率因数
  energy: number // 累计电度 kWh
  thdu: number // 电压谐波畸变率 %
  thdi: number // 电流谐波畸变率 %
  loadPct: number // 负载率 %
}
/** 防雷 / 浪涌保护器 (SPD) */
export interface LvSpd {
  id: string // 安装位置
  state: string // 正常/劣化/失效
  level: 'g' | 'a' | 'r'
  leakI: number // 漏电流 mA
  count: number // 动作计数
  status: string // 遥信：正常/报警
}
export interface LvTransformer {
  id: string
  load: number
  t: number
  state: string
  u: number
  i: number
  p: number
  q: number
  pf: number
  freq: number // 电压kV/电流A/有功kW/无功kvar/功率因数/频率
  energy: number
  thdu: number
  thdi: number // 电度/谐波
}
export interface LvUpsGroup {
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
export interface LvHvdc {
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
export interface LvAts {
  id: string
  state: string
  mode: string
  lastSw: string
  uIn: number
  uOut: number
  pf: number
  p: number
}
export interface LvBusbar {
  id: string
  load: number
  i: number
  state: string
  u: number
  pf: number
  energy: number
  thdu: number
}
export interface PowerLv {
  transformers: LvTransformer[]
  upsGroups: LvUpsGroup[]
  hvdc: LvHvdc[]
  ats: LvAts[]
  busbars: LvBusbar[]
  branches: LvBranch[] // 低压馈线回路（断路器 + 全电参量）
  spds: LvSpd[] // 防雷 / 浪涌保护器
  knowledge?: PowerKnowledge
}
export interface GensetFault {
  name: string
  value: string
  level: 'g' | 'a' | 'r' | 'b'
}
export interface GensetProtection {
  name: string
  state: string
  level: 'g' | 'a' | 'r' | 'b'
}
/** 柴油发电机组 (柴发并机) — 含进线/出线三相电参量、开关分合、故障与保护装置 */
export interface GensetUnit {
  id: string
  state: string // 运行 / 备用 / 维保
  breaker: string // 出口断路器分合：合闸 / 分闸
  incomer: string // 进线(母线侧)开关分合：合闸 / 分闸
  // 三相电参量 (高压 10kV 级)
  ua: number
  ub: number
  uc: number
  u: number // 三相线电压 kV / 平均
  ia: number
  ib: number
  ic: number
  i: number // 三相电流 A / 平均
  p: number
  q: number
  pf: number
  freq: number // 有功kW / 无功kvar / 功率因数 / 频率Hz
  energy: number // 累计有功电度 kWh
  // 运行参数
  rpm: number
  waterT: number
  oilP: number
  battU: number
  heater: string
  startCnt: number
  runHrs: number
  faults: GensetFault[] // 当前故障 / 告警遥信
  protections: GensetProtection[] // 保护装置投退 / 动作状态
}
export interface Genset {
  scheme: string
  busState: string
  autoMode: string
  units: GensetUnit[]
  lastTest: { date: string; type: string; result: string; duration: string }
  parallelSteps: string[]
  stepActive: number
  knowledge?: PowerKnowledge
}
/** 油位四段开关 (低低位 LL / 低位 L / 高位 H / 高高位 HH) */
export interface FuelSwitch {
  name: string
  th: string
  state: '断开' | '闭合'
  level: 'g' | 'a' | 'r' | 'b'
}
/** 阀门分合状态 */
export interface FuelValve {
  name: string
  state: string
  level: 'g' | 'a' | 'r' | 'b'
}
/** 保护装置投退/动作状态 */
export interface FuelProtection {
  name: string
  state: string
  level: 'g' | 'a' | 'r' | 'b'
}
/** 油泵告警 (遥信) */
export interface FuelAlarm {
  name: string
  value: string
  level: 'g' | 'a' | 'r' | 'b'
}
/** 燃油监控 — 主油罐 / 日用油箱 / 输油泵 */
export interface MainTank {
  id: string
  cap: number
  level: number
  t: number
  water: string
  leak: string
  valves: FuelValve[] // 进油阀 / 出油阀
  switches: FuelSwitch[] // 低低位/低位/高位/高高位
  protections: FuelProtection[]
}
export interface DayTank {
  id: string
  cap: number
  level: number
  leak: string
  valve: FuelValve // 进油阀
  switches: FuelSwitch[]
  protections: FuelProtection[]
}
export interface FuelPump {
  id: string
  state: string
  mode: string
  alarms: FuelAlarm[] // 油泵告警
  protections: FuelProtection[]
}
export interface Fuel {
  mainTanks: MainTank[]
  dayTanks: DayTank[]
  pumps: FuelPump[]
  endurance: number
  contract: string
  pipeline: { pressure: number; state: string; tracing: string }
  knowledge?: PowerKnowledge
}
/** 单体电池 — 电压/温度/内阻 */
export interface BattCell {
  no: string // 单体编号 #01
  u: number // 单体电压 V
  t: number // 单体温度 ℃
  ir: number // 内阻 mΩ
  level: 'g' | 'a' | 'r' | 'b'
}
/** 蓄电池组 — 总电压 / 充放电电流状态 / 单体级数据 */
export interface BattGroup {
  id: string
  type: string
  soc: number
  u: number // 电池组总电压 V
  i: number // 充放电电流 A (正=充电/浮充, 负=放电)
  cdState: string // 充放电状态: 充电 / 放电 / 浮充
  maxT: number // 组最高温 ℃
  worstCell: string // 最差单体描述
  ir: string // 组整体内阻结论
  state: string // 运行模式 浮充/均充/放电
  cells: BattCell[] // 单体级数据
}
export interface Battery {
  groups: BattGroup[]
  backupMin: number
  lastDischarge: string
  cellAlarms: { g: string; cell: string; item: string; lv: string; ts: string }[]
  knowledge?: PowerKnowledge
}

/* ===== 运维知识库（电力侧通用，来自《阿里云数据中心弱电手册》）===== */
/** 设计/告警阈值 */
export interface KnowledgeThreshold {
  k: string
  v: string
  note?: string
}
/** 控制/切换逻辑步骤 */
export interface KnowledgeLogicStep {
  step: number
  text: string
  ok?: boolean
}
/** 一组控制/切换逻辑 */
export interface KnowledgeLogicGroup {
  title: string
  steps: KnowledgeLogicStep[]
}
/** 故障锁定知识库 */
export interface KnowledgeFault {
  no: number
  fault: string
  lock: string
  action: string
  manualReset: boolean
}
/** 系统架构与组成 */
export interface KnowledgeArch {
  components: string[]
  design: string
  redundancy?: string
}
/** 通用运维知识块：阈值 / 架构 / 逻辑 / 故障知识库 */
export interface PowerKnowledge {
  thresholds?: KnowledgeThreshold[]
  arch?: KnowledgeArch
  logic?: KnowledgeLogicGroup[]
  faults?: KnowledgeFault[]
  note?: string
}

/* ===== 安防消防 ===== */
export interface Cctv {
  total: number
  online: number
  offline: number
  nvr: { total: number; ok: number; storeDays: number; required: number }
  zones: { id: string; cams: number; offline: number }[]
  ai: string[]
  events: { ts: string; zone: string; desc: string; lv: string }[]
  /** 运维知识面板：设计阈值/系统架构/控制逻辑/故障知识库 */
  knowledge?: PowerKnowledge
}
export interface Acs {
  doors: number
  online: number
  openAbnormal: number
  todayEvents: number
  denied: number
  visitors: number
  areas: { id: string; auth: string; doors: number }[]
  events: { ts: string; door: string; person: string; act: string; lv: string }[]
  /** 运维知识面板：设计阈值/系统架构/控制逻辑/故障知识库 */
  knowledge?: PowerKnowledge
}
export interface Ids {
  perimeter: { type: string; zones: number; armed: number; alarm: number }
  indoor: { ir: number; glass: number; armed: string; state: string }
  linkage: string
  events: { ts: string; zone: string; desc: string; lv: string }[]
  /** 运维知识面板：设计阈值/系统架构/控制逻辑/故障知识库 */
  knowledge?: PowerKnowledge
}
export interface Fire {
  hostState: string
  loops: number
  points: number
  faultPoints: number
  detectors: { type: string; n: number; fault: number }[]
  gas: { zones: number; ready: number; released: number; agent: string }
  vesda: { id: string; level: string; val: number }[]
  qieFei: { desc: string; state: string; lastDrill: string }
  emergency: { lights: number; ok: number; batteryOk: number; evacSigns: number }
  events: { ts: string; desc: string; lv: string }[]
  /** 运维知识面板：设计阈值/系统架构/控制逻辑/故障知识库 */
  knowledge?: PowerKnowledge
}

/* ===== 智能运营 + 运维作业 ===== */
export interface Twin {
  platform: string
  coverage: { points: number; mapped: number; models: number; refreshMs: number }
  layers: string[]
  scenes: { id: string; state: string; last: string }[]
  autoOps: { id: string; state: string; saving: string }[]
  /** 运维知识面板：平台定位/数据接入架构/设计理念 */
  knowledge?: PowerKnowledge
}

/* ===== 阶段四 任务1: 数字孪生图层 / 链路拓扑图 / 推演仿真 (数据驱动底座) ===== */
export type RoomStatus = 'normal' | 'warning' | 'critical'

/** 孪生图: 单台设备 (来自统一台账, 复用 equipment_health 健康分) */
export interface TwinGraphEquipment {
  id: number
  code: string
  name: string
  domain: string
  category: string
  status: string
  loadPct: number
  health: number
  redundancy: string
}
/** 孪生图: 包间 (按设备 domain 映射房间类型派生) */
export interface TwinGraphRoom {
  id: number
  code: string
  name: string
  kind: string
  floor: string
  rackCapacity: number
  coldAisleT: number
  hotAisleT: number
  rh: number
  pressurePa: number
  equipmentCount: number
  avgLoadPct: number
  avgHealth: number
  status: RoomStatus
  equipments: TwinGraphEquipment[]
}
export interface TwinGraphIdc {
  id: number
  code: string
  name: string
  region: string
  powerCapacityMw: number
  coolingCapacityMw: number
  rackCapacity: number
  rooms: TwinGraphRoom[]
}
export interface TwinGraphSummary {
  idcCount: number
  roomCount: number
  equipmentCount: number
  mappedPct: number
  avgHealth: number
}
export interface TwinGraph {
  generatedAt: string
  source: 'db' | 'generated'
  idcs: TwinGraphIdc[]
  summary: TwinGraphSummary
}

/** 链路拓扑图: 节点 (设备台账 + 负载/健康/冗余) */
export interface TopologyNode {
  id: number
  label: string
  kind: string
  domain: string
  category: string
  roomId: number | null
  roomCode: string
  status: string
  loadPct: number
  health: number
  redundancy: string
}
export interface TopologyEdge {
  source: number
  target: number
  type: 'power' | 'cool'
  label: string
}
export interface TopologyRedundancy {
  'N+1': number
  '2N': number
  single: number
}
export interface TopologyGraph {
  generatedAt: string
  source: 'db' | 'generated'
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  redundancy: TopologyRedundancy
}

/** 链路节点真实测点 (来自 /api/external/.../metrics/realtime, 驱动能流速度/温度)。 */
export interface NodeRealtime {
  loadPct?: number | null // 真实负载率 %, 驱动能流速度
  powerKw?: number | null // 真实功率 kW, 供电域节点标注
  supplyTemp?: number | null // 供水/送风温度 ℃ (冷量流)
  returnTemp?: number | null // 回水/回风温度 ℃
  temp?: number | null // 通用温度 ℃ (绕组/油温/水温等)
  online?: boolean | null
}

/** 链路节点实时测点映射响应。 */
export interface TopologyRealtime {
  source: string
  updatedAt: string
  nodes: Record<number, NodeRealtime>
}

/** build-graph-apis: 孪生拓扑数据底座 — 合并孪生层级图 + 链路拓扑图 + 汇总指标 */
export interface TwinTopologySummary {
  source: 'db' | 'generated'
  idcCount: number
  roomCount: number
  equipmentCount: number
  avgHealth: number
  mappedPct: number
  topoNodes: number
  topoEdges: number
  topoRedundancy: TopologyRedundancy
  topoSource: 'db' | 'generated'
}
export interface TwinTopology {
  generatedAt: string
  source: 'db' | 'generated'
  twinGraph: TwinGraph
  topology: TopologyGraph
  summary: TwinTopologySummary
}

/** 推演仿真: 请求与结果 */
export type TwinScenario = '市电失电' | '冷源故障' | '全停演练'
export interface TwinSimulateRequest {
  scenario: TwinScenario
  affectedIds?: number[]
  params?: Record<string, unknown>
}
export interface TwinSimulateBaseline {
  equipmentTotal: number
  avgHealth: number
  powerLoad: number
  coolLoad: number
}
export interface TwinSimulateAfter {
  equipmentOnline: number
  avgHealth: number
  powerLoad: number
  coolLoad: number
}
export interface TwinSimulateImpact {
  equipmentLost: number
  roomsAffected: number
  itRoomsLostPower: number
  itRoomsLostCool: number
  redundancyCover: boolean
}
export interface TwinSimulateResult {
  scenario: TwinScenario
  generatedAt: string
  baseline: TwinSimulateBaseline
  after: TwinSimulateAfter
  impact: TwinSimulateImpact
  affectedEquipmentIds: number[]
  affectedRoomIds: number[]
}

/* ===== 阶段四 任务3: 推演场景库 + 方舟闭环(真实节能) ===== */
export type TwinRiskLevel = 'low' | 'medium' | 'high'
/** 场景库条目: 点选即可运行推演, 附带波及预览 */
export interface TwinScenarioDef {
  id: string
  scenario: TwinScenario
  name: string
  desc: string
  tags: string[]
  targetCount: number
  impactCount: number
  roomsAffected: number
  redundancyCover: boolean
  riskLevel: TwinRiskLevel
  runnable: boolean
}
export interface TwinScenarioLibrary {
  generatedAt: string
  source: 'db' | 'generated'
  equipmentTotal: number
  scenarios: TwinScenarioDef[]
}

/** 方舟闭环: 单条节能闭环策略 */
export interface ArkLoop {
  id: string
  name: string
  desc: string
  state: string
  /** achieved=已实现节能; potential=可挖潜力 */
  kind: 'achieved' | 'potential'
  savedKw: number
  savingPct: number
  savedKwhYear: number
  basis: string
  metrics: { k: string; v: string }[]
}
export interface ArkSummary {
  source: 'real' | 'generated'
  pue: number | null
  baselinePue: number
  facilityKw: number
  itKw: number
  coolingKw: number
  achievedKw: number
  achievedKwhYear: number
  potentialKw: number
  carbonTonYear: number
  loopCount: number
  runningCount: number
}
export interface ArkClosedLoop {
  generatedAt: string
  summary: ArkSummary
  loops: ArkLoop[]
}

export interface Capacity {
  dims: { id: string; used: number; total: number; unit: string }[]
  rooms: { id: string; racks: number; used: number; powerPct: number; coolPct: number }[]
  forecast: string
  forecastDetail?: CapacityForecast
  /** 运维知识面板：容量/风险前瞻联动 */
  knowledge?: PowerKnowledge
}
export interface CapacityForecastPoint {
  month: number
  pct: number
  lo: number
  hi: number
}
export interface CapacityForecastDim {
  id: string
  unit: string
  currentPct: number
  slopePerMonth: number
  projected: CapacityForecastPoint[]
  warnMonth: number | null
  fullMonth: number | null
  status: string
}
export interface CapacityForecastTrendRow {
  monthOffset: number
  type: string
  [dim: string]: number | string
}
export interface CapacityForecast {
  method: string
  generatedAt: string
  historyMonths: number
  horizonMonths: number
  warnThreshold: number
  fullThreshold: number
  byDim: CapacityForecastDim[]
  trend: CapacityForecastTrendRow[]
  headline: string
  advice: string
}
export interface Energy {
  todayKwh: number
  monthKwh: number
  yearKwh: number
  pueTrend: number[]
  loadForecast: { h: number; actual: number | null; pred: number }[]
  aiSaving: { enabled: boolean; algo: string; monthSaveKwh: number; saveRate: number }
  breakdown: { id: string; kw: number; pct: number }[]
  carbon: { greenPct: number; pv: string; monthCO2: number }
  advice?: EnergyAdvice
}
export interface EnergySuggestion {
  id: string
  title: string
  priority: string
  savingKw: number
  savingPct: number
  detail: string
  basis: string
}
export interface EnergyEfficiency {
  chillerCop: number
  upsEff: number
  upsAvgLoad: number
  cracSupplyTemp: number | null
  chillerSupplyTemp: number
}
export interface EnergyAdvice {
  pue: { current: number | null; target: number }
  efficiency: EnergyEfficiency
  breakdown: { id: string; kw: number; pct: number }[]
  suggestions: EnergySuggestion[]
  totalSavingKw: number
  totalSavingPct: number
  realData: {
    itLoadKw: number
    coolingKw: number
    chillerPowerKw: number
    cracPowerKw: number
    pumpPowerKw: number
    facilityKw: number
    distributionKw: number
    dataSource: string
  }
  generatedAt: string
}
/* ===== 工单模型 (CRUD 生命周期) ===== */
/** 工单状态生命周期: 待处理 → 处理中 → 待归档 → 已完成(闭环) */
export type TicketStatus = 'open' | 'doing' | 'pending' | 'done'
export const TICKET_STATUS_LABEL: Record<TicketStatus, string> = {
  open: '待处理',
  doing: '处理中',
  pending: '待归档',
  done: '已完成',
}
export const TICKET_STATUS_ORDER: TicketStatus[] = ['open', 'doing', 'pending', 'done']

/** 工单来源: 手动创建 / 告警自动转 / 巡检发现 / 机器人巡检 */
export type TicketSource = 'manual' | 'alarm' | 'inspect' | 'patrol'

/** 工单操作日志 (生命周期留痕) */
export interface TicketLog {
  ts: string
  operator: string
  action: 'create' | 'transition' | 'update' | 'note' | 'close'
  from?: TicketStatus
  to?: TicketStatus
  note?: string
}

export interface Ticket {
  id: string
  title: string
  sys: string
  lv: 'crit' | 'warn' | 'info'
  state: TicketStatus
  owner: string
  created: string
  createdBy: string
  updatedAt: string
  sla: string
  dueAt?: string
  progress: number
  source: TicketSource
  sourceAlarmId?: string
  description: string
  logs: TicketLog[]
}

export interface TicketCenter {
  stats: { open: number; doing: number; pending: number; done: number }
  list: Ticket[]
}

export interface TicketCreateRequest {
  title: string
  sys: string
  lv: 'crit' | 'warn' | 'info'
  owner: string
  sla?: string
  description?: string
  source?: TicketSource
  sourceAlarmId?: string
}

export interface TicketUpdateRequest {
  title?: string
  sys?: string
  lv?: 'crit' | 'warn' | 'info'
  owner?: string
  sla?: string
  description?: string
  progress?: number
}

export interface TicketTransitionRequest {
  state: TicketStatus
  operator: string
  note?: string
}
export interface InspectionRoute {
  id: number
  code: string
  freq: string
  items: number
  last: string
  next: string
  state: string
  deviceId?: string
  deviceName?: string
  area?: string
  source?: 'real' | 'db'
}
export interface InspectionFinding {
  id: number
  route: string
  item: string
  ts: string
  lv: string
  action: string
}
export interface Inspect {
  today: { plan: number; done: number; abnormal: number; rate: number }
  robot: { units: number; running: number; coverage: number; findings: number }
  routes: InspectionRoute[]
  findings: InspectionFinding[]
}
export interface Maintain {
  stats: { plan: number; done: number; overdue: number; thisWeek: number }
  plans: {
    id: string
    equip: string
    cycle: string
    last: string
    next: string
    vendor: string
    state: string
    deviceId?: string
    category?: string
    source?: 'real' | 'generated'
  }[]
  spares: { id: string; stock: number; min: number; state: string }[]
}
export interface DrillPlan {
  id: number
  code: string
  name: string
  type: string
  date: string
  state: string
  result: string
  source?: 'real' | 'db'
}
export interface Drill {
  stats: { year: number; done: number; pass: number; next: string }
  plans: DrillPlan[]
}
export interface Shift {
  teams: string[]
  today: { onDuty: number; dayShift: number; nightShift: number; leader: string }
  roster: { day: number; day1: string; night: string }[]
}
export interface RiskItem {
  id: number
  code: string
  risk: string
  cat: string
  prob: number
  impact: number
  level: string
  ctrl: string
  owner: string
  closed?: number
}
export interface Risk {
  matrix: RiskItem[]
  stats: { high: number; mid: number; low: number; closed: number }
  /** 运维知识面板：事件→问题→风险 闭环 / 容量联动 */
  knowledge?: PowerKnowledge
}
export interface Knowledge {
  stats: { sop: number; drawing: number; manual: number; emergency: number }
  cats: { id: string; n: number; hot: string }[]
  recent: { title: string; ver: string; date: string; by: string }[]
  /** 运维知识面板：EOP 62 类事件目录 */
  knowledge?: PowerKnowledge
}

/* ===== 外部设备接入数据契约 (采集器对接标准) ===== */
export type MetricQuality = 'good' | 'uncertain' | 'bad'

/** 设备注册请求 (POST /api/external/device/register) — 必填: device_id/ip/sn/model */
export interface ExternalDevice {
  device_id: string
  ip: string
  sn: string
  model: string
  name?: string
  vendor?: string
  domain?: string
  category?: string
  location?: string
  protocol?: string
  tags?: string[]
  description?: string
  extra?: Record<string, unknown>
}

/** 单条实时测点 (POST /api/external/metrics/upload 数组元素) */
export interface MetricPoint {
  device_id: string
  timestamp: string // ISO8601 或 Unix 秒
  metric_name: string // 如 cpu_usage / inlet_temp / power_kw
  value: number
  quality: MetricQuality
  unit?: string
  tags?: Record<string, unknown>
}

export interface DeviceRegisterResponse {
  device_id: string
  status: 'registered' | 'duplicate' | 'updated'
  received_at: string
  message: string
}

/** 设备信息更新请求 (PUT /api/external/devices/{id}) — 所有字段可选 */
export interface DeviceUpdateRequest {
  ip?: string
  sn?: string
  model?: string
  name?: string
  vendor?: string
  domain?: string
  category?: string
  location?: string
  protocol?: string
  tags?: string[]
  description?: string
  extra?: Record<string, unknown>
}

/** 设备操作通用响应 (更新/删除) */
export interface DeviceActionResponse {
  device_id: string
  action: 'updated' | 'deleted'
  received_at: string
  message: string
}

/** 物模型测点定义 */
export interface ThingModelMetricDef {
  metric_name: string
  unit: string
  description: string
}

/** 物模型: 某类设备的传感器/测点模板 */
export interface ThingModelDef {
  category: string
  category_label: string
  domain: string
  protocol: string
  metrics: ThingModelMetricDef[]
}

export interface RejectedItem {
  index: number
  device_id?: string
  reason: string
}

export interface MetricUploadResponse {
  total: number
  accepted: number
  rejected: number
  rejected_items: RejectedItem[]
  received_at: string
  message: string
}

/** 已注册设备视图 (GET /api/external/devices 元素) */
export interface ExternalDeviceView {
  device_id: string
  ip: string
  sn: string
  model: string
  name?: string
  vendor?: string
  domain?: string
  category?: string
  location?: string
  protocol?: string
  tags?: string[]
  description?: string
  extra?: Record<string, unknown>
  registered_at?: string
  last_seen?: string
  metric_count: number
  online: boolean
}

/** 设备注册状态列表响应 (GET /api/external/devices) */
export interface DeviceListResponse {
  total: number
  online: number
  offline: number
  total_metrics: number
  items: ExternalDeviceView[]
}

/** 单条测点记录视图 (GET /api/external/devices/{id}/metrics 元素) */
export interface MetricRecordView {
  device_id: string
  ts?: string
  metric_name: string
  value: number
  quality: MetricQuality
  unit?: string
  received_at?: string
}

/* ===== 物模型驱动·实时/历史查询 (Task 2 数据闭环) ===== */
export interface MetricRealtimePoint {
  metric_name: string
  value: number
  unit?: string
  quality: MetricQuality
}

export interface MetricRealtimeResponse {
  device_id: string
  ts?: string
  online: boolean
  points: MetricRealtimePoint[]
}

export interface MetricHistoryPoint {
  ts: string
  value: number
  quality: MetricQuality
}

export interface MetricHistoryResponse {
  device_id: string
  unit: Record<string, string> // metric_name → 单位
  series: Record<string, MetricHistoryPoint[]> // metric_name → 序列
}

/* ===== 2.3 知识库 / 处置预案 (GET /api/ops/knowledge) ===== */
export interface KnowledgeItem {
  id: number
  code: string
  title: string
  category: string
  domain: string
  type: string // sop/drawing/manual/emergency/case/training
  tags: string[]
  relatedCategories: string[]
  relatedDomains: string[]
  relatedMetrics: string[]
  summary: string
  content: string
  steps: string[]
  owner: string
  hot: boolean
  version: number
  createdAt?: string
  updatedAt?: string
}

/* ===== 2.4 AI 运维助手 (POST /api/ops/assistant/ask) ===== */
export interface AssistantContext {
  system?: string | null
  domain?: string | null
  metric?: string | null
  alarm?: string | null
  page?: string | null
}
export interface AssistantAskReq {
  question: string
  context?: AssistantContext | null
}
export interface AssistantRef {
  code: string
  title: string
  type: string
}
export interface AssistantAskResp {
  question: string
  answer: string
  steps: string[]
  refs: AssistantRef[]
  model: string
  grounded: boolean
  noMatch: boolean
  /** 配置了大模型但调用失败回退时的可读原因（Key 失效/网络不通/模型不存在等） */
  llmError?: string | null
}

/** 大模型接入状态自查响应 (GET /api/ops/assistant/status) */
export interface AssistantStatusResp {
  configured: boolean
  base_url: string
  model: string
  reachable: boolean
  http_status: number | null
  latency: number | null
  model_available: boolean | null
  detail: string
}

/* ===== 2.3 值班排班 (GET /api/ops/shift) ===== */
export interface ShiftMember {
  name: string
  role?: string
  phone?: string
}
export interface ShiftSchedule {
  id: number
  date: string // YYYY-MM-DD
  shift: 'day' | 'night'
  members: ShiftMember[]
  leader: string
  note: string
  createdAt?: string
  updatedAt?: string
}

/* ===== 网络监控域 ===== */
export interface SwitchPort {
  name: string
  alias: string
  status: string
  speed_mbps: number
  in_bps: number
  out_bps: number
  in_util_pct: number
  out_util_pct: number
  in_errors: number
  out_errors: number
  in_discards: number
}
export interface NetworkSwitch {
  id: string
  name: string
  ip: string
  model: string
  role: string
  location: string
  status: string
  cpu_pct: number
  mem_pct: number
  uptime_days: number
  total_ports: number
  up_ports: number
  down_ports: number
  ports: SwitchPort[]
}
export interface NetworkOverview {
  total_switches: number
  online_switches: number
  offline_switches: number
  total_ports: number
  up_ports: number
  down_ports: number
  overall_port_rate: number
  total_traffic_bps: number
  avg_cpu_pct: number
  avg_mem_pct: number
  switches: NetworkSwitch[]
}
export interface PingTarget {
  target: string
  name: string
  category: string
  rtt_min_ms: number
  rtt_avg_ms: number
  rtt_max_ms: number
  loss_pct: number
  jitter_ms: number
  status: string
}
export interface PingOverview {
  targets: PingTarget[]
  avg_rtt_ms: number
  avg_loss_pct: number
  worst_rtt_target: string
}
export interface BwUtilItem {
  rank: number
  name: string
  device: string
  direction: string
  util_pct: number
  traffic_bps: number
  capacity_mbps: number
  alert: boolean
}
export interface BwUtilOverview {
  items: BwUtilItem[]
}

/* ===== 多 DC 聚合 ===== */
export interface DCCampus {
  id: string
  name: string
  short_name: string
  region: string
  city: string
  status: string
  total_devices: number
  online_devices: number
  online_rate: number
  pue: number
  wue: number
  it_load_mw: number
  total_load_mw: number
  today_alarms: number
  availability: number
  alerts_crit: number
  alerts_warn: number
}
export interface CampusesResponse {
  campuses: DCCampus[]
}
export interface CampusComparisonItem {
  metric: string
  label: string
  unit: string
  data: { campus: string; value: number }[]
  best: string
  worst: string
}
export interface CampusComparisonResponse {
  comparisons: CampusComparisonItem[]
}
