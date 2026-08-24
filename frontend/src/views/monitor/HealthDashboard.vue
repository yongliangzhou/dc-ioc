<template>
  <div class="health-db">
    <div class="view-head">
      <h1>{{ tl('设备健康度') }}</h1>
      <span class="sub">{{ tl('全量设备健康评分 · 趋势监测 · 异常预警') }}</span>
    </div>

    <!-- KPI -->
    <div class="grid cols-4" v-if="data">
      <MetricCard
        metricName="avgHealth"
        :label="tl('平均健康分')"
        :value="data.averageScore"
        unit="分"
        :severity="
          (data.averageScore ?? 100) < 80
            ? 'crit'
            : (data.averageScore ?? 100) < 90
              ? 'warn'
              : 'normal'
        "
      />
      <MetricCard
        metricName="healthyCount"
        :label="tl('健康设备')"
        :value="data.healthyCount"
        unit="台"
        severity="normal"
      />
      <MetricCard
        metricName="warnCount"
        :label="tl('预警设备')"
        :value="data.warningCount"
        unit="台"
        :severity="data.warningCount > 0 ? 'warn' : 'normal'"
      />
      <MetricCard
        metricName="critCount"
        :label="tl('严重设备')"
        :value="data.criticalCount"
        unit="台"
        :severity="data.criticalCount > 0 ? 'crit' : 'normal'"
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

    <!-- 健康分环形图 + 柱状图 -->
    <div class="grid cols-2" v-if="data">
      <Panel :title="tl('健康分分布')">
        <BaseChart v-if="ringOption" :option="ringOption" height="240px" />
      </Panel>
      <Panel :title="tl('设备健康分排行')">
        <BaseChart v-if="barChartOption" :option="barChartOption" height="240px" />
      </Panel>
    </div>

    <!-- 设备明细表 -->
    <Panel v-if="data?.scores?.length" :title="tl('设备健康明细')">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ tl('设备编码') }}</th>
            <th>{{ tl('设备名称') }}</th>
            <th>{{ tl('类别') }}</th>
            <th>{{ tl('域') }}</th>
            <th>{{ tl('健康分') }}</th>
            <th>{{ tl('趋势') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in data.scores" :key="s.equipmentId">
            <td class="mono">{{ s.equipmentCode }}</td>
            <td>{{ s.equipmentName }}</td>
            <td>
              <span class="pill dim">{{ s.category }}</span>
            </td>
            <td>
              <span class="pill dim">{{ s.domain }}</span>
            </td>
            <td>
              <span :class="['score-badge', scoreCls(s.healthScore)]">{{ s.healthScore }}</span>
            </td>
            <td>
              <span v-if="s.trend === 'up'" class="trend up">▲ {{ tl('上升') }}</span>
              <span v-else-if="s.trend === 'down'" class="trend down">▼ {{ tl('下降') }}</span>
              <span v-else class="trend stable">— {{ tl('稳定') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import {
  pieOption as buildPieOption,
  barOption as buildBarOption,
} from '@/components/charts/options'
import { getHealthOverview, type HealthOverview } from '@/api/health'
import type { EChartsOption } from '@/hooks/useECharts'
const { t: tl } = useI18n()

const loading = ref(true)
const err = ref('')
const data = ref<HealthOverview | null>(null)

function scoreCls(v: number) {
  return v >= 90 ? 'ok' : v >= 80 ? 'warn' : 'crit'
}

const ringOption = computed<EChartsOption | null>(() => {
  if (!data.value) return null
  return buildPieOption(
    [
      { name: tl('健康 ≥90'), value: data.value.healthyCount },
      { name: tl('预警 80-90'), value: data.value.warningCount },
      { name: tl('严重 <80'), value: data.value.criticalCount },
    ],
    ['42%', '68%'],
  )
})

const barChartOption = computed<EChartsOption | null>(() => {
  if (!data.value?.scores?.length) return null
  const sorted = [...data.value.scores].sort((a, b) => a.healthScore - b.healthScore)
  return buildBarOption(
    sorted.map((s) => s.equipmentName),
    sorted.map((s) => s.healthScore),
    '分',
  )
})

onMounted(async () => {
  try {
    data.value = await getHealthOverview()
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.health-db {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th,
.tbl td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--line);
}
.tbl th {
  color: var(--txt2);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
}
.tbl td {
  color: var(--txt);
}
.mono {
  font-family: monospace;
  font-size: 12px;
  color: var(--cyan);
}
.score-badge {
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 13px;
}
.score-badge.ok {
  background: rgba(43, 212, 122, 0.15);
  color: var(--green);
}
.score-badge.warn {
  background: rgba(255, 176, 32, 0.15);
  color: var(--amber);
}
.score-badge.crit {
  background: rgba(255, 77, 94, 0.15);
  color: var(--red);
}
.trend {
  font-size: 12px;
  font-weight: 600;
}
.trend.up {
  color: var(--green);
}
.trend.down {
  color: var(--red);
}
.trend.stable {
  color: var(--txt2);
}
</style>
