<template>
  <div class="topo-flow">
    <div class="tf-legend">
      <span class="tf-lg"><i class="dot flow-power" />{{ tl('供电能流') }}</span>
      <span class="tf-lg"><i class="dot flow-cool" />{{ tl('制冷冷量流') }}</span>
      <span class="tf-lg"><i class="dot heat" />{{ tl('机柜热力') }}</span>
      <span class="tf-lg" v-if="affectedIds?.length"
        ><i class="dot fault" />{{ tl('故障传播') }} · {{ affectedIds!.length }} 台波及</span
      >
      <span class="tf-lg dim"
        >{{ realtime ? tl('真实测点驱动') : tl('模拟负载') }} ·
        {{ graph.source === 'db' ? tl('真实台账') : tl('模拟台账') }}</span
      >
      <span class="tf-lg hint">{{ tl('点击节点聚焦 · 缩略图导航') }}</span>
    </div>

    <div class="tf-stage">
      <!-- 主画布 (可滚动, 固定像素尺寸, 缩略图与聚焦据此导航) -->
      <div class="tf-canvas" ref="canvasRef" @scroll="onScroll">
        <svg
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          :style="{ width: layout.width + 'px', height: layout.height + 'px' }"
          class="tf-svg"
          @click="clearFocus"
        >
          <!-- [增强] 机房平面图层: 底板 + 机柜行列网格 + 冷/电通道标注 (最底层) -->
          <g class="tf-floor" v-if="floor.enabled">
            <!-- 机房底板 -->
            <rect
              :x="floor.x"
              :y="floor.y"
              :width="floor.w"
              :height="floor.h"
              rx="14"
              class="floor-board"
            />
            <rect
              :x="floor.x"
              :y="floor.y"
              :width="floor.w"
              :height="22"
              rx="14"
              class="floor-strip"
            />
            <text :x="floor.x + 12" :y="floor.y + 15" class="floor-title">
              {{ tl('机房平面图') }} · {{ tl('机柜热力') }}
            </text>
            <!-- 冷/电通道标签 -->
            <text :x="floor.x + 12" :y="floor.y + floor.h - 10" class="floor-tag cool">
              {{ tl('冷通道') }}
            </text>
            <text :x="floor.x + floor.w - 12" :y="floor.y + floor.h - 10" class="floor-tag power" text-anchor="end">
              {{ tl('电通道') }}
            </text>
            <!-- 机柜行列网格 + 热力气泡 -->
            <g
              v-for="(rack, i) in floor.racks"
              :key="'rack' + i"
              class="floor-rack"
              :class="{ dim: activeId != null && !rack.near }"
            >
              <rect
                :x="rack.x"
                :y="rack.y"
                :width="rack.w"
                :height="rack.h"
                rx="4"
                :fill="rack.color"
                class="rack-cell"
              />
              <!-- 热力脉冲 -->
              <circle
                v-if="rack.hot"
                :cx="rack.x + rack.w / 2"
                :cy="rack.y + rack.h / 2"
                :r="rack.w * 0.7"
                :fill="rack.color"
                class="rack-pulse"
              />
              <text
                :x="rack.x + rack.w / 2"
                :y="rack.y + rack.h / 2 + 3"
                class="rack-label"
              >
                {{ rack.load }}°
              </text>
            </g>
          </g>

          <!-- 边 (底层) -->
          <g class="tf-edges">
            <template v-for="e in layout.edges" :key="e.id">
              <path
                :id="e.id"
                :d="e.d"
                :class="['edge', e.type, { fault: e.affected, dim: dimEdge(e), hot: hotEdge(e) }]"
                fill="none"
              />
              <!-- [增强] 能流粒子密度随负载变化: 负载越高粒子越多 -->
              <template v-for="k in e.particles" :key="'p' + k">
              <circle
                v-if="!dimEdge(e)"
                r="3.2"
                :class="['flow-dot', e.type, { fault: e.affected }]"
              >
                <animateMotion
                  :dur="e.dur"
                  :begin="(-(e.durMs / e.particles) * k).toFixed(2) + 's'"
                  repeatCount="indefinite"
                >
                  <mpath :href="'#' + e.id" />
                </animateMotion>
              </circle>
              </template>
            </template>
          </g>

          <!-- 节点 (上层) -->
          <g class="tf-nodes">
            <g
              v-for="n in layout.nodes"
              :key="n.id"
              class="tf-node"
              :class="[
                n.lane,
                {
                  affected: n.affected,
                  down: n.downstream,
                  dim: dimNode(n),
                  focus: focusedId === n.id,
                },
              ]"
              :transform="`translate(${n.x},${n.y})`"
              @click.stop="focusNode(n.id)"
              @mouseenter="hoveredId = n.id"
              @mouseleave="hoveredId = null"
            >
              <title>
                {{ n.label }} · {{ n.kind }} · {{ tl('负载') }} {{ n.load }}% · {{ tl('健康') }}
                {{ n.health }}{{ n.redundancy ? ' · ' + n.redundancy : ''
                }}{{ n.tempText ? ' · ' + n.tempText : '' }}
              </title>
              <rect :width="NODE_W" :height="NODE_H" rx="9" class="tf-rect" />
              <rect
                :width="NODE_W"
                :height="3"
                rx="1.5"
                class="tf-loadbar"
                :x="0"
                :y="0"
                :style="{ width: NODE_W * Math.min(1, n.load / 100) + 'px' }"
              />
              <text :x="NODE_W / 2" y="14" class="tf-kind">{{ n.kind }}</text>
              <text :x="NODE_W / 2" y="27" class="tf-load">{{ n.loadText }}</text>
              <text v-if="n.tempText" :x="NODE_W / 2" y="39" class="tf-temp">{{ n.tempText }}</text>
              <circle v-if="n.affected" :cx="NODE_W - 7" :cy="7" r="3.5" class="tf-badge" />
            </g>
          </g>
        </svg>
      </div>

      <!-- 链路缩略图 / 聚焦导航 -->
      <div class="tf-minimap">
        <div class="mm-title">
          <span>{{ tl('缩略图') }}</span>
          <span class="mm-tip">{{ tl('点击定位') }}</span>
        </div>
        <svg
          class="mm-svg"
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          preserveAspectRatio="xMidYMid meet"
          @click="onMinimapClick"
        >
          <path
            v-for="e in layout.edges"
            :key="e.id"
            :d="e.d"
            :class="['mm-edge', { 'mm-fault': e.affected }]"
            fill="none"
          />
          <rect
            v-if="viewportRect"
            :x="viewportRect.x"
            :y="viewportRect.y"
            :width="viewportRect.w"
            :height="viewportRect.h"
            class="mm-view"
          />
          <circle
            v-for="n in layout.nodes"
            :key="n.id"
            :cx="n.x + NODE_W / 2"
            :cy="n.y + NODE_H / 2"
            r="2.8"
            :class="['mm-node', n.lane, { affected: n.affected, focus: focusedId === n.id }]"
            @click.stop="focusNode(n.id)"
          >
            <title>{{ n.label }}</title>
          </circle>
        </svg>
      </div>

      <!-- 聚焦详情卡 -->
      <div class="tf-focus-card" v-if="focusedDetail">
        <div class="ff-head">
          <span class="ff-kind" :class="'lane-' + focusedDetail.node.lane">{{
            focusedDetail.node.kind
          }}</span>
          <span class="ff-name">{{ focusedDetail.node.label }}</span>
          <button class="ff-x" @click="clearFocus" :title="tl('取消聚焦')"><X :size="13" /></button>
        </div>
        <div class="ff-room" v-if="focusedDetail.roomName">{{ focusedDetail.roomName }}</div>
        <div class="ff-rows">
          <div class="ff-row">
            <span>{{ tl('负载') }}</span
            ><b>{{ focusedDetail.node.load }}%</b>
          </div>
          <div class="ff-row" v-if="focusedDetail.node.tempText">
            <span>{{ tl('温度') }}</span
            ><b>{{ focusedDetail.node.tempText }}</b>
          </div>
          <div class="ff-row">
            <span>{{ tl('健康') }}</span
            ><b :style="{ color: hColor(focusedDetail.node.health) }">{{
              focusedDetail.node.health
            }}</b>
          </div>
          <div class="ff-row" v-if="focusedDetail.node.redundancy">
            <span>{{ tl('冗余') }}</span
            ><b>{{ focusedDetail.node.redundancy }}</b>
          </div>
          <div class="ff-row" v-if="focusedDetail.rt">
            <span>{{ tl('在线') }}</span>
            <b :style="{ color: focusedDetail.rt.online ? 'var(--green)' : 'var(--red)' }">{{
              focusedDetail.rt.online ? tl('在线') : tl('离线')
            }}</b>
          </div>
        </div>
        <div class="ff-metrics" v-if="rtFields.length">
          <span class="ff-m" v-for="m in rtFields" :key="m.k"
            >{{ m.k }} <b>{{ m.v }}</b></span
          >
        </div>
        <div class="ff-hint">{{ tl('点击空白区域取消聚焦') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import type { TopologyGraph, TopologyNode, NodeRealtime, TopologyRealtime } from '@/types'

const props = defineProps<{
  graph: TopologyGraph
  realtime?: TopologyRealtime | null
  affectedIds?: number[]
  roomName?: (roomId: number) => string | null
}>()

const { t, te } = useI18n()
const tl = (k: string) => (te(k) ? t(k) : k)

const canvasRef = ref<HTMLElement | null>(null)
const scrollPos = ref({ x: 0, y: 0 })

const NODE_W = 92
const NODE_H = 46
const LEFT = 64
const COL_GAP = 116
const ROW_GAP = 30

const POWERS = [
  'hv_incomer',
  'hv_isolator',
  'hv_breaker',
  'transformer',
  'ups',
  'hvdc',
  'lv_feeder',
  'ats',
]
const COOLS = ['chiller', 'chw_pump', 'cooling_tower', 'hex', 'sec_pump', 'valve', 'crac']
const AUX = ['genset', 'bus_tie', 'battery_group']
const powerSet = new Set(POWERS)
const coolSet = new Set(COOLS)
const auxSet = new Set(AUX)

// ---- 真实测点映射 (任务①): 接 /api/external/.../metrics/realtime, 驱动能流速度/温度 ----
function rtOf(id: number): NodeRealtime | undefined {
  return (props.realtime?.nodes ?? {})[id]
}
// 有效负载率: 优先真实测点 loadPct, 缺失时回退模拟 loadPct
function effLoadPct(n: TopologyNode, rt?: NodeRealtime): number {
  if (rt && rt.loadPct != null) return Math.max(0, Math.min(100, rt.loadPct))
  return Math.max(0, Math.min(100, n.loadPct ?? 0))
}
// 冷量流温度文本 (供水→回水), 否则通用温度
function nodeTempText(rt?: NodeRealtime): string | null {
  if (!rt) return null
  if (rt.supplyTemp != null || rt.returnTemp != null) {
    const s = rt.supplyTemp != null ? rt.supplyTemp.toFixed(1) : '–'
    const r = rt.returnTemp != null ? rt.returnTemp.toFixed(1) : '–'
    return `${s}→${r}℃`
  }
  if (rt.temp != null) return `${rt.temp.toFixed(1)}℃`
  return null
}
// 节点负载文本: 真实负载% / 供电域真实功率kW / 模拟负载%
function nodeLoadText(n: TopologyNode, rt?: NodeRealtime, lane?: string): string {
  const health = Math.round(n.health ?? 100)
  if (rt && rt.loadPct != null) return `${Math.round(rt.loadPct)}% · ${health}`
  if (lane === 'power' && rt && rt.powerKw != null) return `${Math.round(rt.powerKw)}kW · ${health}`
  return `${Math.round(n.loadPct ?? 0)}% · ${health}`
}

type Lane = 'power' | 'cool' | 'aux'
function laneOf(domain: string, category: string): Lane {
  if (powerSet.has(category)) return 'power'
  if (coolSet.has(category)) return 'cool'
  if (auxSet.has(category)) return 'aux'
  if (domain.startsWith('power')) return 'power'
  if (domain.startsWith('hvac')) return 'cool'
  return 'aux'
}
function hColor(h: number) {
  return h >= 75 ? 'var(--green)' : h >= 60 ? 'var(--amber)' : 'var(--red)'
}

interface LNode {
  id: number
  x: number
  y: number
  lane: string
  label: string
  kind: string
  load: number
  health: number
  redundancy: string
  affected: boolean
  downstream: boolean
  loadText: string
  tempText: string | null
}
interface LEdge {
  id: string
  d: string
  type: 'power' | 'cool'
  affected: boolean
  dur: string
  durMs: number
  particles: number
  source: number
  target: number
}

// [增强] 机柜热力色: 温度 → 蓝(冷)→青→黄→红(热) 渐变
function heatColor(temp: number): string {
  const t = Math.max(10, Math.min(45, temp))
  // 10℃→蓝, 22℃→青, 30℃→黄, 40℃+→红
  if (t <= 22) {
    const r = (t - 10) / 12
    return `rgba(${Math.round(34 + r * 0)}, ${Math.round(211 - r * 0)}, ${Math.round(238 - r * 0)}, 0.55)`
  }
  if (t <= 30) {
    const r = (t - 22) / 8
    return `rgba(${Math.round(34 + r * 188)}, ${Math.round(211 - r * 12)}, ${Math.round(238 - r * 16)}, 0.6)`
  }
  const r = Math.min(1, (t - 30) / 10)
  return `rgba(251, ${Math.round(199 - r * 4)}, ${Math.round(222 - r * 145)}, ${0.6 + r * 0.2})`
}

const affectedSet = computed(() => new Set(props.affectedIds ?? []))

// ---- 聚焦交互状态 ----
const focusedId = ref<number | null>(null)
const hoveredId = ref<number | null>(null)
const activeId = computed(() => focusedId.value ?? hoveredId.value)

const activeNeighbors = computed(() => {
  const id = activeId.value
  const s = new Set<number>()
  if (id == null) return s
  for (const e of props.graph?.edges ?? []) {
    if (e.source === id) s.add(e.target)
    if (e.target === id) s.add(e.source)
  }
  s.add(id)
  return s
})
function dimNode(n: LNode): boolean {
  return activeId.value != null && !activeNeighbors.value.has(n.id)
}
function dimEdge(e: LEdge): boolean {
  return activeId.value != null && e.source !== activeId.value && e.target !== activeId.value
}
function hotEdge(e: LEdge): boolean {
  return activeId.value != null && (e.source === activeId.value || e.target === activeId.value)
}
function focusNode(id: number) {
  focusedId.value = id
}
function clearFocus() {
  focusedId.value = null
}

// ---- 缩略图视口矩形 (随滚动同步) ----
function onScroll() {
  const c = canvasRef.value
  if (c) scrollPos.value = { x: c.scrollLeft, y: c.scrollTop }
}
const viewportRect = computed(() => {
  const c = canvasRef.value
  if (!c) return null
  scrollPos.value // 依赖, 触发重算
  const w = Math.min(c.clientWidth, layout.value.width)
  const h = Math.min(c.clientHeight, layout.value.height)
  let x = c.scrollLeft
  let y = c.scrollTop
  if (x + w > layout.value.width) x = Math.max(0, layout.value.width - w)
  if (y + h > layout.value.height) y = Math.max(0, layout.value.height - h)
  return { x, y, w, h }
})
function onMinimapClick(ev: MouseEvent) {
  const svg = ev.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  const gx = ((ev.clientX - rect.left) / rect.width) * layout.value.width
  const gy = ((ev.clientY - rect.top) / rect.height) * layout.value.height
  const c = canvasRef.value
  if (!c) return
  c.scrollTo({
    left: Math.max(0, gx - c.clientWidth / 2),
    top: Math.max(0, gy - c.clientHeight / 2),
    behavior: 'smooth',
  })
}

// ---- 聚焦详情 ----
const focusedDetail = computed(() => {
  const id = focusedId.value
  if (id == null) return null
  const node = layout.value.nodes.find((n) => n.id === id)
  if (!node) return null
  const raw = props.graph?.nodes.find((n) => n.id === id)
  const rt = rtOf(id)
  return {
    node,
    raw,
    rt,
    roomName: props.roomName && raw?.roomId != null ? props.roomName(raw.roomId) : null,
  }
})
const RT_LABEL: Record<string, string> = {
  loadPct: '负载%',
  powerKw: '功率kW',
  supplyTemp: '供水℃',
  returnTemp: '回水℃',
  temp: '温度℃',
}
const rtFields = computed(() => {
  const rt = focusedDetail.value?.rt
  if (!rt) return []
  const out: { k: string; v: string }[] = []
  for (const [k, lab] of Object.entries(RT_LABEL)) {
    const v = (rt as Record<string, unknown>)[k]
    if (v != null && typeof v === 'number') {
      const dec = k === 'powerKw' ? 0 : 1
      out.push({ k: lab, v: v.toFixed(dec) })
    }
  }
  return out
})

function onResize() {
  onScroll()
}
onMounted(() => {
  onScroll()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})

// 拓扑分层: 依据真实边给同 lane 节点分配 stage 列 (无入边=第0列, 沿边递增)
function layerAssign(
  ids: number[],
  edgs: { source: number; target: number }[],
): Map<number, number> {
  const indeg = new Map<number, number>()
  const adj = new Map<number, number[]>()
  ids.forEach((id) => {
    indeg.set(id, 0)
    adj.set(id, [])
  })
  for (const e of edgs) {
    if (!adj.has(e.source) || !indeg.has(e.target)) continue
    adj.get(e.source)!.push(e.target)
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1)
  }
  const layer = new Map<number, number>()
  indeg.forEach((v, id) => {
    if (v === 0) layer.set(id, 0)
  })
  for (let pass = 0; pass <= ids.length; pass++) {
    let changed = false
    for (const e of edgs) {
      if (!layer.has(e.source)) continue
      const ls = layer.get(e.source)!
      const cur = layer.has(e.target) ? layer.get(e.target)! : -1
      const want = ls + 1
      if (cur < 0 || want > cur) {
        layer.set(e.target, want)
        changed = true
      }
    }
    if (!changed) break
  }
  ids.forEach((id) => {
    if (!layer.has(id)) layer.set(id, 0)
  })
  return layer
}

/** 提取机房平面图层 (从 layout 中暴露给模板直接使用) */
const floor = computed(() => layout.value.floor)

const layout = computed(() => {
  const nodes = props.graph?.nodes ?? []
  const edges = props.graph?.edges ?? []

  const byId = new Map<number, TopologyNode>()
  for (const n of nodes) byId.set(n.id, n)

  // 真实测点归一化映射: 每个节点的有效负载率 (驱动能流速度)
  const rtm = props.realtime?.nodes ?? {}
  const effById = new Map<number, number>()
  for (const n of nodes) effById.set(n.id, effLoadPct(n, rtm[n.id]))

  // 1) 按 domain 分 lane, 并用真实边做拓扑分层 (数据驱动, 不依赖后端 stage 命名)
  const laneNodes: Record<Lane, TopologyNode[]> = { power: [], cool: [], aux: [] }
  for (const n of nodes) laneNodes[laneOf(n.domain || '', n.category || '')].push(n)

  const pos = new Map<number, { x: number; y: number }>()
  let laneTop = 14
  let maxCol = 0

  const laneOrder: Lane[] = ['power', 'aux', 'cool']
  for (const lane of laneOrder) {
    const ns = laneNodes[lane]
    if (!ns.length) continue
    const idSet = new Set(ns.map((n) => n.id))
    const inLane = edges.filter((e) => idSet.has(e.source) && idSet.has(e.target))
    const layer = layerAssign(
      ns.map((n) => n.id),
      inLane,
    )

    // 参与真实边的节点按拓扑层排布; 断连节点(后端未连边)按 category 横向铺开, 避免单列堆叠
    const connected = new Set<number>()
    for (const e of inLane) {
      connected.add(e.source)
      connected.add(e.target)
    }
    let maxConnLayer = 0
    for (const id of connected) maxConnLayer = Math.max(maxConnLayer, layer.get(id) ?? 0)
    const discCats: string[] = []
    for (const n of ns) {
      if (!connected.has(n.id) && !discCats.includes(n.category || ''))
        discCats.push(n.category || '')
    }
    const colOfNode = (n: TopologyNode): number => {
      if (connected.has(n.id)) return layer.get(n.id) ?? 0
      const ci = discCats.indexOf(n.category || '')
      return maxConnLayer + 1 + (ci < 0 ? 0 : ci)
    }

    const colNodes: Record<number, TopologyNode[]> = {}
    let laneMaxCol = 0
    let laneMaxCount = 0
    for (const n of ns) {
      const c = colOfNode(n)
      laneMaxCol = Math.max(laneMaxCol, c)
      ;(colNodes[c] ??= []).push(n)
      laneMaxCount = Math.max(laneMaxCount, colNodes[c].length)
    }
    maxCol = Math.max(maxCol, laneMaxCol)
    const laneH = laneMaxCount * ROW_GAP + 16
    for (const [cstr, list] of Object.entries(colNodes)) {
      const c = Number(cstr)
      list.forEach((n, i) => {
        pos.set(n.id, { x: LEFT + c * COL_GAP, y: laneTop + 10 + i * ROW_GAP })
      })
    }
    laneTop += laneH + 22
  }

  // 2) 故障下游传播: 从波及节点沿边 BFS 标 downstream
  const downstreamSet = new Set<number>()
  const queue = [...affectedSet.value]
  const seen = new Set(queue)
  while (queue.length) {
    const cur = queue.shift()!
    for (const e of edges) {
      if (e.source === cur && !seen.has(e.target)) {
        seen.add(e.target)
        downstreamSet.add(e.target)
        queue.push(e.target)
      }
    }
  }

  const lnodes: LNode[] = nodes.map((n) => {
    const p = pos.get(n.id) ?? { x: LEFT, y: laneTop }
    const rt = rtm[n.id]
    const lane = laneOf(n.domain || '', n.category || '')
    return {
      id: n.id,
      x: p.x,
      y: p.y,
      lane,
      label: n.label,
      kind: n.kind,
      load: effById.get(n.id) ?? Math.round(n.loadPct ?? 0),
      health: Math.round(n.health ?? 100),
      redundancy: n.redundancy || '',
      affected: affectedSet.value.has(n.id),
      downstream: downstreamSet.has(n.id),
      loadText: nodeLoadText(n, rt, lane),
      tempText: nodeTempText(rt),
    }
  })

  const ledges: LEdge[] = []
  for (const e of edges) {
    const s = pos.get(e.source)
    const tg = pos.get(e.target)
    const sn = byId.get(e.source)
    const tn = byId.get(e.target)
    if (!s || !tg || !sn || !tn) continue
    const sx = s.x + NODE_W
    const sy = s.y + NODE_H / 2
    const tx = tg.x
    const ty = tg.y + NODE_H / 2
    const dx = tx - sx
    const d = `M ${sx} ${sy} C ${sx + dx * 0.5} ${sy}, ${tx - dx * 0.5} ${ty}, ${tx} ${ty}`
    const avgLoad = (effById.get(e.source)! + effById.get(e.target)!) / 2
    const durMs = Math.max(900, Math.min(3000, Math.round(2600 - avgLoad / 45 * 1700)))
    // [增强] 粒子数随负载升高: 负载 20%→2 颗, 100%→6 颗
    const particles = Math.max(2, Math.min(6, Math.round(2 + avgLoad / 20)))
    const dur = (durMs / 1000).toFixed(2) + 's'
    const touch = affectedSet.value.has(e.source) || affectedSet.value.has(e.target)
    ledges.push({
      id: `e-${e.source}-${e.target}`,
      d,
      type: (e.type === 'cool' ? 'cool' : 'power') as 'power' | 'cool',
      affected: touch,
      dur,
      durMs,
      particles,
      source: e.source,
      target: e.target,
    })
  }

  const width = LEFT + (maxCol + 1) * COL_GAP + 24
  const height = laneTop + 10

  // [增强] 机房平面 + 机柜热力层: 把拓扑节点按 lane 聚合为虚拟机柜网格,
  // 每个机柜格显示该 lane 聚合温度(取节点温度均值)的热力色 + 脉冲动画。
  const floor = (() => {
    const pad = 14
    const fx = pad
    const fy = pad
    const fw = width - pad * 2
    const fh = Math.max(height - pad * 2, 220)
    const lanes: Lane[] = ['power', 'cool', 'aux']
    const cols = Math.max(6, maxCol + 2)
    const rows = lanes.length
    const cellGap = 10
    const gridW = fw - 24
    const gridH = fh - 48
    const cw = (gridW - (cols - 1) * cellGap) / cols
    const ch = (gridH - (rows - 1) * cellGap) / rows
    const racks: {
      x: number
      y: number
      w: number
      h: number
      color: string
      load: number
      hot: boolean
      near: boolean
    }[] = []
    lanes.forEach((lane, r) => {
      const ns = laneNodes[lane]
      const temps = ns
        .map((n) => {
          const rt = rtm[n.id]
          if (rt?.temp != null) return rt.temp
          if (rt?.supplyTemp != null && rt?.returnTemp != null)
            return (rt.supplyTemp + rt.returnTemp) / 2
          return 26 - (effById.get(n.id) ?? 0) / 12 // 负载越高越热
        })
        .filter((v) => v != null)
      const avg = temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : 24
      const count = ns.length || 1
      for (let c = 0; c < cols; c++) {
        // 该列机柜格温度: 依据对应节点索引偏移, 形成起伏的热力分布
        const idx = c % count
        const t = avg + (idx - count / 2) * 0.8
        racks.push({
          x: fx + 12 + c * (cw + cellGap),
          y: fy + 30 + r * (ch + cellGap),
          w: cw,
          h: ch,
          color: heatColor(t),
          load: Math.round(t),
          hot: t >= 36,
          near: true,
        })
      }
    })
    return { enabled: true, x: fx, y: fy, w: fw, h: fh, racks }
  })()

  return { nodes: lnodes, edges: ledges, width, height, floor }
})
</script>

<style scoped>
.topo-flow {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tf-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  font-size: 11px;
  color: var(--txt3);
}
.tf-lg {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.tf-lg.dim {
  opacity: 0.7;
}
.tf-lg.hint {
  color: var(--cyan);
  opacity: 0.85;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}
.dot.flow-power {
  background: #fbbf24;
  box-shadow: 0 0 6px #fbbf24;
}
.dot.flow-cool {
  background: #22d3ee;
  box-shadow: 0 0 6px #22d3ee;
}
.dot.fault {
  background: #ff4d4f;
  box-shadow: 0 0 6px #ff4d4f;
}
.dot.heat {
  background: linear-gradient(90deg, #22d3ee, #fbbf24, #ff4d4f);
  box-shadow: 0 0 6px rgba(251, 191, 36, 0.6);
}

/* [增强] 机房平面 + 机柜热力层 */
.floor-board {
  fill: rgba(12, 20, 34, 0.55);
  stroke: rgba(34, 211, 238, 0.22);
  stroke-width: 1.2;
  stroke-dasharray: 3 5;
}
.floor-strip {
  fill: rgba(34, 211, 238, 0.08);
  stroke: none;
}
.floor-title {
  fill: rgba(125, 211, 252, 0.85);
  font-size: 11px;
  font-weight: 700;
}
.floor-tag {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.8;
}
.floor-tag.cool {
  fill: #22d3ee;
}
.floor-tag.power {
  fill: #fbbf24;
}
.rack-cell {
  stroke: rgba(255, 255, 255, 0.08);
  stroke-width: 0.8;
  transition: opacity 0.2s ease;
}
.floor-rack {
  transition: opacity 0.2s ease;
}
.floor-rack.dim {
  opacity: 0.18;
}
.rack-pulse {
  opacity: 0.35;
  transform-origin: center;
  animation: rackPulse 1.6s ease-out infinite;
}
@keyframes rackPulse {
  0% {
    transform: scale(0.4);
    opacity: 0.5;
  }
  100% {
    transform: scale(1.6);
    opacity: 0;
  }
}
.rack-label {
  fill: rgba(8, 12, 20, 0.85);
  font-size: 9px;
  font-weight: 700;
  text-anchor: middle;
  pointer-events: none;
}

.tf-stage {
  position: relative;
}
.tf-canvas {
  width: 100%;
  max-height: 520px;
  overflow: auto;
  background:
    radial-gradient(circle at 20% 10%, rgba(34, 211, 238, 0.05), transparent 40%),
    radial-gradient(circle at 80% 90%, rgba(251, 191, 36, 0.05), transparent 40%), var(--bg);
  border-radius: 12px;
  border: 1px solid var(--line);
}
.tf-svg {
  display: block;
}

/* 边 */
.edge {
  stroke-width: 1.6;
  opacity: 0.55;
  transition:
    opacity 0.15s ease,
    stroke-width 0.15s ease;
}
.edge.power {
  stroke: #fbbf24;
}
.edge.cool {
  stroke: #22d3ee;
}
.edge.fault {
  stroke: #ff4d4f;
  stroke-width: 2.4;
  opacity: 1;
  stroke-dasharray: 6 4;
  animation: dash 1s linear infinite;
}
.edge.dim {
  opacity: 0.1;
}
.edge.hot {
  opacity: 1;
  stroke-width: 2.6;
}
@keyframes dash {
  to {
    stroke-dashoffset: -20;
  }
}

.flow-dot {
  fill: #fbbf24;
  filter: drop-shadow(0 0 3px #fbbf24);
}
.flow-dot.cool {
  fill: #22d3ee;
  filter: drop-shadow(0 0 3px #22d3ee);
}
.flow-dot.fault {
  fill: #ff4d4f;
  filter: drop-shadow(0 0 4px #ff4d4f);
}
.flow-dot.dim {
  opacity: 0.1;
}

/* 节点 */
.tf-rect {
  fill: var(--bg2);
  stroke: var(--line);
  stroke-width: 1.4;
  transition:
    stroke 0.15s ease,
    fill 0.15s ease;
}
.tf-node {
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.tf-node.power .tf-rect {
  stroke: rgba(251, 191, 36, 0.5);
}
.tf-node.cool .tf-rect {
  stroke: rgba(34, 211, 238, 0.5);
}
.tf-node.aux .tf-rect {
  stroke: rgba(148, 163, 184, 0.5);
}
.tf-kind {
  fill: var(--txt);
  font-size: 11px;
  font-weight: 700;
  text-anchor: middle;
}
.tf-load {
  fill: var(--txt3);
  font-size: 9.5px;
  text-anchor: middle;
}
.tf-temp {
  fill: #22d3ee;
  font-size: 9px;
  text-anchor: middle;
  font-weight: 600;
}
.tf-node.power .tf-temp {
  fill: #fbbf24;
}
.tf-loadbar {
  fill: rgba(34, 197, 94, 0.55);
}
.tf-node.affected .tf-rect {
  stroke: #ff4d4f;
  stroke-width: 2.4;
  fill: rgba(255, 77, 79, 0.16);
  animation: pulse 1.1s ease-in-out infinite;
}
.tf-node.affected .tf-kind {
  fill: #ffd7d7;
}
.tf-node.downstream .tf-rect {
  stroke: rgba(255, 77, 79, 0.6);
}
.tf-node.dim {
  opacity: 0.22;
}
.tf-node.focus .tf-rect {
  stroke: #22e3ff;
  stroke-width: 2.8;
  fill: rgba(34, 227, 255, 0.12);
}
@keyframes pulse {
  0%,
  100% {
    stroke-opacity: 1;
  }
  50% {
    stroke-opacity: 0.35;
  }
}
.tf-badge {
  fill: #ff4d4f;
}

/* 缩略图 */
.tf-minimap {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 184px;
  background: rgba(10, 15, 25, 0.8);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 6px 7px 8px;
  backdrop-filter: blur(4px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
  z-index: 5;
}
.mm-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: var(--txt3);
  margin-bottom: 4px;
}
.mm-tip {
  color: var(--cyan);
  opacity: 0.8;
}
.mm-svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 150px;
  cursor: crosshair;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
}
.mm-edge {
  stroke: rgba(148, 163, 184, 0.3);
  stroke-width: 1;
}
.mm-edge.mm-fault {
  stroke: rgba(255, 77, 79, 0.7);
}
.mm-view {
  fill: rgba(34, 227, 255, 0.14);
  stroke: rgba(34, 227, 255, 0.65);
  stroke-width: 1.2;
}
.mm-node {
  cursor: pointer;
}
.mm-node.power {
  fill: #fbbf24;
}
.mm-node.cool {
  fill: #22d3ee;
}
.mm-node.aux {
  fill: #94a3b8;
}
.mm-node.affected {
  fill: #ff4d4f;
}
.mm-node.focus {
  stroke: #fff;
  stroke-width: 1.6;
}

/* 聚焦详情卡 */
.tf-focus-card {
  position: absolute;
  left: 10px;
  bottom: 10px;
  width: 232px;
  background: rgba(12, 18, 30, 0.93);
  border: 1px solid rgba(34, 227, 255, 0.35);
  border-radius: 10px;
  padding: 10px 12px;
  z-index: 6;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
}
.ff-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ff-kind {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--bg2);
  color: var(--txt2);
}
.ff-kind.lane-power {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.14);
}
.ff-kind.lane-cool {
  color: #22d3ee;
  background: rgba(34, 211, 238, 0.14);
}
.ff-kind.lane-aux {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.14);
}
.ff-name {
  font-size: 13px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ff-x {
  border: none;
  background: transparent;
  color: var(--txt3);
  cursor: pointer;
  display: inline-flex;
  padding: 2px;
  border-radius: 5px;
}
.ff-x:hover {
  color: var(--txt);
  background: rgba(255, 255, 255, 0.08);
}
.ff-room {
  font-size: 11px;
  color: #7dd3fc;
  margin: 3px 0 6px;
}
.ff-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ff-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--txt2);
}
.ff-row b {
  color: var(--txt);
  font-weight: 700;
}
.ff-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px dashed var(--line);
  font-size: 11px;
  color: var(--txt3);
}
.ff-m b {
  color: var(--txt);
  font-weight: 700;
}
.ff-hint {
  font-size: 10px;
  color: var(--txt3);
  margin-top: 7px;
  opacity: 0.8;
}
</style>
