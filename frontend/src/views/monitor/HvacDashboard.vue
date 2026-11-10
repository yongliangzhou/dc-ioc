<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.hvacMonitor') }}</h1>
      <span class="sub">
        {{ tl('冷源系统') }} / {{ tl('空调末端') }} / {{ tl('液冷系统') }} {{ tl('·') }}
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
        <!-- ① P0 关键指标行 -->
        <div class="grid cols-4">
          <MetricCard
            metric-name="hvac-fault"
            :label="tl('故障')"
            :value="overview.faultCount"
            unit="台"
            :quality="overview.faultCount ? 'bad' : 'good'"
            :online="true"
            :severity="overview.faultCount ? 'crit' : 'normal'"
          />
          <MetricCard
            metric-name="hvac-warning"
            :label="tl('告警')"
            :value="overview.warningCount"
            unit="台"
            :quality="overview.warningCount ? 'uncertain' : 'good'"
            :online="true"
            :severity="overview.warningCount ? 'warn' : 'normal'"
          />
          <MetricCard
            metric-name="hvac-online"
            :label="tl('在线率')"
            :value="onlinePercent"
            unit="%"
            quality="good"
            :online="true"
          />
          <MetricCard
            metric-name="hvac-total"
            :label="tl('HVAC 设备总数')"
            :value="overview.totalEquipment"
            unit="台"
            quality="good"
            :online="true"
          />
        </div>

        <!-- ② 三子系统入口卡：保留原有的设备域差异化指标 -->
        <div class="grid cols-3" style="margin-top: 12px">
          <router-link v-for="e in entries" :key="e.to" :to="e.to" class="entry-card">
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

        <!-- ③ 可视化入口 -->
        <div class="grid cols-2" style="margin-top: 12px">
          <router-link v-for="e in links" :key="e.to" :to="e.to" class="entry-card linkage-entry">
            <div class="card-head">
              <span class="ct">{{ e.title }}</span>
              <span class="pill">{{ e.badge }}</span>
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
import { getHvacOverview, type HvacOverview } from '@/api/hvac'

const { t: tl } = useI18n()
const { level, reason, isMock, markReal, markFull } = useMockFlag()

const overview = ref<HvacOverview | null>(null)
const error = ref('')
const loading = ref(false)
const lastRefreshed = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

const fmt = (v: number | null | undefined, digits = 1, suffix = '') =>
  v == null ? '-' : v.toFixed(digits) + suffix

interface Entry {
  to: string
  title: string
  pill?: string
  badge: string
  metrics: { k: string; v: string }[]
}

/** 保留原页面 :51-109 的差异化指标（每个设备域关注不同维度），不新增遥测点。
 *  单位沿用接口原始语义：流量 L/min 未换算，单位归一留到阶段 3 统一处理。 */
const entries = computed<Entry[]>(() => {
  const o = overview.value
  if (!o) return []
  const badge = (online: number, total: number) => `${online}/${total} ${tl('在线')}`
  return [
    {
      to: '/monitor/hvac/chiller',
      title: tl('nav.chiller'),
      pill: o.chiller.online === o.chiller.total ? 'g' : 'a',
      badge: badge(o.chiller.online, o.chiller.total),
      metrics: [
        { k: tl('平均负载率'), v: fmt(o.chiller.avgLoadPercent, 1, '%') },
        { k: tl('进水温度均值'), v: fmt(o.chiller.avgTemperatureIn, 1, '°C') },
        { k: tl('出水温度均值'), v: fmt(o.chiller.avgTemperatureOut, 1, '°C') },
      ],
    },
    {
      to: '/monitor/hvac/crac',
      title: `${tl('nav.crac')} (CRAC)`,
      pill: o.crac.online === o.crac.total ? 'g' : 'a',
      badge: badge(o.crac.online, o.crac.total),
      metrics: [
        { k: tl('送风温度均值'), v: fmt(o.crac.avgTemperatureOut, 1, '°C') },
        { k: tl('回风温度均值'), v: fmt(o.crac.avgTemperatureIn, 1, '°C') },
        { k: tl('回风湿度均值'), v: fmt(o.crac.avgHumidityIn, 1, '%') },
        { k: tl('风机转速均值'), v: fmt(o.crac.avgFanSpeed, 0, '%') },
      ],
    },
    {
      to: '/monitor/hvac/liquid',
      title: tl('nav.liquidCooling'),
      pill: o.liquidCooling.online === o.liquidCooling.total ? 'g' : 'a',
      badge: badge(o.liquidCooling.online, o.liquidCooling.total),
      metrics: [
        { k: tl('平均流量'), v: fmt(o.liquidCooling.avgFlowRate, 1, ' L/min') },
        { k: tl('CDU进水温度均值'), v: fmt(o.liquidCooling.avgCdiTemperature, 1, '°C') },
        { k: tl('CDU出水温度均值'), v: fmt(o.liquidCooling.avgCdoTemperature, 1, '°C') },
      ],
    },
  ]
})

const links = computed<Entry[]>(() => [
  {
    to: '/monitor/hvac/linkage',
    title: tl('制冷链路可视化'),
    badge: tl('一次系统'),
    metrics: [
      { k: tl('循环'), v: tl('冷却水 / 冷冻水双循环') },
      { k: tl('特性'), v: tl('水流方向 · 设备状态跳转') },
    ],
  },
  {
    to: '/monitor/hvac/thermal',
    title: tl('温度云图'),
    badge: tl('三层'),
    metrics: [
      { k: tl('层级'), v: tl('机房 / 通道 / 机柜') },
      { k: tl('特性'), v: tl('TOP5 热点 · 区间可调') },
    ],
  },
])

async function load() {
  error.value = ''
  loading.value = true
  const before = mockFallbackCount.value
  try {
    overview.value = await getHvacOverview()
    if (mockFallbackCount.value > before) markFull('部分暖通指标由本地兜底生成')
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
