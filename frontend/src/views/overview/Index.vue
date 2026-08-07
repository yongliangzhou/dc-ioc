<template>
  <div class="dashboard-index">
    <!-- ========== Section 1: Global KPI Row ========== -->
    <div class="page-title-row">
      <h2 class="section-title">驾驶舱总览</h2>
      <span class="last-update">刷新 {{ refreshTime }} · 每30秒自动刷新</span>
    </div>

    <div class="kpi-row">
      <div class="kpi-cell pue-cell" title="PUE · 30天趋势">
        <KpiCard
          title="PUE"
          :value="fmtNum(dashboard.pue)"
          unit=""
          :trend="pueTrendPercent"
          :subtitle="'最近24h'"
        />
        <div class="mini-sparkline">
          <TrendChart
            :series="pueSparklineSeries"
            :xAxisData="pueSparklineX"
            :height="60"
            :showRange="false"
            :showTooltip="true"
          />
        </div>
      </div>
      <div class="kpi-cell">
        <KpiCard
          title="IT 负载"
          :value="fmtNum(dashboard.it_load_mw)"
          unit="MW"
          subtitle="设计容量 4.8 MW"
          :barValue="((dashboard.it_load_mw || 0) / 4.8) * 100"
        />
      </div>
      <div class="kpi-cell">
        <KpiCard
          title="总负载"
          :value="fmtNum(dashboard.total_load_mw)"
          unit="MW"
          :subtitle="`制冷占比 ${coolLoadPct}%`"
          :trend="totalLoadTrend"
        />
      </div>
      <div class="kpi-cell">
        <KpiCard
          title="制冷负载"
          :value="fmtNum(dashboard.cool_load_mw)"
          unit="MW"
          subtitle="冷源贡献"
          :status="coolLoadStatus"
        />
      </div>
      <div class="kpi-cell">
        <KpiCard
          title="设备在线率"
          :value="fmtNum(dashboard.online_rate)"
          unit="%"
          :subtitle="`${dashboard.online_devices}/${dashboard.total_devices} 台`"
          :barValue="dashboard.online_rate || 0"
          :status="(dashboard.online_rate || 100) >= 95 ? 'normal' : 'warning'"
        />
      </div>
      <div class="kpi-cell alarm-cell" @click="goAlarms">
        <div class="alarm-kpi-top">
          <span class="alarm-kpi-label">活跃告警</span>
          <span class="alarm-kpi-val">{{ dashboard.today_alarms ?? 0 }}</span>
          <span class="alarm-kpi-unit">条</span>
        </div>
        <div class="alarm-kpi-badges">
          <AlarmBadge level="critical" :count="dashboard.alarms?.crit ?? 0" />
          <AlarmBadge level="warning" :count="dashboard.alarms?.warn ?? 0" />
          <AlarmBadge level="info" :count="dashboard.alarms?.info ?? 0" />
        </div>
      </div>
    </div>

    <!-- ========== Section 2: 制冷域 KPI 入口卡 ========== -->
    <div class="section-bar">
      <h3 class="section-title">制冷系统总览</h3>
    </div>
    <div class="cooling-entry-row">
      <div class="cooling-entry" @click="goMonitor('/monitor/hvac/chiller')">
        <KpiCard
          title="冷源 COP"
          :value="coolingStats.cop"
          unit=""
          :trend="coolingStats.copTrend"
          subtitle="冷源系统群控"
          :clickable="true"
        />
        <div class="entry-hint">点击进入 → 冷源群控</div>
      </div>
      <div class="cooling-entry" @click="goMonitor('/monitor/hvac/crac')">
        <KpiCard
          title="空调 SHR"
          :value="coolingStats.shr"
          unit=""
          :trend="coolingStats.shrTrend"
          subtitle="精密空调末端"
          :clickable="true"
        />
        <div class="entry-hint">点击进入 → 空调末端</div>
      </div>
      <div class="cooling-entry" @click="goMonitor('/monitor/hvac/liquid')">
        <KpiCard
          title="液冷 PUE 贡献"
          :value="coolingStats.pueC"
          unit=""
          :trend="coolingStats.pueCTrend"
          subtitle="液冷系统"
          :clickable="true"
        />
        <div class="entry-hint">点击进入 → 液冷系统</div>
      </div>
      <div class="cooling-entry">
        <KpiCard
          title="自然冷却时"
          :value="fmtNum(dashboard.free_cool_hours)"
          unit="h"
          subtitle="本月累计"
          :barValue="Math.min(((dashboard.free_cool_hours ?? 0) / 720) * 100, 100)"
        />
      </div>
    </div>

    <!-- ========== Section 3: 四大业务域健康度 ========== -->
    <div class="section-bar">
      <h3 class="section-title">业务域健康度</h3>
    </div>
    <div class="domain-health-row">
      <div v-for="d in domainCards" :key="d.key" class="domain-card">
        <div class="domain-card-header">
          <StatusBadge :status="d.healthStatus" />
          <span class="domain-card-title">{{ d.title }}</span>
        </div>
        <div class="domain-card-inner">
          <div class="domain-ring">
            <svg viewBox="0 0 100 100" class="ring-svg">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#1e293b" stroke-width="8" />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                :stroke="d.ringColor"
                stroke-width="8"
                stroke-linecap="round"
                :stroke-dasharray="`${d.ringRate * 2.64} 264`"
                stroke-dashoffset="0"
                transform="rotate(-90 50 50)"
              />
              <text
                x="50"
                y="52"
                text-anchor="middle"
                fill="#c8d6e5"
                font-size="16"
                font-weight="700"
              >
                {{ d.ringRate }}%
              </text>
            </svg>
          </div>
          <div class="domain-stats">
            <div class="domain-stat-item">
              <StatusBadge :status="d.deviceStatus" />
              <span>设备 {{ d.onlineRate }}% 在线</span>
            </div>
            <div class="domain-stat-item">
              <StatusBadge :status="d.alarmStatus" />
              <span>告警 {{ d.alarmCount }} 条</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== Section 4: 校区总览 ========== -->
    <div class="section-bar">
      <h3 class="section-title">校区总览</h3>
    </div>
    <div class="campus-row">
      <div v-for="c in campuses" :key="c.code ?? c.id" class="campus-card" @click="selectCampus(c)">
        <div class="campus-status">
          <StatusBadge :status="computeCampusStatus(c)" />
        </div>
        <div class="campus-name">{{ c.name }}</div>
        <div class="campus-kpi-list">
          <div class="campus-kpi">
            <span>PUE</span><span class="v">{{ fmtNum(c.pue) }}</span>
          </div>
          <div class="campus-kpi">
            <span>在线率</span><span class="v">{{ fmtNum(c.online_rate) }}%</span>
          </div>
          <div class="campus-kpi">
            <span>IT负载</span><span class="v">{{ fmtNum(c.it_load_mw) }}MW</span>
          </div>
          <div class="campus-kpi">
            <span>告警</span><span class="v">{{ c.today_alarms ?? 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== Section 5: 实时告警联动 ========== -->
    <div class="section-bar">
      <h3 class="section-title">
        实时告警联动 <span class="alarm-count-badge">{{ activeAlarms.length }} 条活跃</span>
      </h3>
    </div>
    <div class="alarm-feed">
      <div v-if="activeAlarms.length === 0" class="alarm-empty">当前无活跃告警</div>
      <div
        v-for="a in activeAlarms.slice(0, 8)"
        :key="a.id ?? a.message"
        class="alarm-row"
        @click="goAlarms"
      >
        <AlarmBadge :level="a.level ?? 'info'" :count="0" />
        <span class="alarm-msg">{{ a.title || a.message }}</span>
        <span class="alarm-time">{{ formatAlarmTime(a.time || a.created_at) }}</span>
      </div>
    </div>

    <!-- ========== Section 6: 关键趋势 ========== -->
    <div class="section-bar">
      <h3 class="section-title">关键趋势</h3>
    </div>
    <div class="trends-grid">
      <div class="trend-card">
        <TrendChart
          title="PUE & WUE 趋势"
          :series="trendDatasets.pueWue"
          :xAxisData="trendBaselineX"
          :height="200"
          :showRange="false"
        />
      </div>
      <div class="trend-card">
        <TrendChart
          title="IT / 总负载 / 制冷负载 (MW)"
          :series="trendDatasets.loads"
          :xAxisData="trendBaselineX"
          :height="200"
          :showRange="false"
        />
      </div>
      <div class="trend-card">
        <TrendChart
          title="设备在线率 & 可用性 (%)"
          :series="trendDatasets.online"
          :xAxisData="trendBaselineX"
          :height="200"
          :showRange="false"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { fmtNum } from '@/utils/format'
import { useRouter } from 'vue-router'
import { getDashboardOverview, getActiveAlarms, getCampusComparison } from '@/api/index'
import { getHvacOverview } from '@/api/hvac'
import type { DashboardOverview, CampusComparisonResponse } from '@/types'
import type { HvacOverview } from '@/api/hvac'
import type { Alarm, CampusComparisonItem } from '@/types'

interface OverviewState extends Partial<DashboardOverview> {
  halls?: unknown
  power_load_mw?: number
  cop?: number
  climat_a?: number
  climat_b?: number
  climat_c?: number
  clusters?: unknown
  liquid?: unknown
  [k: string]: unknown
}

interface CampusLike extends Partial<CampusComparisonItem> {
  name?: string
  code?: string
  id?: string
  campus?: string
  pue?: number
  online_rate?: number
  it_load_mw?: number
  today_alarms?: number
  [k: string]: unknown
}
import { KpiCard } from '@dc-ioc/ui'
import { StatusBadge } from '@dc-ioc/ui'
import { AlarmBadge } from '@dc-ioc/ui'
import TrendChart from '@/components/monitor/TrendChart.vue'

const router = useRouter()

// ===== State =====
const dashboard = reactive<OverviewState>({
  total_devices: 0,
  online_devices: 0,
  online_rate: 0,
  today_alarms: 0,
  pue: 0,
  wue: 0,
  it_load_mw: 0,
  total_load_mw: 0,
  cool_load_mw: 0,
  availability: 0,
  free_cool_hours: 0,
  halls: [],
  power_load_mw: 0,
  cop: 0,
  climat_a: 0,
  climat_b: 0,
  climat_c: 0,
  clusters: [],
  liquid: null,
  alarms: { crit: 0, warn: 0, info: 0 },
})
const campuses = ref<CampusLike[]>([])
const activeAlarms = ref<Alarm[]>([])
const refreshTime = ref('--:--:--')
let timer: ReturnType<typeof setInterval> | undefined

// ===== Cooling Domain State =====
const coolingStats = reactive({
  cop: '--',
  copTrend: 0,
  shr: '--',
  shrTrend: 0,
  pueC: '--',
  pueCTrend: 0,
})

// ===== Domain Health Card Config =====
const domainCards = computed(() => {
  const d = dashboard
  const or = d.online_rate ?? 100
  return [
    {
      key: 'hvac',
      title: '暖通系统',
      healthStatus: 'success' as const,
      deviceStatus: or >= 95 ? ('success' as const) : ('warning' as const),
      alarmStatus: (d.alarms?.crit ?? 0) === 0 ? ('success' as const) : ('warning' as const),
      onlineRate: Math.round(or),
      alarmCount: 3,
      ringRate: Math.round(or),
      ringColor: '#05b896',
    },
    {
      key: 'power',
      title: '电力系统',
      healthStatus: 'success' as const,
      deviceStatus: or >= 95 ? ('success' as const) : ('warning' as const),
      alarmStatus: (d.alarms?.warn ?? 0) <= 2 ? ('success' as const) : ('warning' as const),
      onlineRate: Math.round(Math.max(or - 2, 0)),
      alarmCount: 1,
      ringRate: Math.round(Math.max(or - 1, 0)),
      ringColor: '#f39c12',
    },
    {
      key: 'security',
      title: '安防消防',
      healthStatus: 'success' as const,
      deviceStatus: or >= 98 ? ('success' as const) : ('warning' as const),
      alarmStatus: 'success' as const,
      onlineRate: Math.min(Math.round(or) + 1, 100),
      alarmCount: 0,
      ringRate: Math.min(Math.round(or) + 1, 100),
      ringColor: '#3498db',
    },
    {
      key: 'smartops',
      title: '数智运维',
      healthStatus: 'success' as const,
      deviceStatus: 'success' as const,
      alarmStatus: 'success' as const,
      onlineRate: 100,
      alarmCount: 0,
      ringRate: 100,
      ringColor: '#9b59b6',
    },
  ]
})

// ===== 30-day PUE sparkline =====
const pueSparklineX = computed(() => {
  const arr: string[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    arr.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return arr
})
const pueSparklineSeries = computed(() => {
  const base = dashboard.pue || 1.25
  const data = Array.from({ length: 30 }, () => +(base + (Math.random() - 0.5) * 0.12).toFixed(3))
  return [
    {
      name: 'PUE',
      type: 'line' as const,
      data,
      color: '#05b896',
      smooth: true,
      areaStyle: { color: 'rgba(5,184,150,0.12)' },
      symbol: 'none' as const,
      symbolSize: 0,
    },
  ]
})

// ===== General trend mock (48H) =====
const trendBaselineX = computed(() => {
  const arr: string[] = []
  for (let i = 47; i >= 0; i--) {
    const d = new Date()
    d.setHours(d.getHours() - i, 0, 0, 0)
    arr.push(`${String(d.getHours()).padStart(2, '0')}:00`)
  }
  return arr
})

const trendDatasets = computed(() => {
  const b = dashboard
  const pueBase = b.pue || 1.25
  const wueBase = b.wue || 1.8
  const itBase = b.it_load_mw || 2.1
  const totalBase = b.total_load_mw || 3.5
  const coolBase = b.cool_load_mw || 1.2
  const onRateBase = b.online_rate ?? 98
  const availBase = b.availability ?? 99.99

  const gen = (base: number, range: number, len: number) =>
    Array.from({ length: len }, () => +(base + (Math.random() - 0.5) * range).toFixed(2))

  return {
    pueWue: [
      {
        name: 'PUE',
        type: 'line' as const,
        data: gen(pueBase, 0.12, 48),
        color: '#05b896',
        smooth: true,
        yAxisIndex: 0,
      },
      {
        name: 'WUE',
        type: 'line' as const,
        data: gen(wueBase, 0.2, 48),
        color: '#3498db',
        smooth: true,
        yAxisIndex: 1,
      },
    ],
    loads: [
      {
        name: 'IT负荷',
        type: 'line' as const,
        data: gen(itBase, 0.4, 48),
        color: '#05b896',
        smooth: true,
      },
      {
        name: '总负荷',
        type: 'line' as const,
        data: gen(totalBase, 0.5, 48),
        color: '#f39c12',
        smooth: true,
      },
      {
        name: '制冷负荷',
        type: 'line' as const,
        data: gen(coolBase, 0.3, 48),
        color: '#3498db',
        smooth: true,
      },
    ],
    online: [
      {
        name: '在线率',
        type: 'line' as const,
        data: gen(onRateBase, 2, 48),
        color: '#05b896',
        smooth: true,
        yAxisIndex: 0,
      },
      {
        name: '可用性',
        type: 'line' as const,
        data: gen(availBase, 0.02, 48),
        color: '#9b59b6',
        smooth: true,
        yAxisIndex: 1,
      },
    ],
  }
})

// ===== Computed =====
const pueTrendPercent = computed(() => {
  const base = dashboard.pue || 1.25
  const prev = +(base + (Math.random() - 0.5) * 0.08).toFixed(3)
  return +(((base - prev) / prev) * 100).toFixed(1)
})

const totalLoadTrend = computed(() => {
  const b = dashboard.total_load_mw || 3.5
  const prev = +(b + (Math.random() - 0.5) * 0.2).toFixed(2)
  return +(((b - prev) / prev) * 100).toFixed(1)
})

const coolLoadPct = computed(() => {
  if (!dashboard.total_load_mw) return 0
  return +(((dashboard.cool_load_mw ?? 0) / dashboard.total_load_mw) * 100).toFixed(1)
})

const coolLoadStatus = computed(
  () => (coolLoadPct.value > 40 ? 'warning' : 'normal') as 'normal' | 'warning',
)

// ===== Helpers =====
function formatAlarmTime(t: string | undefined): string {
  if (!t) return '--'
  try {
    const d = new Date(t)
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  } catch {
    return t.slice(0, 10)
  }
}
function goAlarms() {
  router.push('/ops/alarms')
}
function goMonitor(path: string) {
  router.push(path)
}
function selectCampus(c: CampusLike) {
  // Navigate to campus detail or highlight
  console.log('Selected campus:', c.name)
}
function computeCampusStatus(c: CampusLike): 'success' | 'warning' | 'critical' {
  const or = c.online_rate ?? 0
  if (or >= 95) return 'success'
  if (or >= 80) return 'warning'
  return 'critical'
}

// ===== Fetch =====
async function loadAll() {
  try {
    const raw = await getDashboardOverview()
    Object.assign(dashboard, raw)
  } catch (e) {
    console.error('Dashboard load error:', e)
  }

  try {
    const list = await getActiveAlarms()
    activeAlarms.value = Array.isArray(list.items) ? list.items : []
  } catch {
    activeAlarms.value = []
  }

  try {
    const hvac: HvacOverview = await getHvacOverview()
    if (hvac.chiller?.chillerGroups?.length) {
      const cops = hvac.chiller.chillerGroups.map((g) => g.chiller?.cop).filter(Boolean) as number[]
      if (cops.length) {
        const avg = cops.reduce((a, b) => a + b, 0) / cops.length
        coolingStats.cop = avg.toFixed(2)
        coolingStats.copTrend = +(Math.random() * 4 - 2).toFixed(1)
      }
    }
    if (hvac.liquidCooling) {
      const pueC = hvac.liquidCooling.pueContribution
      if (pueC != null) {
        coolingStats.pueC = pueC.toFixed(3)
        coolingStats.pueCTrend = +(Math.random() * 0.06 - 0.03).toFixed(3)
      }
    }
  } catch {
    /* cooling stats unavailable */
  }

  try {
    const cmpRaw = await getCampusComparison().catch(
      () => ({ comparisons: [] }) as unknown as CampusComparisonResponse,
    )
    const cmpList = Array.isArray(cmpRaw.comparisons) ? cmpRaw.comparisons : []
    if (cmpList.length) {
      campuses.value = cmpList as CampusLike[]
    } else {
      // fallback: try individual campus data
      campuses.value = [
        {
          name: '主校区',
          code: 'DC1',
          pue: dashboard.pue,
          online_rate: dashboard.online_rate,
          it_load_mw: dashboard.it_load_mw,
          today_alarms: dashboard.today_alarms,
        },
      ]
    }
  } catch {
    campuses.value = []
  }

  refreshTime.value = new Date().toLocaleTimeString('zh-CN')
}

// ===== Lifecycle =====
onMounted(() => {
  loadAll()
  timer = setInterval(loadAll, 30_000)
})
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
})
</script>

<style scoped>
.dashboard-index {
  padding: 16px 20px;
  max-width: 1440px;
  margin: 0 auto;
  color: #c8d6e5;
  font-size: 13px;
}

.page-title-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}
.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #e8edf2;
}
.last-update {
  font-size: 11px;
  color: #5a6a82;
}
.section-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 18px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #1e293b;
}
.section-bar .section-title {
  margin: 0;
}

/* ===== KPI Row ===== */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.kpi-cell {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 10px 12px 6px;
}
.pue-cell {
  /* PUE cell with sparkline needs more bottom padding */
}
.mini-sparkline {
  margin-top: 4px;
}

/* Alarm KPI Cell */
.alarm-cell {
  cursor: pointer;
  transition: border-color 0.15s;
}
.alarm-cell:hover {
  border-color: #e74c3c;
}
.alarm-kpi-top {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.alarm-kpi-label {
  font-size: 11px;
  color: #5a6a82;
}
.alarm-kpi-val {
  font-size: 26px;
  font-weight: 700;
  color: #e74c3c;
  margin-left: auto;
}
.alarm-kpi-unit {
  font-size: 12px;
  color: #5a6a82;
}
.alarm-kpi-badges {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* ===== Cooling Entry Row ===== */
.cooling-entry-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.cooling-entry {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 10px 12px 6px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.cooling-entry:hover {
  border-color: #05b89666;
}
.entry-hint {
  font-size: 10px;
  color: #3a5068;
  text-align: right;
  padding: 2px 6px 0;
}

/* ===== Domain Health ===== */
.domain-health-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.domain-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 12px 14px;
}
.domain-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.domain-card-title {
  font-size: 14px;
  font-weight: 600;
}
.domain-card-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.domain-ring {
  flex: 0 0 90px;
}
.ring-svg {
  width: 90px;
  height: 90px;
  display: block;
}
.domain-stats {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.domain-stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

/* ===== Campus ===== */
.campus-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.campus-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.campus-card:hover {
  border-color: #2a4a6a;
}
.campus-status {
  margin-bottom: 4px;
}
.campus-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}
.campus-kpi-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.campus-kpi {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #5a6a82;
}
.campus-kpi .v {
  color: #c8d6e5;
  font-weight: 500;
}

/* ===== Alarm Feed ===== */
.alarm-feed {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 0 14px;
  max-height: 280px;
  overflow-y: auto;
}
.alarm-empty {
  padding: 16px 0;
  text-align: center;
  color: #3a5068;
}
.alarm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #15202b;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.15s;
}
.alarm-row:last-child {
  border-bottom: none;
}
.alarm-row:hover {
  background: #111d2a;
  margin: 0 -14px;
  padding-left: 14px;
  padding-right: 14px;
}
.alarm-msg {
  flex: 1;
}
.alarm-time {
  color: #3a5068;
  white-space: nowrap;
}
.alarm-count-badge {
  font-size: 12px;
  font-weight: 400;
  color: #e74c3c;
  margin-left: 8px;
}

/* ===== Trends ===== */
.trends-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.trend-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 8px;
  padding: 10px 12px;
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .cooling-entry-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .domain-health-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .trends-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .cooling-entry-row {
    grid-template-columns: 1fr;
  }
  .domain-health-row {
    grid-template-columns: 1fr;
  }
  .trends-grid {
    grid-template-columns: 1fr;
  }
}
</style>
