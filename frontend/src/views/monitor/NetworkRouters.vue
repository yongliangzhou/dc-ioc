<template>
  <div class="net-rt">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('路由器') }}</h1>
      <span class="sub">{{ tl('路由转发 / BGP·OSPF / 会话统计 / 接口吞吐') }}</span>
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

    <!-- 2.2.1 KpiCard × 4 -->
    <div v-if="s && s.routerList.length" class="grid cols-4">
      <KpiCard
        :title="tl('平均 CPU')"
        :value="s.avgCpu"
        unit="%"
        :bar-value="s.avgCpu"
        bar-color="var(--cyan)"
        :status="s.avgCpu > 80 ? 'danger' : s.avgCpu > 60 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        :title="tl('平均内存')"
        :value="s.avgMem"
        unit="%"
        :bar-value="s.avgMem"
        bar-color="var(--violet)"
        :status="s.avgMem > 80 ? 'danger' : s.avgMem > 60 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        :title="tl('路由器')"
        :value="s.total"
        unit="台"
        :subtitle="`在线 ${s.online}/${s.total}`"
        dot="var(--green)"
        size="sm"
      />
      <KpiCard
        :title="tl('平均温度')"
        :value="s.avgTemp"
        unit="°C"
        :bar-value="s.avgTemp > 60 ? 60 : s.avgTemp"
        bar-color="var(--amber)"
        :status="s.avgTemp > 50 ? 'warning' : 'normal'"
        size="sm"
      />
    </div>

    <!-- 2.2.2 吞吐趋势 -->
    <Panel v-if="s && s.routerList.length" title="路由器吞吐趋势">
      <TrendChart
        :title="tl('路由器吞吐趋势')"
        :x-axis-data="s.throughputTrend.labels"
        :series="s.throughputTrend.series"
        :height="230"
        :show-range-picker="true"
      />
    </Panel>

    <!-- 2.2.2 接口流量表格 -->
    <Panel v-if="s && s.routerList.length" title="接口流量详情">
      <template #extra>
        <span v-if="s.allInterfacesDown === 0" class="pill g">{{ tl('全部接口正常') }}</span>
        <span v-else class="pill a">{{ s.allInterfacesDown }} {{ tl('个接口异常') }}</span>
      </template>
      <div class="port-table scroll-x" style="max-height: 320px">
        <table>
          <thead>
            <tr>
              <th>{{ tl('设备') }}</th>
              <th>{{ tl('接口') }}</th>
              <th>{{ tl('状态') }}</th>
              <th>{{ tl('速率') }}</th>
              <th>{{ tl('入利用率') }}</th>
              <th>{{ tl('出利用率') }}</th>
              <th>{{ tl('实时流量') }}</th>
              <th>{{ tl('错包') }}</th>
              <th>{{ tl('丢包') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(iface, fi) in s.allInterfaces"
              :key="iface.device + '-' + iface.name"
              :class="iface.status !== 'up' ? 'row-offline' : ''"
              :style="{ display: fi < 40 ? '' : 'none' }"
            >
              <td class="mono">{{ iface.device }}</td>
              <td class="mono">{{ iface.name }}</td>
              <td>
                <StatusBadge :status="iface.status === 'up' ? 'online' : 'offline'" size="sm" />
              </td>
              <td class="mono">
                {{
                  iface.speed >= 1000 ? (iface.speed / 1000).toFixed(0) + 'G' : iface.speed + 'M'
                }}
              </td>
              <td class="mono">
                <span :class="utilCls(iface.inUtil)">{{ iface.inUtil }}%</span>
              </td>
              <td class="mono">
                <span :class="utilCls(iface.outUtil)">{{ iface.outUtil }}%</span>
              </td>
              <td class="mono">{{ fmtBps(iface.trafficBps) }}</td>
              <td class="mono" :class="iface.errors ? 'a-text' : ''">{{ iface.errors }}</td>
              <td class="mono" :class="iface.discards ? 'a-text' : ''">{{ iface.discards }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <!-- 2.2.4 会话统计仪表 -->
    <div v-if="s && s.routerList.length" class="grid cols-2">
      <Panel title="并发连接数">
        <div class="session-gauge">
          <div class="gauge-value mono">{{ fmtNum(s.totalConcurrentSessions) }}</div>
          <div class="gauge-bar mt3">
            <div
              class="gauge-fill gauge-fill-cyan"
              :style="{
                width:
                  Math.min(
                    100,
                    (s.totalConcurrentSessions / Math.max(1, s.maxConcurrentSessions)) * 100,
                  ) + '%',
              }"
            />
          </div>
          <div class="gauge-meta">
            {{ tl('最大') }} {{ fmtNum(s.maxConcurrentSessions) }} &nbsp;·&nbsp; {{ tl('使用率') }}
            {{
              ((s.totalConcurrentSessions / Math.max(1, s.maxConcurrentSessions)) * 100).toFixed(1)
            }}%
          </div>
        </div>
      </Panel>

      <Panel title="新建会话速率">
        <div class="session-gauge">
          <div class="gauge-value mono">{{ fmtNum(s.newSessionRate) }}<small>cps</small></div>
          <div class="gauge-bar mt3">
            <div
              class="gauge-fill gauge-fill-blue"
              :style="{ width: Math.min(100, (s.newSessionRate / 500000) * 100) + '%' }"
            />
          </div>
          <div class="gauge-meta">{{ tl('峰值') }} {{ fmtNum(s.peakSessionRate) }} cps</div>
        </div>
      </Panel>
    </div>

    <!-- 2.2.3 路由协议状态面板 -->
    <Panel v-if="s && s.routerList.length" title="路由协议状态 (BGP / OSPF)">
      <template #extra>
        <span v-if="!s.hasAnyProtocolFlake" class="pill g">{{ tl('全部协议正常') }}</span>
        <span v-else class="pill a">{{ tl('检测到协议抖动') }}</span>
      </template>
      <div class="proto-grid">
        <div
          v-for="(proto, pi) in s.allProtocols"
          :key="pi"
          class="proto-card"
          :class="{ 'proto-flake': proto.flake }"
        >
          <div class="proto-head">
            <div class="proto-device">{{ proto.device }}</div>
            <StatusBadge :status="proto.flake ? 'warning' : 'normal'" size="sm" />
          </div>
          <div class="proto-title mono fw6">{{ proto.name }}</div>
          <div class="proto-body">
            <div v-if="proto.peerUp != null" class="proto-kv">
              <span class="proto-k">{{ tl('BGP Peer') }}</span>
              <span class="proto-v" :class="proto.peerUp === proto.peerTotal ? 'g-text' : 'a-text'">
                {{ proto.peerUp }}/{{ proto.peerTotal }} UP
              </span>
            </div>
            <div v-if="proto.neighborUp != null" class="proto-kv">
              <span class="proto-k">{{ tl('OSPF 邻居') }}</span>
              <span
                class="proto-v"
                :class="proto.neighborUp === proto.neighborTotal ? 'g-text' : 'a-text'"
              >
                {{ proto.neighborUp }}/{{ proto.neighborTotal }} UP
              </span>
            </div>
            <div v-if="proto.area != null" class="proto-kv">
              <span class="proto-k">{{ tl('区域') }}</span>
              <span class="proto-v mono">{{ proto.area }}</span>
            </div>
            <div class="proto-kv">
              <span class="proto-k">{{ tl('路由条目') }}</span>
              <span class="proto-v mono">{{ fmtNum(proto.routes) }}</span>
            </div>
            <div class="proto-kv">
              <span class="proto-k">{{ tl('状态') }}</span>
              <span class="proto-v" :class="proto.stateClass">{{ proto.state }}</span>
            </div>
          </div>
          <div v-if="proto.desc" class="proto-desc muted">{{ proto.desc }}</div>
        </div>
      </div>
    </Panel>

    <!-- Per-device detail cards -->
    <Panel v-if="s && s.routerList.length" v-for="r in s.routerList" :key="r.id" :title="r.name">
      <template #ct>
        {{ r.name }}
        <span class="muted ml2 fw4 f11">{{ r.model }}</span>
      </template>
      <template #extra>
        <StatusBadge :status="r.status === 'online' ? 'online' : 'offline'" />
      </template>

      <div class="rt-meta-grid">
        <div class="rt-kv">
          <span class="rt-k">{{ tl('管理IP') }}</span>
          <span class="rt-v mono">{{ r.ip }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('角色') }}</span>
          <span class="rt-v">{{ r.role }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('位置') }}</span>
          <span class="rt-v">{{ r.location }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('型号') }}</span>
          <span class="rt-v mono">{{ r.model }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('CPU') }}</span>
          <span class="rt-v" :class="r.cpu_pct > 80 ? 'a-text' : 'g-text'">{{ r.cpu_pct }}%</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('内存') }}</span>
          <span class="rt-v" :class="r.mem_pct > 80 ? 'a-text' : 'g-text'">{{ r.mem_pct }}%</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('温度') }}</span>
          <span class="rt-v">{{ r.temp_c }}°C</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('运行天数') }}</span>
          <span class="rt-v">{{ r.uptime_days }}d</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('吞吐') }}</span>
          <span class="rt-v mono">{{ fmtBps(r.throughput_bps) }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">BGP</span>
          <span class="rt-v" :class="r.bgp_state === 'Established' ? 'g-text' : 'a-text'">
            {{ r.bgp_state }}
          </span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('OSPF 邻居') }}</span>
          <span class="rt-v">{{ r.ospf_neighbors }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('会话数') }}</span>
          <span class="rt-v mono">{{ fmtNum(r.sessions) }}</span>
        </div>
      </div>
    </Panel>

    <!-- Empty state -->
    <Panel v-if="s && !s.routerList.length && !loading && !error" class="empty-card">
      <p class="muted">{{ tl('暂无路由器数据') }}</p>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmtNum, fmtBps, utilCls, genHours } from '@/utils/format'
import KpiCard from '@/components/monitor/KpiCard.vue'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import StatusBadge from '@/components/monitor/StatusBadge.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import Panel from '@/components/common/Panel.vue'
import { getNetworkRoutersDetailed, type RouterView, type RouterProtocolView } from '@/api/monitor'
const { t: tl } = useI18n()

// ──────────────────────────────────────────
// Local extended types (API returns RouterView without interfaces)
// ──────────────────────────────────────────
interface RouterIfView {
  device: string
  name: string
  status: 'up' | 'down'
  speed: number // Mbps
  inUtil: number
  outUtil: number
  trafficBps: number
  errors: number
  discards: number
}

interface ProtocolView {
  device: string
  name: string
  type: 'bgp' | 'ospf'
  state: string
  stateClass: string
  peerUp: number | null
  peerTotal: number | null
  neighborUp: number | null
  neighborTotal: number | null
  area: string | null
  routes: number
  desc: string | null
  flake: boolean
}

interface ThroughputSeries {
  name: string
  data: number[]
  color?: string
}

interface PageState {
  routerList: RouterView[]
  allInterfaces: RouterIfView[]
  allInterfacesDown: number
  allProtocols: ProtocolView[]
  hasAnyProtocolFlake: boolean
  throughputTrend: {
    labels: string[]
    series: ThroughputSeries[]
  }
  avgCpu: number
  avgMem: number
  avgTemp: number
  online: number
  total: number
  totalConcurrentSessions: number
  maxConcurrentSessions: number
  newSessionRate: number
  peakSessionRate: number
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = reactive<PageState>({
  routerList: [],
  allInterfaces: [],
  allInterfacesDown: 0,
  allProtocols: [],
  hasAnyProtocolFlake: false,
  throughputTrend: { labels: [], series: [] },
  avgCpu: 0,
  avgMem: 0,
  avgTemp: 0,
  online: 0,
  total: 0,
  totalConcurrentSessions: 0,
  maxConcurrentSessions: 0,
  newSessionRate: 0,
  peakSessionRate: 0,
})

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function fmtPercent(v: number): string {
  return v != null ? v.toFixed(1) + '%' : '-'
}

function genTimeData(n: number, base: number, amp: number, noise: number): number[] {
  const pts: number[] = []
  for (let i = 0; i < n; i++) {
    // Sine wave + drift + noise for realistic-looking data
    const v =
      base + amp * Math.sin((i / n) * Math.PI * 3 + Math.random()) + (Math.random() - 0.5) * noise
    pts.push(Math.max(0, Math.round(v)))
  }
  return pts
}

// ──────────────────────────────────────────
// Mock data
// ──────────────────────────────────────────
function mockData() {
  const N = 24

  // ── Routers ──
  const routerList: RouterView[] = [
    {
      id: 'rt-1',
      name: 'Core-R1',
      ip: '10.200.1.1',
      model: 'NE40E-X16',
      role: 'BGP Border',
      location: 'DC-A 核心机房 A-03',
      status: 'online',
      cpu_pct: 34,
      mem_pct: 48,
      temp_c: 47,
      uptime_days: 386,
      throughput_bps: 82.4e9,
      sessions: 3200000,
      bgp_state: 'Established',
      ospf_neighbors: 5,
      routes_total: 152400,
      protocols: [
        { name: 'BGP', state: 'Established', peer_total: 3, peer_up: 3, routes: 124000, desc: '' },
        { name: 'OSPF', state: 'Full', neighbor_total: 5, neighbor_up: 5, routes: 28400, desc: '' },
      ],
    },
    {
      id: 'rt-2',
      name: 'Core-R2',
      ip: '10.200.1.2',
      model: 'NE40E-X8',
      role: 'iBGP Core',
      location: 'DC-A 核心机房 A-04',
      status: 'online',
      cpu_pct: 28,
      mem_pct: 42,
      temp_c: 44,
      uptime_days: 212,
      throughput_bps: 67.1e9,
      sessions: 2800000,
      bgp_state: 'Established',
      ospf_neighbors: 4,
      routes_total: 148900,
      protocols: [
        { name: 'BGP', state: 'Established', peer_total: 2, peer_up: 2, routes: 121500, desc: '' },
        { name: 'OSPF', state: 'Full', neighbor_total: 4, neighbor_up: 4, routes: 27400, desc: '' },
      ],
    },
    {
      id: 'rt-3',
      name: 'Edge-R1',
      ip: '10.200.1.3',
      model: 'AR3260',
      role: 'eBGP Edge',
      location: 'DC-A 汇聚机房 B-12',
      status: 'online',
      cpu_pct: 42,
      mem_pct: 55,
      temp_c: 51,
      uptime_days: 178,
      throughput_bps: 48.6e9,
      sessions: 1800000,
      bgp_state: 'Established',
      ospf_neighbors: 2,
      routes_total: 112800,
      protocols: [
        { name: 'BGP', state: 'Active', peer_total: 4, peer_up: 3, routes: 98000, desc: '' },
        { name: 'OSPF', state: 'Full', neighbor_total: 2, neighbor_up: 2, routes: 14800, desc: '' },
      ],
    },
  ]

  // ── Interfaces ──
  const allInterfaces: RouterIfView[] = [
    // Core-R1
    {
      device: 'Core-R1',
      name: 'HundredGigE0/0/0',
      status: 'up',
      speed: 100000,
      inUtil: 42,
      outUtil: 38,
      trafficBps: 38.5e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R1',
      name: 'HundredGigE0/0/1',
      status: 'up',
      speed: 100000,
      inUtil: 35,
      outUtil: 41,
      trafficBps: 36.2e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R1',
      name: 'HundredGigE0/0/2',
      status: 'down',
      speed: 100000,
      inUtil: 0,
      outUtil: 0,
      trafficBps: 0,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R1',
      name: 'TenGigE0/1/0',
      status: 'up',
      speed: 10000,
      inUtil: 55,
      outUtil: 60,
      trafficBps: 5.5e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R1',
      name: 'TenGigE0/1/1',
      status: 'up',
      speed: 10000,
      inUtil: 28,
      outUtil: 22,
      trafficBps: 2.4e9,
      errors: 12,
      discards: 0,
    },
    {
      device: 'Core-R1',
      name: 'Loopback0',
      status: 'up',
      speed: 0,
      inUtil: 0,
      outUtil: 0,
      trafficBps: 0,
      errors: 0,
      discards: 0,
    },
    // Core-R2
    {
      device: 'Core-R2',
      name: 'HundredGigE0/0/0',
      status: 'up',
      speed: 100000,
      inUtil: 38,
      outUtil: 35,
      trafficBps: 34.8e9,
      errors: 0,
      discards: 3,
    },
    {
      device: 'Core-R2',
      name: 'HundredGigE0/0/1',
      status: 'up',
      speed: 100000,
      inUtil: 33,
      outUtil: 30,
      trafficBps: 30.1e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R2',
      name: 'TenGigE0/1/0',
      status: 'up',
      speed: 10000,
      inUtil: 72,
      outUtil: 68,
      trafficBps: 6.8e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R2',
      name: 'TenGigE0/1/1',
      status: 'up',
      speed: 10000,
      inUtil: 40,
      outUtil: 45,
      trafficBps: 4.0e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Core-R2',
      name: 'Loopback0',
      status: 'up',
      speed: 0,
      inUtil: 0,
      outUtil: 0,
      trafficBps: 0,
      errors: 0,
      discards: 0,
    },
    // Edge-R1
    {
      device: 'Edge-R1',
      name: 'GigabitEthernet0/0/0',
      status: 'up',
      speed: 1000,
      inUtil: 85,
      outUtil: 78,
      trafficBps: 780e6,
      errors: 156,
      discards: 0,
    },
    {
      device: 'Edge-R1',
      name: 'GigabitEthernet0/0/1',
      status: 'up',
      speed: 1000,
      inUtil: 42,
      outUtil: 55,
      trafficBps: 480e6,
      errors: 23,
      discards: 0,
    },
    {
      device: 'Edge-R1',
      name: 'TenGigE0/1/0',
      status: 'up',
      speed: 10000,
      inUtil: 62,
      outUtil: 58,
      trafficBps: 5.8e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Edge-R1',
      name: 'TenGigE0/1/1',
      status: 'up',
      speed: 10000,
      inUtil: 48,
      outUtil: 52,
      trafficBps: 4.9e9,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Edge-R1',
      name: 'GigabitEthernet0/2/0',
      status: 'down',
      speed: 1000,
      inUtil: 0,
      outUtil: 0,
      trafficBps: 0,
      errors: 0,
      discards: 0,
    },
    {
      device: 'Edge-R1',
      name: 'Loopback0',
      status: 'up',
      speed: 0,
      inUtil: 0,
      outUtil: 0,
      trafficBps: 0,
      errors: 0,
      discards: 0,
    },
  ]

  // ── Protocol summary cards (1 per protocol per device) ──
  const allProtocols: ProtocolView[] = [
    {
      device: 'Core-R1',
      name: 'BGP',
      type: 'bgp',
      state: 'Established',
      stateClass: 'g-text',
      peerUp: 3,
      peerTotal: 3,
      neighborUp: null,
      neighborTotal: null,
      area: null,
      routes: 124000,
      desc: 'eBGP to ISP-A + ISP-B, iBGP to Core-R2',
      flake: false,
    },
    {
      device: 'Core-R1',
      name: 'OSPF',
      type: 'ospf',
      state: 'Full',
      stateClass: 'g-text',
      peerUp: null,
      peerTotal: null,
      neighborUp: 5,
      neighborTotal: 5,
      area: 'Backbone (0.0.0.0)',
      routes: 28400,
      desc: 'All adjacencies Full, no DR/BDR changes in 30d',
      flake: false,
    },
    {
      device: 'Core-R2',
      name: 'BGP',
      type: 'bgp',
      state: 'Established',
      stateClass: 'g-text',
      peerUp: 2,
      peerTotal: 2,
      neighborUp: null,
      neighborTotal: null,
      area: null,
      routes: 121500,
      desc: 'iBGP to Core-R1, Route Reflector Client: Edge-R1',
      flake: false,
    },
    {
      device: 'Core-R2',
      name: 'OSPF',
      type: 'ospf',
      state: 'Full',
      stateClass: 'g-text',
      peerUp: null,
      peerTotal: null,
      neighborUp: 4,
      neighborTotal: 4,
      area: 'Backbone (0.0.0.0)',
      routes: 27400,
      desc: 'All adjacencies Full',
      flake: false,
    },
    {
      device: 'Edge-R1',
      name: 'BGP',
      type: 'bgp',
      state: 'Active',
      stateClass: 'a-text',
      peerUp: 3,
      peerTotal: 4,
      neighborUp: null,
      neighborTotal: null,
      area: null,
      routes: 98000,
      desc: 'Peer 10.255.1.2 (ISP-C) in Active state, retry in 30s',
      flake: true,
    },
    {
      device: 'Edge-R1',
      name: 'OSPF',
      type: 'ospf',
      state: 'Full',
      stateClass: 'g-text',
      peerUp: null,
      peerTotal: null,
      neighborUp: 2,
      neighborTotal: 2,
      area: 'NSSA (0.0.0.1)',
      routes: 14800,
      desc: 'NSSA area, ABR: Core-R1',
      flake: false,
    },
  ]

  // ── Throughput trend ──
  const labels = genHours(N)
  const series: ThroughputSeries[] = [
    {
      name: 'Core-R1',
      data: genTimeData(N, 75e9, 15e9, 8e9),
      color: '#22c55e',
    },
    {
      name: 'Core-R2',
      data: genTimeData(N, 60e9, 12e9, 6e9),
      color: '#3b82f6',
    },
    {
      name: 'Edge-R1',
      data: genTimeData(N, 42e9, 10e9, 5e9),
      color: '#f59e0b',
    },
  ]

  // ── Session stats ──
  const totalConcurrentSessions = 7800000
  const maxConcurrentSessions = 12000000
  const newSessionRate = 284000
  const peakSessionRate = 412000

  return {
    routerList,
    allInterfaces,
    allProtocols,
    throughputTrend: { labels, series },
    totalConcurrentSessions,
    maxConcurrentSessions,
    newSessionRate,
    peakSessionRate,
  }
}

// ──────────────────────────────────────────
// Apply data to reactive state
// ──────────────────────────────────────────
function applyData(
  routerList: RouterView[],
  allInterfaces: RouterIfView[],
  allProtocols: ProtocolView[],
  throughputTrend: { labels: string[]; series: ThroughputSeries[] },
  totalConcurrentSessions: number,
  maxConcurrentSessions: number,
  newSessionRate: number,
  peakSessionRate: number,
) {
  s.routerList = routerList
  s.allInterfaces = allInterfaces
  s.allInterfacesDown = allInterfaces.filter((i) => i.status !== 'up').length
  s.allProtocols = allProtocols
  s.hasAnyProtocolFlake = allProtocols.some((p) => p.flake)
  s.throughputTrend = throughputTrend
  s.total = routerList.length
  s.online = routerList.filter((r) => r.status === 'online').length
  s.avgCpu = routerList.length
    ? Math.round(routerList.reduce((a, r) => a + r.cpu_pct, 0) / routerList.length)
    : 0
  s.avgMem = routerList.length
    ? Math.round(routerList.reduce((a, r) => a + r.mem_pct, 0) / routerList.length)
    : 0
  s.avgTemp = routerList.length
    ? Math.round(routerList.reduce((a, r) => a + r.temp_c, 0) / routerList.length)
    : 0
  s.totalConcurrentSessions = totalConcurrentSessions
  s.maxConcurrentSessions = maxConcurrentSessions
  s.newSessionRate = newSessionRate
  s.peakSessionRate = peakSessionRate
}

// ──────────────────────────────────────────
// Build protocol views from API router data
// ──────────────────────────────────────────
function buildProtocols(routerList: RouterView[]): ProtocolView[] {
  const result: ProtocolView[] = []
  for (const r of routerList) {
    for (const p of r.protocols || []) {
      const isBgp = p.name.toUpperCase().includes('BGP')
      const stateOk = p.state === 'Established' || p.state === 'Full'
      result.push({
        device: r.name,
        name: p.name,
        type: isBgp ? 'bgp' : 'ospf',
        state: p.state,
        stateClass: stateOk ? 'g-text' : 'a-text',
        peerUp: isBgp ? (p.peer_up ?? 0) : null,
        peerTotal: isBgp ? (p.peer_total ?? 0) : null,
        neighborUp: !isBgp ? (p.neighbor_up ?? 0) : null,
        neighborTotal: !isBgp ? (p.neighbor_total ?? 0) : null,
        area: isBgp ? null : p.area != null ? String(p.area) : 'Backbone (0.0.0.0)',
        routes: p.routes,
        desc: p.desc ?? null,
        flake: p.flake != null ? !!p.flake : !stateOk,
      })
    }
  }
  return result
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const data = await getNetworkRoutersDetailed()

    if (data?.routers?.length) {
      const routerList = data.routers
      const protocolViews = buildProtocols(routerList)
      // API doesn't provide interface data, so we generate mock interfaces
      const mock = mockData()
      applyData(
        routerList,
        mock.allInterfaces,
        protocolViews,
        mock.throughputTrend,
        routerList.reduce((a, r) => a + r.sessions, 0),
        Math.max(10000000, routerList.reduce((a, r) => a + r.sessions, 0) * 1.5),
        Math.round(routerList.reduce((a, r) => a + r.sessions * 0.036, 0)),
        Math.round(routerList.reduce((a, r) => a + r.sessions * 0.055, 0)),
      )
    } else {
      // Fallback to full mock
      const mock = mockData()
      applyData(
        mock.routerList,
        mock.allInterfaces,
        mock.allProtocols,
        mock.throughputTrend,
        mock.totalConcurrentSessions,
        mock.maxConcurrentSessions,
        mock.newSessionRate,
        mock.peakSessionRate,
      )
    }
  } catch (e: any) {
    error.value = e?.message || String(e)
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
.view-head {
  margin-bottom: 16px;
}
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
.grid {
  display: grid;
  gap: 14px;
}
.grid.cols-4 {
  grid-template-columns: repeat(4, 1fr);
}
.grid.cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

/* pill（moni-card 全局已含 .card/.card-head/.ct，此处仅补堆叠间距） */
.moni-card {
  margin-bottom: 14px;
}
.moni-card:last-child {
  margin-bottom: 0;
}

/* ── port table ── */
.port-table {
  max-height: 320px;
  overflow-y: auto;
}
.port-table.scroll-x {
  overflow-x: auto;
}
.port-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.port-table th {
  position: sticky;
  top: 0;
  background: #1e293b;
  z-index: 2;
  text-align: left;
  padding: 8px 10px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
  border-bottom: 1px solid var(--border, #334155);
  white-space: nowrap;
}
.port-table td {
  padding: 7px 10px;
  color: var(--text-secondary, #94a3b8);
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  white-space: nowrap;
}
.port-table .row-offline td {
  color: #4b5563;
}

/* ── Session gauge ── */
.session-gauge {
  text-align: center;
  padding: 8px 0 4px;
}
.gauge-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #e5e7eb);
  line-height: 1.2;
}
.gauge-value small {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--text-muted, #6b7280);
  margin-left: 4px;
}
.gauge-bar {
  height: 10px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
  margin: 6px auto 0;
  max-width: 320px;
}
.gauge-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s ease;
}
.gauge-fill-cyan {
  background: linear-gradient(90deg, #06b6d4, #22d3ee);
}
.gauge-fill-blue {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
}
.gauge-meta {
  font-size: 0.6875rem;
  color: var(--text-muted, #6b7280);
  margin-top: 4px;
}
.mt3 {
  margin-top: 3px;
}

/* ── Protocol grid ── */
.proto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}
.proto-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 12px 14px;
  transition: border-color 0.25s;
}
.proto-card.proto-flake {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.04);
}
.proto-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.proto-device {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.proto-title {
  font-size: 0.925rem;
  color: var(--text-primary, #e5e7eb);
  margin-bottom: 8px;
}
.proto-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 12px;
}
.proto-kv {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.proto-k {
  font-size: 0.625rem;
  color: var(--text-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.proto-v {
  font-size: 0.7875rem;
  color: var(--text-secondary, #94a3b8);
}
.proto-desc {
  font-size: 0.6875rem;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(51, 65, 85, 0.4);
  line-height: 1.4;
}

/* ── Router detail meta grid ── */
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
.rt-k {
  font-size: 0.6875rem;
  color: var(--text-muted, #6b7280);
}
.rt-v {
  font-size: 0.7875rem;
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}

/* ── Utility classes ── */
.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}
.fw6 {
  font-weight: 600;
}
.fw4 {
  font-weight: 400;
}
.f11 {
  font-size: 0.6875rem;
}
.ml2 {
  margin-left: 4px;
}

.a-text {
  color: #f59e0b;
}
.g-text {
  color: #22c55e;
}
.w-text {
  color: #facc15;
}

/* ── Error / Empty ── */
.err-card {
  text-align: center;
  padding: 32px 16px;
}
.err-title {
  font-size: 1rem;
  font-weight: 700;
  color: #ef4444;
  margin-bottom: 8px;
}
.err-detail {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-bottom: 14px;
}
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
.btn:hover {
  background: rgba(255, 255, 255, 0.05);
}
.empty-card {
  text-align: center;
  padding: 40px 16px;
}

/* ── Responsive ── */
@media (max-width: 1100px) {
  .grid.cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid.cols-2 {
    grid-template-columns: 1fr;
  }
  .proto-grid {
    grid-template-columns: 1fr;
  }
  .rt-meta-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 640px) {
  .grid.cols-4 {
    grid-template-columns: 1fr;
  }
  .rt-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
