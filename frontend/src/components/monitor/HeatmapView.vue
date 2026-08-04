<template>
  <div class="heatmap-view card">
    <div class="hm-header" v-if="title">
      <span class="hm-title">{{ title }}</span>
    </div>
    <div class="hm-body">
      <div v-if="loading" class="hm-loader">
        <SkeletonCard size="sm" />
      </div>
      <div v-else-if="isEmpty" class="hm-empty">
        <EmptyState :text="emptyText" />
      </div>
      <template v-else>
        <div ref="chartRef" class="hm-canvas"></div>
        <div v-if="valueRange" class="hm-legend">
          <span class="hm-legend-label">{{ valueRangeLabelLow }}</span>
          <div class="hm-legend-bar" :style="{ background: gradientCSS }"></div>
          <span class="hm-legend-label">{{ valueRangeLabelHigh }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import SkeletonCard from './SkeletonCard.vue'
import EmptyState from './EmptyState.vue'

const props = withDefaults(
  defineProps<{
    title?: string
    // Mode A: structured data
    data?: { xLabels: string[]; yLabels: string[]; values: number[][] }
    // Mode B: raw coordinates (will internal convert)
    xAxisData?: string[]
    yAxisData?: string[]
    heatData?: [number, number, number][]
    // Config
    valueRange?: [number, number]
    colors?: string[]
    unit?: string
    loading?: boolean
    emptyText?: string
  }>(),
  {
    colors: () => ['#06b6d4', '#22c55e', '#eab308', '#f97316', '#ef4444'],
    unit: '℃',
    loading: false,
    emptyText: '暂无数据',
  },
)

const chartRef = ref<HTMLDivElement | null>(null)
let chartInst: echarts.ECharts | null = null
let ro: ResizeObserver | null = null
let pendingRender = false

const gradientCSS = computed(
  () => `linear-gradient(90deg, ${(props.colors ?? ['#06b6d4', '#ef4444']).join(',')})`,
)

const valueRangeLabelLow = computed(() => (props.valueRange ? String(props.valueRange[0]) : '低'))
const valueRangeLabelHigh = computed(() => (props.valueRange ? String(props.valueRange[1]) : '高'))

// Normalize data: accept both Mode A (data) and Mode B (xAxisData+yAxisData+heatData)
const normData = computed<{ xLabels: string[]; yLabels: string[]; values: number[][] } | null>(
  () => {
    if (props.data) return props.data
    if (props.xAxisData && props.yAxisData && props.heatData && props.heatData.length > 0) {
      const xL = [...new Set(props.heatData.map((d) => d[0]))].sort((a, b) => a - b)
      const yL = [...new Set(props.heatData.map((d) => d[1]))].sort((a, b) => a - b)
      const vals: number[][] = yL.map(() => new Array(xL.length).fill(0))
      for (const [xi, yi, v] of props.heatData) {
        const col = xL.indexOf(xi)
        const row = yL.indexOf(yi)
        if (row >= 0 && col >= 0) vals[row][col] = v
      }
      return {
        xLabels: xL.map((i) => String(props.xAxisData![i] ?? i)),
        yLabels: yL.map((i) => String(props.yAxisData![i] ?? i)),
        values: vals,
      }
    }
    return null
  },
)

const isEmpty = computed(() => !normData.value)

function buildOption(): echarts.EChartsOption {
  const d = normData.value
  if (!d) return {}
  const { xLabels, yLabels, values } = d
  const heatData: [number, number, number][] = []
  for (let yi = 0; yi < yLabels.length; yi++) {
    for (let xi = 0; xi < xLabels.length; xi++) {
      heatData.push([xi, yi, values[yi]?.[xi] ?? 0])
    }
  }
  const [vMin, vMax] = props.valueRange ?? [
    Math.min(...heatData.map((h) => h[2])),
    Math.max(...heatData.map((h) => h[2])),
  ]

  return {
    tooltip: {
      position: 'top',
      formatter: (p) => {
        const params = Array.isArray(p) ? p[0] : p
        const v = (Array.isArray(params.value) ? params.value : []) as number[]
        return `${yLabels[v[1]]}<br/>${xLabels[v[0]]}: <b>${v[2]}${props.unit}</b>`
      },
    },
    grid: { left: 80, right: 80, top: 10, bottom: 10 },
    xAxis: {
      type: 'category' as const,
      data: xLabels,
      axisLabel: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#334155' } },
      position: 'top' as const,
    },
    yAxis: {
      type: 'category' as const,
      data: yLabels,
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    visualMap: {
      min: vMin,
      max: vMax,
      calculable: true,
      orient: 'vertical' as const,
      right: 0,
      top: 'center',
      inRange: { color: props.colors },
      text: [String(vMax), String(vMin)],
      textStyle: { color: '#94a3b8', fontSize: 10 },
    },
    series: [
      {
        name: props.title ?? 'Heatmap',
        type: 'heatmap',
        data: heatData,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
      },
    ],
  }
}

function render() {
  if (!chartInst || !normData.value) return
  const el = chartRef.value
  if (el && (el.clientWidth === 0 || el.clientHeight === 0)) {
    pendingRender = true
    return
  }
  chartInst.setOption(buildOption(), { notMerge: true })
}

watch(() => [props.data, props.xAxisData, props.yAxisData, props.heatData], render, { deep: true })

onMounted(() => {
  const el = chartRef.value
  if (!el) return
  chartInst = echarts.init(el)
  ro = new ResizeObserver(() => {
    if (chartInst && el.clientWidth > 0 && el.clientHeight > 0) {
      chartInst.resize()
      if (pendingRender) {
        pendingRender = false
        render()
      }
    }
  })
  ro.observe(el)
  nextTick(() => {
    if (el.clientWidth > 0 && el.clientHeight > 0) render()
    else pendingRender = true
  })
})

onUnmounted(() => {
  ro?.disconnect()
  chartInst?.dispose()
})
</script>

<style scoped>
.heatmap-view {
  overflow: hidden;
}
.hm-header {
  margin-bottom: 8px;
}
.hm-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--txt);
}
.hm-body {
  position: relative;
}
.hm-canvas {
  width: 100%;
  height: 280px;
}
.hm-loader,
.hm-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
}
.hm-legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 6px;
}
.hm-legend-bar {
  width: 120px;
  height: 10px;
  border-radius: 5px;
}
.hm-legend-label {
  font-size: 10px;
  color: var(--txt3);
}
</style>
