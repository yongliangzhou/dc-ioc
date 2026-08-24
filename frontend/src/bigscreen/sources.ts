import { getDashboardOverview, getActiveAlarms } from '@/api/index'
import { getHvacOverview } from '@/api/hvac'
import type { DashboardOverview } from '@/types'

export type WidgetType = 'kpi' | 'gauge' | 'line' | 'bar'

export interface DataSourceTemplate {
  id: string
  label: string
  type: WidgetType
  unit?: string
  // 从聚合数据中提取数值 (大屏加载时统一 fetch 一次 overview)
  pick: (d: DashboardOverview, extra: { activeAlarms: number; cop: number }) => number
  // 生成时序样例 (用于 line/bar 演示趋势)
  series?: (base: number) => number[]
  max?: number // gauge 量程
  color?: string
}

// ---- 可用数据源池 (定制大屏可选) ----
export const SOURCE_POOL: DataSourceTemplate[] = [
  {
    id: 'pue',
    label: 'PUE',
    type: 'gauge',
    unit: '',
    pick: (d) => d.pue,
    max: 2.5,
    color: '#22e3ff',
  },
  {
    id: 'it_load',
    label: 'IT 负载',
    type: 'kpi',
    unit: 'MW',
    pick: (d) => d.it_load_mw ?? 0,
  },
  {
    id: 'cool_load',
    label: '制冷负载',
    type: 'kpi',
    unit: 'MW',
    pick: (d) => d.cool_load_mw ?? 0,
  },
  {
    id: 'total_load',
    label: '总负载',
    type: 'kpi',
    unit: 'MW',
    pick: (d) => d.total_load_mw ?? 0,
  },
  {
    id: 'online_rate',
    label: '设备在线率',
    type: 'gauge',
    unit: '%',
    pick: (d) => d.online_rate,
    max: 100,
    color: '#2bd47a',
  },
  {
    id: 'today_alarms',
    label: '今日告警',
    type: 'kpi',
    unit: '条',
    pick: (_d, e) => e.activeAlarms,
  },
  {
    id: 'availability',
    label: '可用性',
    type: 'gauge',
    unit: '%',
    pick: (d) => d.availability ?? 0,
    max: 100,
    color: '#ffb020',
  },
  {
    id: 'free_cool',
    label: '自然冷源小时',
    type: 'kpi',
    unit: 'h',
    pick: (d) => d.free_cool_hours ?? 0,
  },
  {
    id: 'cop',
    label: '制冷 COP',
    type: 'gauge',
    unit: '',
    pick: (_d, e) => e.cop,
    max: 8,
    color: '#3b82f6',
  },
  {
    id: 'total_devices',
    label: '设备总数',
    type: 'kpi',
    unit: '台',
    pick: (d) => d.total_devices,
  },
]

// ---- 肤色预设 ----
export const SKIN_PRESETS = [
  { id: 'cyan', label: '科技青', color: '#22e3ff', blue: '#3b82f6', green: '#2bd47a', amber: '#ffb020' },
  { id: 'blue', label: '深空蓝', color: '#3b82f6', blue: '#6366f1', green: '#0ea5e9', amber: '#38bdf8' },
  { id: 'green', label: '生态绿', color: '#2bd47a', blue: '#10b981', green: '#22c55e', amber: '#84cc16' },
  { id: 'purple', label: '神秘紫', color: '#a855f7', blue: '#8b5cf6', green: '#d946ef', amber: '#f472b6' },
  { id: 'orange', label: '暖橙', color: '#fb923c', blue: '#f97316', green: '#f59e0b', amber: '#fbbf24' },
]

// ---- 大屏配置结构 ----
export interface BigScreenConfig {
  title: string
  skin: string // SKIN_PRESETS id
  customColor?: string // 自定义主色 (覆盖)
  theme: 'dark' | 'light'
  sourceIds: string[]
  refreshSec: number
}

export const DEFAULT_CONFIG: BigScreenConfig = {
  title: '数据中心运营大屏',
  skin: 'cyan',
  theme: 'dark',
  sourceIds: ['pue', 'it_load', 'cool_load', 'online_rate', 'today_alarms', 'availability'],
  refreshSec: 10,
}

const STORAGE_KEY = 'dcioc-bigscreen-config'

export function loadConfig(): BigScreenConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_CONFIG }
}

export function saveConfig(cfg: BigScreenConfig) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg))
  } catch {
    /* ignore */
  }
}

// 应用肤色到 CSS 变量 + 同步 ECharts 主色
export function applySkin(cfg: BigScreenConfig) {
  const preset = SKIN_PRESETS.find((s) => s.id === cfg.skin) || SKIN_PRESETS[0]
  const root = document.documentElement
  root.style.setProperty('--cyan', cfg.customColor || preset.color)
  root.style.setProperty('--blue', preset.blue)
  root.style.setProperty('--green', preset.green)
  root.style.setProperty('--amber', preset.amber)
}

export async function fetchOverview(): Promise<{ overview: DashboardOverview; activeAlarms: number; cop: number }> {
  const [ov, alarms, hvac] = await Promise.all([
    getDashboardOverview(),
    getActiveAlarms().catch(() => ({ items: [] as any[] })),
    getHvacOverview().catch(() => null),
  ])
  const activeAlarms = (alarms as any)?.items?.length ?? 0
  let cop = 0
  const chiller = (hvac as any)?.chiller
  if (chiller?.chillerGroups?.length) {
    const cops = chiller.chillerGroups.map((g: any) => Number(g.chiller?.cop)).filter((x: number) => x > 0)
    cop = cops.length ? +(cops.reduce((a: number, b: number) => a + b, 0) / cops.length).toFixed(2) : 0
  }
  return { overview: ov, activeAlarms, cop }
}
