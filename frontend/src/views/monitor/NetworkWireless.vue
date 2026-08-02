<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }} {{ tl('·') }} {{ tl('nav.networkWireless') }}</h1>
      <span class="sub">{{ tl('无线监控') }} {{ tl('·') }} {{ tl('AP 射频(2.4G/5G) / 用户数 / 信号强度 / 噪声') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="ap-total" :label="tl('AP 总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="ap-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="ap-users" :label="tl('接入用户')" :value="s.users" unit="人" quality="good" :online="true" />
      <MetricCard metric-name="ap-rssi" :label="tl('平均信号')" :value="s.avgRssi" unit="dBm" :quality="s.avgRssi > -65 ? 'good' : s.avgRssi > -75 ? 'uncertain' : 'bad'" :online="true" :severity="s.avgRssi > -65 ? 'normal' : 'warn'" />
    </div>

    <template v-if="s">
      <div class="card" v-for="ap in s.aps" :key="ap.id">
        <div class="card-head">
          <span class="ct">{{ ap.name }} <span class="muted">({{ ap.location }})</span></span>
          <span class="pill" :class="ap.status === 'online' ? 'g' : 'r'">{{ ap.status === 'online' ? tl('在线') : tl('离线') }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('型号') }}</span><span class="v">{{ ap.model }}</span></div>
          <div class="kv"><span class="k">{{ tl('管理IP') }}</span><span class="v mono">{{ ap.ip }}</span></div>
          <div class="kv"><span class="k">{{ tl('接入用户') }}</span><span class="v">{{ ap.users_total }} {{ tl('人') }}</span></div>
          <div class="kv"><span class="k">{{ tl('接收信号') }}</span><span class="v" :class="ap.rx_rssi_dbm > -65 ? 'g-text' : 'a-text'">{{ ap.rx_rssi_dbm }} dBm</span></div>
          <div class="kv"><span class="k">{{ tl('底噪') }}</span><span class="v mono">{{ ap.noise_floor_dbm }} dBm</span></div>
          <div class="kv"><span class="k">{{ tl('运行时长') }}</span><span class="v">{{ ap.uptime_days }} {{ tl('天') }}</span></div>
        </div>

        <!-- 双射频 -->
        <div class="radio-grid">
          <div class="radio-block" v-for="(r, key) in [['2.4G', ap.radio_2g], ['5G', ap.radio_5g]]" :key="key">
            <div class="radio-head">
              <span class="d-name">{{ r[0] }}</span>
              <span class="tag" :class="r[1].status === 'up' ? 'g' : 'r'">{{ r[1].status }}</span>
            </div>
            <div class="radio-meta">
              <span class="muted">{{ tl('信道') }}</span><span class="mono">{{ r[1].channel }}</span>
              <span class="muted">{{ tl('功率') }}</span><span class="mono">{{ r[1].tx_power_dbm }}dBm</span>
              <span class="muted">{{ tl('用户') }}</span><span class="mono">{{ r[1].users }}</span>
              <span class="muted">{{ tl('利用率') }}</span><span class="mono" :class="r[1].util_pct > 70 ? 'a-text' : 'g-text'">{{ r[1].util_pct }}%</span>
            </div>
            <div class="radio-bar"><span class="radio-fill" :class="r[1].util_pct > 70 ? 'a' : 'g'" :style="{ width: Math.min(100, r[1].util_pct) + '%' }"></span></div>
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
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getNetworkWirelessDetailed, type NetworkWirelessSummary } from '@/api/monitor'
const { t: tl } = useI18n()

const s = ref<NetworkWirelessSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})

async function load() {
  error.value = ''
  try {
    s.value = await getNetworkWirelessDetailed()
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

.radio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }
.radio-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 8px 10px; background: var(--bg2); }
.radio-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.radio-meta { display: grid; grid-template-columns: auto auto; gap: 2px 10px; font-size: 11px; margin-bottom: 6px; }
.radio-bar { height: 8px; background: var(--track); border-radius: 3px; overflow: hidden; }
.radio-fill { display: block; height: 100%; border-radius: 3px; }
.radio-fill.g { background: linear-gradient(90deg, rgba(43,212,122,.5), rgba(43,212,122,.85)); }
.radio-fill.a { background: linear-gradient(90deg, rgba(255,176,32,.5), rgba(255,176,32,.85)); }

.tag { font-size: 10px; padding: 1px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }

.flex { display: flex; } .center { align-items: center; } .grid { display: grid; gap: 12px; }
@media (max-width: 1180px) { .kv-grid, .radio-grid { grid-template-columns: 1fr; } }
</style>
