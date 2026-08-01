<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.fuel') }}</h1>
      <span class="sub">{{ tl('燃油监控') }} {{ tl('·') }} {{ tl('油位与油耗') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="fuel-total" :label="tl('设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="fuel-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="fuel-load" :label="tl('平均负载率')" :value="s.avgLoadPercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="fuel-voltage" :label="tl('平均电压')" :value="s.avgVoltage" unit="V" quality="good" :online="true" />
    </div>

    <div class="card" v-if="s">
      <div class="card-head">
        <span class="ct">{{ tl('nav.fuel') }}</span>
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
            <span v-if="d.fuelLevel != null">{{ tl('油位') }} {{ d.fuelLevel.toFixed(0) }}%</span>
            <span v-if="d.loadPercent != null"> | {{ tl('负载') }} {{ d.loadPercent.toFixed(0) }}%</span>
            <span v-if="d.powerKw != null"> | {{ d.powerKw.toFixed(1) }}kW</span>
          </div>
        </div>
      </div>
      <div class="empty-tip" v-else>{{ tl('暂无设备') }}</div>
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
import { getPowerFuel, type PowerSystemSummary } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<PowerSystemSummary | null>(null)
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
    s.value = await getPowerFuel()
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
.d-metrics { color: var(--muted); font-size: 11px; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
</style>
