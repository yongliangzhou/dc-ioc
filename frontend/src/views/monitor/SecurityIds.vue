<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">防入侵系统</h2>
        <p class="page-sub">Intrusion Detection · 周界电子围栏/振动光纤 + 室内红外/玻璃破碎</p>
      </div>
      <div class="head-actions">
        <span class="arm-badge" :class="s.perimeter.armed === s.perimeter.zones ? 'g' : 'a'">
          周界布防 {{ s.perimeter.armed }}/{{ s.perimeter.zones }}
        </span>
        <button class="btn" @click="refresh">刷新</button>
        <span v-if="usingMock" class="mock-flag-sm">⚠ 模拟数据</span>
      </div>
    </div>

    <!-- 总览 KPI -->
    <div class="kpi-row">
      <KpiCard
        title="周界防区"
        :value="s.perimeter.zones"
        unit="区"
        :sub="'布防 ' + s.perimeter.armed"
      />
      <KpiCard
        title="周界布防率"
        :value="armRate"
        unit="%"
        :trend="s.perimeter.armed === s.perimeter.zones ? 1 : -1"
        :sub="s.perimeter.zones - s.perimeter.armed + ' 区未布防'"
      />
      <KpiCard
        title="室内探测器"
        :value="s.indoor.ir + s.indoor.glass"
        unit="个"
        :sub="'红外 ' + s.indoor.ir + ' / 玻璃 ' + s.indoor.glass"
      />
      <KpiCard
        title="周界告警"
        :value="s.perimeter.alarm"
        unit="起"
        :trend="s.perimeter.alarm ? -1 : 1"
        :sub="s.perimeter.alarm ? '需处置' : '正常'"
      />
    </div>

    <div class="grid-main">
      <!-- 左：周界示意图 SVG -->
      <Panel class="plan-card">
        <div class="card-head">
          <span class="card-title">周界示意图</span>
          <div class="legend">
            <span class="lg"><i class="lg-dot g"></i>布防</span>
            <span class="lg"><i class="lg-dot r"></i>报警</span>
            <span class="lg"><i class="lg-dot y"></i>撤防</span>
          </div>
        </div>
        <div class="plan-wrap">
          <svg viewBox="0 0 600 360" class="plan-svg" @click="selectedZone = null">
            <!-- 园区外框 + 内部建筑 -->
            <rect x="20" y="20" width="560" height="320" rx="10" class="site" />
            <rect x="230" y="120" width="140" height="120" rx="6" class="building" />
            <text x="240" y="140" class="b-label">数据中心楼</text>
            <text x="34" y="42" class="s-label">园区周界 · 防区布防</text>
            <!-- 周界防区点位（沿外框分布） -->
            <g v-for="z in zones" :key="z.id" @click.stop="selectZone(z)">
              <line
                v-if="
                  z.side === 'top' || z.side === 'bottom' || z.side === 'left' || z.side === 'right'
                "
                :x1="z.x1"
                :y1="z.y1"
                :x2="z.x2"
                :y2="z.y2"
                :class="'fence ' + z.state"
              />
              <circle :cx="z.cx" :cy="z.cy" r="7" :class="'z-dot ' + z.state" />
              <text :x="z.cx" :y="z.cy + 18" class="z-name">{{ z.short }}</text>
              <circle v-if="z.state === 'alarm'" :cx="z.cx" :cy="z.cy" r="12" class="z-pulse" />
            </g>
            <!-- 报警时联动视频弹窗 -->
            <g v-if="linkageCam" class="pop">
              <rect x="400" y="250" width="170" height="92" rx="6" class="pop-bg" />
              <text x="412" y="270" class="pop-t">{{ linkageCam }}</text>
              <rect x="412" y="278" width="146" height="52" rx="3" class="pop-feed" />
              <text x="420" y="312" class="pop-d">入侵联动视频 · 复核中</text>
            </g>
          </svg>
          <div v-if="selectedZone" class="z-info">
            <div class="z-info-h">
              <span class="z-dot" :class="selectedZone.state"></span>{{ selectedZone.id }}
            </div>
            <div class="z-info-b">
              <span>状态：{{ stateText(selectedZone.state) }}</span>
              <span>技术：{{ selectedZone.tech }}</span>
              <span v-if="selectedZone.alarmDesc">告警：{{ selectedZone.alarmDesc }}</span>
            </div>
          </div>
        </div>
      </Panel>

      <!-- 右：探测器状态面板 -->
      <Panel class="det-card">
        <div class="card-head">
          <span class="card-title">探测器状态</span
          ><span class="card-sub">{{ detectors.length }} 路</span>
        </div>
        <div class="det-tabs">
          <button class="det-tab" :class="{ active: detType === 'all' }" @click="detType = 'all'">
            全部
          </button>
          <button class="det-tab" :class="{ active: detType === 'ir' }" @click="detType = 'ir'">
            红外
          </button>
          <button class="det-tab" :class="{ active: detType === 'vib' }" @click="detType = 'vib'">
            振动光纤
          </button>
          <button class="det-tab" :class="{ active: detType === 'mic' }" @click="detType = 'mic'">
            微波
          </button>
          <button
            class="det-tab"
            :class="{ active: detType === 'glass' }"
            @click="detType = 'glass'"
          >
            玻璃破碎
          </button>
        </div>
        <div class="det-list">
          <div v-for="d in filteredDet" :key="d.id" class="det-row" :class="d.state">
            <span class="d-dot" :class="d.state"></span>
            <span class="d-name">{{ d.name }}</span>
            <span class="d-zone">{{ d.zone }}</span>
            <span class="d-st" :class="d.state">{{ stateText(d.state) }}</span>
          </div>
          <EmptyState v-if="!filteredDet.length" text="无探测器" />
        </div>
      </Panel>
    </div>

    <div class="grid-sub">
      <!-- 入侵告警列表 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">入侵告警列表</span
          ><span class="card-sub">{{ s.events.length }} 条</span>
        </div>
        <div class="evt-list">
          <div v-for="(e, i) in s.events" :key="i" class="evt-row" :class="lvCls(e.lv)">
            <AlarmBadge :level="e.lv" />
            <span class="evt-ts mono">{{ e.ts }}</span>
            <span class="evt-zone">{{ e.zone }}</span>
            <span class="evt-desc">{{ e.desc }}</span>
          </div>
          <EmptyState v-if="!s.events.length" text="无告警" />
        </div>
      </Panel>

      <!-- 布防/撤防时间线 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">布防 / 撤防时间线</span
          ><span class="card-sub">{{ timeline.length }} 条</span>
        </div>
        <div class="timeline">
          <div v-for="(t, i) in timeline" :key="i" class="tl-row">
            <span class="tl-dot" :class="t.action === '布防' ? 'g' : 'y'"></span>
            <span class="tl-ts mono">{{ t.ts }}</span>
            <span class="tl-act" :class="t.action === '布防' ? 'g' : 'y'">{{ t.action }}</span>
            <span class="tl-zone">{{ t.zone }}</span>
            <span class="tl-by">{{ t.by }}</span>
          </div>
        </div>
      </Panel>

      <!-- 联动策略 + 知识库 -->
      <Panel>
        <div class="card-head"><span class="card-title">联动策略</span></div>
        <div class="linkage-box">
          <span class="lk-ico">⚡</span>
          <span>{{ s.linkage }}</span>
        </div>
        <div v-if="s.knowledge?.thresholds?.length" class="know-mini">
          <h4>设计阈值</h4>
          <ul>
            <li v-for="t in s.knowledge.thresholds" :key="t.k">
              <b>{{ t.k }}</b
              >：{{ t.v }}<em v-if="t.note">（{{ t.note }}）</em>
            </li>
          </ul>
        </div>
      </Panel>
    </div>

    <!-- 知识库 -->
    <Panel class="know">
      <div class="card-head"><span class="card-title">防入侵架构 · 逻辑 · 故障锁定</span></div>
      <div class="know-grid">
        <SecurityKnowledge :knowledge="s.knowledge" logic-title="检测 / 联动逻辑" />
        <div class="know-col">
          <h4>状态概览</h4>
          <ul>
            <li>周界类型：{{ s.perimeter.type }}</li>
            <li>室内布防：{{ s.indoor.armed }}</li>
            <li>室内状态：{{ s.indoor.state }}</li>
            <li>探测器总数：{{ s.indoor.ir + s.indoor.glass }} 个</li>
          </ul>
        </div>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Fence, Shield, ScanEye, AlertTriangle } from 'lucide-vue-next'
import KpiCard from '@/components/monitor/KpiCard.vue'
import Panel from '@/components/common/Panel.vue'
import SecurityKnowledge from '@/components/SecurityKnowledge.vue'
import AlarmBadge from '@/components/monitor/AlarmBadge.vue'
import EmptyState from '@/components/monitor/EmptyState.vue'
import { getSecurityIdsDetailed } from '@/api/security'
import type { IdsSummary, IdsEventView } from '@/api/security'

interface Zone {
  id: string
  short: string
  side: string
  state: 'armed' | 'alarm' | 'disarm'
  tech: string
  cx: number
  cy: number
  x1: number
  y1: number
  x2: number
  y2: number
  alarmDesc?: string
}
interface Det {
  id: string
  name: string
  zone: string
  type: 'ir' | 'vib' | 'mic' | 'glass'
  state: 'online' | 'alarm' | 'offline'
}

const s = ref<IdsSummary>({
  perimeter: { type: '', zones: 0, armed: 0, alarm: 0 },
  indoor: { ir: 0, glass: 0, armed: '', state: '' },
  linkage: '',
  events: [],
  knowledge: { thresholds: [] },
})
const usingMock = ref(false)

const armRate = computed(() =>
  s.value.perimeter.zones
    ? +((s.value.perimeter.armed / s.value.perimeter.zones) * 100).toFixed(1)
    : 0,
)

// 周界防区（沿外框分布 16 区）
const zones = ref<Zone[]>([])
const selectedZone = ref<Zone | null>(null)

function buildZones(perimeter: IdsSummary['perimeter'], events: IdsEventView[]): Zone[] {
  const n = perimeter.zones || 16
  const arr: Zone[] = []
  const techs = ['电子围栏', '振动光纤', '电子围栏', '振动光纤']
  const pts: { x: number; y: number; side: string }[] = []
  const sideN = Math.ceil(n / 4)
  for (let i = 0; i < n; i++) {
    const r = Math.floor(i / sideN)
    const k = i % sideN
    if (r === 0) pts.push({ x: 40 + k * (520 / sideN), y: 20, side: 'top' })
    else if (r === 1) pts.push({ x: 580, y: 40 + k * (300 / sideN), side: 'right' })
    else if (r === 2) pts.push({ x: 560 - k * (520 / sideN), y: 340, side: 'bottom' })
    else pts.push({ x: 20, y: 320 - k * (300 / sideN), side: 'left' })
  }
  for (let i = 0; i < n; i++) {
    const p = pts[i]
    arr.push({
      id: `周界 Z-${String(i + 1).padStart(2, '0')}`,
      short: `Z${i + 1}`,
      side: p.side,
      state: 'armed',
      tech: techs[i % techs.length],
      cx: p.x,
      cy: p.y,
      x1: p.x,
      y1: p.y,
      x2: p.x,
      y2: p.y,
    })
  }
  // 报警防区来自事件
  events.forEach((e) => {
    const m = e.zone.match(/Z-(\d+)/)
    if (m) {
      const z = arr[parseInt(m[1], 10) - 1]
      if (z && /报警|闯入|触网/.test(e.desc)) {
        z.state = 'alarm'
        z.alarmDesc = e.desc
      }
    }
  })
  return arr
}

function selectZone(z: Zone) {
  selectedZone.value = z
}

// 探测器（派生）
const detectors = ref<Det[]>([])
const detType = ref<'all' | 'ir' | 'vib' | 'mic' | 'glass'>('all')
const filteredDet = computed(() =>
  detType.value === 'all'
    ? detectors.value
    : detectors.value.filter((d) => d.type === detType.value),
)

function buildDetectors(indoor: IdsSummary['indoor'], events: IdsEventView[]): Det[] {
  const out: Det[] = []
  for (let i = 1; i <= indoor.ir; i++)
    out.push({
      id: `IR-${i}`,
      name: `被动红外 ${i}`,
      zone: `室内 R${Math.ceil(i / 14)}`,
      type: 'ir',
      state: 'online',
    })
  for (let i = 1; i <= indoor.glass; i++)
    out.push({
      id: `GB-${i}`,
      name: `玻璃破碎 ${i}`,
      zone: `窗口 W${Math.ceil(i / 8)}`,
      type: 'glass',
      state: 'online',
    })
  // 周界振动光纤/微波探测器（取自防区）
  zones.value.forEach((z, i) => {
    out.push({
      id: `VIB-${i + 1}`,
      name: `${z.tech} ${i + 1}`,
      zone: z.id,
      type: z.tech === '振动光纤' ? 'vib' : 'mic',
      state: z.state === 'alarm' ? 'alarm' : 'online',
    })
  })
  void events
  return out
}

// 告警联动视频弹窗（取首个报警事件关联的周界防区）
const linkageCam = computed(() => {
  const alarm = s.value.events.find((e) => /报警|闯入/.test(e.desc))
  if (!alarm) return null
  const m = alarm.zone.match(/Z-\d+/)
  return m ? `CAM-${m[0]} 预置位` : 'CAM-周界 预置位'
})

// 布防/撤防时间线（派生）
const timeline = ref<{ ts: string; action: string; zone: string; by: string }[]>([])
function buildTimeline(): void {
  timeline.value = [
    { ts: '今日 20:00', action: '布防', zone: '周界 16 区', by: '定时策略' },
    { ts: '今日 20:00', action: '布防', zone: '室内重点区', by: '定时策略' },
    { ts: '今日 07:30', action: '撤防', zone: '室内非重点区', by: '定时策略' },
    { ts: '昨日 23:40', action: '布防', zone: '周界 Z-03', by: '保安(复核后)' },
  ]
}

function stateText(st: string) {
  return { armed: '布防', alarm: '报警', disarm: '撤防', online: '在线', offline: '离线' }[st] || st
}
function lvCls(lv: string) {
  return lv === 'crit' || lv === 'r' ? 'crit' : lv === 'warn' || lv === 'a' ? 'warn' : 'info'
}

async function load() {
  try {
    const data = await getSecurityIdsDetailed()
    if (data && data.perimeter && data.perimeter.zones) {
      s.value = data
      usingMock.value = false
    } else throw new Error('empty')
  } catch {
    s.value = mockSummary()
    usingMock.value = true
  } finally {
    zones.value = buildZones(s.value.perimeter, s.value.events)
    detectors.value = buildDetectors(s.value.indoor, s.value.events)
    buildTimeline()
  }
}
function refresh() {
  load()
}

function mockSummary(): IdsSummary {
  return {
    perimeter: { type: '电子围栏 + 振动光纤', zones: 16, armed: 16, alarm: 0 },
    indoor: { ir: 84, glass: 36, armed: '夜间自动布防', state: '白天撤防(重点区布防)' },
    linkage: '报警 → 联动摄像机预置位 + 声光 + IOC 弹窗',
    events: [
      {
        ts: '02:14',
        zone: '周界 Z-07',
        desc: '振动光纤扰动, AI 判定树枝刮碰, 自动消警',
        lv: 'info',
      },
      {
        ts: '昨日 23:40',
        zone: '周界 Z-03',
        desc: '电子围栏触网报警, 保安 3min 到场, 无异常',
        lv: 'warn',
      },
    ],
    knowledge: {
      thresholds: [
        { k: '电子围栏', v: '触网/短路/断线 报警', note: '高压脉冲' },
        { k: '振动光纤', v: '扰动 > 阈值 报警', note: 'AI 降误报' },
        { k: '红外对射', v: '遮挡 > 0.2s 报警' },
        { k: '玻璃破碎', v: '高频声纹识别' },
      ],
      arch: {
        components: [
          '电子围栏主机',
          '振动光纤解调仪',
          '红外对射',
          '玻璃破碎探测器',
          '报警主机/平台',
        ],
        design:
          '多层纵深：周界(电子围栏+振动光纤) + 建筑周界(红外对射) + 室内(被动红外+玻璃破碎)。',
        redundancy: '双防区总线，报警主机双机热备，联动视频 N+1。',
      },
      logic: [
        {
          title: '入侵检测',
          steps: [
            { step: 1, text: '周界探测器触发 → 平台确认', ok: true },
            { step: 2, text: 'AI 复核降误报 → 真实入侵升级告警', ok: true },
          ],
        },
        {
          title: '报警联动',
          steps: [
            { step: 1, text: '联动摄像机预置位抓拍', ok: true },
            { step: 2, text: '声光威慑 + IOC 弹窗 + 保安 APP', ok: true },
          ],
        },
      ],
      faults: [
        {
          no: 1,
          fault: '电子围栏断线',
          lock: '该防区失防+告警',
          action: '查终端杆/合金线',
          manualReset: false,
        },
        {
          no: 2,
          fault: '振动光纤误报',
          lock: '调灵敏度/AI 复核',
          action: '复核样本',
          manualReset: false,
        },
        {
          no: 3,
          fault: '红外对射被遮',
          lock: '告警+视频复核',
          action: '现场核查',
          manualReset: false,
        },
        {
          no: 4,
          fault: '报警主机离线',
          lock: '标记离线',
          action: '查供电/网络',
          manualReset: true,
        },
      ],
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

void Fence
void Shield
void ScanEye
void AlertTriangle
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
.arm-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
}
.arm-badge.g {
  background: rgba(47, 174, 107, 0.12);
  color: #2fae6b;
}
.arm-badge.a {
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
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 14px;
}
/* 周界 SVG */
.plan-card {
  min-height: 400px;
}
.legend {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-2);
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
.lg-dot.g {
  background: #2fae6b;
}
.lg-dot.r {
  background: #d23b3b;
}
.lg-dot.y {
  background: #d06a3a;
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
.site {
  fill: #0d141d;
  stroke: #243240;
  stroke-width: 1.5;
}
.building {
  fill: #14202c;
  stroke: #2a3d4d;
}
.s-label {
  fill: #7d93a8;
  font-size: 12px;
  font-weight: 600;
}
.b-label {
  fill: #8aa2b5;
  font-size: 11px;
}
.fence {
  stroke-width: 2;
}
.fence.armed {
  stroke: #2fae6b;
}
.fence.alarm {
  stroke: #d23b3b;
  stroke-dasharray: 4 3;
}
.fence.disarm {
  stroke: #d06a3a;
  stroke-dasharray: 2 4;
}
.z-dot {
  stroke: #0a0e14;
  stroke-width: 1.5;
}
.z-dot.armed {
  fill: #2fae6b;
}
.z-dot.alarm {
  fill: #d23b3b;
}
.z-dot.disarm {
  fill: #d06a3a;
}
.z-name {
  fill: #9fb3c5;
  font-size: 8px;
  text-anchor: middle;
}
.z-pulse {
  fill: none;
  stroke: #d23b3b;
  stroke-width: 1.5;
  animation: zpulse 1.4s ease-out infinite;
}
@keyframes zpulse {
  0% {
    r: 8;
    opacity: 0.9;
  }
  100% {
    r: 18;
    opacity: 0;
  }
}
.pop-bg {
  fill: #14202c;
  stroke: #3f9fcf;
  stroke-width: 1.5;
}
.pop-t {
  fill: #3f9fcf;
  font-size: 11px;
  font-weight: 600;
}
.pop-feed {
  fill: #0a0e14;
  stroke: #243240;
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
  font-size: 12px;
  color: var(--text-2);
}

/* 探测器面板 */
.det-card {
  display: flex;
  flex-direction: column;
}
.det-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
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
.det-list {
  overflow-y: auto;
  max-height: 360px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.det-row {
  display: grid;
  grid-template-columns: 12px 1fr 80px 44px;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  border-radius: 5px;
  font-size: 12px;
}
.det-row:hover {
  background: var(--bg-2);
}
.det-row.alarm {
  background: rgba(210, 59, 59, 0.1);
}
.d-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.d-dot.online {
  background: #2fae6b;
}
.d-dot.alarm {
  background: #d23b3b;
}
.d-dot.offline {
  background: #d06a3a;
}
.d-name {
  font-weight: 500;
}
.d-zone {
  color: var(--text-2);
}
.d-st {
  font-size: 11px;
}
.d-st.online {
  color: #2fae6b;
}
.d-st.alarm {
  color: #d23b3b;
}
.d-st.offline {
  color: #d06a3a;
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
.evt-zone {
  color: var(--brand);
  font-weight: 500;
  min-width: 84px;
}
.evt-desc {
  flex: 1;
  color: var(--text-2);
}

/* 时间线 */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
.tl-row {
  display: grid;
  grid-template-columns: 10px 70px 44px 1fr auto;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.tl-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.tl-dot.g {
  background: #2fae6b;
}
.tl-dot.y {
  background: #d06a3a;
}
.tl-ts {
  color: var(--text-2);
}
.tl-act {
  font-weight: 600;
}
.tl-act.g {
  color: #2fae6b;
}
.tl-act.y {
  color: #d06a3a;
}
.tl-zone {
  color: var(--text-1);
}
.tl-by {
  color: var(--text-2);
}

/* 联动策略 */
.linkage-box {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 13px;
  color: var(--text-1);
  background: var(--bg-2);
  border-radius: 8px;
  padding: 10px;
  line-height: 1.6;
}
.lk-ico {
  font-size: 16px;
}
.know-mini {
  margin-top: 10px;
}
.know-mini h4 {
  font-size: 13px;
  margin: 0 0 6px;
}
.know-mini ul {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
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
