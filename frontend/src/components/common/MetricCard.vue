<template>
  <div
    class="metric-card card"
    :class="{
      alert: severity === 'crit',
      warn: severity === 'warn',
      stale: !online,
      pstale: stale,
    }"
    @click="$emit('select', metricName)"
  >
    <!-- Header: label + quality indicator -->
    <div class="mc-head">
      <span class="mc-label">{{ label }}</span>
      <span class="mc-status">
        <CircleOff v-if="!online" :size="10" class="mc-status-icon offline" />
        <AlertTriangle v-else-if="stale" :size="10" class="mc-status-icon uncertain" />
        <Circle v-else :size="10" class="mc-status-icon" :class="quality" />
        <span class="mc-quality">{{ statusText }}</span>
      </span>
    </div>

    <!-- Value -->
    <div class="mc-value" :style="{ color: valueColor }">
      <component :is="metricIcon" :size="16" class="mc-type-icon" />
      <span class="mc-num">{{ displayValue }}</span>
      <small v-if="unit">{{ unit }}</small>
    </div>

    <!-- Sparkline -->
    <svg v-if="sparkData.length > 1" class="mc-spark" viewBox="0 0 100 28" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="'sg-' + uid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="sparkColor" stop-opacity="0.35" />
          <stop offset="100%" :stop-color="sparkColor" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      <polygon :fill="'url(#sg-' + uid + ')'" :points="areaPts" />
      <polyline
        fill="none"
        :stroke="sparkColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        :points="linePts"
      />
    </svg>

    <!-- Trend -->
    <div v-if="sparkData.length >= 2" class="mc-trend">
      <TrendingUp v-if="trendDir > 0" :size="12" class="mc-icon up" />
      <TrendingDown v-else-if="trendDir < 0" :size="12" class="mc-icon down" />
      <Minus v-else :size="12" class="mc-icon flat" />
      <span :class="trendDir > 0 ? 'up' : trendDir < 0 ? 'down' : 'flat'">
        {{ trendPct >= 0 ? '+' : '' }}{{ trendPct.toFixed(1) }}%
      </span>
      <Activity v-if="online && !stale" :size="10" class="mc-pulse" />
      <AlertTriangle v-else-if="stale" :size="10" class="mc-stale-icon" />
      <span class="mc-ts muted" v-if="relative">{{ relative }}<span v-if="stale" class="stale-flag"> · 数据陈旧</span></span>
    </div>
    <div v-else class="mc-trend muted">
      <CircleOff :size="10" />
      <span>暂无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onBeforeUnmount, type Component } from 'vue'
import { TrendingUp, TrendingDown, Minus, Circle, CircleOff, Activity, AlertTriangle, Zap, Thermometer, Droplets, CircleGauge } from 'lucide-vue-next'
import type { MetricQuality } from '@/types'

const props = withDefaults(
  defineProps<{
    metricName: string
    label: string
    value?: number | null
    unit?: string
    quality?: MetricQuality
    online?: boolean
    sparkData?: { ts: string; value: number }[]
    severity?: 'normal' | 'warn' | 'crit'
    /** 可选: 按测点名自动选择图标, 或手动指定 */
    iconHint?: string
    /** 上次更新绝对时间 ISO, 用于"Xs 前"与陈旧判定 */
    lastUpdateTs?: string
    /** 设备在线但该测点超过上报周期未更新 (断流/卡住) */
    stale?: boolean
  }>(),
  {
    value: null,
    unit: '',
    quality: 'good',
    online: true,
    sparkData: () => [],
    severity: 'normal',
    iconHint: '',
    lastUpdateTs: '',
    stale: false,
  }
)

defineEmits<{ select: [name: string] }>()

const uid = Math.random().toString(36).slice(2, 8)

/* ---- 实时时钟: 驱动"Xs 前"相对时间刷新 (设备在线但测点卡住时显式标 stale) ---- */
const now = ref(Date.now())
let tick = window.setInterval(() => { now.value = Date.now() }, 1000)
onBeforeUnmount(() => window.clearInterval(tick))

const relative = computed(() => {
  if (!props.lastUpdateTs) return ''
  const diff = Math.max(0, Math.floor((now.value - new Date(props.lastUpdateTs).getTime()) / 1000))
  if (diff < 60) return `${diff}s 前`
  if (diff < 3600) return `${Math.floor(diff / 60)}m 前`
  return `${Math.floor(diff / 3600)}h 前`
})

/* ---- Heuristic icon selection based on metric name ---- */
const metricIcon = computed<Component>(() => {
  const name = (props.metricName + props.label + (props.iconHint ?? '')).toLowerCase()
  if (/temp|温/.test(name)) return Thermometer
  if (/power|kw|电力|功率|负载/.test(name)) return Zap
  if (/flow|humidity|humid|湿/.test(name)) return Droplets
  return CircleGauge
})

/* ---- Display helpers ---- */
const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—'
  const v = Math.abs(props.value)
  if (v >= 10000) return props.value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
  if (v >= 1000) return props.value.toLocaleString('zh-CN', { maximumFractionDigits: 1 })
  if (Number.isInteger(props.value)) return String(props.value)
  return props.value.toFixed(2)
})

const statusText = computed(() => {
  if (!props.online) return '离线'
  if (props.stale) return '数据陈旧'
  return { good: '正常', uncertain: '异常', bad: '故障' }[props.quality] ?? '正常'
})

const valueColor = computed(() => {
  if (!props.online) return 'var(--txt3)'
  if (props.severity === 'crit' || props.quality === 'bad') return 'var(--red)'
  if (props.severity === 'warn' || props.quality === 'uncertain') return 'var(--amber)'
  return 'var(--cyan)'
})

const sparkColor = computed(() => {
  if (!props.online) return '#3a4a66'
  if (props.severity === 'crit' || props.quality === 'bad') return '#ff4d5e'
  if (props.severity === 'warn' || props.quality === 'uncertain') return '#ffb020'
  return '#22e3ff'
})

/* ---- Sparkline SVG math ---- */
const linePts = computed(() => {
  const d = props.sparkData
  if (d.length < 2) return ''
  const vs = d.map(p => p.value)
  const min = Math.min(...vs)
  const max = Math.max(...vs)
  const r = max - min || 1
  return d
    .map((p, i) => `${((i / (d.length - 1)) * 100).toFixed(1)},${(26 - ((p.value - min) / r) * 20 - 3).toFixed(1)}`)
    .join(' ')
})

const areaPts = computed(() => {
  const ln = linePts.value
  return ln ? `0,26 ${ln} 100,26` : ''
})

const trendDir = computed(() => {
  const d = props.sparkData
  if (d.length < 3) return 0
  return d[d.length - 1].value > d[0].value ? 1 : d[d.length - 1].value < d[0].value ? -1 : 0
})

const trendPct = computed(() => {
  const d = props.sparkData
  if (d.length < 3) return 0
  const f = d[0].value
  const l = d[d.length - 1].value
  return f === 0 ? l * 100 : ((l - f) / Math.abs(f)) * 100
})


</script>

<style scoped>
.metric-card {
  cursor: pointer;
  transition: border-color 0.25s, box-shadow 0.25s, transform 0.15s;
  padding: 12px 14px;
  min-height: 144px;
  display: flex;
  flex-direction: column;
}
.metric-card:hover {
  border-color: rgba(34, 227, 255, 0.4);
  box-shadow: var(--glow);
  transform: translateY(-1px);
}
.metric-card.alert {
  border-color: rgba(255, 77, 94, 0.3);
  background: linear-gradient(180deg, rgba(255, 77, 94, 0.06), var(--bg2));
}
.metric-card.warn {
  border-color: rgba(255, 176, 32, 0.3);
  background: linear-gradient(180deg, rgba(255, 176, 32, 0.06), var(--bg2));
}
.metric-card.stale {
  opacity: 0.55;
}
.metric-card.pstale {
  border-color: rgba(255, 176, 32, 0.45);
  background: linear-gradient(180deg, rgba(255, 176, 32, 0.05), var(--bg2));
}
.mc-stale-icon {
  color: var(--amber);
  animation: mc-pulse 1.8s ease-in-out infinite;
}
.stale-flag {
  color: var(--amber);
}

.mc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.mc-label {
  font-size: 11.5px;
  color: var(--txt2);
  letter-spacing: 0.3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mc-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  flex-shrink: 0;
}
.mc-status-icon {
  flex-shrink: 0;
}
.mc-status-icon.good {
  color: var(--green);
}
.mc-status-icon.uncertain {
  color: var(--amber);
}
.mc-status-icon.bad {
  color: var(--red);
}
.mc-status-icon.offline {
  color: var(--txt3);
}
.mc-quality {
  color: var(--txt3);
}

.mc-value {
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
}
.mc-value small {
  font-size: 12px;
  color: var(--txt3);
  font-weight: 500;
}
.mc-num {
  transition: color 0.3s;
}
.mc-type-icon {
  flex-shrink: 0;
  opacity: 0.5;
  margin-right: 2px;
}

.mc-spark {
  width: 100%;
  height: 28px;
  margin-top: 6px;
  overflow: visible;
}

.mc-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.mc-icon {
  flex-shrink: 0;
}
.mc-pulse {
  animation: mc-pulse 1.8s ease-in-out infinite;
  color: var(--cyan);
  opacity: 0.6;
}
@keyframes mc-pulse {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.8;
  }
}
.up {
  color: var(--green);
}
.down {
  color: var(--red);
}
.flat {
  color: var(--txt3);
}
.mc-ts {
  margin-left: auto;
  font-size: 9.5px;
}
</style>
