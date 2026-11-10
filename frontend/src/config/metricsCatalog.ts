/**
 * 指标字典 —— 单位 / 阈值 / 严重度 / 来源 / 分组的唯一来源。
 *
 * 阈值全部来自 docs/design/03_METRICS_IA.md §2 中「当前代码实际渲染的判断表达式」，
 * 不引入代码中不存在的遥测点。新增或调整阈值须业务确认后登记，禁止在模板里
 * 再写数值型三元表达式。
 *
 * 本文件不承载用户可见文案：labelKey 可选，指向已有 i18n 键；组件渲染一律走
 * tl() / t()，因此不需要为此文件新增 zh/en 文案键。
 */

export type MetricPriority = 'P0' | 'P1' | 'P2'
export type MetricSeverity = 'normal' | 'warning' | 'danger'
export type ThresholdDirection = 'above' | 'below'

export interface MetricThresholds {
  /** 达到预警的边界（严格大于 / 小于，与现有页面表达式一致） */
  warn?: number
  /** 达到严重的边界；未配置时该指标不会判为 danger */
  danger?: number
  direction: ThresholdDirection
}

export interface MetricDef {
  key: string
  /** 可选，指向已存在的 i18n 键；缺省时由页面自行 tl() 渲染 */
  labelKey?: string
  /** 统一单位，见 03_METRICS_IA.md §6 单位归一表 */
  unit: string
  precision: number
  thresholds?: MetricThresholds
  priority: MetricPriority
  /** 端点路径，用于可信度标记 */
  source: string
  /** 设备域 */
  group: string
}

const powerFuel = '/api/power/fuel'
const powerBattery = '/api/power/battery'
const powerGenset = '/api/power/genset'
const networkOverview = '/api/network/overview'

export const metricsCatalog: Record<string, MetricDef> = {
  // ---- 燃油系统（PowerFuel.vue :74 :414 :428 :442）----
  'power.fuel.pressure': {
    key: 'power.fuel.pressure',
    unit: 'MPa',
    precision: 2,
    thresholds: { warn: 0.5, direction: 'above' },
    priority: 'P1',
    source: powerFuel,
    group: 'power',
  },
  'power.fuel.fullLoadHours': {
    key: 'power.fuel.fullLoadHours',
    unit: 'h',
    precision: 1,
    thresholds: { warn: 12, danger: 8, direction: 'below' },
    priority: 'P0',
    source: powerFuel,
    group: 'power',
  },
  'power.fuel.halfLoadHours': {
    key: 'power.fuel.halfLoadHours',
    unit: 'h',
    precision: 1,
    thresholds: { warn: 24, direction: 'below' },
    priority: 'P1',
    source: powerFuel,
    group: 'power',
  },
  'power.fuel.dayTankHours': {
    key: 'power.fuel.dayTankHours',
    unit: 'h',
    precision: 1,
    thresholds: { warn: 8, danger: 4, direction: 'below' },
    priority: 'P0',
    source: powerFuel,
    group: 'power',
  },

  // ---- 电池 / UPS（PowerBattery.vue :55 :62 :72 :81 :120 :131）----
  'power.battery.voltage': {
    key: 'power.battery.voltage',
    unit: 'V',
    precision: 1,
    thresholds: { danger: 200, direction: 'below' },
    priority: 'P0',
    source: powerBattery,
    group: 'power',
  },
  'power.battery.current': {
    key: 'power.battery.current',
    unit: 'A',
    precision: 1,
    thresholds: { warn: 200, direction: 'above' },
    priority: 'P1',
    source: powerBattery,
    group: 'power',
  },
  'power.battery.soc': {
    key: 'power.battery.soc',
    unit: '%',
    precision: 1,
    thresholds: { warn: 80, direction: 'below' },
    priority: 'P1',
    source: powerBattery,
    group: 'power',
  },
  'power.battery.soh': {
    key: 'power.battery.soh',
    unit: '%',
    precision: 1,
    thresholds: { warn: 90, direction: 'below' },
    priority: 'P1',
    source: powerBattery,
    group: 'power',
  },
  'power.battery.backupMinutes': {
    key: 'power.battery.backupMinutes',
    unit: 'min',
    precision: 1,
    thresholds: { warn: 15, danger: 10, direction: 'below' },
    priority: 'P0',
    source: powerBattery,
    group: 'power',
  },
  'power.genset.loadRate': {
    key: 'power.genset.loadRate',
    unit: '%',
    precision: 1,
    thresholds: { warn: 80, direction: 'above' },
    priority: 'P1',
    source: powerGenset,
    group: 'power',
  },

  // ---- 网络设备（NetworkSwitches.vue :19 :28 :45；NetworkWireless.vue :81）----
  'network.switch.cpu': {
    key: 'network.switch.cpu',
    unit: '%',
    precision: 1,
    thresholds: { warn: 60, danger: 80, direction: 'above' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },
  'network.switch.memory': {
    key: 'network.switch.memory',
    unit: '%',
    precision: 1,
    thresholds: { warn: 60, danger: 80, direction: 'above' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },
  'network.switch.portAvailableRate': {
    key: 'network.switch.portAvailableRate',
    unit: '%',
    precision: 1,
    thresholds: { warn: 95, direction: 'below' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },
  'network.wireless.onlineRate': {
    key: 'network.wireless.onlineRate',
    unit: '%',
    precision: 1,
    thresholds: { warn: 90, direction: 'below' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },
  // 网络总览页原有阈值（NetworkDashboard.vue :35 :37 :45 :48）
  'network.pingMs': {
    key: 'network.pingMs',
    unit: 'ms',
    precision: 1,
    thresholds: { warn: 20, danger: 50, direction: 'above' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },
  'network.bwUtilization': {
    key: 'network.bwUtilization',
    unit: '%',
    precision: 1,
    thresholds: { warn: 70, danger: 85, direction: 'above' },
    priority: 'P1',
    source: networkOverview,
    group: 'network',
  },

  // ---- 容量（CapacityWhatIf.vue :155 :161；capacity_whatif.py :31-32）----
  'capacity.usedRatio': {
    key: 'capacity.usedRatio',
    unit: '%',
    precision: 1,
    thresholds: { warn: 85, direction: 'above' },
    priority: 'P1',
    source: '/api/ops/capacity',
    group: 'capacity',
  },
}

/** 容量 What-If 的两档阈值（85% 预警 / 100% 满载） */
export const CAPACITY_THRESHOLDS = { warn: 85, full: 100 } as const

/** 横向柱状图的阈值着色（原 charts/options.ts barOption 的 70 / 85） */
export const BAR_THRESHOLDS = { warn: 70, danger: 85 } as const

/** 按字典判定严重度；未登记指标或非有限值一律 normal */
export function severityOf(key: string, value: number | null | undefined): MetricSeverity {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'normal'
  const t = metricsCatalog[key]?.thresholds
  if (!t) return 'normal'
  if (t.direction === 'above') {
    if (t.danger !== undefined && value > t.danger) return 'danger'
    if (t.warn !== undefined && value > t.warn) return 'warning'
  } else {
    if (t.danger !== undefined && value < t.danger) return 'danger'
    if (t.warn !== undefined && value < t.warn) return 'warning'
  }
  return 'normal'
}

/** 按字典精度格式化数值（单位由调用方追加） */
export function formatMetric(key: string, value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-'
  const def = metricsCatalog[key]
  return def ? value.toFixed(def.precision) : String(value)
}
