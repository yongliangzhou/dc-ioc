<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }}</h1>
      <span class="sub">{{ tl('nav.hv') }} / {{ tl('nav.lv') }} / {{ tl('nav.genset') }} / {{ tl('nav.fuel') }} / {{ tl('nav.battery') }} {{ tl('·') }} {{ tl('实时电力参数与运行状态') }}</span>
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard metric-name="power-total" :label="tl('电力设备总数')" :value="overview.totalEquipment" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="power-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="power-fault" :label="tl('故障')" :value="overview.faultCount" unit="台" :quality="overview.faultCount ? 'bad' : 'good'" :online="true" :severity="overview.faultCount ? 'crit' : 'normal'" />
      <MetricCard metric-name="power-warning" :label="tl('告警')" :value="overview.warningCount" unit="台" :quality="overview.warningCount ? 'uncertain' : 'good'" :online="true" :severity="overview.warningCount ? 'warn' : 'normal'" />
    </div>

    <!-- 五子系统卡片 -->
    <div class="grid cols-2" v-if="overview">
      <SystemCard icon="🔌" :title="tl('nav.hv')" :label="tl('10KV 中压配电')" :sys="overview.hv" />
      <SystemCard icon="⚡" :title="tl('nav.lv')" :label="tl('0.4KV 低压配电')" :sys="overview.lv" />
    </div>
    <div class="grid cols-3" v-if="overview" style="margin-top:12px">
      <SystemCard icon="🔧" :title="tl('nav.genset')" :label="tl('柴发并机系统')" :sys="overview.genset" />
      <SystemCard icon="⛽" :title="tl('nav.fuel')" :label="tl('燃油监控')" :sys="overview.fuel" />
      <SystemCard icon="🔋" :title="tl('nav.battery')" :label="tl('电池监控')" :sys="overview.battery" />
    </div>

    <!-- 加载 / 错误态 -->
    <div class="card" v-if="!overview && !error">
      <div class="flex center" style="padding:40px"><span class="muted">{{ tl('common.loading') }}</span></div>
    </div>
    <div class="card" v-if="error">
      <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('common.error') }}: {{ error }}</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerOverview, type PowerOverview, type PowerSystemSummary } from '@/api/power'
const { t: tl } = useI18n()

const overview = ref<PowerOverview | null>(null)
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
    overview.value = await getPowerOverview()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)
</script>

<script lang="ts">
import { defineComponent, h, type PropType } from 'vue'
import type { PowerDeviceView } from '@/api/power'

const SystemCard = defineComponent({
  props: {
    icon: String,
    title: String,
    label: String,
    sys: { type: Object as PropType<PowerSystemSummary>, required: true },
  },
  setup(props) {
    return () => {
      const s = props.sys
      const d = s?.devices ?? []
      return h('div', { class: 'card' }, [
        h('div', { class: 'card-head' }, [
          h('span', { class: 'ct' }, [(props.icon ?? '') + ' ' + (props.title ?? '')]),
          h('span', { class: 'pill ' + (s?.online === s?.total ? 'g' : 'a') },
            `${s?.online ?? 0}/${s?.total ?? 0} 在线`),
        ]),
        props.label ? h('div', { class: 'sub-label' }, props.label) : null,
        h('div', { class: 'kvs' }, [
          ['平均负载率', s?.avgLoadPercent != null ? s.avgLoadPercent.toFixed(1) + '%' : '-'],
          ['平均电压', s?.avgVoltage != null ? s.avgVoltage.toFixed(1) + 'V' : '-'],
          ['平均电流', s?.avgCurrent != null ? s.avgCurrent.toFixed(1) + 'A' : '-'],
        ].map(([k, v]) => [h('span', { class: 'k' }, k), h('span', { class: 'v' }, v)]).flat()),
        d.length > 0
          ? h('div', { class: 'device-list' },
              d.map((dev: PowerDeviceView) =>
                h('div', { class: 'device-row', key: dev.id }, [
                  h('div', { class: 'd-info' }, [
                    h('span', { class: 'd-status ' + (dev.status === 'running' ? 'g' : dev.status === 'fault' ? 'r' : dev.status === 'warning' ? 'a' : 'm') }, '●'),
                    h('span', { class: 'd-name' }, dev.name),
                    h('span', { class: 'd-code' }, dev.code),
                  ]),
                  h('div', { class: 'd-metrics' }, [
                    dev.loadPercent != null ? `负载 ${dev.loadPercent.toFixed(0)}%` : null,
                    dev.powerKw != null ? ` | ${dev.powerKw.toFixed(1)}kW` : null,
                    dev.voltage != null ? ` | ${dev.voltage.toFixed(0)}V` : null,
                    dev.fuelLevel != null ? ` | 油位 ${dev.fuelLevel.toFixed(0)}%` : null,
                  ].filter(Boolean).join('')),
                ])
              )
            )
          : h('div', { class: 'empty-tip' }, '暂无设备'),
      ])
    }
  },
})
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.ct {
  font-weight: 600;
  font-size: 14px;
}
.sub-label {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 8px;
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
  max-height: 220px;
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
.d-metrics { color: var(--muted); font-size: 11px; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
</style>
