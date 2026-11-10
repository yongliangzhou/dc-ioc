<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.networkMonitor') }}</h1>
      <span class="sub">
        {{ tl('nav.networkSwitch') }} / {{ tl('nav.networkRouter') }} /
        {{ tl('nav.networkFirewall') }} / {{ tl('nav.networkWireless') }} {{ tl('·') }}
        {{ tl('总览 · 点击进入子系统') }}
      </span>
      <div class="vh-right">
        <DataBadge v-if="isMock" :tone="level === 'partial' ? 'partial' : 'mock'" />
        <span v-if="lastRefreshed" class="pill"><Clock :size="12" /> {{ lastRefreshed }}</span>
      </div>
    </div>

    <MockDataBanner :level="level" :reason="reason" />

    <AsyncSection
      :loading="loading"
      :error="error"
      :empty="!overview && !loading && !error"
      @retry="load"
    >
      <template v-if="overview">
        <div class="grid cols-4">
          <MetricCard
            metric-name="net-fault"
            :label="tl('故障')"
            :value="overview.faultCount"
            unit="台"
            :quality="overview.faultCount ? 'bad' : 'good'"
            :online="true"
            :severity="overview.faultCount ? 'crit' : 'normal'"
          />
          <MetricCard
            metric-name="net-warning"
            :label="tl('告警')"
            :value="overview.warningCount"
            unit="台"
            :quality="overview.warningCount ? 'uncertain' : 'good'"
            :online="true"
            :severity="overview.warningCount ? 'warn' : 'normal'"
          />
          <MetricCard
            metric-name="net-ping"
            :label="tl('全网平均延迟')"
            :value="overview.avgPingMs"
            unit="ms"
            :quality="qualityOf('network.pingMs', overview.avgPingMs)"
            :online="true"
            :severity="sevOf('network.pingMs', overview.avgPingMs)"
          />
          <MetricCard
            metric-name="net-bw"
            :label="tl('全网平均带宽利用率')"
            :value="overview.avgBwUtilization"
            unit="%"
            :quality="qualityOf('network.bwUtilization', overview.avgBwUtilization)"
            :online="true"
            :severity="sevOf('network.bwUtilization', overview.avgBwUtilization)"
          />
        </div>

        <!-- 四子系统入口卡：指标按设备域差异化，字段均来自 /api/network/overview -->
        <div class="grid cols-2" style="margin-top: 12px">
          <router-link v-for="e in entries" :key="e.to" :to="e.to" class="entry-card">
            <div class="card-head">
              <span class="ct">{{ e.title }}</span>
              <span class="pill" :class="e.pill">{{ e.badge }}</span>
            </div>
            <div class="sub-label">{{ e.subtitle }}</div>
            <div class="kvs">
              <template v-for="m in e.metrics" :key="m.k">
                <span class="k">{{ m.k }}</span>
                <span class="v">{{ m.v }}</span>
              </template>
            </div>
          </router-link>
        </div>
      </template>
    </AsyncSection>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock } from 'lucide-vue-next'
import { toErrorMessage, useMockFlag } from '@/composables/useAsyncPage'
import { mockFallbackCount } from '@/api/request'
import { severityOf } from '@/config/metricsCatalog'
import MetricCard from '@/components/common/MetricCard.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import { getNetworkOverview, type NetworkOverview, type NetworkSystemSummary } from '@/api/monitor'

const { t: tl } = useI18n()
const { level, reason, isMock, markReal, markFull } = useMockFlag()

const overview = ref<NetworkOverview | null>(null)
const error = ref('')
const loading = ref(false)
const lastRefreshed = ref('')

const qualityOf = (key: string, v: number | null | undefined) => {
  const s = severityOf(key, v)
  return s === 'normal' ? 'good' : s === 'danger' ? 'bad' : 'uncertain'
}
const sevOf = (key: string, v: number | null | undefined) => {
  const s = severityOf(key, v)
  return s === 'normal' ? 'normal' : s === 'danger' ? 'crit' : 'warn'
}

const fmt = (v: number | null | undefined, digits = 1, suffix = '') =>
  v == null ? '-' : v.toFixed(digits) + suffix
const rate = (s: NetworkSystemSummary) =>
  s.total ? ((s.online / s.total) * 100).toFixed(1) + '%' : '-'
const sum = (s: NetworkSystemSummary, key: 'portCount' | 'uplinkPort') =>
  s.devices.reduce((acc, d) => acc + (d[key] ?? 0), 0)
const avgHealth = (s: NetworkSystemSummary): number | null => {
  const vals = s.devices.map((d) => d.healthScore).filter((v): v is number => v != null)
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
}
const badgeOf = (s: NetworkSystemSummary) => ({
  pill: s.online === s.total ? 'g' : 'a',
  badge: `${s.online}/${s.total} ${tl('在线')}`,
})

interface Entry {
  to: string
  title: string
  subtitle: string
  pill: string
  badge: string
  metrics: { k: string; v: string }[]
}

/** 不引用未接线的 /api/network/bandwidth 与 /api/network/ping（决策 5）；
 *  ping/bw 字段来自已接线的 /api/network/overview，端口与健康度来自其 devices。 */
const entries = computed<Entry[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      to: '/monitor/net/switches',
      title: tl('nav.networkSwitch'),
      subtitle: tl('核心层 · 汇聚层 · 接入层'),
      ...badgeOf(o.switchs),
      metrics: [
        { k: tl('端口总数'), v: `${sum(o.switchs, 'portCount')}` },
        { k: tl('上联端口'), v: `${sum(o.switchs, 'uplinkPort')}` },
        { k: tl('平均健康度'), v: fmt(avgHealth(o.switchs), 0) },
      ],
    },
    {
      to: '/monitor/net/routers',
      title: tl('nav.networkRouter'),
      subtitle: tl('路由转发 · 协议状态'),
      ...badgeOf(o.routers),
      metrics: [
        { k: tl('平均健康度'), v: fmt(avgHealth(o.routers), 0) },
        { k: tl('平均延迟'), v: fmt(o.routers.avgPingMs, 1, 'ms') },
        { k: tl('在线率'), v: rate(o.routers) },
      ],
    },
    {
      to: '/monitor/net/firewalls',
      title: tl('nav.networkFirewall'),
      subtitle: tl('安全策略 · 流量过滤'),
      ...badgeOf(o.firewalls),
      metrics: [
        { k: tl('平均延迟'), v: fmt(o.firewalls.avgPingMs, 1, 'ms') },
        { k: tl('带宽利用率'), v: fmt(o.firewalls.avgBwUtilization, 1, '%') },
        { k: tl('设备总数'), v: `${o.firewalls.total} ${tl('台')}` },
      ],
    },
    {
      to: '/monitor/net/wireless',
      title: tl('nav.networkWireless'),
      subtitle: tl('AP管理 · 信号覆盖'),
      ...badgeOf(o.wireless),
      metrics: [
        { k: tl('在线率'), v: rate(o.wireless) },
        { k: tl('设备总数'), v: `${o.wireless.total} ${tl('台')}` },
        { k: tl('平均健康度'), v: fmt(avgHealth(o.wireless), 0) },
      ],
    },
  ]
})

async function load() {
  error.value = ''
  loading.value = true
  const before = mockFallbackCount.value
  try {
    overview.value = await getNetworkOverview()
    if (mockFallbackCount.value > before) markFull('部分网络指标由本地兜底生成')
    else markReal()
    lastRefreshed.value = new Date().toLocaleTimeString()
  } catch (e: unknown) {
    error.value = toErrorMessage(e)
    markReal()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
