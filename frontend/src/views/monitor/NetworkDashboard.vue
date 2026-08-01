<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }}</h1>
      <span class="sub">{{ tl('nav.networkSwitch') }} / {{ tl('nav.networkRouter') }} / {{ tl('nav.networkFirewall') }} / {{ tl('nav.networkWireless') }} {{ tl('·') }} {{ tl('实时通信链路状态与流量') }}</span>
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard metric-name="net-total" :label="tl('网络设备总数')" :value="overview.totalEquipment" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="net-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="net-ping" :label="tl('全网平均延迟')" :value="overview.avgPingMs" unit="ms" :quality="overview.avgPingMs && overview.avgPingMs > 20 ? 'uncertain' : 'good'" :online="true" :severity="overview.avgPingMs && overview.avgPingMs > 50 ? 'warn' : 'normal'" />
      <MetricCard metric-name="net-bw" :label="tl('全网平均带宽利用率')" :value="overview.avgBwUtilization" unit="%" :quality="overview.avgBwUtilization && overview.avgBwUtilization > 70 ? 'uncertain' : 'good'" :online="true" :severity="overview.avgBwUtilization && overview.avgBwUtilization > 85 ? 'warn' : 'normal'" />
    </div>

    <!-- 四子系统卡片 -->
    <div class="grid cols-2" v-if="overview">
      <SystemCard icon="🔀" :title="tl('nav.networkSwitch')" :label="tl('核心层 · 汇聚层 · 接入层')" :sys="overview.switchs" />
      <SystemCard icon="📡" :title="tl('nav.networkRouter')" :label="tl('路由转发 · 协议状态')" :sys="overview.routers" />
    </div>
    <div class="grid cols-2" v-if="overview" style="margin-top:12px">
      <SystemCard icon="🛡️" :title="tl('nav.networkFirewall')" :label="tl('安全策略 · 流量过滤')" :sys="overview.firewalls" />
      <SystemCard icon="📶" :title="tl('nav.networkWireless')" :label="tl('AP管理 · 信号覆盖')" :sys="overview.wireless" />
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
import { getNetworkOverview, type NetworkOverview } from '@/api/network'
const { t: tl } = useI18n()

const overview = ref<NetworkOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

async function load() {
  error.value = ''
  try {
    overview.value = await getNetworkOverview()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)
</script>

<script lang="ts">
import { defineComponent, h, type PropType } from 'vue'
import type { NetworkSystemSummary, NetworkDeviceView } from '@/api/network'

const SystemCard = defineComponent({
  props: {
    icon: String,
    title: String,
    label: String,
    sys: { type: Object as PropType<NetworkSystemSummary>, required: true },
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
          ['平均延迟', s?.avgPingMs != null ? s.avgPingMs.toFixed(1) + 'ms' : '-'],
          ['带宽利用率', s?.avgBwUtilization != null ? s.avgBwUtilization.toFixed(1) + '%' : '-'],
        ].map(([k, v]) => [h('span', { class: 'k' }, k), h('span', { class: 'v' }, v)]).flat()),
        d.length > 0
          ? h('div', { class: 'device-list' },
              d.map((dev: NetworkDeviceView) =>
                h('div', { class: 'device-row', key: dev.id }, [
                  h('div', { class: 'd-info' }, [
                    h('span', { class: 'd-status ' + (dev.status === 'running' ? 'g' : dev.status === 'fault' ? 'r' : dev.status === 'warning' ? 'a' : 'm') }, '●'),
                    h('span', { class: 'd-name' }, dev.name),
                    h('span', { class: 'd-code' }, dev.code),
                  ]),
                  h('div', { class: 'd-metrics' }, [
                    dev.pingMs != null ? `${dev.pingMs.toFixed(1)}ms` : null,
                    ` | ${dev.bwUtilization != null ? dev.bwUtilization.toFixed(0) + '%' : '-'}`,
                    ` | ${dev.portCount}P`,
                    dev.firmwareVersion ? ` | ${dev.firmwareVersion}` : null,
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
