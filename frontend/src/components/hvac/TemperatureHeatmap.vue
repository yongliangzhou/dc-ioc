<template>
  <div class="heatmap-wrap">
    <svg :viewBox="`0 0 ${vbW} ${vbH}`" class="heatmap-svg" preserveAspectRatio="xMidYMid meet">
      <g v-for="(cell, idx) in positioned" :key="idx">
        <rect
          :x="cell.x"
          :y="cell.y"
          :width="cellW - gap"
          :height="cellH - gap"
          rx="4"
          :fill="color(cell.temp)"
          :stroke="isHot(cell) ? '#ef4444' : 'transparent'"
          :stroke-width="isHot(cell) ? 2 : 0"
          @click="$emit('cell-click', cell)"
        >
          <title>{{ cell.label }}: {{ cell.temp.toFixed(1) }}℃</title>
        </rect>
        <!-- TOP5 热点标注 -->
        <g v-if="cell.top" @click="$emit('cell-click', cell)">
          <circle
            :cx="cell.x + cellW - gap - 10"
            :cy="cell.y + 10"
            r="8"
            class="hot-rank"
          />
          <text :x="cell.x + cellW - gap - 10" :y="cell.y + 13" class="hot-num">{{ cell.rank }}</text>
        </g>
      </g>
    </svg>
    <div v-if="!cells.length" class="empty">{{ tl('暂无温度数据') }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t: tl } = useI18n()

export interface HeatCell {
  id: string
  label: string
  temp: number
  row?: number
  col?: number
  meta?: Record<string, unknown>
}

const props = defineProps<{
  cells: HeatCell[]
  cols: number
  coldThreshold: number // 低温区间下限
  hotThreshold: number // 高温区间上限
  topIds?: string[] // TOP5 热点 id
}>()
defineEmits<{ (e: 'cell-click', cell: HeatCell): void }>()

const gap = 4
const margin = 6
const cellW = 56
const cellH = 56
const vbW = computed(() => margin * 2 + props.cols * cellW)
const rows = computed(() => Math.ceil(props.cells.length / props.cols))
const vbH = computed(() => margin * 2 + Math.max(1, rows.value) * cellH)

const positioned = computed(() => {
  const topSet = new Set(props.topIds ?? [])
  return props.cells.map((c, i) => {
    const r = c.row ?? Math.floor(i / props.cols)
    const col = c.col ?? i % props.cols
    return {
      ...c,
      x: margin + col * cellW,
      y: margin + r * cellH,
      top: topSet.has(c.id),
      rank: props.topIds ? props.topIds.indexOf(c.id) + 1 : 0,
    }
  })
})

function isHot(c: HeatCell) {
  return c.temp > props.hotThreshold
}

// 区间着色：低于 cold 偏蓝，区间内绿黄，高于 hot 偏红
function color(temp: number) {
  if (temp <= props.coldThreshold) {
    const t = Math.max(0, (temp - 10) / Math.max(1, props.coldThreshold - 10))
    return `rgb(${Math.round(56 + t * 30)}, ${Math.round(189 - t * 40)}, ${Math.round(248 - t * 80)})`
  }
  if (temp >= props.hotThreshold) {
    const t = Math.min(1, (temp - props.hotThreshold) / 6)
    return `rgb(${Math.round(239 + t * 16)}, ${Math.round(68 - t * 50)}, ${Math.round(68 - t * 40)})`
  }
  const t = (temp - props.coldThreshold) / Math.max(0.1, props.hotThreshold - props.coldThreshold)
  // 绿(34,197,94) -> 黄(234,179,8)
  return `rgb(${Math.round(34 + t * 200)}, ${Math.round(197 - t * 18)}, ${Math.round(94 - t * 86)})`
}
</script>

<style scoped>
.heatmap-svg { width: 100%; height: auto; }
.heatmap-svg rect { cursor: pointer; transition: opacity 0.15s; }
.heatmap-svg rect:hover { opacity: 0.85; }
.hot-rank { fill: #ef4444; stroke: #fff; stroke-width: 1.5; }
.hot-num { fill: #fff; font-size: 10px; font-weight: 700; text-anchor: middle; }
.empty { color: #64748b; text-align: center; padding: 40px; }
</style>
