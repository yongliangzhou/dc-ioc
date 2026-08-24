<template>
  <div
    ref="wrap"
    class="cooling-diagram"
    :class="{ dragging }"
    @wheel.prevent="onWheel"
    @mousedown="onBgDown"
    @mousemove="onMove"
    @mouseup="onUp"
    @mouseleave="onUp"
  >
    <svg :viewBox="`0 0 ${width} ${height}`" class="cooling-svg" preserveAspectRatio="xMidYMid meet">
      <defs>
        <marker id="arrowChw" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#2dd4bf" />
        </marker>
        <marker id="arrowCw" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#38bdf8" />
        </marker>
      </defs>

      <g :transform="`translate(${pan.x},${pan.y}) scale(${scale})`">
        <!-- 管道（带方向箭头 + 流动粒子 + 悬停高亮） -->
        <g class="pipes">
          <g v-for="(p, idx) in pipeList" :key="'p' + idx">
            <path
              :id="'pipe' + idx" :d="p.d" fill="none"
              :class="['pipe', p.kind, { 'pipe-off': p.off, 'pipe-hi': isPipeLinked(idx) }]"
              :marker-end="p.kind === 'cw' ? 'url(#arrowCw)' : 'url(#arrowChw)'"
            />
            <circle v-for="k in 4" :key="k" r="3" :class="['flow-dot', p.kind]">
              <animateMotion
                :dur="p.dur"
                :begin="(-(durMs(p.dur) / 4) * k).toFixed(2) + 's'"
                repeatCount="indefinite"
              >
                <mpath :href="'#pipe' + String(idx)" />
              </animateMotion>
            </circle>
          </g>
        </g>

        <!-- 设备节点 -->
        <g
          v-for="n in nodeList" :key="n.id" class="dev-group"
          :transform="`translate(${n.x},${n.y})`"
          :class="{ selected: n.id === selectedId, ['st-' + n.status]: true, hi: isNodeLinked(n.id) }"
          @click="onClick(n)"
          @mouseenter="hoverId = n.id"
          @mouseleave="hoverId = null"
        >
          <rect
            :x="-(n.w ?? 140) / 2" :y="-(n.h ?? 56) / 2" :width="n.w ?? 140" :height="n.h ?? 56" rx="8"
            :class="['dev-box', 'st-' + n.status, { 'has-alarm': (n.alarmCount ?? 0) > 0 }]"
          />
          <circle v-if="(n.alarmCount ?? 0) > 0" :cx="(n.w ?? 140) / 2 - 8" :cy="-(n.h ?? 56) / 2 + 8" r="7" class="alarm-dot" />
          <text :y="-2" class="dev-title">{{ n.title }}</text>
          <text :y="14" class="dev-sub">{{ n.sub }}</text>
        </g>
      </g>
    </svg>

    <div class="zoom-ctrl">
      <button @click="zoomBtn(1.2)" title="放大">＋</button>
      <span class="zoom-val">{{ Math.round(scale * 100) }}%</span>
      <button @click="zoomBtn(1 / 1.2)" title="缩小">－</button>
      <button @click="resetView" title="复位">{{ tl('复位') }}</button>
      <button @click="fitView" title="适配">{{ tl('适配') }}</button>
    </div>
    <div v-if="!nodeList.length" class="empty">{{ tl('暂无制冷链路数据') }}</div>
    <div class="hint">{{ tl('滚轮缩放 · 拖拽平移 · 点击查看详情') }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t: tl } = useI18n()

export interface CoolingDevice {
  id: string
  title: string
  sub: string
  status: 'normal' | 'warning' | 'fault' | 'off'
  alarmCount?: number
  x: number
  y: number
  w?: number
  h?: number
  kind?: string // chiller | tower | pump | hex | tank | crac
  meta?: Record<string, unknown>
}
export interface CoolingPipe {
  d: string
  kind: 'chw' | 'cw' // 冷冻水 | 冷却水
  off?: boolean
  dur?: string
}
export interface CoolingRow {
  key: string
  title: string
  color?: string
  devices: CoolingDevice[]
}

const props = defineProps<{
  // 推荐：按行传入，组件自动排版并自动生成正交管道
  rows?: CoolingRow[]
  // 兼容旧用法：父页面已算好坐标的扁平节点 + 管道路径
  nodes?: CoolingDevice[]
  pipes?: CoolingPipe[]
  selectedId?: string
  rowGap?: number
  colGap?: number
}>()
const emit = defineEmits<{ (e: 'device-click', node: CoolingDevice): void }>()

const width = 1120
const height = 560
const rowGap = props.rowGap ?? 150
const colGap = props.colGap ?? 170

const pan = reactive({ x: 0, y: 0 })
const scale = ref(1)
const wrap = ref<HTMLElement | null>(null)
const dragging = ref(false)
const hoverId = ref<string | null>(null)

const nodeList = ref<CoolingDevice[]>([])
const pipeList = ref<CoolingPipe[]>([])

function buildFromRows() {
  const rows = props.rows ?? []
  const all: CoolingDevice[] = []
  const built: CoolingPipe[] = []
  rows.forEach((row, ri) => {
    const y = 110 + ri * rowGap
    const totalW = (row.devices.length - 1) * colGap
    row.devices.forEach((d, di) => {
      const x = width / 2 - totalW / 2 + di * colGap
      all.push({ ...d, x, y })
    })
    // 同行相邻设备用正交管道连接
    for (let i = 0; i < row.devices.length - 1; i++) {
      const a = all[all.length - row.devices.length + i]
      const b = all[all.length - row.devices.length + i + 1]
      built.push({ d: orthPath(a, b), kind: row.key === 'cw' ? 'cw' : 'chw' })
    }
  })
  // 行与行之间通过首设备竖向管道连接（简化示意）
  for (let ri = 0; ri < rows.length - 1; ri++) {
    const cur = rows[ri].devices
    const nxt = rows[ri + 1].devices
    if (cur.length && nxt.length) {
      const a = { x: width / 2 - (cur.length - 1) * colGap / 2, y: 110 + ri * rowGap }
      const b = { x: width / 2 - (nxt.length - 1) * colGap / 2, y: 110 + (ri + 1) * rowGap }
      built.push({ d: orthPath(a, b), kind: 'chw' })
    }
  }
  nodeList.value = all
  pipeList.value = built
}
function orthPath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const midY = (a.y + b.y) / 2
  return `M ${a.x} ${a.y} L ${a.x} ${midY} L ${b.x} ${midY} L ${b.x} ${b.y}`
}
function syncFromProps() {
  nodeList.value = props.nodes ?? []
  pipeList.value = props.pipes ?? []
}

function init() {
  if (props.rows && props.rows.length) buildFromRows()
  else syncFromProps()
}
init()
watch(() => props.rows, () => { if (props.rows && props.rows.length) buildFromRows() }, { deep: true })
watch(() => props.nodes, syncFromProps, { deep: true })
watch(() => props.pipes, syncFromProps, { deep: true })

function activeRef(): string | undefined { return hoverId.value ?? props.selectedId }
function isNodeLinked(id: string) {
  const a = activeRef()
  if (!a || a === id) return false
  return pipeList.value.some((p) => p.d.includes(id))
}
function isPipeLinked(idx: number) {
  const a = activeRef()
  if (!a) return false
  return pipeList.value[idx].d.includes(a)
}

function onClick(n: CoolingDevice) { emit('device-click', n) }
function durMs(dur: string | undefined) { return parseFloat(dur ?? '3') * 1000 }
function zoomBtn(f: number) { scale.value = clamp(scale.value * f, 0.4, 3) }
function resetView() { scale.value = 1; pan.x = 0; pan.y = 0 }
function fitView() {
  const ids = nodeList.value
  if (!ids.length) return
  const xs = ids.map((n) => n.x)
  const ys = ids.map((n) => n.y)
  const minX = Math.min(...xs) - (nodeList.value[0].w ?? 140) - 30
  const maxX = Math.max(...xs) + (nodeList.value[0].w ?? 140) + 30
  const minY = Math.min(...ys) - 40
  const maxY = Math.max(...ys) + 40
  const cw = maxX - minX
  const ch = maxY - minY
  scale.value = clamp(Math.min(width / cw, height / ch), 0.4, 3)
  pan.x = (width - cw * scale.value) / 2 - minX * scale.value
  pan.y = (height - ch * scale.value) / 2 - minY * scale.value
}
function onWheel(e: WheelEvent) { scale.value = clamp(scale.value * (e.deltaY < 0 ? 1.1 : 1 / 1.1), 0.4, 3) }

let dragMode: 'none' | 'bg' = 'none'
let start = { x: 0, y: 0 }
let origin = { x: 0, y: 0 }
function onBgDown(e: MouseEvent) {
  dragMode = 'bg'; dragging.value = true; start = { x: e.clientX, y: e.clientY }; origin = { x: pan.x, y: pan.y }
}
function onMove(e: MouseEvent) {
  if (dragMode !== 'bg') return
  const rect = wrap.value?.getBoundingClientRect()
  if (!rect) return
  pan.x = origin.x + ((e.clientX - start.x) / rect.width) * width
  pan.y = origin.y + ((e.clientY - start.y) / rect.height) * height
}
function onUp() { dragMode = 'none'; dragging.value = false }
function clamp(v: number, lo: number, hi: number) { return Math.min(hi, Math.max(lo, v)) }

onMounted(() => fitView())
defineExpose({ fitView, resetView })
</script>

<style scoped>
.cooling-diagram {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  cursor: grab;
  user-select: none;
}
.cooling-diagram.dragging { cursor: grabbing; }
.cooling-svg {
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #0b1220 0%, #0e1a2e 100%);
  border-radius: 12px;
}
.pipe { stroke-width: 5; opacity: 0.55; transition: stroke 0.2s, opacity 0.2s; }
.pipe.chw { stroke: #2dd4bf; }
.pipe.cw { stroke: #38bdf8; }
.pipe-off { stroke: #475569; stroke-dasharray: 6 6; opacity: 0.4; }
.pipe-hi { stroke: #f472b6 !important; opacity: 1; stroke-width: 6; filter: drop-shadow(0 0 6px rgba(244,114,182,0.8)); }
.flow-dot { fill: #fff; opacity: 0.85; }
.flow-dot.chw { fill: #5eead4; }
.flow-dot.cw { fill: #7dd3fc; }
.dev-group { cursor: pointer; }
.dev-box {
  fill: #1e293b;
  stroke: #334155;
  stroke-width: 1.5;
  transition: all 0.2s;
}
.dev-group:hover .dev-box, .dev-group.hi .dev-box {
  stroke: #38bdf8;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.6));
}
.st-normal { stroke: #22c55e; }
.st-warning { stroke: #f59e0b; }
.st-fault { stroke: #ef4444; }
.st-off { stroke: #64748b; fill: #172033; }
.has-alarm { fill: #3f2d12; }
.alarm-dot { fill: #ef4444; stroke: #fff; stroke-width: 1.5; animation: pulse 1.4s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.dev-title { fill: #e2e8f0; font-size: 13px; font-weight: 600; text-anchor: middle; }
.dev-sub { fill: #94a3b8; font-size: 11px; text-anchor: middle; }
.zoom-ctrl {
  position: absolute; right: 12px; bottom: 12px;
  display: flex; align-items: center; gap: 6px;
  background: rgba(15, 23, 42, 0.85); border: 1px solid #334155; border-radius: 10px; padding: 6px 8px;
}
.zoom-ctrl button {
  background: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px;
  height: 28px; min-width: 28px; padding: 0 8px; cursor: pointer; font-size: 13px;
}
.zoom-ctrl button:hover { background: #273449; }
.zoom-val { color: #94a3b8; font-size: 12px; min-width: 44px; text-align: center; }
.hint { position: absolute; right: 12px; top: 12px; color: #475569; font-size: 11px; }
.empty { color: #64748b; text-align: center; padding: 40px; }
</style>
