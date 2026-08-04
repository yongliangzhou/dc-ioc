<template>
  <div class="dm-root">
    <!-- View Head -->
    <div class="view-head">
      <h1>
        <component :is="categoryIcon" :size="20" class="dm-cat-icon" />
        {{ thingModelLabel }}
      </h1>
      <span class="sub">{{ deviceName }}</span>
      <span class="dm-device-id mono muted">{{ deviceId }}</span>
      <span class="pill" :class="{ g: online, r: !online }">
        <span class="dot" :class="{ g: online, r: !online }"></span>
        {{ online ? '在线' : '离线' }}
      </span>
      <span class="tag b" v-if="protocol">{{ protocol }}</span>
      <span class="tag" :class="{ g: wsConnected, o: !wsConnected }" style="margin-left: auto">
        <Signal :size="10" />
        {{ wsConnected ? '实时' : '轮询' }}
      </span>
    </div>

    <!-- KPI Header Row -->
    <div class="dm-kpi-row" v-if="kpiCards.length">
      <div class="dm-kpi" v-for="k in kpiCards" :key="k.name">
        <span class="dm-kpi-label">{{ k.label }}</span>
        <span class="dm-kpi-value" :style="{ color: k.color }">{{ k.displayValue }}</span>
        <small v-if="k.unit" class="dm-kpi-unit">{{ k.unit }}</small>
      </div>
    </div>

    <!-- MetricCards Grid -->
    <div class="section-title">
      <Activity :size="14" class="dm-sec-icon" />
      实时测点
    </div>
    <div v-if="!metricCards.length" class="dm-empty muted">
      该设备暂无物模型测点数据。请确认 collector 已上报或检查设备注册状态。
    </div>
    <div v-else class="grid" :class="`cols-${gridCols}`">
      <MetricCard
        v-for="card in metricCards"
        :key="card.name"
        :metric-name="card.name"
        :label="card.label"
        :value="card.value"
        :unit="card.unit"
        :quality="card.quality"
        :online="online"
        :spark-data="card.spark"
        :severity="card.severity"
        :stale="card.stale"
        :last-update-ts="card.lastUpdateTs"
        :icon-hint="card.name"
        @select="onMetricSelect"
      />
    </div>

    <!-- Trend Section -->
    <div class="section-title">
      <TrendingUp :size="14" class="dm-sec-icon" />
      趋势分析
    </div>
    <TrendChart
      :metrics="trendMetrics"
      :active="activeMetric"
      :series="trendSeries"
      :unit-map="trendUnitMap"
      :loading="loadingHistory"
      @select="onTrendSelect"
      @range-change="onRangeChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, type Component } from 'vue'
import { useTelemetry } from '@/hooks/useTelemetry'
import MetricCard from '@/components/common/MetricCard.vue'
import TrendChart, { type TrendMetric } from '@/components/charts/TrendChart.vue'
import {
  Activity,
  TrendingUp,
  Signal,
  CircuitBoard,
  CircleGauge,
  Zap,
  Thermometer,
} from 'lucide-vue-next'
import type { ThingModelDef, ThingModelMetricDef, MetricHistoryPoint, MetricQuality } from '@/types'
import { PALETTE } from '@/components/charts/options'

const props = withDefaults(
  defineProps<{
    deviceId: string
    deviceName?: string
    thingModels?: ThingModelDef[]
    metricLabels?: Record<string, string>
    category?: string
    protocol?: string
    kpiMetrics?: string[]
  }>(),
  {
    deviceName: '',
    thingModels: () => [],
    metricLabels: () => ({}),
    category: '',
    protocol: '',
    kpiMetrics: () => [],
  },
)

/* ---- ThingModel matching ---- */
const thingModel = computed<ThingModelDef | null>(() => {
  if (props.category && props.thingModels.length) {
    return props.thingModels.find((t) => t.category === props.category) ?? null
  }
  const prefix = props.deviceId.split('-')[0]?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    ch: 'chiller',
    cr: 'crac',
    ct: 'cooling_tower',
    cp: 'chw_pump',
    ba: 'battery',
    ge: 'genset',
    up: 'ups',
    fu: 'fuel_tank',
    hv: 'hv_switch',
    lv: 'lv_switchgear',
  }
  const cat = map[prefix.slice(0, 2)] ?? prefix
  return props.thingModels.find((t) => t.category === cat) ?? null
})

const thingModelLabel = computed(() => {
  return thingModel.value?.category_label ?? props.deviceName ?? props.deviceId
})

const metrics = computed<ThingModelMetricDef[]>(() => {
  return thingModel.value?.metrics ?? []
})

/* ---- Icon heuristics by category ---- */
const categoryIcon = computed<Component>(() => {
  const cat = thingModel.value?.category?.toLowerCase() ?? ''
  const domain = thingModel.value?.domain?.toLowerCase() ?? ''
  if (cat.includes('chiller') || cat.includes('crac') || cat.includes('cool')) return Thermometer
  if (cat.includes('genset') || cat.includes('fuel')) return Zap
  if (cat.includes('battery') || cat.includes('ups')) return CircleGauge
  if (cat.includes('hv') || cat.includes('lv') || cat.includes('switch')) return CircuitBoard
  if (domain.includes('power')) return Zap
  if (domain.includes('hvac')) return Thermometer
  return Activity
})

/* ---- Telemetry ---- */
const metricNames = computed(() => metrics.value.map((m) => m.metric_name))
const {
  realtime,
  online,
  connected: wsConnected,
  history: historyData,
  loadingHistory,
  spark,
  val,
  unitOf,
  fetchRecentHistory,
  // [P1-6] 由后端 WS connected 下发的单测点 stale 阈值 (动态, 默认 15000 兜底)
  metricStaleMs,
} = useTelemetry(props.deviceId, { metrics: metricNames.value })

/* ---- 实时时钟: 用于测点"上次更新 Xs 前"与陈旧判定 ----
   stale 阈值取自后端下发 (DEVICE_REPORT_INTERVAL_S × REALTIME_STALE_MULTIPLIER),
   原硬编码 15s 改为动态采纳, 采集器改上报周期后前端无需改代码。 */
const now = ref(Date.now())
let clock = window.setInterval(() => {
  now.value = Date.now()
}, 1000)
onBeforeUnmount(() => window.clearInterval(clock))

/* ---- MetricCard data ---- */
interface CardData {
  name: string
  label: string
  value: number | null
  unit: string
  quality: MetricQuality
  spark: { ts: string; value: number }[]
  severity: 'normal' | 'warn' | 'crit'
  color: string
  displayValue: string
  lastUpdateTs: string
  stale: boolean
}

function fmtVal(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  if (Number.isInteger(v)) return String(v)
  return Math.abs(v) >= 1000
    ? v.toLocaleString('zh-CN', { maximumFractionDigits: 1 })
    : v.toFixed(2)
}

function labelOf(name: string): string {
  return props.metricLabels[name] ?? name
}

const metricCards = computed<CardData[]>(() => {
  return metrics.value.map((m, i) => {
    const rt = realtime[m.metric_name]
    const v = rt?.value ?? null
    const q = (rt?.quality ?? 'good') as MetricQuality
    let sev: CardData['severity'] = 'normal'
    if (q === 'bad') sev = 'crit'
    else if (q === 'uncertain') sev = 'warn'
    // 设备在线但该测点超过下发的 stale 阈值未更新 → 断流/卡住 (stale)
    const mts = rt?.ts ? new Date(rt.ts).getTime() : 0
    const stale = online.value && mts > 0 && now.value - mts > metricStaleMs.value
    return {
      name: m.metric_name,
      label: labelOf(m.metric_name),
      value: v,
      unit: m.unit || rt?.unit || unitOf(m.metric_name) || '',
      quality: q,
      spark: rt?.spark ?? [],
      severity: sev,
      color: PALETTE[i % PALETTE.length],
      displayValue: fmtVal(v),
      lastUpdateTs: rt?.ts ?? '',
      stale,
    }
  })
})

const kpiCards = computed(() => {
  const kpi = props.kpiMetrics.length
    ? props.kpiMetrics
    : metricCards.value.slice(0, 6).map((c) => c.name)
  return kpi.map((name, i) => {
    const card = metricCards.value.find((c) => c.name === name)
    return (
      card ?? {
        name,
        label: labelOf(name),
        displayValue: '—',
        unit: '',
        color: PALETTE[i % PALETTE.length],
      }
    )
  })
})

const gridCols = computed(() => {
  const n = metricCards.value.length
  if (n <= 3) return Math.max(n, 2)
  if (n <= 6) return n
  return 6
})

/* ---- Trend ---- */
const activeMetric = ref('')
const activeRange = ref('30m')

const trendMetrics = computed<TrendMetric[]>(() => {
  return metrics.value.map((m) => ({
    name: m.metric_name,
    label: labelOf(m.metric_name),
    unit: m.unit || unitOf(m.metric_name) || '',
    latest: val(m.metric_name) ?? undefined,
  }))
})

const trendSeries = computed<Record<string, MetricHistoryPoint[]>>(() => {
  return historyData.value?.series ?? {}
})

const trendUnitMap = computed<Record<string, string>>(() => {
  return historyData.value?.unit ?? {}
})

function onMetricSelect(name: string) {
  activeMetric.value = name
  triggerHistory()
}

function onTrendSelect(name: string) {
  activeMetric.value = name
  triggerHistory()
}

function onRangeChange(range: string) {
  activeRange.value = range
  triggerHistory()
}

function triggerHistory() {
  const ranges: Record<string, number> = {
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '6h': 360,
    '24h': 1440,
  }
  const min = ranges[activeRange.value] ?? 30
  fetchRecentHistory(min, 500)
}

onMounted(() => {
  if (metricCards.value.length > 0) {
    activeMetric.value = metricCards.value[0].name
    triggerHistory()
  }
})
</script>

<style scoped>
.dm-root {
  min-height: 0;
}

.dm-cat-icon {
  margin-right: 4px;
  vertical-align: middle;
  opacity: 0.7;
}

.dm-device-id {
  font-size: 11px;
  color: var(--txt3);
}

.dm-sec-icon {
  margin-right: 4px;
  vertical-align: middle;
  opacity: 0.6;
}

.dm-empty {
  text-align: center;
  padding: 40px 0;
  font-size: 13px;
}

.dm-kpi-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.dm-kpi {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 12px;
  min-width: 96px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.dm-kpi-label {
  font-size: 10px;
  color: var(--txt2);
  white-space: nowrap;
}

.dm-kpi-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--cyan);
}

.dm-kpi-unit {
  font-size: 10px;
  color: var(--txt3);
}
</style>
