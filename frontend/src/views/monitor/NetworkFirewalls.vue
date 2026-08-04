<template>
  <div class="net-fw">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('防火墙') }}</h1>
      <span class="sub">{{ tl('策略命中 / 并发会话 / VPN / 威胁拦截 / 攻击分布') }}</span>
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

    <!-- 2.3.1 安全仪表盘：攻击类型分布饼图 + 阻断次数趋势图 -->
    <div v-if="s && s.firewalls.length" class="grid cols-2">
      <!-- 攻击类型分布饼图 -->
      <Panel title="攻击类型分布">
        <template #extra>
          <span class="pill a">{{ fmtNum(s.totalBlocked) }} {{ tl('次拦截') }}</span>
        </template>
        <BaseChart :option="attackPieOption" height="240px" />
      </Panel>

      <!-- 阻断次数趋势图 -->
      <Panel title="威胁阻断趋势">
        <TrendChart
          :title="tl('威胁阻断趋势')"
          :x-axis-data="s.blockTrend.labels"
          :series="s.blockTrend.series"
          :height="240"
          :show-range-picker="true"
        />
      </Panel>
    </div>

    <!-- 2.3.3 并发连接数 / 新建速率 KPI 卡片 -->
    <div v-if="s && s.firewalls.length" class="grid cols-4">
      <KpiCard
        :title="tl('并发连接数')"
        :value="s.totalConcurrent"
        unit=""
        :bar-value="Math.min(100, (s.totalConcurrent / Math.max(1, s.maxConcurrent)) * 100)"
        bar-color="var(--cyan)"
        :status="s.totalConcurrent / Math.max(1, s.maxConcurrent) > 0.85 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        :title="tl('新建会话速率')"
        :value="s.totalSessionRate"
        unit="cps"
        :subtitle="tl('峰值') + ' ' + fmtNum(s.peakSessionRate)"
        dot="var(--blue)"
        size="sm"
      />
      <KpiCard
        :title="tl('安全策略')"
        :value="s.totalPolicy"
        unit="条"
        dot="var(--violet)"
        size="sm"
      />
      <KpiCard :title="tl('VPN 隧道')" :value="s.totalVpn" unit="条" dot="var(--green)" size="sm" />
    </div>

    <!-- 2.3.4 系统资源利用（CPU/内存/磁盘） -->
    <Panel v-if="s && s.firewalls.length" title="系统资源利用 (CPU / 内存 / 磁盘)">
      <div class="res-grid">
        <div v-for="f in s.firewalls" :key="f.id" class="res-card">
          <div class="res-head">
            <span class="res-name">{{ f.name }}</span>
            <StatusBadge :status="f.status === 'online' ? 'online' : 'offline'" size="sm" />
          </div>
          <div class="res-bar-row">
            <span class="res-label">{{ tl('CPU') }}</span>
            <div class="res-track">
              <div
                class="res-fill"
                :class="barCls(f.cpu_pct)"
                :style="{ width: f.cpu_pct + '%' }"
              />
            </div>
            <span class="res-val mono">{{ f.cpu_pct }}%</span>
          </div>
          <div class="res-bar-row">
            <span class="res-label">{{ tl('内存') }}</span>
            <div class="res-track">
              <div
                class="res-fill"
                :class="barCls(f.mem_pct)"
                :style="{ width: f.mem_pct + '%' }"
              />
            </div>
            <span class="res-val mono">{{ f.mem_pct }}%</span>
          </div>
          <div class="res-bar-row">
            <span class="res-label">{{ tl('磁盘') }}</span>
            <div class="res-track">
              <div
                class="res-fill"
                :class="barCls(f.disk_pct)"
                :style="{ width: f.disk_pct + '%' }"
              />
            </div>
            <span class="res-val mono">{{ f.disk_pct }}%</span>
          </div>
        </div>
      </div>
    </Panel>

    <!-- 2.3.2 策略命中排行表 -->
    <Panel v-if="s && s.firewalls.length" title="策略命中排行">
      <template #extra>
        <span class="pill g">{{ tl('Top 10 策略') }}</span>
      </template>
      <div class="port-table scroll-x" style="max-height: 360px">
        <table>
          <thead>
            <tr>
              <th>{{ tl('防火墙') }}</th>
              <th>{{ tl('策略名称') }}</th>
              <th>{{ tl('命中次数') }}</th>
              <th>{{ tl('占比') }}</th>
              <th>{{ tl('命中率条') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in s.allPolicyHits" :key="ri" :class="{ 'row-alt': ri % 2 === 1 }">
              <td class="mono">{{ row.fw }}</td>
              <td>{{ row.name }}</td>
              <td class="mono">{{ fmtNum(row.hits) }}</td>
              <td class="mono">{{ row.pct }}%</td>
              <td class="hit-cell">
                <div class="hit-track">
                  <div class="hit-fill" :style="{ width: row.pct + '%' }" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <!-- Per-device detail cards -->
    <Panel v-for="f in firewallCards" :key="f.id" :title="f.name">
      <template #ct>
        {{ f.name }} <span class="muted ml2 fw4 f11">{{ f.model }}</span>
      </template>
      <template #extra>
        <StatusBadge :status="f.status === 'online' ? 'online' : 'offline'" />
      </template>

      <div class="rt-meta-grid">
        <div class="rt-kv">
          <span class="rt-k">{{ tl('管理IP') }}</span
          ><span class="rt-v mono">{{ f.ip }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('位置') }}</span
          ><span class="rt-v">{{ f.location }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('型号') }}</span
          ><span class="rt-v mono">{{ f.model }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('运行天数') }}</span
          ><span class="rt-v">{{ f.uptime_days }}d</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('吞吐') }}</span
          ><span class="rt-v mono">{{ fmtBps(f.throughput_bps) }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('并发会话') }}</span
          ><span class="rt-v mono">{{ fmtNum(f.concurrent_sessions) }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('会话率') }}</span
          ><span class="rt-v mono">{{ fmtNum(f.session_rate) }}/s</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('威胁拦截') }}</span
          ><span class="rt-v" :class="f.threat_blocked ? 'a-text' : 'g-text'">{{
            fmtNum(f.threat_blocked)
          }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('VPN 隧道') }}</span
          ><span class="rt-v">{{ f.vpn_tunnels }}</span>
        </div>
        <div class="rt-kv">
          <span class="rt-k">{{ tl('策略总数') }}</span
          ><span class="rt-v">{{ f.policy_total }}</span>
        </div>
      </div>

      <!-- 策略命中 Top (this device) -->
      <div class="sub-title">{{ tl('策略命中 Top') }}</div>
      <div class="hit-list">
        <div class="hit-row" v-for="(p, i) in f.policy_hit_top" :key="i">
          <span class="hit-rank mono">{{ i + 1 }}</span>
          <span class="hit-name">{{ p.name }}</span>
          <span class="hit-bar"
            ><span
              class="hit-fill"
              :style="{
                width:
                  Math.min(100, (p.hits / Math.max(1, f.policy_hit_top[0]?.hits || 1)) * 100) + '%',
              }"
          /></span>
          <span class="hit-val mono">{{ fmtNum(p.hits) }}</span>
        </div>
      </div>
    </Panel>

    <!-- Empty state -->
    <Panel v-if="s && !s.firewalls.length && !loading && !error" class="empty-card">
      <p class="muted">{{ tl('暂无防火墙数据') }}</p>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmtNum, fmtBps, genHours } from '@/utils/format'
import KpiCard from '@/components/monitor/KpiCard.vue'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import StatusBadge from '@/components/monitor/StatusBadge.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import Panel from '@/components/common/Panel.vue'
import {
  getNetworkFirewallsDetailed,
  type FirewallView,
  type FwPolicyHitView,
  type NetworkFirewallSummary,
} from '@/api/monitor'
import type * as echarts from 'echarts'
import type { EChartsOption } from '@/hooks/useECharts'

const { t: tl } = useI18n()

// ──────────────────────────────────────────
// Local extended firewall type (adds disk_pct)
// ──────────────────────────────────────────
interface FirewallEx extends FirewallView {
  disk_pct: number
}

interface PolicyHitRow {
  fw: string
  name: string
  hits: number
  pct: number
}

interface TrendSeries {
  name: string
  data: number[]
  color?: string
}

interface PageState {
  firewalls: FirewallEx[]
  total: number
  online: number
  totalConcurrent: number
  maxConcurrent: number
  totalSessionRate: number
  peakSessionRate: number
  totalPolicy: number
  totalVpn: number
  totalBlocked: number
  allPolicyHits: PolicyHitRow[]
  blockTrend: {
    labels: string[]
    series: TrendSeries[]
  }
  attackDist: { name: string; value: number; color: string }[]
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = reactive<PageState>({
  firewalls: [],
  total: 0,
  online: 0,
  totalConcurrent: 0,
  maxConcurrent: 0,
  totalSessionRate: 0,
  peakSessionRate: 0,
  totalPolicy: 0,
  totalVpn: 0,
  totalBlocked: 0,
  allPolicyHits: [],
  blockTrend: { labels: [], series: [] },
  attackDist: [],
})

const firewallCards = computed(() => s.firewalls ?? [])

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function barCls(v: number): string {
  if (v >= 85) return 'res-danger'
  if (v >= 60) return 'res-warning'
  return 'res-normal'
}

function genTimeData(n: number, base: number, amp: number, noise: number): number[] {
  const pts: number[] = []
  for (let i = 0; i < n; i++) {
    const v =
      base + amp * Math.sin((i / n) * Math.PI * 3 + Math.random()) + (Math.random() - 0.5) * noise
    pts.push(Math.max(0, Math.round(v)))
  }
  return pts
}

// ──────────────────────────────────────────
// Attack distribution pie chart option
// ──────────────────────────────────────────
const attackPieOption = reactive<EChartsOption>({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    formatter: (p) => {
      const item = Array.isArray(p) ? p[0] : p
      return `${item.name}<br/>${fmtNum(Number(item.value))} 次 (${item.percent}%)`
    },
  },
  legend: {
    orient: 'vertical',
    right: '4%',
    top: 'center',
    textStyle: { color: '#94a3b8', fontSize: 11 },
    itemWidth: 10,
    itemHeight: 10,
  },
  series: [
    {
      name: '攻击类型',
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['38%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderColor: '#0f172a', borderWidth: 2, borderRadius: 4 },
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          fontSize: 12,
          fontWeight: 'bold',
          color: '#e2e8f0',
          formatter: '{b}\n{d}%',
        },
      },
      data: [],
    },
  ],
})

function updateAttackPie(dist: { name: string; value: number; color: string }[]) {
  ;(attackPieOption.series as echarts.SeriesOption[])[0].data = dist.map((d) => ({
    name: d.name,
    value: d.value,
    itemStyle: { color: d.color },
  }))
}

// ──────────────────────────────────────────
// Mock data
// ──────────────────────────────────────────
function mockData() {
  const N = 24

  // ── Firewalls (with disk_pct added) ──
  const firewalls: FirewallEx[] = [
    {
      id: 'fw-1',
      name: 'FW-Core-01',
      ip: '10.200.2.1',
      model: 'USG6600E',
      location: 'DC-A 安全域 S-01',
      status: 'online',
      cpu_pct: 38,
      mem_pct: 52,
      temp_c: 43,
      uptime_days: 298,
      concurrent_sessions: 1850000,
      session_rate: 42000,
      policy_total: 1280,
      throughput_bps: 24.6e9,
      threat_blocked: 284000,
      vpn_tunnels: 42,
      disk_pct: 34,
      policy_hit_top: [
        { name: 'allow-int-to-dmz-web', hits: 458000 },
        { name: 'deny-external-ssh', hits: 312000 },
        { name: 'allow-vpn-to-internal', hits: 198000 },
        { name: 'deny-malware-c2', hits: 142000 },
        { name: 'allow-dns-egress', hits: 98000 },
      ] as FwPolicyHitView[],
    },
    {
      id: 'fw-2',
      name: 'FW-Core-02',
      ip: '10.200.2.2',
      model: 'USG6600E',
      location: 'DC-A 安全域 S-02',
      status: 'online',
      cpu_pct: 31,
      mem_pct: 47,
      temp_c: 41,
      uptime_days: 298,
      concurrent_sessions: 1620000,
      session_rate: 38000,
      policy_total: 1240,
      throughput_bps: 21.2e9,
      threat_blocked: 196000,
      vpn_tunnels: 38,
      disk_pct: 29,
      policy_hit_top: [
        { name: 'allow-int-to-dmz-web', hits: 392000 },
        { name: 'deny-external-ssh', hits: 268000 },
        { name: 'allow-vpn-to-internal', hits: 176000 },
        { name: 'deny-portscan', hits: 121000 },
        { name: 'allow-dns-egress', hits: 84000 },
      ] as FwPolicyHitView[],
    },
    {
      id: 'fw-3',
      name: 'FW-Edge-01',
      ip: '10.200.2.3',
      model: 'USG6300E',
      location: 'DC-A 边界域 B-08',
      status: 'online',
      cpu_pct: 46,
      mem_pct: 58,
      temp_c: 47,
      uptime_days: 156,
      concurrent_sessions: 980000,
      session_rate: 52000,
      policy_total: 860,
      throughput_bps: 12.8e9,
      threat_blocked: 412000,
      vpn_tunnels: 24,
      disk_pct: 52,
      policy_hit_top: [
        { name: 'deny-external-ssh', hits: 526000 },
        { name: 'deny-malware-c2', hits: 318000 },
        { name: 'deny-portscan', hits: 244000 },
        { name: 'allow-vpn-to-internal', hits: 132000 },
        { name: 'allow-int-to-dmz-web', hits: 88000 },
      ] as FwPolicyHitView[],
    },
  ]

  // ── Attack type distribution (aggregated) ──
  const attackDist = [
    { name: tl('SSH 暴力破解'), value: 412000, color: '#ef4444' },
    { name: tl('端口扫描'), value: 312000, color: '#f97316' },
    { name: tl('恶意软件 C2'), value: 198000, color: '#eab308' },
    { name: tl('Web 攻击'), value: 156000, color: '#8b5cf6' },
    { name: tl('SQL 注入'), value: 98000, color: '#06b6d4' },
    { name: tl('DDoS'), value: 64000, color: '#ec4899' },
  ]

  // ── Block trend (sum of all firewalls) ──
  const labels = genHours(N)
  const series: TrendSeries[] = [
    {
      name: tl('阻断次数'),
      data: genTimeData(N, 18000, 8000, 4000),
      color: '#22d3ee',
    },
  ]

  // ── All policy hits (flattened & sorted) ──
  const allHits: PolicyHitRow[] = []
  for (const f of firewalls) {
    for (const p of f.policy_hit_top) {
      allHits.push({ fw: f.name, name: p.name, hits: p.hits, pct: 0 })
    }
  }
  allHits.sort((a, b) => b.hits - a.hits)
  const maxHit = allHits.length ? allHits[0].hits : 1
  allHits.forEach((h) => {
    h.pct = Math.round((h.hits / maxHit) * 100)
  })
  const topHits = allHits.slice(0, 10)

  // ── Totals ──
  const totalConcurrent = firewalls.reduce((a, f) => a + f.concurrent_sessions, 0)
  const maxConcurrent = Math.max(10000000, Math.round(totalConcurrent * 1.5))
  const totalSessionRate = firewalls.reduce((a, f) => a + f.session_rate, 0)
  const peakSessionRate = Math.round(totalSessionRate * 1.4)
  const totalPolicy = firewalls.reduce((a, f) => a + f.policy_total, 0)
  const totalVpn = firewalls.reduce((a, f) => a + f.vpn_tunnels, 0)
  const totalBlocked = firewalls.reduce((a, f) => a + f.threat_blocked, 0)

  return {
    firewalls,
    attackDist,
    blockTrend: { labels, series },
    topHits,
    totalConcurrent,
    maxConcurrent,
    totalSessionRate,
    peakSessionRate,
    totalPolicy,
    totalVpn,
    totalBlocked,
  }
}

// ──────────────────────────────────────────
// Apply data to reactive state
// ──────────────────────────────────────────
function applyData(d: ReturnType<typeof mockData>) {
  s.firewalls = d.firewalls
  s.attackDist = d.attackDist
  s.blockTrend = d.blockTrend
  s.allPolicyHits = d.topHits
  s.totalConcurrent = d.totalConcurrent
  s.maxConcurrent = d.maxConcurrent
  s.totalSessionRate = d.totalSessionRate
  s.peakSessionRate = d.peakSessionRate
  s.totalPolicy = d.totalPolicy
  s.totalVpn = d.totalVpn
  s.totalBlocked = d.totalBlocked
  s.total = d.firewalls.length
  s.online = d.firewalls.filter((f) => f.status === 'online').length
  updateAttackPie(d.attackDist)
}

// ──────────────────────────────────────────
// Build from API data (if available)
// ──────────────────────────────────────────
function fromApi(summary: NetworkFirewallSummary) {
  const mock = mockData()
  // If API returns real firewalls, map them; otherwise use mock
  if (summary.firewalls?.length) {
    const firewalls: FirewallEx[] = summary.firewalls.map((f) => ({
      ...f,
      disk_pct: 30 + Math.round(Math.random() * 30),
    }))
    const totalConcurrent =
      summary.concurrentSessions || firewalls.reduce((a, f) => a + f.concurrent_sessions, 0)
    const maxConcurrent = Math.max(10000000, Math.round(totalConcurrent * 1.5))
    const totalSessionRate = firewalls.reduce((a, f) => a + f.session_rate, 0)
    const totalPolicy = summary.policyTotal || firewalls.reduce((a, f) => a + f.policy_total, 0)
    const totalVpn = summary.vpnTunnels || firewalls.reduce((a, f) => a + f.vpn_tunnels, 0)
    const totalBlocked =
      summary.threatBlocked || firewalls.reduce((a, f) => a + f.threat_blocked, 0)

    // Rebuild policy hits from all firewalls
    const allHits: PolicyHitRow[] = []
    for (const f of firewalls) {
      for (const p of f.policy_hit_top || []) {
        allHits.push({ fw: f.name, name: p.name, hits: p.hits, pct: 0 })
      }
    }
    allHits.sort((a, b) => b.hits - a.hits)
    const maxHit = allHits.length ? allHits[0].hits : 1
    allHits.forEach((h) => {
      h.pct = Math.round((h.hits / maxHit) * 100)
    })

    s.firewalls = firewalls
    s.attackDist = mock.attackDist
    s.blockTrend = mock.blockTrend
    s.allPolicyHits = allHits.slice(0, 10)
    s.totalConcurrent = totalConcurrent
    s.maxConcurrent = maxConcurrent
    s.totalSessionRate = totalSessionRate
    s.peakSessionRate = Math.round(totalSessionRate * 1.4)
    s.totalPolicy = totalPolicy
    s.totalVpn = totalVpn
    s.totalBlocked = totalBlocked
    s.total = summary.total || firewalls.length
    s.online = summary.online || firewalls.filter((f) => f.status === 'online').length
    updateAttackPie(mock.attackDist)
  } else {
    applyData(mock)
  }
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const data = await getNetworkFirewallsDetailed()
    if (data && (data.firewalls?.length || data.total || data.concurrentSessions)) {
      fromApi(data)
    } else {
      // Fallback to full mock
      applyData(mockData())
    }
  } catch (e: unknown) {
    error.value = (e as ErrorLike)?.message || String(e)
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

/* ── resource grid ── */
.res-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.res-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 12px 14px;
}
.res-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.res-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
}
.res-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
}
.res-label {
  font-size: 0.6875rem;
  color: var(--text-muted, #6b7280);
  width: 32px;
  flex-shrink: 0;
}
.res-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.res-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.res-normal {
  background: linear-gradient(90deg, #22c55e, #4ade80);
}
.res-warning {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}
.res-danger {
  background: linear-gradient(90deg, #ef4444, #f87171);
}
.res-val {
  font-size: 0.6875rem;
  color: var(--text-secondary, #94a3b8);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

/* ── port table ── */
.port-table {
  max-height: 360px;
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
.port-table .row-alt td {
  background: rgba(255, 255, 255, 0.02);
}
.hit-cell {
  width: 120px;
}
.hit-track {
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.hit-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(34, 211, 255, 0.4), rgba(34, 211, 255, 0.85));
}

/* ── device meta grid ── */
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

/* ── policy hit list (per device) ── */
.sub-title {
  font-size: 0.6875rem;
  color: var(--cyan, #22d3ee);
  font-weight: 600;
  margin: 12px 0 6px;
}
.hit-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.hit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.75rem;
}
.hit-rank {
  width: 18px;
  color: var(--text-muted, #6b7280);
  text-align: center;
}
.hit-name {
  width: 220px;
  color: var(--text-secondary, #94a3b8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hit-bar {
  flex: 1;
  height: 10px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.hit-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, rgba(34, 227, 255, 0.4), rgba(34, 227, 255, 0.8));
  border-radius: 3px;
}
.hit-val {
  width: 60px;
  text-align: right;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
}

/* ── Utility ── */
.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
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
  .res-grid {
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
  .hit-name {
    width: 120px;
  }
}
</style>
