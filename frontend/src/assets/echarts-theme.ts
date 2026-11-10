/**
 * 统一 ECharts 主题与颜色板（monitor 侧图表基础设施）
 * 颜色不再硬编码：全部通过 chartVars() 从 :root 的 CSS 变量解析，
 * 用 getter 保证主题切换后每次构造 option 都取到当前主题值。
 */
import echarts from '@/utils/echarts'
import type * as echartsTypes from 'echarts'
import { chartVars } from '@/components/charts/options'

// ---- 统一调色板（getter：跟随主题） ----
export const CHART_COLORS = {
  get cyan() {
    return chartVars().accent
  },
  get blue() {
    return chartVars().palette[1]
  },
  get green() {
    return chartVars().palette[3]
  },
  get orange() {
    return chartVars().amber
  },
  get red() {
    return chartVars().red
  },
  get purple() {
    return chartVars().palette[2]
  },
  get yellow() {
    return chartVars().amber
  },
  get amber() {
    return chartVars().amber
  },
  get pink() {
    return chartVars().palette[5]
  },
  get teal() {
    return chartVars().accent
  },
  get palette() {
    return chartVars().palette
  },
}

// ---- 图表基础颜色（getter：跟随主题） ----
export const CHART_BASE = {
  background: 'transparent',
  get textColor() {
    return chartVars().axisLabel
  },
  get labelColor() {
    return chartVars().axisLabel
  },
  get splitLine() {
    return chartVars().axisLine
  },
  get axisLine() {
    return chartVars().axisLine
  },
  get transparent() {
    return chartVars().transparent
  },
}

// ---- 基础 grid 配置 ----
export function baseGrid(
  overrides?: Partial<echartsTypes.GridComponentOption>,
): echartsTypes.GridComponentOption {
  return { left: 55, right: 20, top: 20, bottom: 30, containLabel: false, ...overrides }
}

// ---- 基础 tooltip 配置 ----
export function baseTooltip(
  overrides?: Partial<echartsTypes.TooltipComponentOption>,
): echartsTypes.TooltipComponentOption {
  const v = chartVars()
  return {
    trigger: 'axis',
    backgroundColor: v.tooltipBg,
    borderColor: v.tooltipBorder,
    textStyle: { color: v.tooltipTxt, fontSize: 12 },
    ...overrides,
  }
}

// ---- 基础 xAxis 配置 ----
export function baseXAxis(
  overrides?: Partial<echartsTypes.XAXisComponentOption>,
): echartsTypes.XAXisComponentOption {
  const v = chartVars()
  return {
    type: 'category',
    axisLabel: { color: v.axisLabel, fontSize: 10 },
    axisLine: { lineStyle: { color: v.axisLine } },
    axisTick: { show: false },
    splitLine: { show: false },
    ...overrides,
  }
}

// ---- 基础 yAxis 配置 ----
export function baseYAxis(
  overrides?: Partial<echartsTypes.YAXisComponentOption>,
): echartsTypes.YAXisComponentOption {
  const v = chartVars()
  return {
    type: 'value',
    axisLabel: { color: v.axisLabel },
    splitLine: { lineStyle: { color: v.splitLine } },
    ...overrides,
  }
}

// ---- 基础 legend 配置 ----
export function baseLegend(
  overrides?: Partial<echartsTypes.LegendComponentOption>,
): echartsTypes.LegendComponentOption {
  return { bottom: 0, textStyle: { color: chartVars().axisLabel, fontSize: 11 }, ...overrides }
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
  data: echartsTypes.LineSeriesOption['data'],
  color: string,
  overrides?: Partial<echartsTypes.LineSeriesOption>,
): echartsTypes.LineSeriesOption {
  return {
    name,
    type: 'line',
    data,
    smooth: true,
    symbol: 'none',
    lineStyle: { color, width: 2 },
    ...overrides,
  }
}

// ---- 快速创建柱状 series ----
export function barSeries(
  name: string,
  data: echartsTypes.BarSeriesOption['data'],
  color: string,
  overrides?: Partial<echartsTypes.BarSeriesOption>,
): echartsTypes.BarSeriesOption {
  return {
    name,
    type: 'bar' as const,
    data,
    barWidth: '40%',
    itemStyle: { color: barGradient(color) },
    ...overrides,
  }
}
