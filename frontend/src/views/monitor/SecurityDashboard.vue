<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }}</h1>
      <span class="sub">{{ tl('nav.securityCctv') }} / {{ tl('nav.securityAcs') }} / {{ tl('nav.securityIds') }} / {{ tl('nav.securityFire') }} {{ tl('·') }} {{ tl('实时安防态势与事件记录') }}</span>
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard metric-name="sec-total" :label="tl('安防设备总数')" :value="overview.totalEquipment" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="sec-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="sec-fault" :label="tl('故障')" :value="overview.faultCount" unit="台" :quality="overview.faultCount ? 'bad' : 'good'" :online="true" :severity="overview.faultCount ? 'crit' : 'normal'" />
      <MetricCard metric-name="sec-warning" :label="tl('告警')" :value="overview.warningCount" unit="台" :quality="overview.warningCount ? 'uncertain' : 'good'" :online="true" :severity="overview.warningCount ? 'warn' : 'normal'" />
    </div>

    <!-- 四子系统卡片 -->
    <div class="grid cols-2" v-if="overview">
      <SystemCard icon="📹" :title="tl('nav.securityCctv')" :label="tl('视频监控 · 实时录像与回放')" :sys="overview.cctv" />
      <SystemCard icon="🔐" :title="tl('nav.securityAcs')" :label="tl('门禁管理 · 出入控制与授权')" :sys="overview.acs" />
    </div>
    <div class="grid cols-2" v-if="overview" style="margin-top:12px">
      <SystemCard icon="🛡️" :title="tl('nav.securityIds')" :label="tl('防入侵系统 · 周界与内部探测')" :sys="overview.ids" />
      <SystemCard icon="🔥" :title="tl('nav.securityFire')" :label="tl('消防报警 · 烟感/温感/灭火')" :sys="overview.fire" />
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
import { getSecurityOverview, type SecurityOverview } from '@/api/security'
const { t: tl } = useI18n()

const overview = ref<SecurityOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

async function load() {
  error.value = ''
  try {
    overview.value = await getSecurityOverview()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)
</script>

<script lang="ts">
import { defineComponent, h, type PropType } from 'vue'
import type { SecuritySystemSummary, SecurityDeviceView } from '@/api/security'

const SystemCard = defineComponent({
  props: {
    icon: String,
    title: String,
    label: String,
    sys: { type: Object as PropType<SecuritySystemSummary>, required: true },
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
          ['今日事件', `${s?.eventsToday ?? 0}` + ' 起'],
          ['今日告警', `${s?.alertsToday ?? 0}` + ' 起'],
        ].map(([k, v]) => [h('span', { class: 'k' }, k), h('span', { class: 'v' }, v)]).flat()),
        d.length > 0
          ? h('div', { class: 'device-list' },
              d.map((dev: SecurityDeviceView) =>
                h('div', { class: 'device-row', key: dev.id }, [
                  h('div', { class: 'd-info' }, [
                    h('span', { class: 'd-status ' + (dev.status === 'running' ? 'g' : dev.status === 'fault' ? 'r' : dev.status === 'warning' ? 'a' : 'm') }, '●'),
                    h('span', { class: 'd-name' }, dev.name),
                    h('span', { class: 'd-code' }, dev.code),
                  ]),
                  h('div', { class: 'd-metrics' }, [
                    dev.lastEvent ? `最近: ${dev.lastEvent}` : null,
                    dev.lastEventTime ? ` | ${dev.lastEventTime}` : null,
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
.d-metrics { color: var(--muted); font-size: 11px; text-align: right; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
</style>
