<template>
  <div class="net-sw">
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('网络监控') }} {{ tl('·') }} {{ tl('核心交换机') }}</h1>
      <span class="sub">{{ tl('Spine-Leaf 拓扑 / 端口面板 / 链路聚合 / 流量监控') }}</span>
    </div>

    <!-- 2.1.5 系统资源仪表区 KpiCard × 4 -->
    <div class="grid cols-4" v-if="s && s.switches.length">
      <KpiCard
        title="平均 CPU"
        :value="s.avgCpu"
        unit="%"
        :bar-value="s.avgCpu"
        bar-color="var(--cyan)"
        :status="s.avgCpu > 80 ? 'danger' : s.avgCpu > 60 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        title="平均内存"
        :value="s.avgMem || 0"
        unit="%"
        :bar-value="s.avgMem || 0"
        bar-color="var(--violet)"
        :status="(s.avgMem || 0) > 80 ? 'danger' : (s.avgMem || 0) > 60 ? 'warning' : 'normal'"
        size="sm"
      />
      <KpiCard
        title="交换机总数"
        :value="s.total"
        unit="台"
        :subtitle="`在线 ${s.online}/${s.total}`"
        dot="var(--green)"
        size="sm"
      />
      <KpiCard
        title="端口可用率"
        :value="s.overallPortRate"
        unit="%"
        :bar-value="s.overallPortRate"
        bar-color="var(--green)"
        :status="s.overallPortRate < 95 ? 'warning' : 'normal'"
        size="sm"
      />
    </div>

    <!-- 2.1.1 SVG Spine-Leaf 拓扑图 -->
    <div class="card" v-if="s && s.switches.length">
      <div class="card-head">
        <span class="ct">{{ tl('Spine-Leaf 网络拓扑') }}</span>
        <div class="topo-legend">
          <span><i class="tl-dot" style="background:#22c55e"></i> {{ tl('正常') }}</span>
          <span><i class="tl-dot" style="background:#f59e0b"></i> {{ tl('高负载') }}</span>
          <span><i class="tl-dot" style="background:#ef4444"></i> {{ tl('拥塞/告警') }}</span>
        </div>
      </div>
      <svg class="topo-svg" :viewBox="`0 0 ${svgW} ${svgH}`">
        <!-- spine switches -->
        <g v-for="(sp, si) in spineSwitches" :key="sp.id">
          <rect :x="sp.x" :y="sp.y" :width="sp.w" :height="sp.h" rx="6"
            :fill="sp.status === 'online' ? 'rgba(34,227,255,0.10)' : 'rgba(107,114,128,0.08)'"
            :stroke="sp.status === 'online' ? 'rgba(34,227,255,0.5)' : 'rgba(107,114,128,0.3)'"
            stroke-width="1.5" />
          <text :x="sp.x + sp.w/2" :y="sp.y + 22" text-anchor="middle"
            fill="var(--txt)" font-size="11" font-weight="600">{{ sp.name }}</text>
          <text :x="sp.x + sp.w/2" :y="sp.y + 40" text-anchor="middle"
            fill="var(--txt3)" font-size="10">{{ sp.role }}</text>
          <text :x="sp.x + sp.w/2" :y="sp.y + 54" text-anchor="middle"
            :fill="sp.cpu_pct > 80 ? '#ef4444' : sp.cpu_pct > 60 ? '#f59e0b' : '#22c55e'"
            font-size="10" font-weight="600">CPU {{ sp.cpu_pct }}%</text>
        </g>

        <!-- leaf switches -->
        <g v-for="(lf, li) in leafSwitches" :key="lf.id">
          <rect :x="lf.x" :y="lf.y" :width="lf.w" :height="lf.h" rx="6"
            :fill="lf.status === 'online' ? 'rgba(168,85,247,0.08)' : 'rgba(107,114,128,0.06)'"
            :stroke="lf.status === 'online' ? 'rgba(168,85,247,0.4)' : 'rgba(107,114,128,0.25)'"
            stroke-width="1.5" />
          <text :x="lf.x + lf.w/2" :y="lf.y + 20" text-anchor="middle"
            fill="var(--txt)" font-size="10" font-weight="600">{{ lf.name }}</text>
          <text :x="lf.x + lf.w/2" :y="lf.y + 36" text-anchor="middle"
            fill="var(--txt3)" font-size="9">{{ lf.role }}</text>
          <text :x="lf.x + lf.w/2" :y="lf.y + 52" text-anchor="middle"
            font-size="9" font-weight="600" :fill="lf.status === 'online' ? '#22c55e' : '#6b7280'">
            {{ lf.up_ports }}/{{ lf.total_ports }} UP
          </text>
        </g>

        <!-- links: each leaf connects to each spine -->
        <line v-for="(lnk, li) in topoLinks" :key="'l'+li"
          :x1="lnk.x1" :y1="lnk.y1" :x2="lnk.x2" :y2="lnk.y2"
          :stroke="lnk.color" :stroke-width="lnk.sw" :opacity="lnk.op" />
      </svg>
    </div>

    <!-- 2.1.6 链路健康面板 -->
    <div class="card" v-if="s && s.switches.length">
      <div class="card-head">
        <span class="ct">{{ tl('链路聚合与冗余状态') }}</span>
        <span class="pill g" v-if="healthyTrunks.length === allTrunks.length">{{ tl('全部链路正常') }}</span>
        <span class="pill a" v-else>{{ tl('异常') }}: {{ allTrunks.length - healthyTrunks.length }}/{{ allTrunks.length }}</span>
      </div>
      <div class="trunk-grid" v-if="allTrunks.length">
        <div
          v-for="t in allTrunks"
          :key="t.id"
          class="trunk-card"
          :class="{ 'trunk-ok': t.isHealthy, 'trunk-warn': !t.isHealthy }"
        >
          <div class="trunk-bar-head">
            <span class="mono fw6">{{ t.id }}</span>
            <span class="pill" :class="t.isHealthy ? 'g' : 'a'">{{ t.isHealthy ? tl('正常') : tl('降级') }}</span>
          </div>
          <div class="trunk-meta">
            <span>{{ t.mode }} · {{ t.members.length }} {{ tl('成员') }}</span>
            <span class="trunk-members">{{ t.members.join(' / ') }}</span>
          </div>
          <div class="trunk-util-bar">
            <div class="bar-label" style="font-size:10px;color:var(--txt2)">{{ tl('链路利用率') }} {{ t.util_pct }}%</div>
            <div class="bar-track">
              <div class="bar-fill" :class="t.util_pct > 85 ? 'bar-r' : t.util_pct > 60 ? 'bar-a' : 'bar-g'"
                :style="{ width: Math.min(100, t.util_pct) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="muted" v-else style="padding:20px 0;text-align:center">{{ tl('无链路聚合配置') }}</div>
    </div>

    <!-- 设备逐台 (PortPanel + 端口流量表) -->
    <div class="sw-section" v-for="sw in s?.switches ?? []" :key="sw.id">
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ sw.name }} <span class="muted">{{ sw.model }}</span></span>
          <StatusBadge :status="sw.status === 'online' ? 'online' : 'offline'" />
        </div>

        <div class="sw-meta-grid">
          <div class="sw-kv"><span class="sw-k">{{ tl('管理IP') }}</span><span class="sw-v mono">{{ sw.ip }}</span></div>
          <div class="sw-kv"><span class="sw-k">{{ tl('角色') }}</span><span class="sw-v">{{ sw.role }}</span></div>
          <div class="sw-kv"><span class="sw-k">{{ tl('位置') }}</span><span class="sw-v">{{ sw.location }}</span></div>
          <div class="sw-kv"><span class="sw-k">{{ tl('CPU') }}</span>
            <span class="sw-v" :class="sw.cpu_pct > 80 ? 'a-text' : 'g-text'">{{ sw.cpu_pct }}%</span>
          </div>
          <div class="sw-kv"><span class="sw-k">{{ tl('内存') }}</span>
            <span class="sw-v" :class="sw.mem_pct > 80 ? 'a-text' : 'g-text'">{{ sw.mem_pct }}%</span>
          </div>
          <div class="sw-kv"><span class="sw-k">{{ tl('温度') }}</span><span class="sw-v">{{ sw.temp_c }}°C</span></div>
          <div class="sw-kv"><span class="sw-k">{{ tl('运行时长') }}</span><span class="sw-v">{{ sw.uptime_days }} {{ tl('天') }}</span></div>
          <div class="sw-kv"><span class="sw-k">{{ tl('端口') }}</span><span class="sw-v">{{ sw.up_ports }}/{{ sw.total_ports }}</span></div>
          <div class="sw-kv" v-if="sw.stack">
            <span class="sw-k">{{ tl('堆叠') }}</span>
            <span class="sw-v">{{ sw.stack.topo }} · {{ sw.stack.members }} {{ tl('成员') }}</span>
          </div>
        </div>

        <!-- 2.1.2 / 2.1.3 PortPanel 前面板 -->
        <div class="sw-panels">
          <PortPanel :ports="sw.ports" :title="`${sw.name} 前面板`" />
        </div>

        <!-- 2.1.4 端口流量表 -->
        <div class="port-table-wrap" v-if="sw.ports.length">
          <div class="sub-title">{{ tl('端口流量详情') }}</div>
          <div class="port-table scroll-x">
            <table>
              <thead><tr>
                <th>{{ tl('端口') }}</th>
                <th>{{ tl('状态') }}</th>
                <th>{{ tl('速率') }}</th>
                <th>{{ tl('入利用率') }}</th>
                <th>{{ tl('出利用率') }}</th>
                <th>{{ tl('实时流量') }}</th>
                <th>{{ tl('错包率') }}</th>
                <th>{{ tl('丢包率') }}</th>
                <th>{{ tl('收光') }}</th>
                <th>{{ tl('发光') }}</th>
              </tr></thead>
              <tbody>
                <tr
                  v-for="p in sw.ports.slice(0, 24)"
                  :key="p.name"
                  :class="portRowCls(p)"
                >
                  <td class="mono">{{ p.name }}</td>
                  <td>
                    <StatusBadge
                      :status="p.status === 'up' ? 'online' : 'offline'"
                      size="sm"
                    />
                  </td>
                  <td class="mono">{{ p.speed_mbps >= 1000 ? (p.speed_mbps/1000).toFixed(0)+'G' : p.speed_mbps+'M' }}</td>
                  <td class="mono">
                    <span :class="utilCls(p.in_util_pct)">{{ p.in_util_pct }}%</span>
                  </td>
                  <td class="mono">
                    <span :class="utilCls(p.out_util_pct)">{{ p.out_util_pct }}%</span>
                  </td>
                  <td class="mono">{{ fmtBps(p.in_bps + p.out_bps) }}</td>
                  <td class="mono" :class="(p.in_errors + p.out_errors) ? 'a-text' : ''">
                    {{ p.in_errors + p.out_errors }}
                  </td>
                  <td class="mono" :class="(p.in_discards || 0) ? 'a-text' : ''">
                    {{ p.in_discards || 0 }}
                  </td>
                  <td class="mono" :class="opticalPowerCls(p.rx_power_dbm)">
                    {{ p.rx_power_dbm != null ? p.rx_power_dbm + 'dBm' : '-' }}
                  </td>
                  <td class="mono" :class="opticalPowerCls(p.tx_power_dbm)">
                    {{ p.tx_power_dbm != null ? p.tx_power_dbm + 'dBm' : '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 链路质量 Ping -->
    <div class="card" v-if="s && s.pingTargets && s.pingTargets.length">
      <div class="card-head">
        <span class="ct">{{ tl('链路质量探测') }}</span>
        <span class="pill" :class="s.avgPingLossPct >= 1 ? 'a' : 'g'">
          {{ tl('平均') }} {{ s.avgPingRttMs }}ms / {{ tl('丢包') }} {{ s.avgPingLossPct }}%
        </span>
      </div>
      <div class="ping-grid">
        <div class="ping-block" v-for="p in (s.pingTargets ?? [])" :key="p.target">
          <div class="ping-head">
            <span class="d-name">{{ p.name }}</span>
            <StatusBadge
              :status="p.status === 'ok' ? 'online' : p.status === 'lossy' ? 'warning' : 'offline'"
              size="sm"
            />
          </div>
          <div class="ping-meta">
            <span class="muted">{{ tl('RTT') }}</span><span class="mono">{{ p.rtt_avg_ms }}ms ({{ p.rtt_min_ms }}~{{ p.rtt_max_ms }})</span>
            <span class="muted">{{ tl('抖动') }}</span><span class="mono">{{ p.jitter_ms }}ms</span>
            <span class="muted">{{ tl('丢包') }}</span><span class="mono" :class="p.loss_pct > 1 ? 'a-text' : 'g-text'">{{ p.loss_pct }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 负载状态 -->
    <div class="flex center" style="padding:40px" v-if="!s && !error">
      <span class="muted">{{ tl('加载中...') }}</span>
    </div>
    <div class="flex center" style="padding:40px" v-if="error">
      <span class="muted a-text">{{ tl('加载失败') }}: {{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import KpiCard from '@/components/monitor/KpiCard.vue'
import StatusBadge from '@/components/monitor/StatusBadge.vue'
import PortPanel from '@/components/monitor/PortPanel.vue'
import { getNetworkSwitchesDetailed, type NetworkSwitchSummary, type SwitchView, type SwitchPortView } from '@/api/monitor'
const { t: tl } = useI18n()

const s = ref<NetworkSwitchSummary | null>(null)
const error = ref('')

// ---- Spine-Leaf topology layout ----
interface TopoNode {
  id: string
  name: string
  role: string
  status: string
  cpu_pct: number
  total_ports: number
  up_ports: number
  x: number; y: number; w: number; h: number
}

interface TopoLink {
  x1: number; y1: number; x2: number; y2: number
  sw: number; color: string; op: number
}

const svgW = 900
const svgH = 380
const nodeW = 130; const nodeH = 62
const spineY = 50; const leafY = 240

const spineSwitches = computed<TopoNode[]>(() => {
  if (!s.value) return []
  const core = s.value.switches.filter((sw) => sw.role === 'core' && sw.status === 'online')
  if (!core.length) {
    const anyOnline = s.value.switches.filter((sw) => sw.status === 'online').slice(0, 2)
    return anyOnline.map((sw, i) => nodeDef(sw, i, 2))
  }
  return core.slice(0, 2).map((sw, i) => nodeDef(sw, i, Math.min(2, core.length)))
})

const leafSwitches = computed<TopoNode[]>(() => {
  if (!s.value) return []
  const nonCore = s.value.switches.filter((sw) => sw.role !== 'core').slice(0, 6)
  if (!nonCore.length) return []
  return nonCore.map((sw, i) => {
    const total = nonCore.length; const spacing = svgW / (total + 1)
    return { id: sw.id, name: sw.name, role: sw.role, status: sw.status, cpu_pct: sw.cpu_pct, total_ports: sw.total_ports, up_ports: sw.up_ports, x: spacing * (i + 1) - nodeW / 2, y: leafY, w: nodeW, h: nodeH }
  })
})

const topoLinks = computed<TopoLink[]>(() => {
  const links: TopoLink[] = []
  for (const sp of spineSwitches.value) {
    for (const lf of leafSwitches.value) {
      const sx = sp.x + sp.w / 2; const sy = sp.y + sp.h
      const ex = lf.x + lf.w / 2; const ey = lf.y
      // simulate link utilization based on port data
      const util = 30 + Math.abs(sp.name.charCodeAt(sp.name.length-1) * lf.name.charCodeAt(lf.name.length-1)) % 60
      const sw = 1 + (util / 100) * 4
      const color = util > 85 ? '#ef4444' : util > 55 ? '#f59e0b' : '#22c55e'
      const op = sp.status === 'online' && lf.status === 'online' ? 0.7 : 0.2
      links.push({ x1: sx, y1: sy, x2: ex, y2: ey, sw, color, op })
    }
  }
  return links
})

function nodeDef(sw: SwitchView, i: number, total: number): TopoNode {
  const spacing = svgW / (total + 1)
  return {
    id: sw.id, name: sw.name, role: sw.role, status: sw.status,
    cpu_pct: sw.cpu_pct, total_ports: sw.total_ports, up_ports: sw.up_ports,
    x: spacing * (i + 1) - nodeW / 2, y: spineY, w: nodeW, h: nodeH,
  }
}

// ---- Trunk health ----
const allTrunks = computed(() => {
  if (!s.value) return []
  const trunks: (any & { isHealthy: boolean })[] = []
  for (const sw of s.value.switches) {
    for (const t of sw.trunks) {
      const isHealthy = t.status === 'up' && t.util_pct < 90
      trunks.push({ ...t, device: sw.name, isHealthy })
    }
  }
  return trunks
})
const healthyTrunks = computed(() => allTrunks.value.filter((t) => t.isHealthy))

// ---- helpers ----
function fmtBps(v: number): string {
  if (!v) return '0'
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + ' Mbps'
  return (v / 1e3).toFixed(1) + ' Kbps'
}
function utilCls(v: number): string { return v > 85 ? 'a-text' : v > 60 ? 'a-text' : 'g-text' }
function portRowCls(p: SwitchPortView): string {
  if (p.status !== 'up') return 'row-offline'
  if (p.optical_alarm && p.optical_alarm !== '正常') return 'row-alarm'
  if (p.in_errors + p.out_errors > 0) return 'row-alarm'
  return ''
}
function opticalPowerCls(v: number | undefined): string {
  if (v == null) return ''
  if (v < -20) return 'a-text'
  return 'g-text'
}

function mockPorts(count: number, start = 1): SwitchPortView[] {
  const arr: SwitchPortView[] = []
  for (let i = 0; i < count; i++) {
    const idx = start + i
    const up = Math.random() > 0.15
    const speed = Math.random() > 0.3 ? 10000 : 1000
    const inU = up ? Math.floor(Math.random() * 85) : 0
    const outU = up ? Math.floor(Math.random() * 70) : 0
    const hasOpt = speed >= 10000
    arr.push({
      name: `Eth1/${idx}`,
      alias: `Eth1/${idx}`,
      status: up ? 'up' : 'down',
      speed_mbps: speed,
      in_bps: up ? inU * speed * 1000 : 0,
      out_bps: up ? outU * speed * 1000 : 0,
      in_util_pct: inU,
      out_util_pct: outU,
      in_errors: Math.floor(Math.random() * 5),
      out_errors: 0,
      in_discards: 0,
      rx_power_dbm: hasOpt ? +(Math.random() * 6 - 5).toFixed(2) : undefined,
      tx_power_dbm: hasOpt ? +(Math.random() * 6 - 3).toFixed(2) : undefined,
      optical_alarm: '正常',
    })
  }
  return arr
}

function makeTrunk(id: string, members: string[], util: number, mode = 'LACP') {
  return { id, members, mode, status: 'up', util_pct: util, traffic_bps: util * 100000000 }
}
function makeStack(topo: string, members: number) {
  return { enabled: true, topo, members, master: 'Slot 1', status: 'online' }
}

function mockData(): NetworkSwitchSummary {
  const sws: SwitchView[] = [
    { id: 'sp-01', name: 'Spine-01', role: 'core', status: 'online', ip: '10.1.1.1', location: '机房A顶列', model: 'CE12800E', cpu_pct: 42, mem_pct: 55, temp_c: 38, uptime_days: 365, total_ports: 48, up_ports: 48, down_ports: 0, ports: mockPorts(48), trunks: [makeTrunk('Eth-Trunk10', ['Eth1/1', 'Eth1/2'], 35)], stack: makeStack('Ring', 2) },
    { id: 'sp-02', name: 'Spine-02', role: 'core', status: 'online', ip: '10.1.1.2', location: '机房A顶列', model: 'CE12800E', cpu_pct: 38, mem_pct: 52, temp_c: 37, uptime_days: 365, total_ports: 48, up_ports: 48, down_ports: 0, ports: mockPorts(48, 49), trunks: [makeTrunk('Eth-Trunk20', ['Eth1/1', 'Eth1/2'], 28)], stack: makeStack('Ring', 2) },
    { id: 'lf-01', name: 'Leaf-01', role: 'aggregation', status: 'online', ip: '10.1.2.1', location: '机房A列头', model: 'CE6881-48S6CQ', cpu_pct: 31, mem_pct: 45, temp_c: 35, uptime_days: 320, total_ports: 48, up_ports: 42, down_ports: 6, ports: mockPorts(48, 97), trunks: [makeTrunk('Eth-Trunk1', ['Eth1/47', 'Eth1/48'], 55)], stack: null },
    { id: 'lf-02', name: 'Leaf-02', role: 'aggregation', status: 'online', ip: '10.1.2.2', location: '机房A列头', model: 'CE6881-48S6CQ', cpu_pct: 29, mem_pct: 48, temp_c: 34, uptime_days: 320, total_ports: 48, up_ports: 43, down_ports: 5, ports: mockPorts(48, 145), trunks: [makeTrunk('Eth-Trunk2', ['Eth1/47', 'Eth1/48'], 48)], stack: null },
    { id: 'ac-01', name: 'Access-01', role: 'access', status: 'online', ip: '10.1.3.1', location: 'A01列', model: 'S6735-S', cpu_pct: 18, mem_pct: 30, temp_c: 32, uptime_days: 290, total_ports: 24, up_ports: 22, down_ports: 2, ports: mockPorts(24, 193), trunks: [makeTrunk('Eth-Trunk100', ['Eth1/23', 'Eth1/24'], 22)], stack: null },
  ]
  const avgCpu = Math.round(sws.reduce((a, b) => a + b.cpu_pct, 0) / sws.length)
  const avgMem = Math.round(sws.reduce((a, b) => a + b.mem_pct, 0) / sws.length)
  const totalP = sws.reduce((a, b) => a + b.total_ports, 0)
  const upP = sws.reduce((a, b) => a + b.up_ports, 0)
  const pingTargets = [
    { target: '10.1.2.1', name: 'Leaf-01 Spine侧', category: 'leaf', status: 'ok', rtt_avg_ms: 1.2, rtt_min_ms: 0.8, rtt_max_ms: 2.1, jitter_ms: 0.3, loss_pct: 0 },
    { target: '10.1.2.2', name: 'Leaf-02 Spine侧', category: 'leaf', status: 'ok', rtt_avg_ms: 1.3, rtt_min_ms: 0.9, rtt_max_ms: 2.4, jitter_ms: 0.4, loss_pct: 0 },
    { target: '10.1.3.1', name: 'Access-01 Leaf侧', category: 'access', status: 'lossy', rtt_avg_ms: 3.5, rtt_min_ms: 1.0, rtt_max_ms: 12.0, jitter_ms: 2.1, loss_pct: 1.2 },
  ]
  return {
    total: sws.length,
    online: sws.filter((sw) => sw.status === 'online').length,
    offline: sws.filter((sw) => sw.status !== 'online').length,
    totalPorts: totalP,
    upPorts: upP,
    downPorts: totalP - upP,
    overallPortRate: totalP ? Math.round((upP / totalP) * 1000) / 10 : 0,
    totalTrafficBps: 1234567890,
    avgCpu, avgMem,
    switches: sws,
    pingTargets,
    avgPingRttMs: 1.2,
    avgPingLossPct: 0.4,
    worstPingTarget: 'Access-01 Leaf侧',
    bwTopN: [],
  }
}

async function load() {
  error.value = ''
  const data = await getNetworkSwitchesDetailed()
  if (!data || !data.switches?.length) {
    console.warn('NetworkSwitches empty data, using mock fallback')
    s.value = mockData()
  } else {
    s.value = data
  }
}
onMounted(load)
</script>

<style scoped>
/* layout */
.view-head { margin-bottom: 16px; }
.view-head h1 { font-size: 20px; font-weight: 700; color: var(--txt); margin: 0 0 4px; }
.view-head .sub { font-size: 12px; color: var(--txt2); }
.card { background: var(--bg1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 14px; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.muted { color: var(--txt2); }
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }
.g-text { color: var(--green); }
.a-text { color: var(--amber); }
.fw6 { font-weight: 600; }

/* grid */
.grid { display: grid; gap: 12px; }
.cols-4 { grid-template-columns: repeat(4, 1fr); }
.flex { display: flex; } .center { align-items: center; } .scroll-x { overflow-x: auto; }

/* pills & badges */
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(34,197,94,0.12); color: var(--green); }
.pill.a { background: rgba(245,158,11,0.12); color: var(--amber); }

/* Spine-Leaf topology */
.topo-legend { display: flex; gap: 16px; font-size: 10px; color: var(--txt3); }
.topo-legend span { display: flex; align-items: center; gap: 4px; }
.tl-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.topo-svg { width: 100%; height: auto; max-height: 400px; }

/* switch meta grid */
.sw-meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px 16px; margin-bottom: 12px; }
.sw-kv { display: flex; flex-direction: column; gap: 2px; padding: 5px 0; border-bottom: 1px dashed var(--td-line); }
.sw-k { font-size: 11px; color: var(--txt3); }
.sw-v { font-size: 13px; color: var(--txt); font-weight: 600; }

/* PortPanel wrapper */
.sw-panels { margin-bottom: 14px; }

/* port table */
.sub-title { font-size: 11px; color: var(--cyan); font-weight: 600; margin-bottom: 8px; }
.port-table-wrap { margin-top: 10px; }
.port-table { max-height: 320px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10px; padding: 6px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 5px 8px; border-bottom: 1px solid var(--td-line); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }
.row-offline { color: var(--txt3); opacity: 0.7; }
.row-alarm { background: rgba(245,158,11,0.04); }

/* trunk grid */
.trunk-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.trunk-card { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.trunk-card.trunk-ok { border-color: rgba(34,197,94,0.2); background: rgba(34,197,94,0.03); }
.trunk-card.trunk-warn { border-color: rgba(245,158,11,0.25); background: rgba(245,158,11,0.03); }
.trunk-bar-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.trunk-meta { display: flex; flex-direction: column; gap: 2px; font-size: 11px; color: var(--txt2); margin-bottom: 8px; }
.trunk-members { font-size: 10px; color: var(--txt3); font-family: "SF Mono", Consolas, monospace; }
.trunk-util-bar { margin-top: 4px; }
.bar-label { margin-bottom: 3px; }
.bar-track { height: 6px; background: var(--track); border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; }
.bar-g { background: linear-gradient(90deg, rgba(34,197,94,.5), rgba(34,197,94,.85)); }
.bar-a { background: linear-gradient(90deg, rgba(245,158,11,.5), rgba(245,158,11,.85)); }
.bar-r { background: linear-gradient(90deg, rgba(239,68,68,.5), rgba(239,68,68,.85)); }

/* ping grid */
.ping-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ping-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.ping-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ping-meta { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; font-size: 11px; }

@media (max-width: 1180px) {
  .cols-4 { grid-template-columns: repeat(2, 1fr); }
  .trunk-grid, .ping-grid { grid-template-columns: 1fr 1fr; }
  .sw-meta-grid { grid-template-columns: 1fr 1fr; }
}
</style>
