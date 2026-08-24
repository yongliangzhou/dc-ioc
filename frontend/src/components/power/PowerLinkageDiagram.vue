<template>
  <div
    ref="wrap"
    class="linkage-diagram"
    :class="{ dragging }"
    @wheel.prevent="onWheel"
    @mousedown="onBgDown"
    @mousemove="onMove"
    @mouseup="onUp"
    @mouseleave="onUp"
  >
    <svg :viewBox="`0 0 ${width} ${height}`" class="linkage-svg" preserveAspectRatio="xMidYMid meet">
      <defs>
        <marker id="flow-arrow" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L6,3 L0,6 Z" fill="#34d399" />
        </marker>
        <marker id="flow-arrow-off" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L6,3 L0,6 Z" fill="#64748b" />
        </marker>
        <linearGradient id="flowGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#34d399" stop-opacity="0.1" />
          <stop offset="100%" stop-color="#34d399" stop-opacity="0.9" />
        </linearGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      <g :transform="`translate(${pan.x},${pan.y}) scale(${scale})`">
        <!-- 分组背景框（自动按层生成） -->
        <g v-for="grp in autoGroups" :key="'g' + grp.key">
          <rect
            :x="grp.x" :y="grp.y" :width="grp.w" :height="grp.h" rx="14"
            class="group-box"
            :style="grp.color ? { stroke: grp.color, fill: grp.color + '12' } : undefined"
          />
          <text
            :x="grp.x + 14" :y="grp.y + 22" class="group-title"
            :style="grp.color ? { fill: grp.color } : undefined"
          >{{ grp.title }}</text>
        </g>

        <!-- 连线条（带流动动画 + 链路高亮） -->
        <g class="links">
          <g v-for="(lk, idx) in links" :key="'l' + idx">
            <line
              :x1="coord(lk.from).x" :y1="coord(lk.from).y" :x2="coord(lk.to).x" :y2="coord(lk.to).y"
              :class="['link-base', { 'link-off': lk.off, 'link-hi': isLinked(lk) }]"
            />
            <line
              v-if="!lk.off && !lk.backup"
              :x1="coord(lk.from).x" :y1="coord(lk.from).y" :x2="coord(lk.to).x" :y2="coord(lk.to).y"
              class="link-flow" :class="{ 'link-hi': isLinked(lk) }" marker-end="url(#flow-arrow)"
            />
            <line
              v-if="lk.backup"
              :x1="coord(lk.from).x" :y1="coord(lk.from).y" :x2="coord(lk.to).x" :y2="coord(lk.to).y"
              class="link-backup"
            />
          </g>
        </g>

        <!-- 节点 -->
        <g
          v-for="node in flatNodes" :key="node.id" class="node-group"
          :transform="`translate(${coord(node.id).x},${coord(node.id).y})`"
          :class="{ selected: node.id === selectedId, ['st-' + node.status]: true, hi: isLinkedTo(node.id) }"
          @click.stop="onClick(node)"
          @mousedown.stop="onNodeDown(node, $event)"
        >
          <circle v-if="node.status !== 'off'" :r="boxH / 2 + 6" :class="['halo', 'halo-' + node.status]" />
          <rect
            :x="-boxW / 2" :y="-boxH / 2" :width="boxW" :height="boxH" rx="10"
            :class="['node-box', 'st-' + node.status, { 'has-alarm': (node.alarmCount ?? 0) > 0 }]"
          />
          <text :y="-boxH / 2 + 16" class="node-ico">{{ node.icon }}</text>
          <text :y="2" class="node-title">{{ node.title }}</text>
          <text :y="18" class="node-sub">{{ node.sub }}</text>
          <text v-if="node.kpi" :y="34" class="node-kpi">{{ node.kpi }}</text>
          <circle
            v-if="(node.alarmCount ?? 0) > 0"
            :cx="boxW / 2 - 12" :cy="-boxH / 2 + 12" r="7" class="alarm-dot"
          />
          <text v-if="node.isBattery" :x="0" :y="boxH / 2 + 14" class="backup-tag">{{ tl('备用电源') }}</text>
        </g>
      </g>
    </svg>

    <!-- 缩放控制 -->
    <div class="zoom-ctrl">
      <button @click="zoomBtn(1.2)" title="放大">＋</button>
      <span class="zoom-val">{{ Math.round(scale * 100) }}%</span>
      <button @click="zoomBtn(1 / 1.2)" title="缩小">－</button>
      <button @click="resetView" title="复位">{{ tl('复位') }}</button>
      <button @click="fitView" title="适配">{{ tl('适配') }}</button>
    </div>

    <div v-if="!flatNodes.length" class="empty">{{ tl('暂无配电链路数据') }}</div>
    <div class="hint">{{ tl('滚轮缩放 · 拖拽空白平移 · 拖拽节点移动 · 点击查看详情') }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t: tl } = useI18n()

export interface LinkNode {
  id: string
  title: string
  sub: string
  kpi?: string
  status: 'normal' | 'warning' | 'fault' | 'off'
  alarmCount?: number
  icon?: string
  group?: string
  isBattery?: boolean
  kind?: string
  meta?: any
  x?: number
  y?: number
}
export interface LinkEdge {
  from: string
  to: string
  off?: boolean
  backup?: boolean
  alarm?: boolean
}
export interface LinkLayer {
  key: string
  title: string
  color?: string
  nodes: LinkNode[]
}
export interface LinkGroup {
  key: string
  title: string
  x: number
  y: number
  w: number
  h: number
  nodeIds: string[]
  color?: string
}

const props = defineProps<{
  // 推荐：按层传入，组件自动排版
  layers?: LinkLayer[]
  // 兼容旧用法：父页面已算好坐标的扁平节点（仍可用，但失去自动布局优势）
  nodes?: LinkNode[]
  links: LinkEdge[]
  groups?: LinkGroup[]
  selectedId?: string
  layerGap?: number
  colGap?: number
  nodeW?: number
  nodeH?: number
}>()
const emit = defineEmits<{
  (e: 'node-click', node: LinkNode): void
  (e: 'node-move', id: string, x: number, y: number): void
}>()

const width = 1280
const height = 760
const boxW = props.nodeW ?? 150
const boxH = props.nodeH ?? 78
const layerGap = props.layerGap ?? 230
const colGap = props.colGap ?? 116

const pan = reactive({ x: 0, y: 0 })
const scale = ref(1)
const wrap = ref<HTMLElement | null>(null)
const dragging = ref(false)
const hoveredId = ref<string | null>(null)
const coordMap = reactive<Record<string, { x: number; y: number }>>({})

// 兼容模式：把 groups + nodes 还原成分层结构
const effectiveLayers = computed<LinkLayer[]>(() => {
  if (props.layers && props.layers.length) return props.layers
  if (props.groups && props.nodes) {
    return props.groups.map((g) => ({
      key: g.key,
      title: g.title,
      color: g.color,
      nodes: props.nodes!.filter((n) => n.group === g.key),
    }))
  }
  return []
})

const flatNodes = computed<LinkNode[]>(() =>
  effectiveLayers.value.length
    ? effectiveLayers.value.flatMap((l) => l.nodes)
    : (props.nodes ?? []),
)

function layout() {
  Object.keys(coordMap).forEach((k) => delete coordMap[k])
  const layers = effectiveLayers.value
  const nLayers = layers.length
  layers.forEach((layer, li) => {
    const x = layerGap * (li + 1)
    const totalH = (layer.nodes.length - 1) * colGap
    layer.nodes.forEach((n, ni) => {
      const y = height / 2 - totalH / 2 + ni * colGap
      coordMap[n.id] = { x, y }
    })
  })
  // 兼容模式：保留父页面传入的坐标
  if (!nLayers && props.nodes) {
    props.nodes.forEach((n) => { if (n.x != null && n.y != null) coordMap[n.id] = { x: n.x, y: n.y } })
  }
}
layout()

const coord = (id: string) => coordMap[id] ?? { x: 0, y: 0 }

const autoGroups = computed<LinkGroup[]>(() => {
  if (props.groups && props.groups.length && !effectiveLayers.value.length) return props.groups
  return effectiveLayers.value.map((layer, li) => {
    const x = layerGap * (li + 1)
    const ys = layer.nodes.map((n) => coord(n.id).y)
    const minY = Math.min(...ys) - boxH / 2 - 24
    const maxY = Math.max(...ys) + boxH / 2 + 24
    return {
      key: layer.key,
      title: layer.title,
      color: layer.color,
      x: x - boxW / 2 - 22,
      y: minY,
      w: boxW + 44,
      h: maxY - minY,
      nodeIds: layer.nodes.map((n) => n.id),
    }
  })
})

function activeRef(): string | undefined {
  return hoveredId.value ?? props.selectedId
}
function isLinkedTo(id: string) {
  const a = activeRef()
  if (!a || a === id) return false
  return props.links.some((l) => (l.from === a && l.to === id) || (l.to === a && l.from === id))
}
function isLinked(lk: LinkEdge) {
  const a = activeRef()
  return !!a && (lk.from === a || lk.to === a)
}

function onClick(node: LinkNode) { emit('node-click', node) }
function zoomBtn(f: number) { scale.value = clamp(scale.value * f, 0.4, 3) }
function resetView() { scale.value = 1; pan.x = 0; pan.y = 0 }
function fitView() {
  const ids = flatNodes.value.map((n) => n.id)
  if (!ids.length) return
  const xs = ids.map((id) => coord(id).x)
  const ys = ids.map((id) => coord(id).y)
  const minX = Math.min(...xs) - boxW - 30
  const maxX = Math.max(...xs) + boxW + 30
  const minY = Math.min(...ys) - boxH - 30
  const maxY = Math.max(...ys) + boxH + 30
  const cw = maxX - minX
  const ch = maxY - minY
  scale.value = clamp(Math.min(width / cw, height / ch), 0.4, 3)
  pan.x = (width - cw * scale.value) / 2 - minX * scale.value
  pan.y = (height - ch * scale.value) / 2 - minY * scale.value
}
function onWheel(e: WheelEvent) { scale.value = clamp(scale.value * (e.deltaY < 0 ? 1.1 : 1 / 1.1), 0.4, 3) }

let dragMode: 'none' | 'bg' | 'node' = 'none'
let dragId = ''
let start = { x: 0, y: 0 }
let origin = { x: 0, y: 0 }
function toSvg(cx: number, cy: number) {
  const el = wrap.value
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  const vbX = ((cx - rect.left) / rect.width) * width
  const vbY = ((cy - rect.top) / rect.height) * height
  return { x: (vbX - pan.x) / scale.value, y: (vbY - pan.y) / scale.value }
}
function onBgDown(e: MouseEvent) {
  dragMode = 'bg'; dragging.value = true; start = { x: e.clientX, y: e.clientY }; origin = { x: pan.x, y: pan.y }
}
function onNodeDown(node: LinkNode, e: MouseEvent) {
  dragMode = 'node'; dragId = node.id
  const p = toSvg(e.clientX, e.clientY)
  start = { x: e.clientX, y: e.clientY }
  origin = { x: coord(node.id).x - p.x, y: coord(node.id).y - p.y }
}
function onMove(e: MouseEvent) {
  if (dragMode === 'bg') {
    const rect = wrap.value?.getBoundingClientRect()
    if (!rect) return
    pan.x = origin.x + ((e.clientX - start.x) / rect.width) * width
    pan.y = origin.y + ((e.clientY - start.y) / rect.height) * height
  } else if (dragMode === 'node') {
    const p = toSvg(e.clientX, e.clientY)
    coordMap[dragId] = { x: p.x + origin.x, y: p.y + origin.y }
    emit('node-move', dragId, coordMap[dragId].x, coordMap[dragId].y)
  }
}
function onUp() { dragMode = 'none'; dragging.value = false }
function clamp(v: number, lo: number, hi: number) { return Math.min(hi, Math.max(lo, v)) }

onMounted(() => fitView())
defineExpose({ fitView, resetView })
</script>

<style scoped>
.linkage-diagram {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  cursor: grab;
  user-select: none;
}
.linkage-diagram.dragging { cursor: grabbing; }
.linkage-svg {
  width: 100%;
  height: 100%;
  background:
    radial-gradient(900px 420px at 20% -10%, rgba(16, 185, 129, 0.08), transparent 60%),
    radial-gradient(900px 420px at 80% 110%, rgba(56, 189, 248, 0.08), transparent 60%),
    linear-gradient(160deg, #0a1322 0%, #0b1626 100%);
  border-radius: 12px;
}
.group-box {
  fill: rgba(148, 163, 184, 0.04);
  stroke: rgba(148, 163, 184, 0.18);
  stroke-width: 1;
  stroke-dasharray: 4 5;
}
.group-title {
  fill: #64748b;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
}
.link-base { stroke: #475569; stroke-width: 3.5; opacity: 0.7; }
.link-off { stroke: #475569; opacity: 0.4; stroke-dasharray: 5 5; }
.link-hi { stroke: #38bdf8 !important; opacity: 1; stroke-width: 4.5; filter: drop-shadow(0 0 5px rgba(56,189,248,0.8)); }
.link-flow {
  stroke: url(#flowGrad);
  stroke-width: 3.5;
  stroke-dasharray: 10 8;
  animation: flow 1.1s linear infinite;
  filter: drop-shadow(0 0 4px rgba(52, 211, 153, 0.6));
}
.link-backup { stroke: #f59e0b; stroke-width: 2.5; stroke-dasharray: 7 6; opacity: 0.9; }
@keyframes flow { to { stroke-dashoffset: -18; } }
.node-group { cursor: pointer; }
.halo { fill: none; opacity: 0.35; }
.halo-normal { stroke: #22c55e; stroke-width: 2; filter: drop-shadow(0 0 6px #22c55e); }
.halo-warning { stroke: #f59e0b; stroke-width: 2; filter: drop-shadow(0 0 6px #f59e0b); }
.halo-fault { stroke: #ef4444; stroke-width: 2; filter: drop-shadow(0 0 6px #ef4444); }
.node-box { fill: #16233a; stroke: #334155; stroke-width: 1.5; transition: stroke 0.2s, fill 0.2s; }
.node-group:hover .node-box { stroke: #38bdf8; fill: #1b2b47; }
.node-group.selected .node-box { stroke: #38bdf8; stroke-width: 2.5; filter: url(#glow); }
.node-group.hi .node-box { stroke: #38bdf8; fill: #1b2b47; }
.st-normal .node-box { stroke: #22c55e; }
.st-warning .node-box { stroke: #f59e0b; }
.st-fault .node-box { stroke: #ef4444; }
.st-off .node-box { stroke: #64748b; fill: #111b2c; }
.node-ico { fill: #e2e8f0; font-size: 16px; text-anchor: middle; }
.node-title { fill: #e2e8f0; font-size: 13px; font-weight: 700; text-anchor: middle; }
.node-sub { fill: #94a3b8; font-size: 11px; text-anchor: middle; }
.node-kpi { fill: #7dd3fc; font-size: 10px; text-anchor: middle; }
.backup-tag { fill: #f59e0b; font-size: 10px; text-anchor: middle; }
.alarm-dot { fill: #ef4444; stroke: #fff; stroke-width: 1.5; animation: pulse 1.4s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

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
.empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #64748b; }
</style>
