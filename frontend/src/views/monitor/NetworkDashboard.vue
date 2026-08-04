<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }}</h1>
      <span class="sub"
        >{{ tl('nav.networkSwitch') }} / {{ tl('nav.networkRouter') }} /
        {{ tl('nav.networkFirewall') }} / {{ tl('nav.networkWireless') }} {{ tl('·') }}
        {{ tl('总览 · 点击进入子系统') }}</span
      >
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard
        metric-name="net-total"
        :label="tl('网络设备总数')"
        :value="overview.totalEquipment"
        unit="台"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="net-online"
        :label="tl('在线率')"
        :value="onlinePercent"
        unit="%"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="net-ping"
        :label="tl('全网平均延迟')"
        :value="overview.avgPingMs"
        unit="ms"
        :quality="overview.avgPingMs && overview.avgPingMs > 20 ? 'uncertain' : 'good'"
        :online="true"
        :severity="overview.avgPingMs && overview.avgPingMs > 50 ? 'warn' : 'normal'"
      />
      <MetricCard
        metric-name="net-bw"
        :label="tl('全网平均带宽利用率')"
        :value="overview.avgBwUtilization"
        unit="%"
        :quality="
          overview.avgBwUtilization && overview.avgBwUtilization > 70 ? 'uncertain' : 'good'
        "
        :online="true"
        :severity="overview.avgBwUtilization && overview.avgBwUtilization > 85 ? 'warn' : 'normal'"
      />
    </div>

    <!-- 四子系统入口卡片 -->
    <div class="grid cols-2" v-if="overview">
      <router-link to="/monitor/net/switches" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.networkSwitch') }}</span
          ><span class="pill" :class="pillCls(overview.switchs)"
            >{{ overview.switchs.online }}/{{ overview.switchs.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('核心层 · 汇聚层 · 接入层') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('平均延迟') }}</span
          ><span class="v">{{ ms(overview.switchs.avgPingMs) }}</span
          ><span class="k">{{ tl('带宽利用率') }}</span
          ><span class="v">{{ pct(overview.switchs.avgBwUtilization) }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/net/routers" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.networkRouter') }}</span
          ><span class="pill" :class="pillCls(overview.routers)"
            >{{ overview.routers.online }}/{{ overview.routers.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('路由转发 · 协议状态') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('平均延迟') }}</span
          ><span class="v">{{ ms(overview.routers.avgPingMs) }}</span
          ><span class="k">{{ tl('带宽利用率') }}</span
          ><span class="v">{{ pct(overview.routers.avgBwUtilization) }}</span>
        </div>
      </router-link>
    </div>
    <div class="grid cols-2" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/net/firewalls" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.networkFirewall') }}</span
          ><span class="pill" :class="pillCls(overview.firewalls)"
            >{{ overview.firewalls.online }}/{{ overview.firewalls.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('安全策略 · 流量过滤') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('平均延迟') }}</span
          ><span class="v">{{ ms(overview.firewalls.avgPingMs) }}</span
          ><span class="k">{{ tl('带宽利用率') }}</span
          ><span class="v">{{ pct(overview.firewalls.avgBwUtilization) }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/net/wireless" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.networkWireless') }}</span
          ><span class="pill" :class="pillCls(overview.wireless)"
            >{{ overview.wireless.online }}/{{ overview.wireless.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('AP管理 · 信号覆盖') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('平均延迟') }}</span
          ><span class="v">{{ ms(overview.wireless.avgPingMs) }}</span
          ><span class="k">{{ tl('带宽利用率') }}</span
          ><span class="v">{{ pct(overview.wireless.avgBwUtilization) }}</span>
        </div>
      </router-link>
    </div>

    <!-- 加载 / 错误态 -->
    <Panel v-if="!overview && !error">
      <div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div>
    </Panel>
    <Panel v-if="error">
      <div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ tl('common.error') }}: {{ error }}</span>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getNetworkOverview, type NetworkOverview, type NetworkSystemSummary } from '@/api/monitor'
const { t: tl } = useI18n()

const overview = ref<NetworkOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

function pillCls(s: NetworkSystemSummary) {
  return s.online === s.total ? 'g' : 'a'
}
function ms(v: number | null) {
  return v != null ? v.toFixed(1) + 'ms' : '-'
}
function pct(v: number | null) {
  return v != null ? v.toFixed(1) + '%' : '-'
}

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

.kvs {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  font-size: 12.5px;
}
.k {
  color: var(--muted);
}
.v {
  text-align: right;
  font-weight: 500;
}

.entry-card {
  display: block;
  text-decoration: none;
  color: inherit;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  transition:
    border-color 0.2s,
    transform 0.15s,
    box-shadow 0.2s;
}
.entry-card:hover {
  border-color: rgba(34, 227, 255, 0.45);
  box-shadow: var(--glow);
  transform: translateY(-2px);
}
</style>
