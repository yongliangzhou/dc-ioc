<template>
  <div class="trend-chart card">
    <div class="tc-header">
      <span class="tc-title">{{ title }}</span>
      <slot name="actions">
        <TimeRangePicker
          v-if="showRangePicker"
          :model-value="activeRange"
          @update:model-value="onRangeChange"
        />
      </slot>
    </div>
    <div class="tc-body" :style="{ height: containerHeight }">
      <div v-if="loading" class="tc-loader">
        <SkeletonCard size="sm" />
      </div>
      <div v-else-if="isEmpty" class="tc-empty">
        <EmptyState :text="emptyText" />
      </div>
      <div ref="chartRef" class="tc-canvas" v-show="!isEmpty && !loading"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import TimeRangePicker from './TimeRangePicker.vue'
import SkeletonCard from './SkeletonCard.vue'
import EmptyState from './EmptyState.vue'
import {
  CHART_BASE,
  baseGrid,
  baseTooltip,
  baseLegend,
  baseXAxis,
  baseYAxis,
} from '@/assets/echarts-theme'

export interface TrendSeries {
  name: string
  type?: 'line' | 'bar' | 'scatter'
  data?: (number | string | [number, number])[]
  color?: string
  yAxisIndex?: number
  smooth?: boolean
  areaStyle?: boolean | Record<string, unknown>
  lineStyle?: Record<string, unknown>
  symbol?: string
  symbolSize?: number
  barWidth?: string
  itemStyle?: Record<string, unknown>
  silent?: boolean
}

const props = withDefaults(
  defineProps<{
    title?: string
    // 模式 A: 直接传 ECharts option
    option?: echarts.EChartsOption | null
    // 模式 B: xAxisData + series（组件内部构建 option）
    xAxisData?: string[]
    series?: TrendSeries[]
    height?: number
    showRangePicker?: boolean
    loading?: boolean
    emptyText?: string
  }>(),
  {
    title: '',
    showRangePicker: false,
    loading: false,
    emptyText: '暂无趋势数据',
  },
)

const emit = defineEmits<{
  rangeChange: [key: string]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chartInst: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null
let pendingRender = false
const activeRange = ref('24h')

const containerHeight = computed(() => (props.height ? `${props.height}px` : '200px'))

const isEmpty = computed(() => {
  if (props.option) return false
  const seriesData = props.series ?? []
  return seriesData.length === 0 || seriesData.every((s) => !s.data || s.data.length === 0)
})

// 从 xAxisData + series 构建 ECharts option
const builtOption = computed<echarts.EChartsOption>(() => {
  if (props.option) return props.option
  const xData = props.xAxisData ?? []
  const s = props.series ?? []
  if (!xData.length || !s.length) return { series: [] }

  const hasDualY = s.some((ser) => ser.yAxisIndex === 1)
  const yAxis: echarts.YAXisComponentOption[] = [
    {
      ...baseYAxis(),
      nameTextStyle: { color: CHART_BASE.textColor },
    },
  ]
  if (hasDualY) {
    yAxis.push({ ...baseYAxis(), nameTextStyle: { color: CHART_BASE.textColor } })
  }

  const colors = [
    CHART_BASE.labelColor,
    '#22c55e',
    '#f97316',
    '#8b5cf6',
    '#ef4444',
    '#eab308',
    '#3b82f6',
    '#ec4899',
  ]

  const echartsSeries: echarts.SeriesOption[] = s.map((ser, i) => {
    const c = ser.color ?? colors[i % colors.length]
    const base: Record<string, unknown> = {
      name: ser.name,
      type: ser.type ?? 'line',
      data: ser.data ?? [],
      smooth: ser.smooth ?? (ser.type !== 'bar' && ser.type !== 'scatter'),
      symbol: ser.symbol ?? 'none',
      symbolSize: ser.symbolSize,
      lineStyle: ser.lineStyle ? { ...ser.lineStyle, color: c } : { color: c, width: 2 },
      yAxisIndex: ser.yAxisIndex ?? 0,
      silent: ser.silent,
    }

    if (ser.type === 'bar') {
      base.barWidth = ser.barWidth ?? '40%'
      base.itemStyle = ser.itemStyle ?? {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: c },
          { offset: 1, color: 'rgba(0,0,0,0.05)' },
        ]),
      }
      base.smooth = false
      base.symbol = undefined
      base.lineStyle = undefined
    }

    if (ser.type === 'scatter') {
      base.itemStyle = ser.itemStyle ?? { color: c, opacity: 0.8 }
      base.smooth = false
      base.lineStyle = undefined
    }

    if (ser.areaStyle !== undefined) {
      base.areaStyle =
        ser.areaStyle === true
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: c },
                { offset: 1, color: 'rgba(0,0,0,0)' },
              ]),
            }
          : (ser.areaStyle as LineSeriesOption['areaStyle'])
    }

    return base
  })

  return {
    tooltip: baseTooltip(),
    legend: baseLegend(),
    grid: baseGrid({ bottom: s.length > 2 ? 35 : 25 }),
    xAxis: baseXAxis({ data: xData }),
    yAxis,
    series: echartsSeries,
  } as echarts.EChartsOption
})

function onRangeChange(key: string) {
  activeRange.value = key
  emit('rangeChange', key)
}

function initChart() {
  const el = chartRef.value
  if (!el) return
  chartInst = echarts.init(el)
  resizeObserver = new ResizeObserver(() => {
    // 容器尺寸变化（含从隐藏变为显示）时触发，避免 0 尺寸报错
    if (chartInst && el.clientWidth > 0 && el.clientHeight > 0) {
      chartInst.resize()
      if (pendingRender) {
        pendingRender = false
        applyOption()
      }
    }
  })
  resizeObserver.observe(el)
  nextTick(() => {
    // 若挂载时容器已可见则直接渲染，否则等待 ResizeObserver 在显示后触发
    if (el.clientWidth > 0 && el.clientHeight > 0) {
      applyOption()
    } else {
      pendingRender = true
    }
  })
}

function applyOption() {
  if (!chartInst) return
  const el = chartRef.value
  // 容器不可见时暂不渲染，避免 "Can't get DOM width or height"
  if (el && (el.clientWidth === 0 || el.clientHeight === 0)) {
    pendingRender = true
    return
  }
  const opt = builtOption.value
  if (!opt.series || !(opt.series as echarts.SeriesOption[]).length) {
    nextTick(() => {
      chartInst?.clear()
    })
    return
  }
  nextTick(() => {
    chartInst?.setOption(opt, { notMerge: true })
  })
}

watch(
  () => props.option,
  () => applyOption(),
  { deep: true },
)
watch(
  () => [props.xAxisData, props.series],
  () => applyOption(),
  { deep: true },
)

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chartInst?.dispose()
  chartInst = null
})
</script>

<style scoped>
.trend-chart {
  overflow: hidden;
}
.tc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.tc-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--txt);
  letter-spacing: 0.4px;
}
.tc-body {
  position: relative;
  min-height: 200px;
}
.tc-canvas {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
.tc-loader,
.tc-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
