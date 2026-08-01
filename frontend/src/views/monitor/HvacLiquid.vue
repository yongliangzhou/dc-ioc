<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.hvacMonitor') }} {{ tl('·') }} {{ tl('nav.liquidCooling') }}</h1>
      <span class="sub">{{ tl('液冷系统') }} {{ tl('·') }} {{ tl('CDU 流量与进出液温度') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="liquid-total" :label="tl('液冷设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="liquid-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="liquid-flow" :label="tl('平均流量')" :value="s.avgFlowRate" unit="L/min" quality="good" :online="true" />
      <MetricCard metric-name="liquid-temp" :label="tl('CDU 进出液温度')" :value="s.avgCdoTemperature" unit="°C" quality="good" :online="true" />
    </div>

    <div class="card" v-if="s">
      <div class="card-head">
        <span class="ct">{{ tl('nav.liquidCooling') }}</span>
        <span class="pill" :class="s.online === s.total ? 'g' : 'a'">{{ s.online }}/{{ s.total }} {{ tl('在线') }}</span>
      </div>
      <div class="device-list" v-if="s.devices.length">
        <div class="device-row" v-for="d in s.devices" :key="d.id">
          <div class="d-info">
            <span class="d-status" :class="statusCls(d.status)">●</span>
            <span class="d-name">{{ d.name }}</span>
            <span class="d-code">{{ d.code }}</span>
          </div>
          <div class="d-metrics">
            <span>{{ d.flowRate?.toFixed(0) ?? '-' }} L/min</span>
            <span class="sep">|</span>
            <span>{{ d.cdiTemperature?.toFixed(1) ?? '-' }}/{{ d.cdoTemperature?.toFixed(1) ?? '-' }}°C</span>
          </div>
        </div>
      </div>
      <div class="empty-tip" v-else>{{ tl('暂无液冷设备') }}</div>
    </div>

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
import { getLiquidCooling, type LiquidCoolingSummary } from '@/api/hvac'
const { t: tl } = useI18n()

const s = ref<LiquidCoolingSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})

function statusCls(st: string) {
  if (st === 'running' || st === 'online') return 'g'
  if (st === 'fault') return 'r'
  if (st === 'warning') return 'a'
  return 'm'
}

async function load() {
  error.value = ''
  try {
    s.value = await getLiquidCooling()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }
.device-list { border-top: 1px solid var(--border); padding-top: 8px; max-height: 420px; overflow-y: auto; }
.device-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; font-size: 12px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.device-row:last-child { border-bottom: none; }
.d-info { display: flex; align-items: center; gap: 6px; }
.d-status { font-size: 8px; }
.d-status.g { color: var(--green); }
.d-status.r { color: var(--red); }
.d-status.a { color: var(--amber); }
.d-status.m { color: var(--muted); }
.d-name { font-weight: 500; }
.d-code { color: var(--muted); font-size: 11px; }
.d-metrics { color: var(--muted); font-size: 11px; display: flex; gap: 4px; }
.d-metrics .sep { opacity: 0.3; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
</style>
