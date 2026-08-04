<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">门禁系统</h2>
        <p class="page-sub">Access Control · 分级分区授权 · 防尾随 · 消防联动</p>
      </div>
      <div class="head-actions">
        <button class="btn" @click="refresh" title="刷新">刷新</button>
        <span v-if="usingMock" class="mock-flag-sm">⚠ 模拟数据</span>
      </div>
    </div>

    <!-- 总览 KPI -->
    <div class="kpi-row">
      <KpiCard title="门禁总数" :value="s.total" unit="樘" :sub="'在线 ' + s.online" />
      <KpiCard title="在线率" :value="onlinePercent" unit="%" :trend="s.openAbnormal ? -1 : 1" :sub="s.openAbnormal + ' 樘门磁异常'" />
      <KpiCard title="今日刷卡" :value="s.todayEvents" unit="次" :sub="s.visitors + ' 名访客'" />
      <KpiCard title="拒绝/异常" :value="s.denied + s.openAbnormal" unit="次" :trend="(s.denied + s.openAbnormal) ? -1 : 1" :sub="s.denied + ' 次拒绝'" />
    </div>

    <div class="grid-main">
      <!-- 左：门禁平面图 -->
      <Panel class="plan-card">
        <div class="card-head">
          <span class="card-title">门禁平面图</span>
          <div class="legend">
            <span class="lg"><i class="lg-dot g"></i>正常</span>
            <span class="lg"><i class="lg-dot b"></i>开门</span>
            <span class="lg"><i class="lg-dot y"></i>异常</span>
            <span class="lg"><i class="lg-dot r"></i>闯入</span>
          </div>
        </div>
        <div class="plan-wrap">
          <svg viewBox="0 0 600 380" class="plan-svg">
            <!-- 楼层外框 -->
            <rect x="20" y="20" width="560" height="340" rx="8" class="floor" />
            <text x="34" y="44" class="floor-label">B1 动力 / 机房层</text>
            <!-- 走廊 -->
            <rect x="60" y="170" width="480" height="40" class="corridor" />
            <text x="64" y="195" class="corr-label">主通道</text>
            <!-- 区域块 -->
            <g v-for="(zone, zi) in zones" :key="zone.id">
              <rect :x="zone.x" :y="zone.y" :width="zone.w" :height="zone.h" rx="6" class="zone" />
              <text :x="zone.x + 8" :y="zone.y + 18" class="zone-label">{{ zone.short }}</text>
            </g>
            <!-- 门禁点位 -->
            <g v-for="pt in points" :key="pt.id" @click="selectPoint(pt)" class="pt" :class="{ sel: selectedPoint && selectedPoint.id === pt.id }">
              <circle :cx="pt.x" :cy="pt.y" r="9" :class="'pt-dot ' + pt.state" />
              <text :x="pt.x" :y="pt.y + 22" class="pt-name">{{ pt.short }}</text>
              <circle v-if="pt.state === 'open'" :cx="pt.x" :cy="pt.y" r="13" class="pt-pulse" />
            </g>
          </svg>
          <div v-if="selectedPoint" class="pt-info">
            <div class="pt-info-h"><span class="pt-dot" :class="selectedPoint.state"></span>{{ selectedPoint.name }}</div>
            <div class="pt-info-b">
              <span>所属区：{{ selectedPoint.zone }}</span>
              <span>状态：{{ stateText(selectedPoint.state) }}</span>
              <span>今日通行：{{ selectedPoint.pass }} 人次</span>
              <span>认证：{{ selectedPoint.auth }}</span>
            </div>
          </div>
        </div>
      </Panel>

      <!-- 右：远程控制 + 告警 -->
      <div class="side-col">
        <Panel>
          <div class="card-head"><span class="card-title">远程控制</span></div>
          <QuickControl
            label="门禁操作"
            :show-power="false"
            :show-start-stop="false"
            @toggle-start-stop="noop"
          >
            <button class="qc-btn open" @click="bulkOpen">批量开门</button>
            <button class="qc-btn lock" @click="bulkLock">批量锁门</button>
          </QuickControl>
          <div class="ctrl-tip">选中平面图点位后，可对单樘门执行远程控制</div>
          <div v-if="selectedPoint" class="ctrl-sel">
            <span class="ctrl-sel-name">{{ selectedPoint.name }}</span>
            <div class="qc-actions">
              <button class="qc-btn open" @click="toggleDoor(selectedPoint, 'open')">远程开门</button>
              <button class="qc-btn lock" @click="toggleDoor(selectedPoint, 'lock')">远程锁门</button>
            </div>
            <span class="ctrl-state" :class="selectedPoint.state">{{ stateText(selectedPoint.state) }}</span>
          </div>
        </Panel>

        <Panel class="alarm-card">
          <div class="card-head"><span class="card-title">告警信息</span><span class="card-sub">{{ alarms.length }} 条</span></div>
          <div class="alarm-list">
            <div v-for="(a, i) in alarms" :key="i" class="alarm-row" :class="a.lv">
              <AlarmBadge :level="a.lv" />
              <span class="a-door">{{ a.door }}</span>
              <span class="a-desc">{{ a.desc }}</span>
            </div>
            <EmptyState v-if="!alarms.length" text="无告警" />
          </div>
        </Panel>
      </div>
    </div>

    <div class="grid-sub">
      <!-- 实时事件流 -->
      <Panel class="evt-card">
        <div class="card-head"><span class="card-title">实时事件流</span><span class="card-sub">{{ s.events.length }} 条</span></div>
        <div class="evt-stream">
          <div v-for="(e, i) in s.events" :key="i" class="evt-row">
            <span class="evt-time mono">{{ e.ts }}</span>
            <span class="evt-door">{{ e.door }}</span>
            <span class="evt-person">{{ e.person }}</span>
            <span class="evt-act">{{ e.act }}</span>
            <span class="tag" :class="lvCls(e.lv)">{{ lvText(e.lv) }}</span>
          </div>
        </div>
      </section>

      <!-- 通行统计 -->
      <Panel>
        <div class="card-head"><span class="card-title">通行统计</span><span class="card-sub">各门禁点今日通行人次</span></div>
        <TrendChart
          title=""
          :series="passSeries"
          :x-axis-data="passLabels"
          type="bar"
          :show-area="false"
          :height="220"
          :show-legend="false"
        />
      </section>

      <!-- 授权分级 -->
      <s          />
      </Panel>

      <!-- 授权分级 -->
      <Panel>
        <div class="card-head"><span class="card-title">授权区域分级</span><span class="card-sub">{{ s.areas.length }} 级区 · {{ s.total }} 门</span></div>
        <div class="area-grid">
          <div class="area-block" v-for="a in s.areas" :key="a.id">
            <div class="area-head">
              <span class="d-name">{{ a.id }}</span>
              <span class="tag b">{{ a.doors }} 门</span>
            </div>
            <div class="area-auth"><span class="muted">认证方式</span><span class="auth-val">{{ a.auth }}</span></div>
          </div>
        </div>
      </Panel>
    </div>

    <!-- 知识库 -->
    <Panel class="know">
      <div class="card-head"><span class="card-title">门禁设计阈值 · 架构 · 故障锁定</span></div>
      <SecurityKnowledge :knowledge="s.knowledge" logic-title="授权 / 联动逻辑" />
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { DoorOpen, Activity, LogIn, ShieldAlert } from 'lucide-vue-next'
import KpiCard from '@/components/monitor/KpiCard.vue'
import Panel from '@/components/common/Panel.vue'
import SecurityKnowledge from '@/components/SecurityKnowledge.vue'
import AlarmBadge from '@/components/monitor/AlarmBadge.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import QuickControl from '@/components/monitor/QuickControl.vue'
import EmptyState from '@/components/monitor/EmptyState.vue'
import { getSecurityAcsDetailed } from '@/api/security'
import type { AcsSummary, AcsAreaView, AcsEventView, AcsKnowledgeView } from '@/api/security'

interface Point {
  id: string
  name: string
  short: string
  zone: string
  x: number
  y: number
  state: 'normal' | 'open' | 'abnormal' | 'intrude'
  pass: number
  auth: string
}

const s = ref<AcsSummary>({
  total: 0, online: 0, openAbnormal: 0, todayEvents: 0, denied: 0, visitors: 0,
  areas: [], events: [], knowledge: { thresholds: [] },
})
const usingMock = ref(false)
const loading = ref(false)

const onlinePercent = computed(() => (s.value.total ? +((s.value.online / s.value.total) * 100).toFixed(1) : 0))

// 平面图区域块（固定布局）
const zones = [
  { id: '动力机房', short: '动力机房', x: 40, y: 50, w: 150, h: 95 },
  { id: '柴发/油罐区', short: '柴发区', x: 210, y: 50, w: 150, h: 95 },
  { id: '网络核心', short: '网络核心', x: 380, y: 50, w: 160, h: 95 },
  { id: '机房包间', short: '机房包间', x: 40, y: 230, w: 200, h: 110 },
  { id: 'UPS 室', short: 'UPS 室', x: 260, y: 230, w: 140, h: 110 },
  { id: '存储库房', short: '存储库房', x: 420, y: 230, w: 120, h: 110 },
]

// 派生门禁点位
const points = ref<Point[]>([])
const selectedPoint = ref<Point | null>(null)

function derivePoints(areas: AcsAreaView[], events: AcsEventView[]): Point[] {
  const zoneDoors: Record<string, number> = {
    '动力机房': 24, '柴发/油罐区': 40, '网络核心': 40, '机房包间': 118, 'UPS 室': 26, '存储库房': 20,
  }
  const map: { zone: string; x: number; y: number }[] = [
    { zone: '动力机房', x: 75, y: 90 }, { zone: '柴发/油罐区', x: 245, y: 90 }, { zone: '网络核心', x: 420, y: 90 },
    { zone: '机房包间', x: 90, y: 270 }, { zone: 'UPS 室', x: 300, y: 270 }, { zone: '存储库房', x: 460, y: 270 },
  ]
  const list: Point[] = []
  map.forEach((m) => {
    const n = zoneDoors[m.zone] || 10
    const show = Math.min(6, Math.max(2, Math.round(n / 20)))
    for (let i = 0; i < show; i++) {
      list.push({
        id: `${m.zone}-${i + 1}`,
        name: `${m.zone} 门 ${i + 1}`,
        short: m.zone.slice(0, 2) + (i + 1),
        zone: m.zone,
        x: m.x + i * 26,
        y: m.y,
        state: 'normal',
        pass: Math.round(20 + Math.random() * 180),
        auth: areas.find((a) => m.zone.includes(a.id.slice(0, 2)))?.auth || '刷卡',
      })
    }
  })
  // 异常/闯入：来自事件
  events.forEach((e) => {
    if (/门磁异常/.test(e.act)) {
      const p = list.find((x) => e.door.startsWith(x.zone.slice(0, 2)))
      if (p) p.state = 'abnormal'
    }
    if (/闯入|非法/.test(e.act)) {
      const p = list.find((x) => e.door.startsWith(x.zone.slice(0, 2)))
      if (p) p.state = 'intrude'
    }
  })
  return list
}

function selectPoint(p: Point) { selectedPoint.value = p }

// 告警派生
const alarms = computed(() => {
  const out: { lv: string; door: string; desc: string }[] = []
  s.value.events.forEach((e) => {
    if (e.lv === 'crit' || e.lv === 'warn' || /拒绝|异常|闯入|非法/.test(e.act)) {
      out.push({ lv: e.lv === 'crit' ? 'crit' : 'warn', door: e.door, desc: e.act })
    }
  })
  if (s.value.openAbnormal) out.unshift({ lv: 'crit', door: '门磁异常', desc: `${s.value.openAbnormal} 樘门磁异常开启 > 60s` })
  if (s.value.denied) out.push({ lv: 'warn', door: '授权校验', desc: `${s.value.denied} 次刷卡被拒绝` })
  return out
})

// 通行统计（取前 8 个门点）
const passSeries = computed(() => [{
  name: '今日通行(人次)',
  data: points.value.slice(0, 8).map((p) => p.pass),
}])
const passLabels = computed(() => points.value.slice(0, 8).map((p) => p.short))

// 远程控制
function noop() {}
function bulkOpen() { points.value.forEach((p) => { if (p.state !== 'intrude') p.state = 'open' }) }
function bulkLock() { points.value.forEach((p) => { if (p.state !== 'intrude' && p.state !== 'abnormal') p.state = 'normal' }) }
function toggleDoor(p: Point, action: 'open' | 'lock') {
  if (action === 'open') p.state = p.state === 'intrude' ? 'intrude' : 'open'
  else p.state = p.state === 'intrude' || p.state === 'abnormal' ? p.state : 'normal'
}

function stateText(st: string) {
  return { normal: '正常/关门', open: '开门', abnormal: '门磁异常', intrude: '非法闯入' }[st] || st
}
function lvCls(lv: string) { return lv === 'crit' || lv === 'r' ? 'r' : lv === 'warn' || lv === 'a' ? 'a' : 'g' }
function lvText(lv: string) { return lv === 'crit' || lv === 'r' ? '严重' : lv === 'warn' || lv === 'a' ? '告警' : '信息' }

async function load() {
  loading.value = true
  try {
    const data = await getSecurityAcsDetailed()
    if (data && data.total) { s.value = data; usingMock.value = false }
    else throw new Error('empty')
  } catch {
    s.value = mockSummary()
    usingMock.value = true
  } finally {
    points.value = derivePoints(s.value.areas, s.value.events)
    loading.value = false
  }
}
function refresh() { load() }

function mockSummary(): AcsSummary {
  const areas: AcsAreaView[] = [
    { id: '一级区 · 园区/大堂', auth: '刷卡', doors: 24 },
    { id: '二级区 · 办公/走廊', auth: '刷卡+密码', doors: 86 },
    { id: '三级区 · 机房包间', auth: '刷卡+指纹', doors: 118 },
    { id: '四级区 · 动力/网络核心', auth: '刷卡+人脸+双人互锁', doors: 40 },
  ]
  const events: AcsEventView[] = [
    { ts: '14:05', door: 'R06 包间北门', person: '王强(运维)', act: '刷卡+指纹通过', lv: 'info' },
    { ts: '13:41', door: 'UPS 室 A', person: '李敏(厂商)', act: '访客授权通过·陪同', lv: 'info' },
    { ts: '12:58', door: 'R11 包间南门', person: '未授权卡', act: '拒绝 · 已联动视频复核', lv: 'warn' },
    { ts: '11:33', door: '油罐区大门', person: '—', act: '门磁异常开启 > 60s', lv: 'crit' },
    { ts: '10:20', door: '网络核心区', person: '张伟', act: '双人互锁开门·授权通过', lv: 'info' },
    { ts: '09:05', door: '大堂主门', person: '保洁(临时)', act: '临时授权·时段内有效', lv: 'info' },
  ]
  const knowledge: AcsKnowledgeView = {
    thresholds: [
      { k: '门磁异常', v: '开启 > 60s 告警', note: '超时未关' },
      { k: '防尾随', v: '双门互锁', note: '一门开另一门闭' },
      { k: '刷卡拒绝', v: '联动视频复核' },
      { k: '消防联动', v: '火警断电锁自动释放', note: '断电开锁' },
    ],
    arch: {
      components: ['读卡器/生物识别', '门禁控制器', '电锁/出门按钮', '门磁', '发卡/平台'],
      design: '分层星型：读卡器→控制器→管理平台，核心区双门互锁+人脸。',
      redundancy: '控制器双总线，平台双机，消防联动断电开锁(NC 锁)。',
    },
    logic: [
      { title: '授权通行', steps: [
        { step: 1, text: '刷卡/人脸 → 平台比对权限', ok: true },
        { step: 2, text: '合法→开锁并记录; 非法→拒绝+复核', ok: true },
      ] },
      { title: '防尾随', steps: [
        { step: 1, text: 'A 门开 → B 门强制闭锁', ok: true },
        { step: 2, text: '双门关后方可再次开启', ok: true },
      ] },
    ],
    faults: [
      { no: 1, fault: '门磁异常开启', lock: '告警+弹窗', action: '现场核实/远程锁门', manualReset: false },
      { no: 2, fault: '非法闯入', lock: '声光+联动视频', action: '保安处置', manualReset: true },
      { no: 3, fault: '控制器离线', lock: '标记离线', action: '查网络/供电', manualReset: false },
      { no: 4, fault: '断电开锁(消防)', lock: '自动释放(NC)', action: '确认火警后复位', manualReset: true },
    ],
  }
  return { total: 268, online: 266, openAbnormal: 1, todayEvents: 1642, denied: 12, visitors: 9, areas, events, knowledge }
}

const REFRESH_MS = 30000
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => { load(); timer = setInterval(load, REFRESH_MS) })
onUnmounted(() => { if (timer) clearInterval(timer) })

void DoorOpen; void Activity; void LogIn; void ShieldAlert
</script>

<style scoped>
.page { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.page-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 20px; margin: 0; }
.page-sub { margin: 2px 0 0; color: var(--text-2); font-size: 12px; }
.head-actions { display: flex; align-items: center; gap: 10px; }
.btn { padding: 6px 14px; border: 1px solid var(--border); background: var(--bg-1); color: var(--text-1); border-radius: 6px; cursor: pointer; font-size: 13px; }
.btn:hover { border-color: var(--brand); color: var(--brand); }
.mock-flag-sm { font-size: 12px; color: #d06a3a; }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.grid-main { display: grid; grid-template-columns: 2.2fr 1fr; gap: 14px; }
.grid-sub { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 14px; }
/* 平面图 */
.plan-card { min-height: 420px; }
.legend { display: flex; gap: 12px; font-size: 11px; color: var(--text-2); }
.lg { display: inline-flex; align-items: center; gap: 4px; }
.lg-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.lg-dot.g { background: #2fae6b; } .lg-dot.b { background: #3f8fbf; } .lg-dot.y { background: #d06a3a; } .lg-dot.r { background: #d23b3b; }
.plan-wrap { display: flex; flex-direction: column; gap: 10px; }
.plan-svg { width: 100%; background: var(--bg-2); border-radius: 8px; }
.floor { fill: #0d141d; stroke: #243240; stroke-width: 1.5; }
.floor-label { fill: #7d93a8; font-size: 13px; font-weight: 600; }
.corridor { fill: #14202c; stroke: #243240; }
.corr-label { fill: #5f7488; font-size: 12px; }
.zone { fill: #12202c; stroke: #2a3d4d; stroke-dasharray: 3 3; }
.zone-label { fill: #8aa2b5; font-size: 11px; }
.pt { cursor: pointer; }
.pt-dot { stroke: #0a0e14; stroke-width: 1.5; }
.pt-dot.normal { fill: #2fae6b; } .pt-dot.open { fill: #3f8fbf; } .pt-dot.abnormal { fill: #d06a3a; } .pt-dot.intrude { fill: #d23b3b; }
.pt-name { fill: #9fb3c5; font-size: 9px; text-anchor: middle; }
.pt.sel .pt-dot { stroke: #fff; stroke-width: 2; }
.pt-pulse { fill: none; stroke: #3f8fbf; stroke-width: 1.5; animation: pulse 1.4s ease-out infinite; }
@keyframes pulse { 0% { r: 9; opacity: .9; } 100% { r: 20; opacity: 0; } }
.pt-info { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; background: var(--bg-2); }
.pt-info-h { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; margin-bottom: 4px; }
.pt-info-b { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 12px; color: var(--text-2); }

/* 侧栏 */
.side-col { display: flex; flex-direction: column; gap: 14px; }
.ctrl-tip { font-size: 11px; color: var(--text-2); margin-top: 8px; }
.ctrl-sel { margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 8px; display: flex; flex-direction: column; gap: 6px; }
.ctrl-sel-name { font-size: 13px; font-weight: 600; }
.qc-actions { display: flex; gap: 8px; }
.qc-btn { border: 1px solid var(--border); background: var(--bg-1); color: var(--text-1); font-size: 12px; padding: 5px 12px; border-radius: 5px; cursor: pointer; }
.qc-btn.open { border-color: #2f8fbf; color: #3f9fcf; } .qc-btn.open:hover { background: rgba(47,143,191,.12); }
.qc-btn.lock { border-color: #b4451f; color: #d06a3a; } .qc-btn.lock:hover { background: rgba(180,69,31,.12); }
.ctrl-state { font-size: 11px; } .ctrl-state.open { color: #3f9fcf; } .ctrl-state.abnormal { color: #d06a3a; } .ctrl-state.intrude { color: #d23b3b; } .ctrl-state.normal { color: #2fae6b; }

/* 告警 */
.alarm-card { flex: 1; }
.alarm-list { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
.alarm-row { display: grid; grid-template-columns: auto 90px 1fr; gap: 6px; align-items: center; font-size: 12px; padding: 4px 0; border-bottom: 1px solid var(--border); }
.a-door { color: var(--brand); } .a-desc { color: var(--text-1); }

/* 事件流 */
.evt-card { min-height: 220px; }
.evt-stream { display: flex; flex-direction: column; gap: 2px; max-height: 260px; overflow-y: auto; }
.evt-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 12px; border-bottom: 1px solid var(--border); }
.evt-time { color: var(--text-2); } .evt-door { color: var(--brand); font-weight: 500; min-width: 90px; }
.evt-person { color: var(--text-1); min-width: 90px; } .evt-act { flex: 1; color: var(--text-2); }

.tag.g { color: #2fae6b; border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: #d06a3a; border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: #d23b3b; border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: #3f9fcf; border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* 授权分级 */
.area-grid { display: flex; flex-direction: column; gap: 10px; }
.area-block { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; background: var(--bg-2); }
.area-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.d-name { font-weight: 500; font-size: 13px; }
.auth-val { font-size: 12px; font-weight: 600; color: #3f9fcf; }
.muted { font-size: 11px; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .grid-main, .grid-sub { grid-template-columns: 1fr; }
}
</style>
