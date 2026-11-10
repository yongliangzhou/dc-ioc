<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }}</h1>
      <span class="sub">
        {{ tl('nav.securityCctv') }} / {{ tl('nav.securityAcs') }} / {{ tl('nav.securityIds') }} /
        {{ tl('nav.securityFire') }} {{ tl('·') }} {{ tl('总览 · 点击进入子系统') }}
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
        <!-- ① P0 关键指标行 -->
        <div class="grid cols-4">
          <MetricCard
            metric-name="sec-fault"
            :label="tl('故障')"
            :value="overview.faultCount"
            unit="台"
            :quality="overview.faultCount ? 'bad' : 'good'"
            :online="true"
            :severity="overview.faultCount ? 'crit' : 'normal'"
          />
          <MetricCard
            metric-name="sec-warning"
            :label="tl('告警')"
            :value="overview.warningCount"
            unit="台"
            :quality="overview.warningCount ? 'uncertain' : 'good'"
            :online="true"
            :severity="overview.warningCount ? 'warn' : 'normal'"
          />
          <MetricCard
            metric-name="sec-online"
            :label="tl('在线率')"
            :value="onlinePercent"
            unit="%"
            quality="good"
            :online="true"
          />
          <MetricCard
            metric-name="sec-total"
            :label="tl('安防设备总数')"
            :value="overview.totalEquipment"
            unit="台"
            quality="good"
            :online="true"
          />
        </div>

        <!-- ② 四子系统入口卡：按设备域差异化，指标均来自 /api/security 现有字段 -->
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
import MetricCard from '@/components/common/MetricCard.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import {
  getSecurityOverview,
  type SecurityOverview,
  type SecuritySystemSummary,
} from '@/api/security'

const { t: tl } = useI18n()
const { level, reason, isMock, markReal, markFull } = useMockFlag()

const overview = ref<SecurityOverview | null>(null)
const error = ref('')
const loading = ref(false)
const lastRefreshed = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

const rate = (s: SecuritySystemSummary) =>
  s.total ? ((s.online / s.total) * 100).toFixed(1) + '%' : '-'
const avgHealth = (s: SecuritySystemSummary): number | null => {
  const vals = s.devices.map((d) => d.healthScore).filter((v): v is number => v != null)
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
}
const badgeOf = (s: SecuritySystemSummary) => ({
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

/** 四个安防域各自选取 3 个不同指标，任意两卡组合不相同。 */
const entries = computed<Entry[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      to: '/monitor/security/cctv',
      title: tl('nav.securityCctv'),
      subtitle: tl('视频监控 · 实时录像与回放'),
      ...badgeOf(o.cctv),
      metrics: [
        { k: tl('今日事件'), v: String(o.cctv.eventsToday ?? 0) },
        { k: tl('今日告警'), v: String(o.cctv.alertsToday ?? 0) },
        { k: tl('在线率'), v: rate(o.cctv) },
      ],
    },
    {
      to: '/monitor/security/acs',
      title: tl('nav.securityAcs'),
      subtitle: tl('门禁管理 · 出入控制与授权'),
      ...badgeOf(o.acs),
      metrics: [
        { k: tl('今日刷卡'), v: String(o.acs.eventsToday ?? 0) },
        { k: tl('拒绝次数'), v: String(o.acs.alertsToday ?? 0) },
        { k: tl('在线设备'), v: `${o.acs.online}/${o.acs.total}` },
      ],
    },
    {
      to: '/monitor/security/ids',
      title: tl('nav.securityIds'),
      subtitle: tl('防入侵系统 · 周界与内部探测'),
      ...badgeOf(o.ids),
      metrics: [
        { k: tl('今日告警'), v: String(o.ids.alertsToday ?? 0) },
        { k: tl('防区总数'), v: String(o.ids.total) },
        { k: tl('布防率'), v: rate(o.ids) },
      ],
    },
    {
      to: '/monitor/security/fire',
      title: tl('nav.securityFire'),
      subtitle: tl('消防报警 · 烟感/温感/灭火'),
      ...badgeOf(o.fire),
      metrics: [
        { k: tl('今日事件'), v: String(o.fire.eventsToday ?? 0) },
        { k: tl('点位总数'), v: String(o.fire.total) },
        { k: tl('平均健康度'), v: avgHealth(o.fire)?.toFixed(0) ?? '-' },
      ],
    },
  ]
})

async function load() {
  error.value = ''
  loading.value = true
  const before = mockFallbackCount.value
  try {
    overview.value = await getSecurityOverview()
    if (mockFallbackCount.value > before) markFull('部分安防指标由本地兜底生成')
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
