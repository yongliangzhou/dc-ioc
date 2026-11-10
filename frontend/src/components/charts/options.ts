import type { EChartsOption } from '@/hooks/useECharts'
import type { DefaultLabelFormatterCallbackParams } from 'echarts'
import { themeMode } from '@/theme'
import { BAR_THRESHOLDS } from '@/config/metricsCatalog'

/* 主题调色板：优先从 :root 的 CSS 变量读取（唯一色彩来源）。
   DARK/LIGHT 常量仅作为 jsdom / SSR 等「无 CSS 计算样式」环境的镜像兜底，
   其值与 frontend/src/assets/styles/index.scss 的 :root 定义保持一致。 */
const PALETTE_KEYS = ['--cyan', '--blue', '--purple', '--green', '--amber', '--pink', '--red']

export const PALETTE = ['#22e3ff', '#3b82f6', '#9b6bff', '#2bd47a', '#ffb020', '#ff5fa2', '#ff4d5e']
const PALETTE_LIGHT = ['#0891b2', '#2563eb', '#7c3aed', '#16a34a', '#d97706', '#db2777', '#dc2626']

interface ChartVars {
  palette: string[]
  axisLine: string
  axisLabel: string
  splitLine: string
  legendTxt: string
  tooltipBg: string
  tooltipBorder: string
  tooltipTxt: string
  track: string
  strong: string
  pieBorder: string
  accent: string
  red: string
  amber: string
  transparent: string
}

const DARK: ChartVars = {
  palette: PALETTE,
  axisLine: '#1d2f4f',
  axisLabel: '#7e93b8',
  splitLine: 'rgba(29,47,79,.6)',
  legendTxt: '#7e93b8',
  tooltipBg: '#0f1b33',
  tooltipBorder: '#1d2f4f',
  tooltipTxt: '#cfe0ff',
  track: '#13233f',
  strong: '#ffffff',
  pieBorder: '#0a1220',
  accent: '#22e3ff',
  red: '#ff4d5e',
  amber: '#ffb020',
  transparent: 'rgba(34,227,255,.08)',
}
const LIGHT: ChartVars = {
  palette: PALETTE_LIGHT,
  axisLine: '#d4deec',
  axisLabel: '#5a6c88',
  splitLine: 'rgba(212,222,236,.8)',
  legendTxt: '#5a6c88',
  tooltipBg: '#ffffff',
  tooltipBorder: '#d4deec',
  tooltipTxt: '#1e2a3c',
  track: '#dbe4f0',
  strong: '#0b1524',
  pieBorder: '#ffffff',
  accent: '#0891b2',
  red: '#dc2626',
  amber: '#d97706',
  transparent: 'rgba(8,145,178,.08)',
}

/** 读取 :root 上真实生效的 CSS 变量；无 DOM / 无 CSS 时回退到主题镜像值。 */
function cssVar(name: string, fallback: string): string {
  if (typeof document === 'undefined' || typeof window === 'undefined') return fallback
  try {
    const v = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    return v || fallback
  } catch {
    return fallback
  }
}

/** 读取当前主题取色（访问 themeMode.value => 在 computed 中调用可响应主题切换） */
export function chartVars(): ChartVars {
  const base = themeMode.value === 'light' ? LIGHT : DARK
  return {
    palette: PALETTE_KEYS.map((k, i) => cssVar(k, base.palette[i])),
    axisLine: cssVar('--line', base.axisLine),
    axisLabel: cssVar('--txt2', base.axisLabel),
    splitLine: cssVar('--td-line', base.splitLine),
    legendTxt: cssVar('--txt2', base.legendTxt),
    tooltipBg: cssVar('--panel', base.tooltipBg),
    tooltipBorder: cssVar('--line', base.tooltipBorder),
    tooltipTxt: cssVar('--txt', base.tooltipTxt),
    track: cssVar('--track', base.track),
    strong: cssVar('--txt-strong', base.strong),
    pieBorder: cssVar('--map-bg', base.pieBorder),
    accent: cssVar('--cyan', base.accent),
    red: cssVar('--red', base.red),
    amber: cssVar('--amber', base.amber),
    transparent: cssVar('--accent-08', base.transparent),
  }
}

function baseParts() {
  const v = chartVars()
  return {
    v,
    axis: {
      axisLine: { lineStyle: { color: v.axisLine } },
      axisLabel: { color: v.axisLabel, fontSize: 10 },
      splitLine: { lineStyle: { color: v.splitLine } },
      axisTick: { show: false },
    },
    legend: {
      textStyle: { color: v.legendTxt, fontSize: 11 },
      itemWidth: 12,
      itemHeight: 8,
      top: 0,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: v.tooltipBg,
      borderColor: v.tooltipBorder,
      textStyle: { color: v.tooltipTxt, fontSize: 11 },
    },
    grid: { left: 8, right: 12, top: 32, bottom: 4, containLabel: true },
  }
}

/* 折线/面积图 */
export function lineOption(
  x: string[],
  series: {
    name: string
    data: (number | null)[]
    color?: string
    dashed?: boolean
    area?: boolean
  }[],
): EChartsOption {
  const { v, axis, legend, tooltip, grid } = baseParts()
  return {
    backgroundColor: 'transparent',
    color: v.palette,
    tooltip,
    legend,
    grid,
    xAxis: { type: 'category', boundaryGap: false, data: x, ...axis },
    yAxis: { type: 'value', ...axis },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: s.data,
      lineStyle: { width: 2, type: s.dashed ? 'dashed' : 'solid', color: s.color ?? v.palette[i] },
      itemStyle: { color: s.color ?? v.palette[i] },
      areaStyle: s.area ? { opacity: 0.18 } : undefined,
    })),
  } as EChartsOption
}

/* 饼图/环图 */
export function pieOption(
  data: { name: string; value: number }[],
  radius: [string, string] = ['42%', '68%'],
): EChartsOption {
  const { v, legend, tooltip } = baseParts()
  return {
    backgroundColor: 'transparent',
    color: v.palette,
    tooltip: { ...tooltip, trigger: 'item' },
    legend: { ...legend, orient: 'vertical', right: 6, top: 'center' },
    series: [
      {
        type: 'pie',
        radius,
        center: ['38%', '52%'],
        avoidLabelOverlap: true,
        label: { show: false },
        itemStyle: { borderColor: v.pieBorder, borderWidth: 2 },
        emphasis: { label: { show: true, color: v.strong, fontSize: 12, formatter: '{b}\n{d}%' } },
        data,
      },
    ],
  } as EChartsOption
}

/* 横向柱状图：阈值色来自状态 token，不再写 hex 字面量 */
export function barOption(y: string[], data: number[], unit = '%'): EChartsOption {
  const { v, axis, tooltip } = baseParts()
  return {
    backgroundColor: 'transparent',
    tooltip: {
      ...tooltip,
      trigger: 'item',
      formatter: (p: DefaultLabelFormatterCallbackParams) => `${p.name}: ${p.value}${unit}`,
    },
    grid: { left: 8, right: 30, top: 10, bottom: 4, containLabel: true },
    xAxis: { type: 'value', max: 100, ...axis, splitLine: { show: false } },
    yAxis: { type: 'category', data: y, ...axis },
    series: [
      {
        type: 'bar',
        data,
        barWidth: 10,
        itemStyle: {
          borderRadius: [0, 5, 5, 0],
          color: (p: DefaultLabelFormatterCallbackParams) =>
            Number(p.value) > BAR_THRESHOLDS.danger
              ? v.red
              : Number(p.value) > BAR_THRESHOLDS.warn
                ? v.amber
                : v.accent,
        },
        label: {
          show: true,
          position: 'right',
          color: v.axisLabel,
          fontSize: 10,
          formatter: `{c}${unit}`,
        },
      },
    ],
  } as EChartsOption
}

/* 单值环形图 (健康度, 中心显示百分比) */
export function ringOption(pct: number, color?: string): EChartsOption {
  const v = chartVars()
  const c = color ?? v.accent
  return {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'pie',
        radius: ['70%', '88%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        silent: true,
        data: [
          { value: pct, itemStyle: { color: c, shadowBlur: 8, shadowColor: c } },
          { value: 100 - pct, itemStyle: { color: v.track } },
        ],
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: { text: `${pct}%`, fill: v.strong, fontSize: 16, fontWeight: 800 },
      },
    ],
  } as EChartsOption
}

/* 仪表盘 */
export function gaugeOption(
  name: string,
  value: number,
  max = 100,
  unit = '%',
  color?: string,
): EChartsOption {
  const v = chartVars()
  const c = color ?? v.accent
  return {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max,
        radius: '100%',
        center: ['50%', '58%'],
        progress: { show: true, width: 8, itemStyle: { color: c } },
        axisLine: { lineStyle: { width: 8, color: [[1, v.track]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '32%'], color: v.axisLabel, fontSize: 11 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '-2%'],
          color: v.strong,
          fontSize: 22,
          fontWeight: 800,
          formatter: `{value}${unit}`,
        },
        data: [{ value, name }],
      },
    ],
  } as EChartsOption
}
