/**
 * 统一 ECharts 深色主题 and 颜色板
 * 所有图表组件共用此配置
 */
import * as echarts from 'echarts'

// ---- 统一调色板 ----
export const CHART_COLORS = {
  cyan: '#06b6d4',
  blue: '#3b82f6',
  green: '#22c55e',
  orange: '#f97316',
  red: '#ef4444',
  purple: '#8b5cf6',
  yellow: '#eab308',
  amber: '#ffb020',
  pink: '#ec4899',
  teal: '#14b8a6',
  // 多系列图自动轮换
  palette: [
    '#06b6d4',
    '#f97316',
    '#8b5cf6',
    '#22c55e',
    '#3b82f6',
    '#ef4444',
    '#eab308',
    '#ec4899',
    '#14b8a6',
    '#fb923c',
  ],
} as const

// ---- 图表基础颜色 ----
export const CHART_BASE = {
  background: 'transparent',
  textColor: '#94a3b8',
  labelColor: '#64748b',
  splitLine: '#1e293b',
  axisLine: '#334155',
  transparent: 'rgba(6,182,212,0.08)',
}

// ---- 基础 grid 配置 ----
export function baseGrid(overrides?: Record<string, any>) {
  return {
    left: 55,
    right: 20,
    top: 20,
    bottom: 30,
    containLabel: false,
    ...overrides,
  }
}

// ---- 基础 tooltip 配置 ----
export function baseTooltip(overrides?: Record<string, any>) {
  return {
    trigger: 'axis' as const,
    backgroundColor: 'rgba(15, 27, 51, 0.95)',
    borderColor: CHART_BASE.splitLine,
    textStyle: { color: CHART_BASE.textColor, fontSize: 12 },
    ...overrides,
  }
}

// ---- 基础 xAxis 配置 ----
export function baseXAxis(overrides?: Record<string, any>) {
  return {
    type: 'category' as const,
    axisLabel: { color: CHART_BASE.labelColor, fontSize: 10 },
    axisLine: { lineStyle: { color: CHART_BASE.axisLine } },
    axisTick: { show: false },
    splitLine: { show: false },
    ...overrides,
  }
}

// ---- 基础 yAxis 配置 ----
export function baseYAxis(overrides?: Record<string, any>) {
  return {
    type: 'value' as const,
    axisLabel: { color: CHART_BASE.labelColor },
    splitLine: { lineStyle: { color: CHART_BASE.splitLine } },
    ...overrides,
  }
}

// ---- 基础 legend 配置 ----
export function baseLegend(overrides?: Record<string, any>) {
  return {
    bottom: 0,
    textStyle: { color: CHART_BASE.textColor, fontSize: 11 },
    ...overrides,
  }
}

// ---- 柱状图渐变填充 ----
export function barGradient(color: string) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color },
    { offset: 1, color: 'rgba(0,0,0,0)' },
  ])
}

// ---- 折线图面积渐变填充 ----
export function areaGradient(color: string, alpha?: number) {
  const a = alpha ?? 0.12
  return {
    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: color.replace(')', `,${a})`).replace('rgb', 'rgba') },
      { offset: 1, color: 'rgba(0,0,0,0)' },
    ]),
  }
}

// ---- 快速创建折线 series ----
export function lineSeries(
  name: string,
  data: any[],
  color: string,
  overrides?: Record<string, any>,
) {
  return {
    name,
    type: 'line' as const,
    data,
    smooth: true,
    symbol: 'none' as const,
    lineStyle: { color, width: 2 },
    ...overrides,
  }
}

// ---- 快速创建柱状 series ----
export function barSeries(
  name: string,
  data: any[],
  color: string,
  overrides?: Record<string, any>,
) {
  return {
    name,
    type: 'bar' as const,
    data,
    barWidth: '40%',
    itemStyle: barGradient(color),
    ...overrides,
  }
}
