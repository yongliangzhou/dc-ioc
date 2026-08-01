<template>
  <div class="trend-card card">
    <!-- Header -->
    <div class="tc-head">
      <div class="tc-title">
        <ChartArea :size="16" class="tc-title-icon" />
        <span class="section-title-inline">{{ selectedLabel }}</span>
        <span v-if="unit" class="tc-unit">{{ unit }}</span>
      </div>
      <div class="tc-controls">
        <!-- Time range buttons -->
        <button
          v-for="r in ranges"
          :key="r.key"
          class="tc-btn"
          :class="{ active: currentRange === r.key }"
          @click="switchRange(r.key)"
        >
          <Clock v-if="currentRange === r.key" :size="10" />
          {{ r.label }}
        </button>
        <!-- Metric selector -->
        <button
          v-if="metrics.length > 1"
          class="tc-btn tc-sel"
          @click="showPicker = !showPicker"
        >
          <SlidersHorizontal :size="14" />
        </button>
      </div>
    </div>

    <!-- Metric picker dropdown -->
    <div v-if="showPicker && metrics.length > 1" class="tc-picker">
      <div
        v-for="m in metrics"
        :key="m.name"
        class="tc-opt"
        :class="{ active: m.name === active }"
        @click="selectMetric(m.name)"
      >
        <span class="dot" :class="{ g: !loading, o: loading }"></span>
        {{ m.label }}
        <span class="tc-opt-unit">{{ m.unit }}</span>
        <span class="tc-opt-val">{{ m.latest?.toFixed(1) ?? '—' }}</span>
      </div>
    </div>

    <!-- Chart area -->
    <div class="tc-chart-wrap">
      <div v-if="loading" class="tc-loading">
        <RefreshCw :size="16" class="tc-spin" />
        <span>加载中...</span>
      </div>
      <div v-else-if="!hasData" class="tc-empty">
        <BarChart3 :size="32" class="tc-empty-icon" />
        <span>暂无趋势数据</span>
      </div>
      <BaseChart v-else ref="chartRef" :option="chartOption" height="220px" />
    </div>

    <!-- Stats footer -->
    <div v-if="hasData" class="tc-footer flex between">
      <span class="tc-stat">
        <span class="tc-stat-label">{{ minLabel }}</span>
        <span class="tc-stat-val">{{ minVal }}</span>
      </span>
      <span class="tc-stat">
        <span class="tc-stat-label">{{ avgLabel }}</span>
        <span class="tc-stat-val">{{ avgVal }}</span>
      </span>
      <span class="tc-stat">
        <span class="tc-stat-label">{{ maxLabel }}</span>
        <span class="tc-stat-val">{{ maxVal }}</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import { lineOption, PALETTE } from '@/components/charts/options'
import { Clock, SlidersHorizontal, ChartArea, RefreshCw, BarChart3 } from 'lucide-vue-next'
import type { MetricHistoryPoint } from '@/types'

export interface TrendMetric {
  name: string
  label: string
  unit: string
  latest?: number
}

const props = withDefaults(
  defineProps<{
    metrics: TrendMetric[]
    active?: string
    series?: Record<string, MetricHistoryPoint[]>
    unitMap?: Record<string, string>
    loading?: boolean
  }>(),
  {
    active: '',
    series: () => ({}),
    unitMap: () => ({}),
    loading: false,
  }
)

const emit = defineEmits<{
  select: [metricName: string]
  rangeChange: [range: string]
}>()

const chartRef = ref<InstanceType<typeof BaseChart> | null>(null)
const showPicker = ref(false)
const currentRange = ref('30m')

const ranges = [
  { key: '5m', label: '5m' },
  { key: '15m', label: '15m' },
  { key: '30m', label: '30m' },
  { key: '1h', label: '1h' },
  { key: '6h', label: '6h' },
  { key: '24h', label: '24h' },
]

const activeMetric = computed(() => {
  return props.metrics.find(m => m.name === props.active) ?? props.metrics[0] ?? null
})

const selectedLabel = computed(() => activeMetric.value?.label ?? props.active ?? '趋势')
const unit = computed(() => activeMetric.value?.unit ?? props.unitMap[props.active] ?? '')

const pts = computed((): MetricHistoryPoint[] => {
  return props.series[props.active] ?? []
})

const hasData = computed(() => pts.value.length > 0)

const xLabels = computed(() => {
  return pts.value.map(p => {
    const d = new Date(p.ts)
    if (currentRange.value === '24h' || currentRange.value === '6h') {
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  })
})

const values = computed(() => pts.value.map(p => p.value))

const chartOption = computed(() => {
  if (!hasData.value) return {}
  const idx = activeMetric.value ? props.metrics.indexOf(activeMetric.value) : 0
  const color = PALETTE[Math.max(0, idx) % PALETTE.length]
  return lineOption(xLabels.value, [
    { name: selectedLabel.value, data: values.value, color, area: true },
  ])
})

const minVal = computed(() => !values.value.length ? '—' : Math.min(...values.value).toFixed(2))
const maxVal = computed(() => !values.value.length ? '—' : Math.max(...values.value).toFixed(2))
const avgVal = computed(() => {
  if (!values.value.length) return '—'
  return (values.value.reduce((a, b) => a + b, 0) / values.value.length).toFixed(2)
})
const minLabel = '最低'
const avgLabel = '平均'
const maxLabel = '最高'

function selectMetric(name: string): void {
  emit('select', name)
  showPicker.value = false
}

function switchRange(key: string): void {
  currentRange.value = key
  emit('rangeChange', key)
}
</script>

<style scoped>
.trend-card {
  padding: 16px;
}

.tc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  position: relative;
}

.tc-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tc-title-icon {
  color: var(--cyan);
  opacity: 0.7;
}
.section-title-inline {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--cyan);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.section-title-inline::before {
  content: '';
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: var(--cyan);
  box-shadow: var(--glow);
}
.tc-unit {
  font-size: 11px;
  color: var(--txt3);
  font-weight: 500;
  margin-left: 4px;
}

.tc-controls {
  display: flex;
  gap: 4px;
  position: relative;
}
.tc-btn {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 3px;
}
.tc-btn:hover {
  border-color: var(--cyan);
  color: #fff;
}
.tc-btn.active {
  background: rgba(34, 227, 255, 0.12);
  border-color: var(--cyan);
  color: var(--cyan);
  font-weight: 600;
}
.tc-sel {
  padding: 3px 6px;
}

.tc-picker {
  position: absolute;
  top: 44px;
  right: 16px;
  z-index: 10;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  min-width: 220px;
  max-height: 260px;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  padding: 4px;
}
.tc-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  color: var(--txt);
}
.tc-opt:hover {
  background: rgba(34, 227, 255, 0.08);
}
.tc-opt.active {
  background: rgba(34, 227, 255, 0.12);
  color: var(--cyan);
  font-weight: 600;
}
.tc-opt-unit {
  font-size: 10px;
  color: var(--txt3);
  margin-left: auto;
}
.tc-opt-val {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--txt);
  margin-left: 8px;
  min-width: 48px;
  text-align: right;
}

.tc-chart-wrap {
  min-height: 220px;
  position: relative;
}
.tc-loading,
.tc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 220px;
  color: var(--txt3);
  font-size: 13px;
}
.tc-empty-icon {
  opacity: 0.3;
}
.tc-spin {
  animation: tc-spin 1s linear infinite;
}
@keyframes tc-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tc-footer {
  margin-top: 6px;
  gap: 12px;
}
.tc-stat {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tc-stat-label {
  font-size: 10px;
  color: var(--txt3);
}
.tc-stat-val {
  font-size: 11px;
  font-weight: 600;
  color: var(--txt);
  font-variant-numeric: tabular-nums;
}
</style>
