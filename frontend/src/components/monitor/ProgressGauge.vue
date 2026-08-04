<template>
  <div class="progress-gauge" :class="sizeClass">
    <svg viewBox="0 0 100 100" class="gauge-svg">
      <!-- 背景轨道 -->
      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        :stroke="trackColor"
        :stroke-width="strokeWidth"
      />
      <!-- 进度弧 -->
      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        :stroke="progressColor"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        class="gauge-progress"
      />
    </svg>
    <div class="gauge-content">
      <span class="gauge-value" :class="statusClass">{{ formattedValue }}</span>
      <span v-if="unit" class="gauge-unit">{{ unit }}</span>
      <span v-if="label" class="gauge-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    max?: number
    unit?: string
    label?: string
    size?: 'sm' | 'md' | 'lg'
    status?: 'normal' | 'warning' | 'danger'
    decimals?: number
    color?: string
  }>(),
  {
    max: 100,
    size: 'md',
    decimals: 1,
  },
)

const sizeMap: Record<string, { r: number; sw: number }> = {
  sm: { r: 38, sw: 6 },
  md: { r: 40, sw: 7 },
  lg: { r: 42, sw: 8 },
}

const radius = computed(() => sizeMap[props.size]?.r ?? 40)
const strokeWidth = computed(() => sizeMap[props.size]?.sw ?? 7)
const circumference = computed(() => 2 * Math.PI * radius.value)
const pct = computed(() => Math.min(Math.max(props.value / props.max, 0), 1))
const dashOffset = computed(() => circumference.value * (1 - pct.value))

const trackColor = 'var(--track)'
const progressColor = computed(() => {
  if (props.color) return props.color
  if (props.status === 'danger') return 'var(--red)'
  if (props.status === 'warning') return 'var(--amber)'
  return 'var(--cyan)'
})

const statusClass = computed(() => {
  if (props.status === 'danger') return 'danger'
  if (props.status === 'warning') return 'warning'
  return ''
})

const sizeClass = computed(() => `gauge-${props.size}`)

const formattedValue = computed(() => {
  if (props.value === undefined || props.value === null) return '-'
  if (Number.isInteger(props.value)) return String(props.value)
  return props.value.toFixed(props.decimals)
})
</script>

<style scoped>
.progress-gauge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.gauge-sm {
  width: 90px;
  height: 90px;
}
.gauge-md {
  width: 110px;
  height: 110px;
}
.gauge-lg {
  width: 130px;
  height: 130px;
}

.gauge-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.gauge-progress {
  transition: stroke-dashoffset 0.6s ease;
}

.gauge-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  z-index: 1;
}
.gauge-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  color: var(--txt-strong);
  font-variant-numeric: tabular-nums;
}
.gauge-sm .gauge-value {
  font-size: 16px;
}
.gauge-lg .gauge-value {
  font-size: 28px;
}
.gauge-value.warning {
  color: var(--amber);
}
.gauge-value.danger {
  color: var(--red);
}
.gauge-unit {
  font-size: 10px;
  color: var(--txt2);
}
.gauge-label {
  font-size: 10px;
  color: var(--txt3);
  margin-top: 1px;
}
</style>
