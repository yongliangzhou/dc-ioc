<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">消防系统</h2>
        <p class="page-sub">Fire Alarm · 烟感/温感/喷淋/手报/消火栓 + 气体灭火 + 极早期 VESDA</p>
      </div>
      <div class="head-actions">
        <span class="host-badge" :class="s.hostState.includes('正常') ? 'g' : 'a'">
          主机 {{ s.hostState }} · {{ s.loops }} 回路
        </span>
        <button class="btn" @click="refresh">刷新</button>
        <span v-if="usingMock" class="mock-flag-sm">⚠ 模拟数据</span>
      </div>
    </div>

    <MockDataBanner :level="mockLevel" :reason="mockReason" />

    <!-- 总览 KPI -->
    <div class="kpi-row">
      <KpiCard
        title="探测点位"
        :value="s.points"
        unit="点"
        :sub="'故障 ' + s.faultPoints + ' 点'"
      />
      <KpiCard
        title="主机遇警率"
        :value="hostOkRate"
        unit="%"
        :trend="s.faultPoints ? -1 : 1"
        :sub="s.faultPoints ? '需处置' : '正常'"
      />
      <KpiCard
        title="气体灭火区"
        :value="s.gas.ready"
        :unit="'/ ' + s.gas.zones + ' 区'"
        :sub="'药剂 ' + s.gas.agent"
      />
      <KpiCard
        title="应急照明"
        :value="s.emergency.ok"
        :unit="'/ ' + s.emergency.lights"
        :trend="batteryOk ? 1 : -1"
        :sub="'蓄电池 ' + s.emergency.batteryOk + '%'"
      />
    </div>

    <div class="grid-main">
      <!-- 左：消防平面图 SVG -->
      <Panel class="plan-card">
        <div class="card-head">
          <span class="card-title">消防平面图</span>
          <div class="legend">
            <span class="lg"><i class="lg-dot sm"></i>烟感</span>
            <span class="lg"><i class="lg-dot tm"></i>温感</span>
            <span class="lg"><i class="lg-dot sp"></i>喷淋</span>
            <span class="lg"><i class="lg-dot mb"></i>手报</span>
            <span class="lg"><i class="lg-dot hy"></i>消火栓</span>
            <span class="lg"><i class="lg-dot a"></i>报警</span>
            <button class="plan-edit" @click="editOpen = true">
              编辑{{ hasGraphicEdits ? ' ●' : '' }}
            </button>
          </div>
        </div>
        <div class="plan-wrap">
          <svg viewBox="0 0 620 400" class="plan-svg" @click="selected = null">
            <!-- 楼层外框 + 走廊 + 分区 -->
            <rect x="20" y="20" width="580" height="360" rx="10" class="floor" />
            <rect x="250" y="170" width="120" height="100" rx="4" class="corridor" />
            <text x="34" y="42" class="s-label">A 区机房层 · 消防点位</text>
            <!-- 分区块 -->
            <rect x="40" y="60" width="180" height="90" rx="5" class="zone-block" />
            <text x="52" y="80" class="z-label">模块机房 A</text>
            <rect x="240" y="60" width="180" height="90" rx="5" class="zone-block" />
            <text x="252" y="80" class="z-label">主机房 B</text>
            <rect x="440" y="60" width="140" height="90" rx="5" class="zone-block" />
            <text x="452" y="80" class="z-label">配电区 C</text>
            <rect x="40" y="290" width="180" height="70" rx="5" class="zone-block" />
            <text x="52" y="310" class="z-label">钢瓶间</text>
            <rect x="440" y="290" width="140" height="70" rx="5" class="zone-block" />
            <text x="452" y="310" class="z-label">疏散通道</text>

            <!-- 报警点位弹窗 -->
            <g v-if="alarmPoint" class="pop">
              <rect x="430" y="150" width="170" height="92" rx="6" class="pop-bg" />
              <text x="442" y="170" class="pop-t">{{ alarmPoint.label }}</text>
              <text x="442" y="190" class="pop-d">类型：{{ alarmPoint.kind }}</text>
              <text x="442" y="208" class="pop-d">
                状态：{{ alarmPoint.state === 'alarm' ? '报警' : '故障' }}
              </text>
              <text x="442" y="226" class="pop-d" v-if="alarmPoint.desc">
                {{ alarmPoint.desc }}
              </text>
            </g>

            <!-- 消防点位 -->
            <g v-for="p in pointsView" :key="p.id" @click.stop="selectPoint(p)">
              <circle :cx="p.x" :cy="p.y" r="5.5" :class="'fp ' + p.kind + ' ' + p.state" />
              <circle v-if="p.state === 'alarm'" :cx="p.x" :cy="p.y" r="10" class="fp-pulse" />
              <text
                :x="p.x + 8"
                :y="p.y + 3"
                class="fp-name"
                v-if="p.state !== 'normal' || selected"
              >
                {{ p.short }}
              </text>
            </g>
          </svg>
          <div v-if="selected" class="z-info">
            <div class="z-info-h">
              <span
                class="fp"
                :class="selected.kind + ' ' + selected.state"
                style="width: 10px; height: 10px; border-radius: 50%; display: inline-block"
              ></span
              >{{ selected.label }}
            </div>
            <div class="z-info-b">
              <span>类型：{{ kindText(selected.kind) }}</span>
              <span>状态：{{ stateText(selected.state) }}</span>
              <span>位置：{{ selected.zone }}</span>
            </div>
          </div>
          <div v-else class="z-info muted">点击平面图上的点位查看详情</div>
        </div>
      </Panel>

      <!-- 统一图形编辑入口: 对消防平面图点位做增删改 (覆盖层, 不影响接口数据) -->
      <GraphicEditDrawer
        v-model="editOpen"
        :editor="graphicEditor"
        title="消防平面图"
        :defaults="graphicDefaults"
      />

      <!-- 右：报警主机状态面板 -->
      <Panel class="host-card">
        <div class="card-head">
          <span class="card-title">报警主机状态</span
          ><span class="card-sub">{{ s.hostState }}</span>
        </div>
        <div class="host-grid">
          <div class="host-kv">
            <span class="k">主机状态</span
            ><span class="v" :class="s.hostState.includes('正常') ? 'g' : 'a'">{{
              s.hostState
            }}</span>
          </div>
          <div class="host-kv">
            <span class="k">回路数</span><span class="v">{{ s.loops }}</span>
          </div>
          <div class="host-kv">
            <span class="k">探测点位</span><span class="v">{{ s.points }}</span>
          </div>
          <div class="host-kv">
            <span class="k">故障点位</span
            ><span class="v" :class="s.faultPoints ? 'a' : 'g'">{{ s.faultPoints }}</span>
          </div>
          <div class="host-kv">
            <span class="k">气体灭火</span
            ><span class="v" :class="s.gas.ready === s.gas.zones ? 'g' : 'a'"
              >{{ s.gas.ready }}/{{ s.gas.zones }} 就绪</span
            >
          </div>
          <div class="host-kv">
            <span class="k">已释放</span
            ><span class="v" :class="s.gas.released ? 'a' : 'g'">{{ s.gas.released }} 区</span>
          </div>
        </div>
        <div class="host-vesda">
          <div class="hv-head">极早期 VESDA（吸气式）</div>
          <div class="hv-list">
            <div
              v-for="v in s.vesda"
              :key="v.id"
              class="hv-row"
              :class="v.level === '轻微' ? 'warn' : 'ok'"
            >
              <span class="hv-id">{{ v.id }}</span>
              <span class="hv-val mono">{{ v.val }}%</span>
              <span class="hv-lv" :class="v.level === '轻微' ? 'warn' : 'ok'">{{ v.level }}</span>
            </div>
          </div>
        </div>
      </Panel>
    </div>

    <div class="grid-sub">
      <!-- 探测器状态统计 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">探测器状态统计</span
          ><span class="card-sub">{{ s.points }} 点</span>
        </div>
        <div class="det-tabs">
          <button
            class="det-tab"
            :class="{ active: detFilter === 'all' }"
            @click="detFilter = 'all'"
          >
            全部
          </button>
          <button
            class="det-tab"
            :class="{ active: detFilter === 'smoke' }"
            @click="detFilter = 'smoke'"
          >
            烟感
          </button>
          <button
            class="det-tab"
            :class="{ active: detFilter === 'heat' }"
            @click="detFilter = 'heat'"
          >
            温感
          </button>
          <button
            class="det-tab"
            :class="{ active: detFilter === 'manual' }"
            @click="detFilter = 'manual'"
          >
            手报/声光
          </button>
          <button
            class="det-tab"
            :class="{ active: detFilter === 'door' }"
            @click="detFilter = 'door'"
          >
            防火门
          </button>
        </div>
        <div class="stat-row">
          <div class="stat-pie">
            <div class="sp-ring" :style="ringStyle">
              <span class="sp-center"
                ><b>{{ detSummary.normal }}</b
                ><em>正常</em></span
              >
            </div>
          </div>
          <div class="stat-legend">
            <div class="sl" @click="detFilter = 'all'">
              <i class="sl-dot g"></i>正常<b>{{ detSummary.normal }}</b>
            </div>
            <div class="sl" @click="detFilter = 'alarm'">
              <i class="sl-dot a"></i>报警<b>{{ detSummary.alarm }}</b>
            </div>
            <div class="sl" @click="detFilter = 'fault'">
              <i class="sl-dot w"></i>故障<b>{{ detSummary.fault }}</b>
            </div>
            <div class="sl" @click="detFilter = 'offline'">
              <i class="sl-dot o"></i>离线<b>{{ detSummary.offline }}</b>
            </div>
          </div>
        </div>
        <div class="det-list">
          <div
            v-for="d in filteredDets"
            :key="d.type"
            class="det-row"
            :class="d.fault ? 'warn' : 'ok'"
          >
            <span class="d-name">{{ d.type }}</span>
            <span class="d-bar"
              ><span
                class="d-fill"
                :class="d.fault ? 'warn' : 'ok'"
                :style="{ width: detPct(d) + '%' }"
              ></span
            ></span>
            <span class="d-st">{{ d.n - d.fault }}/{{ d.n }}</span>
          </div>
          <EmptyState v-if="!filteredDets.length" text="无探测器" />
        </div>
      </Panel>

      <!-- 消防联动设备状态 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">消防联动设备</span><span class="card-sub">状态联动</span>
        </div>
        <div class="link-grid">
          <div v-for="lk in linkageDevices" :key="lk.name" class="link-item" :class="lk.state">
            <div class="li-ico">
              <component :is="lk.icon" :size="18" />
            </div>
            <div class="li-body">
              <div class="li-name">{{ lk.name }}</div>
              <div class="li-st" :class="lk.state">{{ lk.stateText }}</div>
            </div>
          </div>
        </div>
        <div class="qie-fei">
          <div class="qf-row">
            <span class="k">切非联动</span><span class="v">{{ s.qieFei.state }}</span>
          </div>
          <div class="qf-row">
            <span class="k">最近演练</span><span class="v">{{ s.qieFei.lastDrill }}</span>
          </div>
          <div class="qf-row">
            <span class="k">联动逻辑</span><span class="v">{{ s.qieFei.desc }}</span>
          </div>
        </div>
      </Panel>

      <!-- 火警/故障/监管告警列表 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">火警 / 故障 / 监管</span
          ><span class="card-sub">{{ s.events.length }} 条</span>
        </div>
        <div class="evt-list">
          <div v-for="(e, i) in s.events" :key="i" class="evt-row" :class="lvCls(e.lv)">
            <AlarmBadge :level="e.lv" />
            <span class="evt-ts mono">{{ e.ts }}</span>
            <span class="evt-desc">{{ e.desc }}</span>
          </div>
          <EmptyState v-if="!s.events.length" text="无告警" />
        </div>
      </Panel>
    </div>

    <!-- 知识库 -->
    <Panel class="know">
      <div class="card-head"><span class="card-title">消防架构 · 逻辑 · 故障锁定</span></div>
      <SecurityKnowledge :knowledge="s.knowledge" logic-title="联动逻辑" />
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { Component } from 'vue'
import { Fan, Volume2, DoorOpen, ArrowDownToLine } from 'lucide-vue-next'
import { KpiCard } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import SecurityKnowledge from '@/components/SecurityKnowledge.vue'
import { AlarmBadge } from '@dc-ioc/ui'
import EmptyState from '@/components/monitor/EmptyState.vue'
import {
  getSecurityFireDetailed,
  type FireSummary,
  type FireDetectorView,
  type FireEventView,
} from '@/api/security'
import { useMockFlag } from '@/composables/useAsyncPage'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import GraphicEditDrawer from '@/components/common/GraphicEditDrawer.vue'
import { useGraphicEditor, type NodeAdapter } from '@/composables/useGraphicEditor'
import type { GraphicNode } from '@/types/graphic'

interface Point {
  id: string
  label: string
  short: string
  kind: 'smoke' | 'temp' | 'sprinkler' | 'manual' | 'hydrant'
  state: 'normal' | 'alarm' | 'fault' | 'offline'
  x: number
  y: number
  zone: string
  desc?: string
}
interface LinkDev {
  name: string
  icon: Component
  state: 'ok' | 'act' | 'fault'
  stateText: string
}

const s = ref<FireSummary>({
  hostState: '',
  loops: 0,
  points: 0,
  faultPoints: 0,
  detectors: [],
  gas: { zones: 0, ready: 0, released: 0, agent: '' },
  vesda: [],
  qieFei: { desc: '', state: '', lastDrill: '' },
  emergency: { lights: 0, ok: 0, batteryOk: 0, evacSigns: 0 },
  events: [],
  knowledge: { thresholds: [] },
})
const usingMock = ref(false)
const { level: mockLevel, reason: mockReason, markPartial, markFull } = useMockFlag()

const hostOkRate = computed(() => {
  if (!s.value.points) return 100
  return +(((s.value.points - s.value.faultPoints) / s.value.points) * 100).toFixed(2)
})
const batteryOk = computed(() => s.value.emergency.batteryOk >= 90)

// 消防平面图点位（派生）
const points = ref<Point[]>([])
const selected = ref<Point | null>(null)
// 报警弹窗取覆盖层合并后的点位, 保证改名/自建节点的报警同样可见 (无编辑时与原行为一致)
const alarmPoint = computed(() => pointsView.value.find((p) => p.state === 'alarm') || null)

function buildPoints(detectors: FireDetectorView[], events: FireEventView[]): Point[] {
  const out: Point[] = []
  const layout: { kind: Point['kind']; zone: string; xs: number[]; ys: number[] }[] = [
    { kind: 'smoke', zone: '模块机房 A', xs: [70, 110, 150, 190], ys: [110, 110, 110, 110] },
    { kind: 'temp', zone: '主机房 B', xs: [270, 310, 350, 390], ys: [110, 110, 110, 110] },
    { kind: 'hydrant', zone: '配电区 C', xs: [470, 520], ys: [110, 110] },
    { kind: 'smoke', zone: '走廊', xs: [290, 330], ys: [220, 220] },
    { kind: 'manual', zone: '疏散通道', xs: [470, 520], ys: [330, 330] },
    { kind: 'sprinkler', zone: '钢瓶间', xs: [70, 120, 170], ys: [330, 330, 330] },
  ]
  let idx = 0
  layout.forEach((l) => {
    l.xs.forEach((x, i) => {
      out.push({
        id: `${l.kind}-${idx + 1}`,
        label: `${kindText(l.kind)} ${idx + 1}`,
        short: `${lk(l.kind)}${idx + 1}`,
        kind: l.kind,
        state: 'normal',
        x,
        y: l.ys[i] ?? l.ys[0],
        zone: l.zone,
      })
      idx++
    })
  })
  // 报警/故障点位来自事件
  const alarmEvent = events.find((e) => /报警|火警|烟感/.test(e.desc))
  if (alarmEvent) {
    const p = out.find((o) => o.kind === 'smoke')
    if (p) {
      p.state = 'alarm'
      p.desc = alarmEvent.desc
    }
  }
  const faultEvent = events.find((e) => /故障|误报/.test(e.desc))
  if (faultEvent) {
    const p = out.find((o) => o.kind === 'temp')
    if (p) {
      p.state = 'fault'
      p.desc = faultEvent.desc
    }
  }
  return out
}
function kindText(k: string) {
  return (
    {
      smoke: '感烟探测器',
      temp: '感温探测器',
      sprinkler: '喷淋头',
      manual: '手动报警',
      hydrant: '消火栓',
    }[k] || k
  )
}
function lk(k: string) {
  return { smoke: 'S', temp: 'T', sprinkler: 'P', manual: 'M', hydrant: 'H' }[k] || 'X'
}
function selectPoint(p: Point) {
  selected.value = p
}
function stateText(st: string) {
  return { normal: '正常', alarm: '报警', fault: '故障', offline: '离线' }[st] || st
}

/* ───────── 统一图形编辑入口 (消防平面图) ─────────
 * 场景覆盖层: 改名/改类型/改状态/改坐标/改参数 = 覆盖; 删除 = removed; 新增 = 自建点位。
 * 接口派生点位仍是默认值并持续刷新, 编辑只在其上叠加, 不污染数据源。 */
const graphicEditor = useGraphicEditor('security-fire-plan', { title: '消防平面图' })
const editOpen = ref(false)
const hasGraphicEdits = computed(() => graphicEditor.hasOverrides.value)

/** Point ↔ GraphicNode 双向映射 (short/位置/描述走 params, 未改动字段保留接口原值) */
const pointAdapter: NodeAdapter<Point> = {
  toNode: (p) => ({
    id: p.id,
    label: p.label,
    type: p.kind,
    x: p.x,
    y: p.y,
    status: p.state,
    params: { short: p.short, zone: p.zone, desc: p.desc ?? '' },
  }),
  fromNode: (g, base) => {
    const src: Point = base ?? {
      id: g.id,
      label: g.label || g.id,
      short: g.params?.short || g.id.slice(0, 2),
      kind: (g.type as Point['kind']) || 'smoke',
      state: (g.status as Point['state']) || 'normal',
      x: g.x ?? 0,
      y: g.y ?? 0,
      zone: g.params?.zone || '未分区',
      desc: g.params?.desc || undefined,
    }
    return {
      ...src,
      id: g.id,
      label: g.label || src.label,
      short: g.params?.short || src.short,
      kind: (g.type || src.kind) as Point['kind'],
      state: (g.status || src.state) as Point['state'],
      x: g.x ?? src.x,
      y: g.y ?? src.y,
      zone: g.params?.zone || src.zone,
      desc: g.params?.desc || src.desc,
    }
  },
}

const pointsView = computed(() => graphicEditor.apply(points.value, pointAdapter))
const graphicDefaults = (): GraphicNode[] => points.value.map(pointAdapter.toNode)

// 探测器统计
const detFilter = ref<'all' | 'smoke' | 'heat' | 'manual' | 'door' | 'alarm' | 'fault' | 'offline'>(
  'all',
)
const detSummary = computed(() => {
  const d = s.value.detectors
  const normal = d.reduce((a, b) => a + (b.n - b.fault), 0)
  const fault = d.reduce((a, b) => a + b.fault, 0)
  return { normal, fault, alarm: alarmPoint.value ? 1 : 0, offline: 0 }
})
const ringStyle = computed(() => {
  const total = s.value.points || 1
  const ok = ((detSummary.value.normal / total) * 100).toFixed(1)
  return { background: `conic-gradient(var(--green, #2fae6b) ${ok}%, var(--track, #2a3645) 0)` }
})
const filteredDets = computed(() => {
  if (detFilter.value === 'all') return s.value.detectors
  const map: Record<string, string[]> = {
    smoke: ['感烟探测器', '极早期(VESDA)'],
    heat: ['感温探测器'],
    manual: ['手报/声光'],
    door: ['防火门监控'],
  }
  return s.value.detectors.filter((d) => map[detFilter.value]?.includes(d.type))
})
function detPct(d: FireDetectorView): number {
  return d.n ? +(((d.n - d.fault) / d.n) * 100).toFixed(0) : 0
}
function lvCls(lv: string) {
  return lv === 'crit' || lv === 'r' ? 'crit' : lv === 'warn' || lv === 'a' ? 'warn' : 'info'
}

// 消防联动设备（派生：基于火警状态）
const linkageDevices = ref<LinkDev[]>([])
function buildLinkage(events: FireEventView[]): LinkDev[] {
  const hasAlarm = events.some((e) => /报警|火警/.test(e.desc))
  return [
    {
      name: '排烟风机',
      icon: Fan,
      state: hasAlarm ? 'act' : 'ok',
      stateText: hasAlarm ? '联动启动' : '待命',
    },
    {
      name: '消防广播',
      icon: Volume2,
      state: hasAlarm ? 'act' : 'ok',
      stateText: hasAlarm ? '疏散广播' : '待命',
    },
    {
      name: '门禁释放',
      icon: DoorOpen,
      state: hasAlarm ? 'act' : 'ok',
      stateText: hasAlarm ? '已释放' : '正常',
    },
    {
      name: '电梯迫降',
      icon: ArrowDownToLine,
      state: hasAlarm ? 'act' : 'ok',
      stateText: hasAlarm ? '迫降首层' : '正常',
    },
  ]
}

async function load() {
  try {
    const data = await getSecurityFireDetailed()
    if (data && data.points) {
      s.value = data
      usingMock.value = false
      markPartial('平面图点位/联动设备由前端基于实时事件派生，非后端实测明细')
    } else throw new Error('empty')
  } catch {
    s.value = mockSummary()
    usingMock.value = true
    markFull()
  } finally {
    points.value = buildPoints(s.value.detectors, s.value.events)
    linkageDevices.value = buildLinkage(s.value.events)
  }
}
function refresh() {
  load()
}

function mockSummary(): FireSummary {
  return {
    hostState: '正常运行',
    loops: 8,
    points: 5860,
    faultPoints: 2,
    detectors: [
      { type: '感烟探测器', n: 3120, fault: 1 },
      { type: '感温探测器', n: 1480, fault: 1 },
      { type: '极早期(VESDA)', n: 96, fault: 0 },
      { type: '手报/声光', n: 420, fault: 0 },
      { type: '气体灭火控制盘', n: 46, fault: 0 },
      { type: '防火门监控', n: 268, fault: 0 },
    ],
    gas: { zones: 46, ready: 46, released: 0, agent: '七氟丙烷' },
    vesda: Array.from({ length: 6 }, (_, i) => ({
      id: `VESDA R${String(i * 2 + 1).padStart(2, '0')}`,
      level: i === 1 ? '轻微' : '正常',
      val: +(i === 1 ? 0.012 : 0.002).toFixed(3),
    })),
    qieFei: {
      desc: '确认火警 → 切除非消防电源(切非) → 联动气灭 → 应急照明投入',
      state: '自动允许',
      lastDrill: '2026-06-28 消防演练通过',
    },
    emergency: { lights: 1240, ok: 1236, batteryOk: 99.2, evacSigns: 386 },
    events: [
      { ts: '07-20 16:02', desc: 'R08 VESDA 轻微烟雾预警, 现场复核为清洁扬尘', lv: 'warn' },
      { ts: '07-18 10:00', desc: '月度消防联动测试: 切非/气灭启动回路校验通过', lv: 'info' },
    ],
    knowledge: {
      thresholds: [
        { k: '感烟', v: '≥ 烟雾浓度阈值 报警', note: '光电式' },
        { k: '感温', v: '≥ 57℃ 或温升速率 报警' },
        { k: 'VESDA', v: '四级报警(预警/行动/火警1/火警2)' },
        { k: '手报', v: '触发即确认火警' },
      ],
      arch: {
        components: [
          '感烟/感温探测器',
          '手动报警按钮',
          '声光报警器',
          '消防广播',
          '防火门监控',
          '气体灭火控制盘',
          '消防联动控制器',
        ],
        design: '分区探测：机房(极早期 VESDA + 点型烟温) + 公共区(烟温复合) + 钢瓶间(气体灭火)。',
        redundancy: '双回路总线，联动控制器双机热备，气灭钢瓶 N+1。',
      },
      logic: [
        {
          title: '火警确认',
          steps: [
            { step: 1, text: '探测器/手报触发 → 主机确认', ok: true },
            { step: 2, text: '确认火警 → 声光 + 广播疏散', ok: true },
          ],
        },
        {
          title: '联动控制',
          steps: [
            { step: 1, text: '切非电源 + 排烟风机启动', ok: true },
            { step: 2, text: '防火门释放 + 电梯迫降 + 气灭延时', ok: true },
          ],
        },
      ],
      faults: [
        {
          no: 1,
          fault: '探测器故障',
          lock: '该点位失监+故障告警',
          action: '查线路/底座',
          manualReset: false,
        },
        { no: 2, fault: '回路短路', lock: '整回路失监', action: '查短路点', manualReset: false },
        {
          no: 3,
          fault: '气灭钢瓶压力低',
          lock: '该区气灭失效',
          action: '补气/换瓶',
          manualReset: true,
        },
        {
          no: 4,
          fault: '联动控制器离线',
          lock: '联动失效',
          action: '查供电/网络',
          manualReset: true,
        },
      ],
      note: '消防系统严禁屏蔽/旁路；故障须在 24h 内闭环。',
    },
  }
}

const REFRESH_MS = 30000
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  load()
  timer = setInterval(load, REFRESH_MS)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.page-title {
  font-size: 20px;
  margin: 0;
}
.page-sub {
  margin: 2px 0 0;
  color: var(--text-2);
  font-size: 12px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.host-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
}
.host-badge.g {
  background: rgba(47, 174, 107, 0.12);
  color: #2fae6b;
}
.host-badge.a {
  background: rgba(208, 106, 58, 0.12);
  color: #d06a3a;
}
.btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  background: var(--bg-1);
  color: var(--text-1);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.mock-flag-sm {
  font-size: 12px;
  color: #d06a3a;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.grid-main {
  display: grid;
  grid-template-columns: 2.2fr 1fr;
  gap: 14px;
}
.grid-sub {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1.3fr;
  gap: 14px;
}
/* 平面图 */
.plan-card {
  min-height: 420px;
}
.legend {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--text-2);
  flex-wrap: wrap;
}
.lg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.lg-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}
.lg-dot.sm {
  background: #3f9fcf;
}
.lg-dot.tm {
  background: #d06a3a;
}
.lg-dot.sp {
  background: #5b8def;
}
.lg-dot.mb {
  background: #c065d6;
}
.lg-dot.hy {
  background: #2fae6b;
}
.lg-dot.a {
  background: #d23b3b;
}
.plan-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.plan-svg {
  width: 100%;
  background: var(--bg-2);
  border-radius: 8px;
}
.floor {
  fill: #0d141d;
  stroke: #243240;
  stroke-width: 1.5;
}
.corridor {
  fill: #14202c;
  stroke: #2a3d4d;
}
.zone-block {
  fill: #101b26;
  stroke: #243240;
  stroke-dasharray: 3 3;
}
.s-label {
  fill: #7d93a8;
  font-size: 12px;
  font-weight: 600;
}
.z-label {
  fill: #8aa2b5;
  font-size: 11px;
}
.fp {
  stroke: #0a0e14;
  stroke-width: 1;
}
.fp.smoke {
  fill: #3f9fcf;
}
.fp.temp {
  fill: #d06a3a;
}
.fp.sprinkler {
  fill: #5b8def;
}
.fp.manual {
  fill: #c065d6;
}
.fp.hydrant {
  fill: #2fae6b;
}
.fp.alarm {
  fill: #d23b3b;
}
.fp.fault {
  fill: #d23b3b;
  stroke: #d23b3b;
}
.fp-pulse {
  fill: none;
  stroke: #d23b3b;
  stroke-width: 1.5;
  animation: fppulse 1.4s ease-out infinite;
}
@keyframes fppulse {
  0% {
    r: 7;
    opacity: 0.9;
  }
  100% {
    r: 16;
    opacity: 0;
  }
}
.fp-name {
  fill: #9fb3c5;
  font-size: 8px;
}
.pop-bg {
  fill: #14202c;
  stroke: #d23b3b;
  stroke-width: 1.5;
}
.pop-t {
  fill: #d23b3b;
  font-size: 11px;
  font-weight: 600;
}
.pop-d {
  fill: #7d93a8;
  font-size: 9px;
}
.z-info {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-2);
  font-size: 12px;
}
/* 统一图形编辑入口按钮 */
.plan-edit {
  background: var(--bg-1);
  border: 1px solid var(--brand);
  color: var(--brand);
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
.plan-edit:hover {
  background: rgba(63, 159, 191, 0.14);
}

.z-info-h {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
}
.z-info-b {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  color: var(--text-2);
}

/* 主机面板 */
.host-card {
  display: flex;
  flex-direction: column;
}
.host-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 14px;
}
.host-kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--border);
}
.host-kv .k {
  font-size: 11px;
  color: var(--text-3);
}
.host-kv .v {
  font-size: 13px;
  font-weight: 600;
}
.g {
  color: #2fae6b;
}
.a {
  color: #d06a3a;
}
.host-vesda {
  margin-top: 10px;
}
.hv-head {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-2);
}
.hv-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.hv-row {
  display: grid;
  grid-template-columns: 1fr auto 44px;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 6px;
  border-radius: 5px;
}
.hv-row.ok {
  background: rgba(47, 174, 107, 0.08);
}
.hv-row.warn {
  background: rgba(208, 106, 58, 0.12);
}
.hv-id {
  font-weight: 500;
}
.hv-val {
  color: var(--text-2);
}
.hv-lv {
  font-size: 11px;
}
.hv-lv.ok {
  color: #2fae6b;
}
.hv-lv.warn {
  color: #d06a3a;
}

/* 探测器统计 */
.det-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.det-tab {
  font-size: 12px;
  padding: 3px 10px;
  border: 1px solid var(--border);
  background: var(--bg-1);
  color: var(--text-2);
  border-radius: 14px;
  cursor: pointer;
}
.det-tab.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.stat-row {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 12px;
}
.sp-ring {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.sp-center {
  background: var(--bg-1);
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.sp-center b {
  font-size: 18px;
}
.sp-center em {
  font-size: 10px;
  color: var(--text-2);
  font-style: normal;
}
.stat-legend {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.sl {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.sl-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.sl-dot.g {
  background: #2fae6b;
}
.sl-dot.a {
  background: #d23b3b;
}
.sl-dot.w {
  background: #d06a3a;
}
.sl-dot.o {
  background: #8a93a0;
}
.sl b {
  margin-left: 4px;
}
.det-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
}
.det-row {
  display: grid;
  grid-template-columns: 1fr 70px 50px;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 5px;
  font-size: 12px;
}
.det-row:hover {
  background: var(--bg-2);
}
.det-row.warn {
  background: rgba(208, 106, 58, 0.1);
}
.d-name {
  font-weight: 500;
}
.d-st {
  color: var(--text-2);
  text-align: right;
}
.d-bar {
  height: 8px;
  border-radius: 4px;
  background: var(--track, #2a3645);
  overflow: hidden;
}
.d-fill {
  display: block;
  height: 100%;
  border-radius: 4px;
}
.d-fill.ok {
  background: linear-gradient(90deg, rgba(47, 174, 107, 0.5), rgba(47, 174, 107, 0.85));
}
.d-fill.warn {
  background: linear-gradient(90deg, rgba(208, 106, 58, 0.5), rgba(208, 106, 58, 0.85));
}

/* 联动设备 */
.link-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.link-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-2);
  border: 1px solid var(--border);
}
.link-item.ok {
  border-color: rgba(47, 174, 107, 0.3);
}
.link-item.act {
  border-color: rgba(210, 59, 59, 0.4);
  background: rgba(210, 59, 59, 0.08);
}
.link-item.fault {
  border-color: rgba(208, 106, 58, 0.4);
}
.li-ico {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-1);
}
.link-item.ok .li-ico {
  color: #2fae6b;
}
.link-item.act .li-ico {
  color: #d23b3b;
}
.link-item.fault .li-ico {
  color: #d06a3a;
}
.li-name {
  font-size: 13px;
  font-weight: 500;
}
.li-st {
  font-size: 11px;
}
.li-st.ok {
  color: #2fae6b;
}
.li-st.act {
  color: #d23b3b;
}
.li-st.fault {
  color: #d06a3a;
}
.qie-fei {
  margin-top: 10px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
}
.qf-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  padding: 3px 0;
}
.qf-row .k {
  color: var(--text-3);
  min-width: 60px;
}
.qf-row .v {
  color: var(--text-1);
}

/* 告警列表 */
.evt-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
}
.evt-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}
.evt-ts {
  color: var(--text-2);
}
.evt-desc {
  flex: 1;
  color: var(--text-2);
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid-main,
  .grid-sub {
    grid-template-columns: 1fr;
  }
}
</style>
