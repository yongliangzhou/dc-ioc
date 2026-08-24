<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title: string
    value?: number | string
    unit?: string
    prefix?: string
    subtitle?: string
    dot?: string
    trend?: number // positive = up, negative = down
    barValue?: number // 0-100 progress bar (alias: progress)
    progress?: number // alias for barValue
    progressColor?: string // alias for barColor
    barColor?: string
    target?: number
    targetLabel?: string
    detail?: string
    size?: 'sm' | 'md' | 'lg'
    decimals?: number
    status?: 'normal' | 'warning' | 'danger'
    clickable?: boolean
    valueClass?: string
  }>(),
  {
    size: 'md',
    decimals: 1,
    barColor: 'linear-gradient(90deg, var(--cyan, #06b6d4), var(--blue, #3b82f6))',
    clickable: false,
  },
)

defineEmits<{ click: [] }>()

const sizeClass = computed(() => `dui-kpi-${props.size}`)

const barVal = computed(() => props.barValue ?? props.progress)

const _barColor = computed(
  () =>
    props.barColor ??
    props.progressColor ??
    'linear-gradient(90deg, var(--cyan, #06b6d4), var(--blue, #3b82f6))',
)

const formattedValue = computed(() => {
  const v = props.value
  if (v === undefined || v === null || v === '') return '-'
  if (typeof v === 'string') return v
  if (Number.isInteger(v)) return String(v)
  return v.toFixed(props.decimals)
})

const computedValueClass = computed(() => {
  const parts: string[] = []
  if (props.status === 'danger') parts.push('dui-cv-danger')
  if (props.status === 'warning') parts.push('dui-cv-warning')
  if (props.valueClass) parts.push(props.valueClass)
  return parts.join(' ')
})
</script>

<template>
  <div
    class="dui-kpi-card"
    :class="[sizeClass, { 'dui-kpi-clickable': clickable }]"
    @click="clickable && $emit('click')"
  >
    <div class="dui-kpi-ct">
      <span v-if="dot" class="dui-kpi-dot" :style="{ background: dot }"></span>
      {{ title }}
      <span v-if="subtitle" class="dui-kpi-sub">{{ subtitle }}</span>
      <span v-if="target !== undefined && targetLabel" class="dui-kpi-target">
        {{ targetLabel }} {{ target }}
      </span>
    </div>
    <div class="dui-kpi-cv" :class="computedValueClass">
      <span v-if="prefix" class="dui-cv-prefix">{{ prefix }}</span>
      {{ formattedValue }}
      <small v-if="unit">{{ unit }}</small>
    </div>
    <div v-if="trend !== undefined" class="dui-kpi-trend">
      <span :class="trend >= 0 ? 'dui-up' : 'dui-down'">
        {{ trend >= 0 ? '▲' : '▼' }} {{ Math.abs(trend).toFixed(1) }}%
      </span>
    </div>
    <div v-if="barVal !== undefined" class="dui-kpi-bar">
      <i :style="{ width: barVal + '%', background: _barColor }"></i>
    </div>
    <div v-if="detail" class="dui-kpi-detail">{{ detail }}</div>
  </div>
</template>

<style scoped>
/* KpiCard — @dc-ioc/ui
   Requires CSS variables: --txt2, --txt3, --txt-strong, --red, --amber,
   --green, --cyan, --blue, --track (optional, fall back to #334155).
   Also provides self-contained .dui-kpi-card base styles (no .card dependency). */

.dui-kpi-card {
  background: linear-gradient(180deg, #1e293b, #0f172a);
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 14px;
  position: relative;
  overflow: hidden;
  min-width: 110px;
}
.dui-kpi-card::after {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(34, 227, 255, 0.5),
    transparent
  );
}

.dui-kpi-sm {
  padding: 10px 12px;
}
.dui-kpi-sm .dui-kpi-cv {
  font-size: 18px;
}

.dui-kpi-lg {
  padding: 18px;
}
.dui-kpi-lg .dui-kpi-cv {
  font-size: 28px;
}

.dui-kpi-clickable {
  cursor: pointer;
  transition: border-color 0.2s;
}
.dui-kpi-clickable:hover {
  border-color: rgba(34, 227, 255, 0.5);
}

.dui-kpi-ct {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--txt2, #94a3b8);
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.dui-kpi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dui-kpi-sub {
  font-size: 10px;
  color: var(--txt3, #64748b);
  margin-left: auto;
}
.dui-kpi-target {
  font-size: 10px;
  color: var(--txt3, #64748b);
  margin-left: auto;
}

.dui-kpi-cv {
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--txt-strong, #f1f5f9);
}
.dui-kpi-cv small {
  font-size: 12px;
  color: var(--txt2, #94a3b8);
  font-weight: 500;
  margin-left: 3px;
}

.dui-cv-danger {
  color: var(--red, #ef4444);
}
.dui-cv-warning {
  color: var(--amber, #f59e0b);
}
.dui-cv-prefix {
  font-size: 14px;
  color: var(--txt2, #94a3b8);
  font-weight: 500;
  margin-right: 2px;
}

.dui-kpi-trend {
  margin-top: 6px;
  font-size: 11px;
}
.dui-up {
  color: var(--red, #ef4444);
}
.dui-down {
  color: var(--green, #22c55e);
}

.dui-kpi-bar {
  height: 6px;
  border-radius: 4px;
  background: var(--track, #334155);
  margin-top: 10px;
  overflow: hidden;
}
.dui-kpi-bar > i {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.dui-kpi-detail {
  margin-top: 6px;
  font-size: 10px;
  color: var(--txt3, #64748b);
}
</style>
