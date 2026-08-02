<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }} {{ tl('·') }} {{ tl('nav.networkRouter') }}</h1>
      <span class="sub">{{ tl('路由器监控') }} {{ tl('·') }} {{ tl('路由转发 / BGP·OSPF / 会话 / 吞吐') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="rt-total" :label="tl('路由器')" :value="Number(s.total)" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="rt-bgp" :label="tl('BGP 状态')" :value="s.bgpState === 'Established' ? 1 : 0" unit="" :quality="s.bgpState === 'Established' ? 'good' : 'bad'" :online="true" :severity="s.bgpState === 'Established' ? 'normal' : 'crit'" />
      <MetricCard metric-name="rt-routes" :label="tl('路由表')" :value="Number(s.routesTotal)" unit="条" quality="good" :online="true" />
      <MetricCard metric-name="rt-sessions" :label="tl('会话数')" :value="s.totalSessions" unit="" quality="good" :online="true" />
    </div>

    <template v-if="s">
      <div class="card" v-for="r in s.routers" :key="r.id">
        <div class="card-head">
          <span class="ct">{{ r.name }} <span class="muted">({{ r.id }})</span></span>
          <span class="pill" :class="r.status === 'online' ? 'g' : 'r'">{{ r.status === 'online' ? tl('在线') : tl('离线') }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('型号') }}</span><span class="v">{{ r.model }}</span></div>
          <div class="kv"><span class="k">{{ tl('角色') }}</span><span class="v">{{ r.role }}</span></div>
          <div class="kv"><span class="k">{{ tl('管理IP') }}</span><span class="v mono">{{ r.ip }}</span></div>
          <div class="kv"><span class="k">{{ tl('CPU') }}</span><span class="v" :class="r.cpu_pct > 80 ? 'a-text' : 'g-text'">{{ r.cpu_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('内存') }}</span><span class="v" :class="r.mem_pct > 80 ? 'a-text' : 'g-text'">{{ r.mem_pct }}%</span></div>
          <div class="kv"><span class="k">{{ tl('温度') }}</span><span class="v">{{ r.temp_c }}°C</span></div>
          <div class="kv"><span class="k">{{ tl('吞吐') }}</span><span class="v mono">{{ fmtBps(r.throughput_bps) }}</span></div>
          <div class="kv"><span class="k">{{ tl('并发会话') }}</span><span class="v mono">{{ fmtNum(r.sessions) }}</span></div>
          <div class="kv"><span class="k">{{ tl('BGP') }}</span><span class="v" :class="r.bgp_state === 'Established' ? 'g-text' : 'a-text'">{{ r.bgp_state }}</span></div>
          <div class="kv"><span class="k">{{ tl('OSPF 邻居') }}</span><span class="v">{{ r.ospf_neighbors }}</span></div>
          <div class="kv"><span class="k">{{ tl('路由条目') }}</span><span class="v mono">{{ fmtNum(r.routes_total) }}</span></div>
        </div>
        <div class="sub-title">{{ tl('路由协议状态') }}</div>
        <div class="proto-list">
          <div class="proto" v-for="p in r.protocols" :key="p.name" :class="protoCls(p)">
            <div class="proto-head">
              <b>{{ p.name }}</b>
              <span class="tag" :class="p.flake ? 'a' : 'g'">{{ p.state }}</span>
              <span v-if="p.flake" class="flake">⚠ {{ tl('抖动') }}</span>
            </div>
            <div class="proto-meta muted">
              <span v-if="p.peer_total != null">{{ tl('邻居') }} {{ p.peer_up }}/{{ p.peer_total }}</span>
              <span v-if="p.neighbor_total != null">{{ tl('邻居') }} {{ p.neighbor_up }}/{{ p.neighbor_total }}</span>
              <span v-if="p.area != null">{{ tl('区域') }} {{ p.area }}</span>
              <span>{{ tl('路由') }} {{ fmtNum(p.routes) }}</span>
              <span>{{ p.desc }}</span>
            </div>
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
import { getNetworkRoutersDetailed, type NetworkRouterSummary, type RouterProtocolView } from '@/api/monitor'
const { t: tl } = useI18n()

const s = ref<NetworkRouterSummary | null>(null)
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
function protoCls(p: RouterProtocolView): string {
  if (p.flake) return 'proto-warn'
  return ''
}

async function load() {
  error.value = ''
  try {
    s.value = await getNetworkRoutersDetailed()
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
.proto-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.proto { border: 1px solid var(--td-line); border-radius: 8px; padding: 8px 10px; background: var(--bg2); }
.proto.proto-warn { border-color: rgba(255,176,32,.4); }
.proto-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.proto-head b { font-size: 12.5px; }
.flake { font-size: 10px; color: var(--amber); }
.proto-meta { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; }

.tag { font-size: 10px; padding: 1px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }

.flex { display: flex; } .center { align-items: center; } .grid { display: grid; gap: 12px; }
@media (max-width: 1180px) { .kv-grid, .proto-list { grid-template-columns: 1fr; } }
</style>
