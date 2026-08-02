<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }} {{ tl('·') }} {{ tl('nav.networkFirewall') }}</h1>
      <span class="sub">{{ tl('防火墙监控') }} {{ tl('·') }} {{ tl('策略命中 / 并发会话 / VPN / 威胁拦截') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="fw-total" :label="tl('防火墙')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="fw-sessions" :label="tl('并发会话')" :value="fmtNum(s.concurrentSessions)" unit="" quality="good" :online="true" />
      <MetricCard metric-name="fw-policy" :label="tl('安全策略')" :value="s.policyTotal" unit="条" quality="good" :online="true" />
      <MetricCard metric-name="fw-threat" :label="tl('威胁拦截')" :value="s.threatBlocked" unit="次" :quality="s.threatBlocked ? 'uncertain' : 'good'" :online="true" :severity="s.threatBlocked ? 'warn' : 'normal'" />
    </div>

    <template v-if="s">
      <div class="card" v-for="f in s.firewalls" :key="f.id">
        <div class="card-head">
          <span class="ct">{{ f.name }} <span class="muted">({{ f.id }})</span></span>
          <span class="pill" :class="f.status === 'online' ? 'g' : 'r'">{{ f.status === 'online' ? tl('在线') : tl('离线') }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('型号') }}</span><span class="v">{{ f.model }}</span></div>
          <div class="kv"><span class="k">{{ tl('位置') }}</span><span class="v">{{ f.location }}</span></div>
          <div class="kv"><span class="k">{{ tl('管理IP') }}</span><span class="v mono">{{ f.ip }}</span></div>
          <div class="kv"><span class="k">{{ tl('CPU') }}</span><span class="v" :class="f.cpu_pct > 80 ? 'a-text' : 'g-text'">{{ f.cpu_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('内存') }}</span><span class="v" :class="f.mem_pct > 80 ? 'a-text' : 'g-text'">{{ f.mem_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('温度') }}</span><span class="v">{{ f.temp_c }}°C</span></div>
          <div class="kv"><span class="k">{{ tl('吞吐') }}</span><span class="v mono">{{ fmtBps(f.throughput_bps) }}</span></div>
          <div class="kv"><span class="k">{{ tl('并发会话') }}</span><span class="v mono">{{ fmtNum(f.concurrent_sessions) }}</span></div>
          <div class="kv"><span class="k">{{ tl('新建会话率') }}</span><span class="v mono">{{ fmtNum(f.session_rate) }}/s</span></div>
          <div class="kv"><span class="k">{{ tl('VPN 隧道') }}</span><span class="v">{{ f.vpn_tunnels }}</span></div>
          <div class="kv"><span class="k">{{ tl('威胁拦截') }}</span><span class="v" :class="f.threat_blocked ? 'a-text' : 'g-text'">{{ f.threat_blocked }} {{ tl('次') }}</span></div>
          <div class="kv"><span class="k">{{ tl('运行时长') }}</span><span class="v">{{ f.uptime_days }} {{ tl('天') }}</span></div>
        </div>

        <div class="sub-title">{{ tl('策略命中 Top') }}</div>
        <div class="hit-list">
          <div class="hit-row" v-for="(p, i) in f.policy_hit_top" :key="i">
            <span class="hit-rank mono">{{ i + 1 }}</span>
            <span class="hit-name">{{ p.name }}</span>
            <span class="hit-bar"><span class="hit-fill" :style="{ width: Math.min(100, p.hits / f.policy_hit_top[0].hits * 100) + '%' }"></span></span>
            <span class="hit-val mono">{{ fmtNum(p.hits) }}</span>
          </div>
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
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getNetworkFirewallsDetailed, type NetworkFirewallSummary } from '@/api/monitor'
const { t: tl } = useI18n()

const s = ref<NetworkFirewallSummary | null>(null)
const error = ref('')

function fmtNum(v: number): string {
  return v >= 1000 ? (v / 1000).toFixed(v >= 10000 ? 0 : 1) + 'k' : String(v)
}
function fmtBps(v: number): string {
  if (!v) return '0'
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + ' Mbps'
  return (v / 1e3).toFixed(1) + ' Kbps'
}

async function load() {
  error.value = ''
  try {
    s.value = await getNetworkFirewallsDetailed()
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
.pill.r { background: rgba(255,77,94,0.12); color: var(--red); }
.muted { color: var(--txt2); } .mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }
.g-text { color: var(--green); } .a-text { color: var(--amber); }

.kv-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); } .v { font-size: 13px; color: var(--txt); font-weight: 600; }

.sub-title { font-size: 11px; color: var(--cyan); font-weight: 600; margin: 10px 0 6px; }
.hit-list { display: flex; flex-direction: column; gap: 5px; }
.hit-row { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.hit-rank { width: 18px; color: var(--txt3); }
.hit-name { width: 220px; }
.hit-bar { flex: 1; height: 10px; background: var(--track); border-radius: 3px; overflow: hidden; }
.hit-fill { display: block; height: 100%; background: linear-gradient(90deg, rgba(34,227,255,.4), rgba(34,227,255,.8)); border-radius: 3px; }
.hit-val { width: 60px; text-align: right; font-weight: 600; }

.flex { display: flex; } .center { align-items: center; } .grid { display: grid; gap: 12px; }
@media (max-width: 1180px) { .kv-grid { grid-template-columns: 1fr; } }
</style>
