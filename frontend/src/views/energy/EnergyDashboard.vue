<template>
  <div class="energy-db">
    <div class="view-head">
      <h1>{{ tl('nav.energy') }}</h1>
      <span class="sub">{{ tl('PUE 实时监控 · 7 日能耗趋势与分解') }}</span>
    </div>

    <!-- KPI -->
    <div class="grid cols-4" v-if="data">
      <MetricCard
        metricName="pue"
        :label="tl('当前 PUE')"
        :value="data.todayPue"
        unit=""
        :severity="
          (data.todayPue ?? 2) > 1.6 ? 'crit' : (data.todayPue ?? 2) > 1.4 ? 'warn' : 'normal'
        "
      />
      <MetricCard
        metricName="totalEnergy"
        :label="tl('当日总能耗')"
        :value="data.todayTotalKwh"
        unit="kWh"
      />
      <MetricCard
        metricName="itEnergy"
        :label="tl('IT 设备能耗')"
        :value="data.todayItKwh"
        unit="kWh"
      />
      <MetricCard
        metricName="coolEnergy"
        :label="tl('制冷能耗')"
        :value="data.todayCoolingKwh"
        unit="kWh"
      />
    </div>
    <Panel v-else-if="loading"
      ><div class="flex center">
        <span class="muted">{{ tl('加载中...') }}</span>
      </div></Panel
    >
    <Panel v-else-if="err"
      ><div class="flex center">
        <span class="muted">{{ err }}</span>
      </div></Panel
    >

    <!-- PUE 趋势图 -->
    <Panel v-if="pueChartOption" :title="tl('PUE 7 日趋势')">
      <BaseChart :option="pueChartOption" height="260px" />
    </Panel>

    <!-- 能耗分解图 -->
    <Panel v-if="breakdownChartOption" :title="tl('7 日能耗分解')">
      <BaseChart :option="breakdownChartOption" height="260px" />
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import Panel from '@/components/common/Panel.vue'
import { lineOption } from '@/components/charts/options'
import { getEnergyOverview, type EnergyOverview } from '@/api/energy'
import type { EChartsOption } from '@/hooks/useECharts'
const { t: tl } = useI18n()

const loading = ref(true)
const err = ref('')
const data = ref<EnergyOverview | null>(null)

function fmtKwh(v: number | null) {
  if (v == null) return '—'
  return v >= 1000 ? (v / 1000).toFixed(1) + ' M' : v.toFixed(0)
}

const pueChartOption = computed<EChartsOption | null>(() => {
  if (!data.value?.weekTrend?.length) return null
  const d = data.value.weekTrend
  return lineOption(
    d.map((t) => t.date.slice(5)),
    [{ name: 'PUE', data: d.map((t) => t.pue as number), color: '#22e3ff', area: true }],
  )
})

const breakdownChartOption = computed<EChartsOption | null>(() => {
  if (!data.value?.weekTrend?.length) return null
  const d = data.value.weekTrend
  return lineOption(
    d.map((t) => t.date.slice(5)),
    [
      { name: tl('IT 能耗'), data: d.map((t) => t.itKwh), color: '#3b82f6', area: true },
      { name: tl('制冷能耗'), data: d.map((t) => t.coolingKwh), color: '#22e3ff', area: true },
      {
        name: tl('其他'),
        data: d.map((t) => t.totalKwh - t.itKwh - t.coolingKwh),
        color: '#7e93b8',
        area: false,
        dashed: true,
      },
    ],
  )
})

onMounted(async () => {
  try {
    data.value = await getEnergyOverview()
  } catch (e: any) {
    err.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.energy-db {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>
