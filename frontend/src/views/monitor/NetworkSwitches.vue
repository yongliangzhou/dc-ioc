<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }} {{ tl('·') }} {{ tl('nav.networkSwitch') }}</h1>
      <span class="sub">{{ tl('交换机监控') }} {{ tl('·') }} {{ tl('端口流量 / 光功率 / 链路聚合 / 堆叠 / 链路质量') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="sw-total" :label="tl('交换机')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="sw-port-rate" :label="tl('端口可用率')" :value="s.overallPortRate" unit="%" :quality="s.overallPortRate < 95 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="sw-cpu" :label="tl('平均CPU')" :value="Number(s.avgCpu)" unit="%" :quality="s.avgCpu > 80 ? 'bad' : s.avgCpu > 60 ? 'uncertain' : 'good'" :online="true" :severity="s.avgCpu > 80 ? 'crit' : 'normal'" />
      <MetricCard metric-name="sw-traffic" :label="tl('总吞吐')" :value="s.totalTrafficBps" unit="" quality="good" :online="true" />
    </div>

    <template v-if="s">
      <!-- 链路质量 Ping -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('链路质量探测 (Ping)') }}</span>
          <span class="pill" :class="s.avgPingLossPct > 1 ? 'a' : 'g'">{{ tl('平均') }} {{ s.avgPingRttMs }}ms / 丢包 {{ s.avgPingLossPct }}%</span>
        </div>
        <div class="ping-grid">
          <div class="ping-block" v-for="p in s.pingTargets" :key="p.target">
            <div class="ping-head">
              <span class="d-name">{{ p.name }}</span>
              <span class="tag" :class="pingCls(p.status)">{{ pingText(p.status) }}</span>
            </div>
            <div class="ping-meta">
              <span class="muted">{{ tl('RTT') }}</span><span class="mono">{{ p.rtt_avg_ms }}ms ({{ p.rtt_min_ms }}~{{ p.rtt_max_ms }})</span>
              <span class="muted">{{ tl('抖动') }}</span><span class="mono">{{ p.jitter_ms }}ms</span>
              <span class="muted">{{ tl('丢包') }}</span><span class="mono" :class="p.loss_pct > 1 ? 'a-text' : 'g-text'">{{ p.loss_pct }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 带宽 TopN -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('带宽利用率 Top 10') }}</span><span class="pill" :class="bwAlertCount ? 'a' : 'g'">{{ tl('超阈值') }} {{ bwAlertCount }} {{ tl('条') }}</span></div>
        <div class="bw-list">
          <div class="bw-row" v-for="b in s.bwTopN" :key="b.rank">
            <span class="bw-rank mono">{{ b.rank }}</span>
            <span class="bw-name">{{ b.name }}</span>
            <span class="bw-dir" :class="b.direction === 'in' ? 'di' : 'do'">{{ b.direction === 'in' ? tl('入') : tl('出') }}</span>
            <span class="bw-bar"><span class="bw-fill" :class="bwCls(b.util_pct)" :style="{ width: Math.min(100, b.util_pct) + '%' }"></span></span>
            <span class="bw-val mono">{{ b.util_pct }}%</span>
            <span class="bw-traffic muted">{{ fmtBps(b.traffic_bps) }} / {{ b.capacity_mbps }}Mbps</span>
          </div>
        </div>
      </div>

      <!-- 交换机逐台 -->
      <div class="card" v-for="sw in s.switches" :key="sw.id">
        <div class="card-head">
          <span class="ct">{{ sw.name }} <span class="muted">({{ sw.id }})</span></span>
          <span class="pill" :class="sw.status === 'online' ? 'g' : 'r'">{{ sw.status === 'online' ? tl('在线') : tl('离线') }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('型号') }}</span><span class="v">{{ sw.model }}</span></div>
          <div class="kv"><span class="k">{{ tl('位置') }}</span><span class="v">{{ sw.location }}</span></div>
          <div class="kv"><span class="k">{{ tl('管理IP') }}</span><span class="v mono">{{ sw.ip }}</span></div>
          <div class="kv"><span class="k">{{ tl('角色') }}</span><span class="v">{{ sw.role }}</span></div>
          <div class="kv"><span class="k">{{ tl('CPU') }}</span><span class="v" :class="sw.cpu_pct > 80 ? 'a-text' : 'g-text'">{{ sw.cpu_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('内存') }}</span><span class="v" :class="sw.mem_pct > 80 ? 'a-text' : 'g-text'">{{ sw.mem_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('温度') }}</span><span class="v">{{ sw.temp_c }}°C</span></div>
          <div class="kv"><span class="k">{{ tl('运行时长') }}</span><span class="v">{{ sw.uptime_days }} {{ tl('天') }}</span></div>
          <div class="kv"><span class="k">{{ tl('端口') }}</span><span class="v">{{ sw.up_ports }}/{{ sw.total_ports }} {{ tl('up') }} ({{ tl('down') }} {{ sw.down_ports }})</span></div>
          <div class="kv"><span class="k">{{ tl('堆叠') }}</span><span class="v" v-if="sw.stack">{{ sw.stack.topo }} · {{ sw.stack.members }} 成员 · {{ sw.stack.status }}</span><span class="v" v-else>{{ tl('不支持') }}</span></div>
        </div>

        <!-- 链路聚合 -->
        <div class="sub-title" v-if="sw.trunks.length">{{ tl('链路聚合 (Eth-Trunk)') }}</div>
        <div class="trunk-list" v-if="sw.trunks.length">
          <span class="trunk" v-for="t in sw.trunks" :key="t.id">
            <b>{{ t.id }}</b> {{ t.mode }} · {{ t.members.join('/') }} · {{ t.util_pct }}%
          </span>
        </div>

        <!-- 端口表 (仅显示 up 或有异常的端口, 限 16 条) -->
        <div class="sub-title">{{ tl('端口详情') }} ({{ tl('状态/速率/利用率/错包/光功率') }})</div>
        <div class="port-scroll scroll-x">
          <table>
            <thead><tr>
              <th>{{ tl('端口') }}</th><th>{{ tl('状态') }}</th><th>{{ tl('速率') }}</th>
              <th>{{ tl('入利用率') }}</th><th>{{ tl('出利用率') }}</th><th>{{ tl('入流量') }}</th>
              <th>{{ tl('错包') }}</th><th>{{ tl('收光') }}</th><th>{{ tl('发光') }}</th><th>{{ tl('光告警') }}</th>
            </tr></thead>
            <tbody>
              <tr v-for="p in visiblePorts(sw)" :key="p.name" :class="portRowCls(p)">
                <td class="mono">{{ p.name }}</td>
                <td><span class="tag" :class="p.status === 'up' ? 'g' : 'r'">{{ p.status }}</span></td>
                <td class="mono">{{ p.speed_mbps }}M</td>
                <td class="mono" :class="utilCls(p.in_util_pct)">{{ p.in_util_pct }}%</td>
                <td class="mono" :class="utilCls(p.out_util_pct)">{{ p.out_util_pct }}%</td>
                <td class="mono">{{ fmtBps(p.in_bps + p.out_bps) }}</td>
                <td class="mono" :class="(p.in_errors + p.out_errors) ? 'a-text' : 'g-text'">{{ p.in_errors + p.out_errors }}</td>
                <td class="mono" v-if="p.rx_power_dbm != null">{{ p.rx_power_dbm }}dBm</td>
                <td class="mono muted" v-else>-</td>
                <td class="mono" v-if="p.tx_power_dbm != null">{{ p.tx_power_dbm }}dBm</td>
                <td class="mono muted" v-else>-</td>
                <td><span class="tag" :class="p.optical_alarm && p.optical_alarm !== '正常' ? 'a' : 'g'">{{ p.optical_alarm || '-' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div class="card" v-if="!s && !error">
      <div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div>
    </div>
    <div class="card" v-if="error">
      <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getNetworkSwitchesDetailed, type NetworkSwitchSummary, type SwitchView, type SwitchPortView } from '@/api/monitor'
const { t: tl } = useI18n()

const s = ref<NetworkSwitchSummary | null>(null)
const error = ref('')

const bwAlertCount = computed(() => (s.value?.bwTopN ?? []).filter((b) => b.alert).length)

function fmtBps(v: number): string {
  if (!v) return '0'
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + ' Mbps'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + ' Kbps'
  return v + ' bps'
}
function pingCls(st: string): string {
  if (st === 'ok') return 'g'
  if (st === 'lossy') return 'a'
  return 'r'
}
function pingText(st: string): string {
  if (st === 'ok') return tl('正常')
  if (st === 'lossy') return tl('丢包')
  return tl('不可达')
}
function bwCls(v: number): string {
  if (v > 85) return 'r'
  if (v > 70) return 'a'
  return 'g'
}
function utilCls(v: number): string {
  if (v > 85) return 'a-text'
  return 'g-text'
}
function portRowCls(p: SwitchPortView): string {
  if (p.status !== 'up') return 'row-down'
  if (p.optical_alarm && p.optical_alarm !== '正常') return 'row-warn'
  if (p.in_errors + p.out_errors > 0) return 'row-warn'
  return ''
}
function visiblePorts(sw: SwitchView): SwitchPortView[] {
  // up 端口 + 所有异常端口, 最多 16 行
  const up = sw.ports.filter((p) => p.status === 'up')
  const odd = sw.ports.filter((p) => p.status !== 'up' || p.optical_alarm && p.optical_alarm !== '正常' || (p.in_errors + p.out_errors) > 0)
  return odd.length ? odd.slice(0, 16) : up.slice(0, 16)
}

async function load() {
  error.value = ''
  try {
    s.value = await getNetworkSwitchesDetailed()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }
.muted { color: var(--txt2); } .mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }
.g-text { color: var(--green); } .a-text { color: var(--amber); }

.kv-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); } .v { font-size: 13px; color: var(--txt); font-weight: 600; }

.ping-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.ping-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.ping-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ping-meta { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; font-size: 11px; }

.bw-list { display: flex; flex-direction: column; gap: 6px; }
.bw-row { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.bw-rank { width: 18px; color: var(--txt3); }
.bw-name { width: 180px; font-weight: 500; }
.bw-dir { width: 18px; text-align: center; font-size: 11px; padding: 1px 0; border-radius: 4px; }
.bw-dir.di { background: rgba(34,227,255,0.12); color: var(--cyan); }
.bw-dir.do { background: rgba(255,176,32,0.12); color: var(--amber); }
.bw-bar { flex: 1; height: 12px; background: var(--track); border-radius: 3px; overflow: hidden; }
.bw-fill { display: block; height: 100%; border-radius: 3px; }
.bw-fill.g { background: linear-gradient(90deg, rgba(43,212,122,.5), rgba(43,212,122,.85)); }
.bw-fill.a { background: linear-gradient(90deg, rgba(255,176,32,.5), rgba(255,176,32,.85)); }
.bw-fill.r { background: linear-gradient(90deg, rgba(255,77,94,.5), rgba(255,77,94,.85)); }
.bw-val { width: 44px; text-align: right; font-weight: 600; }
.bw-traffic { width: 150px; text-align: right; }

.trunk-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.trunk { font-size: 11px; padding: 3px 9px; border-radius: 6px; background: rgba(34,227,255,0.08); border: 1px solid rgba(34,227,255,0.25); color: var(--txt); }
.sub-title { font-size: 11px; color: var(--cyan); font-weight: 600; margin: 10px 0 6px; }

.port-scroll { max-height: 320px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10px; padding: 6px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 5px 8px; border-bottom: 1px solid var(--td-line); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }
tbody .row-warn { background: rgba(250,173,20,0.06); }
tbody .row-down { color: var(--txt3); }

.tag { display: inline-block; font-size: 10px; padding: 1px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }

.flex { display: flex; } .center { align-items: center; } .scroll-x { overflow-x: auto; } .grid { display: grid; gap: 12px; }
@media (max-width: 1180px) { .ping-grid, .kv-grid { grid-template-columns: 1fr 1fr; } }
</style>
