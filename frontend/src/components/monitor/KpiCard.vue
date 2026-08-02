<template>
  <div class="kpi-card card" :class="[sizeClass, { 'kpi-clickable': clickable }]" @click="clickable && $emit('click')">
    <div class="ct">
      <span class="ct-dot" v-if="dot" :style="{ background: dot }"></span>
      {{ title }}
      <span v-if="subtitle" class="ct-sub">{{ subtitle }}</span>
      <span v-if="target !== undefined && targetLabel" class="ct-target">{{ targetLabel }} {{ target }}</span>
    </div>
    <div class="cv" :class="computedValueClass">
      <span v-if="prefix" class="cv-prefix">{{ prefix }}</span>
      {{ formattedValue }}
      <small v-if="unit">{{ unit }}</small>
    </div>
    <div v-if="trend !== undefined" class="ctrend">
      <span :class="trend >= 0 ? 'up' : 'down'">
        {{ trend >= 0 ? '▲' : '▼' }} {{ Math.abs(trend).toFixed(1) }}%
      </span>
    </div>
    <div v-if="barVal !== undefined" class="cbar">
      <i :style="{ width: barVal + '%', background: barColor }"></i>
    </div>
    <div v-if="detail" class="cdetail">{{ detail }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  value?: number | string
  unit?: string
  prefix?: string
  subtitle?: string
  dot?: string
  trend?: number            // 正=上升，负=下降
  barValue?: number         // 0-100 底部进度条（同 progress）
  progress?: number         // 同 barValue
  progressColor?: string    // 同 barColor，仅在 barColor 未指定时使用
  barColor?: string
  target?: number           // 目标/设定值
  targetLabel?: string      // 目标标签（如"设定"）
  detail?: string
  size?: 'sm' | 'md' | 'lg'
  decimals?: number
  status?: 'normal' | 'warning' | 'danger'
  clickable?: boolean
  valueClass?: string       // 自定义数值颜色 CSS class
}>(), {
  size: 'md',
  decimals: 1,
  barColor: 'linear-gradient(90deg, var(--cyan), var(--blue))',
  clickable: false,
})

defineEmits<{ click: [] }>()

const sizeClass = computed(() => `kpi-${props.size}`)

const barVal = computed(() => props.barValue ?? props.progress)

const barColor = computed(() => props.barColor ?? props.progressColor ?? 'linear-gradient(90deg, var(--cyan), var(--blue))')

const formattedValue = computed(() => {
  const v = props.value
  if (v === undefined || v === null || v === '') return '-'
  if (typeof v === 'string') return v
  if (Number.isInteger(v)) return String(v)
  return v.toFixed(props.decimals)
})

const computedValueClass = computed(() => {
  const parts: string[] = []
  if (props.status === 'danger') parts.push('cv-danger')
  if (props.status === 'warning') parts.push('cv-warning')
  if (props.valueClass) parts.push(props.valueClass)
  return parts.join(' ')
})
</script>

<style scoped>
.kpi-card { min-width: 110px; }
.kpi-sm { padding: 10px 12px; }
.kpi-sm .cv { font-size: 18px; }
.kpi-lg { padding: 18px; }
.kpi-lg .cv { font-size: 28px; }
.kpi-clickable { cursor: pointer; transition: border-color 0.2s; }
.kpi-clickable:hover { border-color: rgba(34, 227, 255, 0.5); }

.ct { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--txt2); letter-spacing: 0.5px; margin-bottom: 8px; }
.ct-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ct-sub { font-size: 10px; color: var(--txt3); margin-left: auto; }
.ct-target { font-size: 10px; color: var(--txt3); margin-left: auto; }
.cv { font-size: 24px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; color: var(--txt-strong); }
.cv small { font-size: 12px; color: var(--txt2); font-weight: 500; margin-left: 2px; }
.cv-danger { color: var(--red); }
.cv-warning { color: var(--amber); }
.cv-prefix { font-size: 14px; color: var(--txt2); font-weight: 500; margin-right: 2px; }

.ctrend { margin-top: 6px; font-size: 11px; }
.ctrend .up { color: var(--red); }
.ctrend .down { color: var(--green); }

.cbar { height: 6px; border-radius: 4px; background: var(--track); margin-top: 10px; overflow: hidden; }
.cbar > i { display: block; height: 100%; border-radius: 4px; transition: width 0.5s ease; }

.cdetail { margin-top: 6px; font-size: 10px; color: var(--txt3); }
</style>
