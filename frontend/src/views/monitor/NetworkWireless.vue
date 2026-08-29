<template>
  <div class="net-wl">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('无线网络') }}</h1>
      <span class="sub">{{ tl('AP 射频 / 信号热力 / 终端统计 / 信道干扰') }}</span>
      <MockDataBanner :level="mockLevel" :reason="mockReason" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid cols-4">
      <SkeletonCard v-for="i in 8" :key="i" />
    </div>

    <!-- Error -->
    <Panel v-else-if="error" class="err-card">
      <div class="err-title">{{ tl('加载失败') }}</div>
      <div class="err-detail">{{ error }}</div>
      <button class="btn" @click="loadData()">{{ tl('重试') }}</button>
    </Panel>

    <!-- 2.4.1 AP 分布热力图 (信号强度) -->
    <Panel v-if="s && s.aps.length" title="AP 信号强度热力图">
      <template #extra>
        <span class="pill g">{{ tl('RSSI dBm') }}</span>
      </template>
      <HeatmapView
        v-if="s.heatmapData"
        :data="s.heatmapData"
        :value-range="[-85, -30]"
        :colors="heatColors"
        unit="dBm"
        :height="300"
      />
    </Panel>

    <!-- 2.4.3 终端统计面板：总数 + 类型分布饼图 -->
    <div v-if="s && s.aps.length" class="grid cols-2">
      <!-- 终端类型分布 -->
      <Panel title="终端类型分布">
        <template #extra>
          <span class="pill g">{{ fmtNum(s.totalUsers) }} {{ tl('终端') }}</span>
        </template>
        <BaseChart :option="clientPieOption" height="240px" />
      </Panel>

      <!-- 射频频段分布 -->
      <Panel title="射频频段分布">
        <div class="band-grid">
          <div class="band-card" v-for="b in s.bandStats" :key="b.band">
            <div class="band-head">
              <span class="band-name mono">{{ b.band }}</span>
              <span class="band-count">{{ b.aps }} {{ tl('台AP') }}</span>
            </div>
            <div class="band-users">
              <span class="band-users-val mono">{{ fmtNum(b.users) }}</span>
              <span class="band-users-lbl">{{ tl('关联终端') }}</span>
            </div>
            <div class="band-bar"><span class="band-fill" :class="b.util > 70 ? 'a' : 'g'" :style="{ width: Math.min(100, b.util) + '%' }" /></div>
            <div class="band-meta muted">{{ tl('平均利用率') }} {{ b.util }}%</div>
          </div>
        </div>
      </Panel>
    </div>

    <!-- 2.4.3 / 2.4.4 KPI 卡片 -->
    <div v-if="s && s.aps.length" class="grid cols-4">
      <KpiCard
        :title="tl('AP 总数')"
        :value="s.total"
        unit="台"
        dot="var(--blue)"
        size="sm"
      />
      <KpiCard
        :title="tl('在线率')"
        :value="s.onlinePercent"
        unit="%"
        :bar-value="s.onlinePercent"
        bar-color="var(--green)"
        :status="s.onlinePercent < 90 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        :title="tl('接入用户')"
        :value="s.totalUsers"
        unit="人"
        dot="var(--cyan)"
        size="sm"
      />
      <KpiCard
        :title="tl('平均信号')"
        :value="s.avgRssi"
        unit="dBm"
        :bar-value="Math.min(100, ((s.avgRssi + 90) / 60) * 100)"
        bar-color="var(--violet)"
        :status="s.avgRssi > -65 ? 'normal' : s.avgRssi > -75 ? 'warning' : 'danger'"
        size="sm"
      />
    </div>

    <!-- 2.4.4 信道干扰可视化 -->
    <Panel v-if="s && s.aps.length" title="信道利用率与干扰">
      <template #extra>
        <span class="pill a" v-if="s.highInterference > 0">{{ s.highInterference }} {{ tl('信道高干扰') }}</span>
        <span class="pill g" v-else>{{ tl('信道健康') }}</span>
      </template>
      <BaseChart :option="channelChartOption" height="300px" />
    </Panel>

    <!-- 2.4.2 AP 列表：DeviceTable -->
    <Panel v-if="s && s.aps.length" title="AP 列表">
      <template #extra>
        <span class="pill g">{{ s.aps.length }} {{ tl('台') }}</span>
      </template>
      <DeviceTable
        :columns="apColumns"
        :rows="s.apRows"
        :count="s.aps.length"
      />
    </Panel>

    <!-- Per-device detail cards -->
    <Panel
      v-for="ap in apCards"
      :key="ap.id"
      :title="ap.name"
    >
      <template #ct>
        {{ ap.name }} <span class="muted ml2 fw4 f11">{{ ap.location }}</span>
      </template>
      <template #extra>
        <StatusBadge :status="ap.status === 'online' ? 'online' : 'offline'" />
      </template>

      <div class="rt-meta-grid">
        <div class="rt-kv"><span class="rt-k">{{ tl('型号') }}</span><span class="rt-v mono">{{ ap.model }}</span></div>
        <div class="rt-kv"><span class="rt-k">{{ tl('管理IP') }}</span><span class="rt-v mono">{{ ap.ip }}</span></div>
        <div class="rt-kv"><span class="rt-k">{{ tl('关联终端') }}</span><span class="rt-v">{{ ap.users_total }} {{ tl('人') }}</span></div>
        <div class="rt-kv"><span class="rt-k">{{ tl('接收信号') }}</span><span class="rt-v" :class="ap.rx_rssi_dbm > -65 ? 'g-text' : 'a-text'">{{ ap.rx_rssi_dbm }} dBm</span></div>
        <div class="rt-kv"><span class="rt-k">{{ tl('底噪') }}</span><span class="rt-v mono">{{ ap.noise_floor_dbm }} dBm</span></div>
        <div class="rt-kv"><span class="rt-k">{{ tl('运行时长') }}</span><span class="rt-v">{{ ap.uptime_days }} {{ tl('天') }}</span></div>
      </div>

      <!-- 双射频 2.4G / 5G -->
      <div class="radio-grid">
        <div class="radio-block" v-for="r in [{ band: '2.4G', radio: ap.radio_2g }, { band: '5G', radio: ap.radio_5g }]" :key="r.band">
          <div class="radio-head">
            <span class="d-name">{{ r.band }}</span>
            <span class="tag" :class="r.radio.status === 'up' ? 'g' : 'r'">{{ r.radio.status }}</span>
          </div>
          <div class="radio-meta">
            <span class="muted">{{ tl('信道') }}</span><span class="mono">{{ r.radio.channel }}</span>
            <span class="muted">{{ tl('功率') }}</span><span class="mono">{{ r.radio.tx_power_dbm }}dBm</span>
            <span class="muted">{{ tl('用户') }}</span><span class="mono">{{ r.radio.users }}</span>
            <span class="muted">{{ tl('利用率') }}</span><span class="mono" :class="r.radio.util_pct > 70 ? 'a-text' : 'g-text'">{{ r.radio.util_pct }}%</span>
          </div>
          <div class="radio-bar"><span class="radio-fill" :class="r.radio.util_pct > 70 ? 'a' : 'g'" :style="{ width: Math.min(100, r.radio.util_pct) + '%' }" /></div>
        </div>
      </div>
    </Panel>

    <!-- Empty state -->
    <Panel v-if="s && !s.aps.length && !loading && !error" class="empty-card">
      <p class="muted">{{ tl('暂无无线数据') }}</p>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { toErrorMessage, useMockFlag } from '@/composables/useAsyncPage'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmtNum, fmtBps } from '@/utils/format'
import { KpiCard } from '@dc-ioc/ui'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import { StatusBadge } from '@dc-ioc/ui'
import DeviceTable from '@/components/monitor/DeviceTable.vue'
import HeatmapView from '@/components/monitor/HeatmapView.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import Panel from '@/components/common/Panel.vue'
import { getNetworkWirelessDetailed, type NetworkWirelessSummary, type WirelessView } from '@/api/monitor'
import type * as echarts from 'echarts'
import type { EChartsOption } from '@/hooks/useECharts'

const { t: tl } = useI18n()

/** 本页真 AP 与模拟字段混排，必须分级提示 */
const { level: mockLevel, reason: mockReason, markPartial, markFull } = useMockFlag()

// ──────────────────────────────────────────
// Local extended wireless type
// ──────────────────────────────────────────
interface WirelessEx extends WirelessView {
  interference_dbm: number
  client_types: { phone: number; laptop: number; iot: number; other: number }
}

interface HeatmapData {
  xLabels: string[]
  yLabels: string[]
  values: number[][]
}

interface BandStat {
  band: string
  aps: number
  users: number
  util: number
}

interface ApRow {
  name: string
  status: string
  users: number
  channel: string
  traffic: string
  _rowClass?: string
}

// ── DeviceTable columns for AP list (2.4.2) ──
const apColumns = [
  { key: 'name', label: tl('AP 名称') },
  { key: 'status', label: tl('状态'), render: 'status' as const },
  { key: 'users', label: tl('关联终端') },
  { key: 'channel', label: tl('信道') },
  { key: 'traffic', label: tl('流量') },
]

interface PageState {
  aps: WirelessEx[]
  total: number
  online: number
  onlinePercent: number
  totalUsers: number
  avgRssi: number
  heatmapData: HeatmapData | null
  clientDist: { name: string; value: number; color: string }[]
  bandStats: BandStat[]
  channelData: { channel: string; util: number; interference: number }[]
  highInterference: number
  apRows: ApRow[]
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = reactive<PageState>({
  aps: [],
  total: 0,
  online: 0,
  onlinePercent: 0,
  totalUsers: 0,
  avgRssi: 0,
  heatmapData: null,
  clientDist: [],
  bandStats: [],
  channelData: [],
  highInterference: 0,
  apRows: [],
})

const apCards = computed(() => s.aps ?? [])

// ──────────────────────────────────────────
// Heatmap colors (signal gradient: weak→strong)
// ──────────────────────────────────────────
const heatColors = ['#1e3a8a', '#1d4ed8', '#06b6d4', '#22c55e', '#eab308', '#f97316', '#ef4444']

// ──────────────────────────────────────────
// Chart options
// ──────────────────────────────────────────
const clientPieOption = reactive<EChartsOption>({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: (p) => {
    const item = Array.isArray(p) ? p[0] : p
    return `${item.name}<br/>${fmtNum(Number(item.value))} 台 (${item.percent}%)`
  } },
  legend: { orient: 'vertical', right: '4%', top: 'center', textStyle: { color: '#94a3b8', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
  series: [{
    name: tl('终端类型'),
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['38%', '50%'],
    avoidLabelOverlap: false,
    itemStyle: { borderColor: '#0f172a', borderWidth: 2, borderRadius: 4 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold', color: '#e2e8f0', formatter: '{b}\n{d}%' } },
    data: [],
  }],
})

const channelChartOption = reactive<EChartsOption>({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { data: [tl('利用率'), tl('干扰')], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 4 },
  grid: { left: 50, right: 20, top: 40, bottom: 30 },
  xAxis: {
    type: 'category',
    data: [],
    axisLabel: { color: '#64748b', fontSize: 10, formatter: (v: string) => 'CH' + v },
    axisLine: { lineStyle: { color: '#334155' } },
  },
  yAxis: {
    type: 'value',
    max: 100,
    axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value}%' },
    splitLine: { lineStyle: { color: 'rgba(51,65,85,0.4)' } },
  },
  series: [
    {
      name: tl('利用率'),
      type: 'bar',
      data: [],
      itemStyle: { color: '#22d3ee', borderRadius: [3, 3, 0, 0] },
      barWidth: '45%',
    },
    {
      name: tl('干扰'),
      type: 'bar',
      data: [],
      itemStyle: { color: 'rgba(245,158,11,0.7)', borderRadius: [3, 3, 0, 0] },
      barWidth: '45%',
    },
  ],
})

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────


// ──────────────────────────────────────────
// Mock data
// ──────────────────────────────────────────
function mockData() {
  // ── AP list (with extended fields) ──
  const aps: WirelessEx[] = [
    {
      id: 'ap-1', name: 'AP-F1-R01', location: '1F 东区走廊', status: 'online',
      model: 'AP7060DN', ip: '10.200.3.11',
      radio_2g: { status: 'up', channel: 1, tx_power_dbm: 20, users: 42, util_pct: 38 },
      radio_5g: { status: 'up', channel: 36, tx_power_dbm: 23, users: 88, util_pct: 52 },
      users_total: 130, rx_rssi_dbm: -48, noise_floor_dbm: -92, uptime_days: 142,
      interference_dbm: -75, client_types: { phone: 78, laptop: 38, iot: 10, other: 4 },
    },
    {
      id: 'ap-2', name: 'AP-F1-R02', location: '1F 西区会议室', status: 'online',
      model: 'AP7060DN', ip: '10.200.3.12',
      radio_2g: { status: 'up', channel: 6, tx_power_dbm: 20, users: 28, util_pct: 24 },
      radio_5g: { status: 'up', channel: 40, tx_power_dbm: 23, users: 64, util_pct: 71 },
      users_total: 92, rx_rssi_dbm: -55, noise_floor_dbm: -90, uptime_days: 142,
      interference_dbm: -68, client_types: { phone: 55, laptop: 30, iot: 5, other: 2 },
    },
    {
      id: 'ap-3', name: 'AP-F2-R01', location: '2F 开放办公区', status: 'online',
      model: 'AP4050DN', ip: '10.200.3.21',
      radio_2g: { status: 'up', channel: 11, tx_power_dbm: 18, users: 52, util_pct: 62 },
      radio_5g: { status: 'up', channel: 149, tx_power_dbm: 21, users: 96, util_pct: 83 },
      users_total: 148, rx_rssi_dbm: -52, noise_floor_dbm: -91, uptime_days: 98,
      interference_dbm: -64, client_types: { phone: 82, laptop: 52, iot: 8, other: 6 },
    },
    {
      id: 'ap-4', name: 'AP-F2-R02', location: '2F 经理办公室', status: 'online',
      model: 'AP4050DN', ip: '10.200.3.22',
      radio_2g: { status: 'down', channel: 0, tx_power_dbm: 0, users: 0, util_pct: 0 },
      radio_5g: { status: 'up', channel: 153, tx_power_dbm: 21, users: 44, util_pct: 45 },
      users_total: 44, rx_rssi_dbm: -61, noise_floor_dbm: -89, uptime_days: 98,
      interference_dbm: -80, client_types: { phone: 30, laptop: 12, iot: 2, other: 0 },
    },
    {
      id: 'ap-5', name: 'AP-F3-R01', location: '3F 研发实验室', status: 'online',
      model: 'AP7060DN', ip: '10.200.3.31',
      radio_2g: { status: 'up', channel: 1, tx_power_dbm: 20, users: 36, util_pct: 41 },
      radio_5g: { status: 'up', channel: 44, tx_power_dbm: 23, users: 72, util_pct: 66 },
      users_total: 108, rx_rssi_dbm: -50, noise_floor_dbm: -93, uptime_days: 76,
      interference_dbm: -72, client_types: { phone: 64, laptop: 34, iot: 6, other: 4 },
    },
    {
      id: 'ap-6', name: 'AP-F3-R02', location: '3F 休息区', status: 'offline',
      model: 'AP4050DN', ip: '10.200.3.32',
      radio_2g: { status: 'down', channel: 0, tx_power_dbm: 0, users: 0, util_pct: 0 },
      radio_5g: { status: 'down', channel: 0, tx_power_dbm: 0, users: 0, util_pct: 0 },
      users_total: 0, rx_rssi_dbm: -999, noise_floor_dbm: -95, uptime_days: 0,
      interference_dbm: -95, client_types: { phone: 0, laptop: 0, iot: 0, other: 0 },
    },
  ]

  // ── Heatmap: floor (y) × zone (x), value = avg RSSI of AP in that cell ──
  const zones = ['西区', '中区', '东区']
  const floors = ['1F', '2F', '3F']
  // Place each online AP into a floor/zone cell with its RSSI
  const cellMap: Record<string, number[]> = {}
  const placement: Record<string, [string, string]> = {
    'AP-F1-R01': ['1F', '东区'], 'AP-F1-R02': ['1F', '西区'],
    'AP-F2-R01': ['2F', '东区'], 'AP-F2-R02': ['2F', '西区'],
    'AP-F3-R01': ['3F', '东区'], 'AP-F3-R02': ['3F', '西区'],
  }
  aps.forEach((ap) => {
    const cell = placement[ap.name]
    if (cell && ap.status === 'online' && ap.rx_rssi_dbm > -900) {
      const key = cell[0] + '|' + cell[1]
      if (!cellMap[key]) cellMap[key] = []
      cellMap[key].push(ap.rx_rssi_dbm)
    }
  })
  const heatValues: number[][] = floors.map((f) =>
    zones.map((z) => {
      const arr = cellMap[f + '|' + z]
      if (!arr || !arr.length) return -95 // no signal
      return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length)
    }),
  )
  const heatmapData: HeatmapData = { xLabels: zones, yLabels: floors, values: heatValues }

  // ── Client type distribution ──
  let phone = 0, laptop = 0, iot = 0, other = 0
  aps.forEach((ap) => {
    phone += ap.client_types.phone
    laptop += ap.client_types.laptop
    iot += ap.client_types.iot
    other += ap.client_types.other
  })
  const clientDist = [
    { name: tl('手机'), value: phone, color: '#22d3ee' },
    { name: tl('笔记本'), value: laptop, color: '#3b82f6' },
    { name: tl('IoT 设备'), value: iot, color: '#a855f7' },
    { name: tl('其他'), value: other, color: '#f59e0b' },
  ]

  // ── Band stats (2.4G / 5G) ──
  const bandStats: BandStat[] = [
    {
      band: '2.4G',
      aps: aps.filter((a) => a.radio_2g.status === 'up').length,
      users: aps.reduce((a, x) => a + x.radio_2g.users, 0),
      util: Math.round(aps.reduce((a, x) => a + x.radio_2g.util_pct, 0) / Math.max(1, aps.length)),
    },
    {
      band: '5G',
      aps: aps.filter((a) => a.radio_5g.status === 'up').length,
      users: aps.reduce((a, x) => a + x.radio_5g.users, 0),
      util: Math.round(aps.reduce((a, x) => a + x.radio_5g.util_pct, 0) / Math.max(1, aps.length)),
    },
  ]

  // ── Channel interference (2.4G channels) ──
  const channelData = [
    { channel: '1', util: 38, interference: 12 },
    { channel: '6', util: 24, interference: 8 },
    { channel: '11', util: 62, interference: 35 },
    { channel: '36', util: 52, interference: 14 },
    { channel: '40', util: 71, interference: 28 },
    { channel: '44', util: 66, interference: 22 },
    { channel: '149', util: 83, interference: 41 },
    { channel: '153', util: 45, interference: 11 },
  ]
  const highInterference = channelData.filter((c) => c.interference > 30).length

  // ── AP rows for DeviceTable ──
  const apRows: ApRow[] = aps.map((ap) => ({
    name: ap.name,
    status: ap.status === 'online' ? 'online' : 'offline',
    users: ap.users_total,
    channel: ap.radio_5g.status === 'up' ? String(ap.radio_5g.channel) : (ap.radio_2g.status === 'up' ? String(ap.radio_2g.channel) : '-'),
    traffic: fmtBps((ap.radio_2g.util_pct + ap.radio_5g.util_pct) * 50e6 / 100),
    _rowClass: ap.status === 'offline' ? 'row-danger' : '',
  }))

  const online = aps.filter((a) => a.status === 'online').length
  const totalUsers = aps.reduce((a, x) => a + x.users_total, 0)
  const onlineRssi = aps.filter((a) => a.rx_rssi_dbm > -900).map((a) => a.rx_rssi_dbm)
  const avgRssi = onlineRssi.length ? Math.round(onlineRssi.reduce((a, b) => a + b, 0) / onlineRssi.length) : 0

  return {
    aps, heatmapData, clientDist, bandStats, channelData, highInterference, apRows,
    total: aps.length, online, totalUsers, avgRssi,
    onlinePercent: aps.length ? Number(((online / aps.length) * 100).toFixed(1)) : 0,
  }
}

// ──────────────────────────────────────────
// Apply data to reactive state
// ──────────────────────────────────────────
function applyData(d: ReturnType<typeof mockData>) {
  s.aps = d.aps
  s.heatmapData = d.heatmapData
  s.clientDist = d.clientDist
  s.bandStats = d.bandStats
  s.channelData = d.channelData
  s.highInterference = d.highInterference
  s.apRows = d.apRows
  s.total = d.total
  s.online = d.online
  s.totalUsers = d.totalUsers
  s.avgRssi = d.avgRssi
  s.onlinePercent = d.onlinePercent
  updatePie(d.clientDist)
  updateChannel(d.channelData)
}

// ──────────────────────────────────────────
// Build from API data
// ──────────────────────────────────────────
function fromApi(summary: NetworkWirelessSummary) {
  if (summary.aps?.length) {
    // Extend with mock-only fields (API doesn't provide them)
    const mock = mockData()
    const aps: WirelessEx[] = summary.aps.map((ap, i) => ({
      ...ap,
      interference_dbm: mock.aps[i]?.interference_dbm ?? -80,
      client_types: mock.aps[i]?.client_types ?? { phone: 0, laptop: 0, iot: 0, other: 0 },
    }))
    // Recompute aggregates from real AP list but keep mock-derived viz data
    const total = summary.total || aps.length
    const online = summary.online || aps.filter((a) => a.status === 'online').length
    const totalUsers = summary.users ?? aps.reduce((a, x) => a + x.users_total, 0)
    const avgRssi = summary.avgRssi ?? Math.round(aps.filter((a) => a.rx_rssi_dbm > -900).reduce((a, b) => a + b.rx_rssi_dbm, 0) / Math.max(1, aps.filter((a) => a.rx_rssi_dbm > -900).length))
    const apRows: ApRow[] = aps.map((ap) => ({
      name: ap.name,
      status: ap.status === 'online' ? 'online' : 'offline',
      users: ap.users_total,
      channel: ap.radio_5g.status === 'up' ? String(ap.radio_5g.channel) : (ap.radio_2g.status === 'up' ? String(ap.radio_2g.channel) : '-'),
      traffic: fmtBps((ap.radio_2g.util_pct + ap.radio_5g.util_pct) * 50e6 / 100),
      _rowClass: ap.status === 'offline' ? 'row-danger' : '',
    }))
    s.aps = aps
    s.heatmapData = mock.heatmapData
    s.clientDist = mock.clientDist
    s.bandStats = mock.bandStats
    s.channelData = mock.channelData
    s.highInterference = mock.highInterference
    s.apRows = apRows
    s.total = total
    s.online = online
    s.totalUsers = totalUsers
    s.avgRssi = avgRssi
    s.onlinePercent = total ? Number(((online / total) * 100).toFixed(1)) : 0
    updatePie(mock.clientDist)
    updateChannel(mock.channelData)
  } else {
    applyData(mockData())
  }
}

// ──────────────────────────────────────────
// Update charts
// ──────────────────────────────────────────
function updatePie(dist: { name: string; value: number; color: string }[]) {
  ;(clientPieOption.series as echarts.SeriesOption[])[0].data = dist
    .filter((d) => d.value > 0)
    .map((d) => ({ name: d.name, value: d.value, itemStyle: { color: d.color } }))
}

function updateChannel(data: { channel: string; util: number; interference: number }[]) {
  ;(channelChartOption.xAxis as { data?: unknown }).data = data.map((d) => d.channel)
  ;(channelChartOption.series as echarts.SeriesOption[])[0].data = data.map((d) => d.util)
  ;(channelChartOption.series as echarts.SeriesOption[])[1].data = data.map((d) => d.interference)
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const data = await getNetworkWirelessDetailed()
    if (data && (data.aps?.length || data.total || data.users)) {
      fromApi(data)
      markPartial('干扰值 / 终端类型 / 热力图 / 信道分布由本地生成，后端未提供')
    } else {
      applyData(mockData())
      markFull()
    }
  } catch (e: unknown) {
    error.value = toErrorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* ── view-head ── */
.view-head { margin-bottom: 16px; }
.view-head h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary, #e5e7eb);
  margin: 0;
}
.view-head .sub {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-top: 2px;
  display: block;
}

/* ── grid ── */
.grid { display: grid; gap: 14px; }
.grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.grid.cols-2 { grid-template-columns: repeat(2, 1fr); }

/* pill 已由全局 .moni-card/.pill 体系提供 */

/* ── band grid ── */
.band-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.band-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 14px;
}
.band-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.band-name { font-size: 0.9375rem; font-weight: 700; color: var(--text-primary, #e5e7eb); }
.band-count { font-size: 0.6875rem; color: var(--text-muted, #6b7280); }
.band-users { display: flex; align-items: baseline; gap: 6px; margin-bottom: 8px; }
.band-users-val { font-size: 1.375rem; font-weight: 700; color: var(--cyan, #22d3ee); }
.band-users-lbl { font-size: 0.6875rem; color: var(--text-muted, #6b7280); }
.band-bar {
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
  margin-bottom: 6px;
}
.band-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.band-fill.g { background: linear-gradient(90deg, #22c55e, #4ade80); }
.band-fill.a { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.band-meta { font-size: 0.6875rem; }

/* ── device meta grid (per AP) ── */
.rt-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px 24px;
}
.rt-kv {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px dotted rgba(51, 65, 85, 0.5);
}
.rt-k { font-size: 0.6875rem; color: var(--text-muted, #6b7280); }
.rt-v {
  font-size: 0.7875rem;
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}

/* ── radio grid (per AP) ── */
.radio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 10px;
}
.radio-block {
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.6);
}
.radio-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.d-name { font-size: 0.8125rem; font-weight: 600; color: var(--text-primary, #e5e7eb); }
.radio-meta {
  display: grid;
  grid-template-columns: auto auto;
  gap: 2px 10px;
  font-size: 0.6875rem;
  margin-bottom: 6px;
}
.radio-meta .muted { color: var(--text-muted, #6b7280); }
.radio-meta .mono { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }
.radio-bar {
  height: 8px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.radio-fill { display: block; height: 100%; border-radius: 3px; }
.radio-fill.g { background: linear-gradient(90deg, rgba(43, 212, 122, 0.5), rgba(43, 212, 122, 0.85)); }
.radio-fill.a { background: linear-gradient(90deg, rgba(255, 176, 32, 0.5), rgba(255, 176, 32, 0.85)); }

/* ── utility ── */
.mono { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }
.fw4 { font-weight: 400; }
.f11 { font-size: 0.6875rem; }
.ml2 { margin-left: 4px; }
.a-text { color: #f59e0b; }
.g-text { color: #22c55e; }

/* ── Error / Empty ── */
.err-card { text-align: center; padding: 32px 16px; }
.err-title { font-size: 1rem; font-weight: 700; color: #ef4444; margin-bottom: 8px; }
.err-detail { font-size: 0.75rem; color: var(--text-muted, #6b7280); margin-bottom: 14px; }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 18px;
  border-radius: 6px;
  border: 1px solid var(--border, #334155);
  background: transparent;
  color: var(--text-primary, #e5e7eb);
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}
.btn:hover { background: rgba(255, 255, 255, 0.05); }
.empty-card { text-align: center; padding: 40px 16px; }

/* ── Responsive ── */
@media (max-width: 1100px) {
  .grid.cols-4 { grid-template-columns: repeat(2, 1fr); }
  .grid.cols-2 { grid-template-columns: 1fr; }
  .band-grid { grid-template-columns: 1fr; }
  .rt-meta-grid { grid-template-columns: 1fr 1fr; }
  .radio-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .grid.cols-4 { grid-template-columns: 1fr; }
  .rt-meta-grid { grid-template-columns: 1fr; }
}
</style>
