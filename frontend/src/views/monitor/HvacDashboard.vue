<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('暖通空调') }}</h1>
      <span class="sub">{{ tl('冷源系统') }} / {{ tl('空调末端') }} / {{ tl('液冷系统') }} {{ tl('·') }} {{ tl('实时运行状态与关键能效指标') }}</span>
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard metric-name="hvac-total" :label="tl('HVAC 设备总数')" :value="overview.totalEquipment" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="hvac-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="hvac-fault" :label="tl('故障')" :value="overview.faultCount" unit="台" :quality="overview.faultCount ? 'bad' : 'good'" :online="true" :severity="overview.faultCount ? 'crit' : 'normal'" />
      <MetricCard metric-name="hvac-warning" :label="tl('告警')" :value="overview.warningCount" unit="台" :quality="overview.warningCount ? 'uncertain' : 'good'" :online="true" :severity="overview.warningCount ? 'warn' : 'normal'" />
    </div>

    <!-- 三列子系统卡片 -->
    <div class="grid cols-3" v-if="overview">
      <!-- 冷源系统 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('冷源系统') }}</span>
          <span class="pill" :class="overview.chiller.online === overview.chiller.total ? 'g' : 'a'">
            {{ overview.chiller.online }}/{{ overview.chiller.total }} {{ tl('在线') }}
          </span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span><span class="v">{{ overview.chiller.avgLoadPercent?.toFixed(1) ?? '-' }}%</span>
          <span class="k">{{ tl('进水温度均值') }}</span><span class="v">{{ overview.chiller.avgTemperatureIn?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('出水温度均值') }}</span><span class="v">{{ overview.chiller.avgTemperatureOut?.toFixed(1) ?? '-' }}°C</span>
        </div>
        <div class="device-list" v-if="overview.chiller.devices.length">
          <div class="device-row" v-for="d in overview.chiller.devices" :key="d.id">
            <div class="d-info">
              <span class="d-status" :class="statusCls(d.status)">●</span>
              <span class="d-name">{{ d.name }}</span>
              <span class="d-code">{{ d.code }}</span>
            </div>
            <div class="d-metrics">
              <span>{{ tl('负载') }} {{ d.loadPercent?.toFixed(0) ?? '-' }}%</span>
              <span class="sep">|</span>
              <span>{{ d.temperatureIn?.toFixed(1) ?? '-' }}/{{ d.temperatureOut?.toFixed(1) ?? '-' }}°C</span>
            </div>
          </div>
        </div>
        <div class="empty-tip" v-else>{{ tl('暂无冷源设备') }}</div>
      </div>

      <!-- 空调末端 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('空调末端') }} (CRAC)</span>
          <span class="pill" :class="overview.crac.online === overview.crac.total ? 'g' : 'a'">
            {{ overview.crac.online }}/{{ overview.crac.total }} {{ tl('在线') }}
          </span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('送风温度均值') }}</span><span class="v">{{ overview.crac.avgTemperatureOut?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('回风温度均值') }}</span><span class="v">{{ overview.crac.avgTemperatureIn?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('回风湿度均值') }}</span><span class="v">{{ overview.crac.avgHumidityIn?.toFixed(1) ?? '-' }}%</span>
          <span class="k">{{ tl('风机转速均值') }}</span><span class="v">{{ overview.crac.avgFanSpeed?.toFixed(0) ?? '-' }}%</span>
        </div>
        <div class="device-list" v-if="overview.crac.devices.length">
          <div class="device-row" v-for="d in overview.crac.devices" :key="d.id">
            <div class="d-info">
              <span class="d-status" :class="statusCls(d.status)">●</span>
              <span class="d-name">{{ d.name }}</span>
              <span class="d-code">{{ d.code }}</span>
            </div>
            <div class="d-metrics">
              <span>{{ d.fanSpeed?.toFixed(0) ?? '-' }}%</span>
              <span class="sep">|</span>
              <span>{{ d.temperatureIn?.toFixed(1) ?? '-' }}°C / {{ d.humidityIn?.toFixed(0) ?? '-' }}%</span>
            </div>
          </div>
        </div>
        <div class="empty-tip" v-else>{{ tl('暂无空调末端设备') }}</div>
      </div>

      <!-- 液冷系统 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('液冷系统') }}</span>
          <span class="pill" :class="overview.liquidCooling.online === overview.liquidCooling.total ? 'g' : 'a'">
            {{ overview.liquidCooling.online }}/{{ overview.liquidCooling.total }} {{ tl('在线') }}
          </span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均流量') }}</span><span class="v">{{ overview.liquidCooling.avgFlowRate?.toFixed(1) ?? '-' }} L/min</span>
          <span class="k">{{ tl('CDU进水温度均值') }}</span><span class="v">{{ overview.liquidCooling.avgCdiTemperature?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('CDU出水温度均值') }}</span><span class="v">{{ overview.liquidCooling.avgCdoTemperature?.toFixed(1) ?? '-' }}°C</span>
        </div>
        <div class="device-list" v-if="overview.liquidCooling.devices.length">
          <div class="device-row" v-for="d in overview.liquidCooling.devices" :key="d.id">
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
    </div>

    <!-- 加载 / 错误态 -->
    <div class="card" v-if="!overview && !error">
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
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import { getHvacOverview, type HvacOverview } from '@/api/hvac'

const overview = ref<HvacOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

function statusCls(s: string) {
  if (s === 'running') return 'g'
  if (s === 'fault') return 'r'
  if (s === 'warning') return 'a'
  return 'm'
}

async function load() {
  error.value = ''
  try {
    overview.value = await getHvacOverview()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.ct {
  font-weight: 600;
  font-size: 14px;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg2);
}
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }

.kvs {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  font-size: 12.5px;
  margin-bottom: 12px;
}
.k { color: var(--muted); }
.v { text-align: right; font-weight: 500; }

.device-list {
  border-top: 1px solid var(--border);
  padding-top: 8px;
  max-height: 280px;
  overflow-y: auto;
}
.device-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04));
}
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
