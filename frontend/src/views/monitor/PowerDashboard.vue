<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }}</h1>
      <span class="sub">
        {{ tl('nav.hv') }} / {{ tl('nav.lv') }} / {{ tl('nav.genset') }} / {{ tl('nav.fuel') }} /
        {{ tl('nav.battery') }} {{ tl('·') }} {{ tl('总览 · 点击进入子系统') }}
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
        <!-- ① P0 关键指标行：故障/告警视觉权重高于统计卡 -->
        <div class="grid cols-4">
          <MetricCard
            metric-name="power-fault"
            :label="tl('故障')"
            :value="overview.faultCount"
            unit="台"
            :quality="overview.faultCount ? 'bad' : 'good'"
            :online="true"
            :severity="overview.faultCount ? 'crit' : 'normal'"
          />
          <MetricCard
            metric-name="power-warning"
            :label="tl('告警')"
            :value="overview.warningCount"
            unit="台"
            :quality="overview.warningCount ? 'uncertain' : 'good'"
            :online="true"
            :severity="overview.warningCount ? 'warn' : 'normal'"
          />
          <MetricCard
            metric-name="power-online"
            :label="tl('在线率')"
            :value="onlinePercent"
            unit="%"
            quality="good"
            :online="true"
          />
          <MetricCard
            metric-name="power-total"
            :label="tl('电力设备总数')"
            :value="overview.totalEquipment"
            unit="台"
            quality="good"
            :online="true"
          />
        </div>

        <!-- ② 子系统入口卡：按设备域差异化指标，任意两卡组合不同 -->
        <div class="grid cols-3" style="margin-top: 12px">
          <router-link
            v-for="e in entries"
            :key="e.to"
            :to="e.to"
            class="entry-card"
            :class="{ 'linkage-entry': e.linkage }"
          >
            <div class="card-head">
              <span class="ct">{{ e.title }}</span>
              <span class="pill" :class="e.pill">{{ e.badge }}</span>
            </div>
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
import { getPowerOverview, type PowerOverview, type PowerSystemSummary } from '@/api/power'

const { t: tl } = useI18n()
const { level, reason, isMock, markReal, markFull } = useMockFlag()

const overview = ref<PowerOverview | null>(null)
const error = ref('')
const loading = ref(false)
const lastRefreshed = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

const fmt = (v: number | null | undefined, digits = 1, suffix = '') =>
  v == null ? '-' : v.toFixed(digits) + suffix
const rate = (s: PowerSystemSummary) =>
  s.total ? ((s.online / s.total) * 100).toFixed(1) + '%' : '-'
const badgeOf = (s: PowerSystemSummary) => ({
  pill: s.online === s.total ? 'g' : 'a',
  badge: `${s.online}/${s.total} ${tl('在线')}`,
})

interface Entry {
  to: string
  title: string
  pill?: string
  badge?: string
  metrics: { k: string; v: string }[]
  linkage?: boolean
}

/** 每张卡展示 3 个按设备域选择的指标，全部取自 PowerSystemSummary 现有字段。
 *  注意：Fuel 的 avgLoadPercent 语义是「平均油位」，Battery 的是「平均 SOC」，
 *  不再是笼统的「平均负载率」（见 api/power.ts mapFuel / mapBattery）。 */
const entries = computed<Entry[]>(() => {
  const o = overview.value
  if (!o) return []
  const b = (s: PowerSystemSummary) => badgeOf(s)
  return [
    {
      to: '/monitor/power/hv',
      title: tl('nav.hv'),
      ...b(o.hv),
      metrics: [
        { k: tl('平均电压'), v: fmt(o.hv.avgVoltage, 0, 'V') },
        { k: tl('平均电流'), v: fmt(o.hv.avgCurrent, 1, 'A') },
        { k: tl('平均负载率'), v: fmt(o.hv.avgLoadPercent, 1, '%') },
      ],
    },
    {
      to: '/monitor/power/lv',
      title: tl('nav.lv'),
      ...b(o.lv),
      metrics: [
        { k: tl('平均负载率'), v: fmt(o.lv.avgLoadPercent, 1, '%') },
        { k: tl('平均电流'), v: fmt(o.lv.avgCurrent, 1, 'A') },
        { k: tl('在线率'), v: rate(o.lv) },
      ],
    },
    {
      to: '/monitor/power/genset',
      title: tl('nav.genset'),
      ...b(o.genset),
      metrics: [
        { k: tl('在线机组'), v: `${o.genset.online}/${o.genset.total}` },
        { k: tl('平均负载率'), v: fmt(o.genset.avgLoadPercent, 1, '%') },
        { k: tl('平均电压'), v: fmt(o.genset.avgVoltage, 0, 'V') },
      ],
    },
    {
      to: '/monitor/power/fuel',
      title: tl('nav.fuel'),
      ...b(o.fuel),
      metrics: [
        { k: tl('平均油位'), v: fmt(o.fuel.avgLoadPercent, 1, '%') },
        { k: tl('在线设备'), v: `${o.fuel.online} ${tl('台')}` },
        { k: tl('设备总数'), v: `${o.fuel.total} ${tl('台')}` },
      ],
    },
    {
      to: '/monitor/power/battery',
      title: tl('nav.battery'),
      ...b(o.battery),
      metrics: [
        { k: tl('平均 SOC'), v: fmt(o.battery.avgLoadPercent, 1, '%') },
        { k: tl('平均电压'), v: fmt(o.battery.avgVoltage, 0, 'V') },
        { k: tl('平均电流'), v: fmt(o.battery.avgCurrent, 1, 'A') },
      ],
    },
    {
      to: '/monitor/power/linkage',
      title: tl('配电链路可视化'),
      pill: 'c',
      badge: tl('端到端'),
      linkage: true,
      metrics: [
        { k: tl('链路'), v: tl('市电 → 中压 → 变压器 → 低压 → UPS → 机柜') },
        { k: tl('特性'), v: tl('实时状态 · 告警点击定位') },
      ],
    },
  ]
})

async function load() {
  error.value = ''
  loading.value = true
  const before = mockFallbackCount.value
  try {
    overview.value = await getPowerOverview()
    // 任一子域走了 request.ts 的 mock 兜底，整页总览即视为不可信（保守标记）
    if (mockFallbackCount.value > before) markFull('部分子系统指标由本地兜底生成')
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
