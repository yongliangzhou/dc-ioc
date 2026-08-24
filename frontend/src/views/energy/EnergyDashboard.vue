<template>
  <div class="energy-db">
    <div class="view-head">
      <h1>{{ tl('nav.energy') }}</h1>
      <span class="sub">{{ tl('PUE 实时监控 · 7 日能耗趋势 · 制冷策略优化 · AI 节能与电量预测') }}</span>
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

    <!-- 未来 24h 负载预测 -->
    <Panel v-if="loadForecastOption" :title="tl('未来 24 小时负载预测 (kW)')">
      <BaseChart :option="loadForecastOption" height="280px" />
    </Panel>

    <!-- 节能概览: PUE 目标 + 效率仪表 + 能耗占比 + AI 节能收益 -->
    <div class="grid cols-2" v-if="data?.advice">
      <Panel :title="tl('能效指标')">
        <div class="eff-wrap" v-if="advice">
          <BaseChart v-if="pueRingOption" :option="pueRingOption" height="180px" />
          <div class="eff-list">
            <div class="eff-item">
              <span class="k">{{ tl('冷机 COP') }}</span>
              <span class="v">{{ advice.efficiency.chillerCop }}</span>
            </div>
            <div class="eff-item">
              <span class="k">{{ tl('UPS 效率') }}</span>
              <span class="v">{{ (advice.efficiency.upsEff * 100).toFixed(1) }}%</span>
            </div>
            <div class="eff-item">
              <span class="k">{{ tl('UPS 平均负载率') }}</span>
              <span class="v">{{ advice.efficiency.upsAvgLoad }}%</span>
            </div>
            <div class="eff-item">
              <span class="k">{{ tl('冷机供水温度') }}</span>
              <span class="v">{{ advice.efficiency.chillerSupplyTemp }}℃</span>
            </div>
          </div>
        </div>
      </Panel>

      <Panel :title="tl('能耗占比')">
        <BaseChart v-if="breakdownPieOption" :option="breakdownPieOption" height="220px" />
      </Panel>
    </div>

    <!-- AI 节能建议 -->
    <Panel v-if="advice" :title="tl('AI 节能建议')">
      <div class="advice-summary" v-if="advice">
        <div class="sum-item">
          <span class="num">{{ advice.totalSavingKw.toLocaleString() }}</span>
          <span class="lbl">{{ tl('可降功率 (kW)') }}</span>
        </div>
        <div class="sum-item">
          <span class="num">{{ advice.totalSavingPct }}%</span>
          <span class="lbl">{{ tl('综合节能率') }}</span>
        </div>
        <div class="sum-item">
          <span class="num">{{ advice.suggestions.length }}</span>
          <span class="lbl">{{ tl('建议条数') }}</span>
        </div>
      </div>

      <div class="advice-cards">
        <div
          v-for="s in advice.suggestions"
          :key="s.id"
          class="advice-card"
          :class="{ adopted: adoptedIds.has(s.id), ignored: ignoredIds.has(s.id) }"
        >
          <div class="ac-head">
            <span class="ac-title">{{ s.title }}</span>
            <span class="badge" :class="prioClass(s.priority)">{{ s.priority }}</span>
          </div>
          <p class="ac-detail">{{ s.detail }}</p>
          <div class="ac-meta">
            <span>{{ tl('估算节能') }} ≈ {{ s.savingKw.toLocaleString() }} kW / {{ s.savingPct }}%</span>
          </div>
          <div class="ac-basis" v-if="s.basis">{{ tl('依据') }}: {{ s.basis }}</div>
          <div class="ac-actions" v-if="!adoptedIds.has(s.id) && !ignoredIds.has(s.id)">
            <button class="btn-sm primary" v-bind="authState('write')" @click="adopt(s)">
              {{ tl('采纳') }}
            </button>
            <button class="btn-sm" v-bind="authState('write')" @click="ignore(s)">
              {{ tl('忽略') }}
            </button>
          </div>
          <div class="ac-state" v-else>
            <span class="tag" :class="adoptedIds.has(s.id) ? 'ok' : 'no'">
              {{ adoptedIds.has(s.id) ? tl('已采纳') : tl('已忽略') }}
            </span>
          </div>
        </div>
      </div>
    </Panel>

    <!-- 采纳记录 -->
    <Panel v-if="adviceRecords.length" :title="tl('节能建议采纳记录')">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ tl('建议') }}</th>
            <th>{{ tl('优先级') }}</th>
            <th>{{ tl('估算节能') }}</th>
            <th>{{ tl('操作') }}</th>
            <th>{{ tl('操作人') }}</th>
            <th>{{ tl('时间') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in adviceRecords" :key="r.id">
            <td>{{ r.title }}</td>
            <td><span class="badge" :class="prioClass(r.priority)">{{ r.priority }}</span></td>
            <td>≈ {{ r.savingKw.toLocaleString() }} kW / {{ r.savingPct }}%</td>
            <td>
              <span class="tag" :class="r.action === 'adopt' ? 'ok' : 'no'">
                {{ r.action === 'adopt' ? tl('采纳') : tl('忽略') }}
              </span>
            </td>
            <td>{{ r.user || '—' }}</td>
            <td class="muted">{{ r.createdAt }}</td>
          </tr>
        </tbody>
      </table>
    </Panel>

    <!-- 制冷策略优化 (iCooling@AI) · 由制冷 AI 优化模块整合而来 -->
    <div class="card mb-6">
      <div class="card-head">
        <span class="dot ai"></span>
        <h3>{{ tl('制冷策略优化') }} <em class="ai-tag">iCooling@AI</em></h3>
        <span class="muted sm">{{ tl('实时分析冷负荷与温场，动态下发制冷设定值优化建议') }}</span>
      </div>

      <div class="feature-grid">
        <div class="feature" v-for="f in coolingFeatures" :key="f.key">
          <div class="f-icon">{{ f.icon }}</div>
          <div class="f-body">
            <div class="f-name">{{ f.name }}</div>
            <div class="f-desc">{{ f.desc }}</div>
            <div class="f-tag" :class="f.state">{{ f.stateLabel }}</div>
          </div>
        </div>
      </div>

      <div class="verify-block">
        <div class="vb-head">
          <span>{{ tl('优化建议验证') }}</span>
          <span class="muted sm">{{ coolingVerify.done }}/{{ coolingVerify.total }}</span>
        </div>
        <div class="progress"><i :style="{ width: coolingVerify.pct + '%' }"></i></div>
        <ul class="verify-list">
          <li v-for="v in coolingVerify.items" :key="v.id">
            <span class="v-state" :class="v.state">{{ v.stateLabel }}</span>
            <span class="v-name">{{ v.name }}</span>
            <span class="muted sm">{{ v.note }}</span>
          </li>
        </ul>
      </div>

      <div class="advice-cards">
        <div
          v-for="s in coolingSuggestions"
          :key="s.id"
          class="advice-card"
          :class="{ adopted: adoptedCoolingIds.has(s.id), ignored: ignoredCoolingIds.has(s.id) }"
        >
          <div class="ac-head">
            <span class="ac-title">{{ s.title }}</span>
            <span class="badge" :class="prioClass(s.priority)">{{ s.priority }}</span>
          </div>
          <p class="ac-detail">{{ s.detail }}</p>
          <div class="ac-meta">
            <span>{{ tl('估算节能') }} ≈ {{ s.savingKw.toLocaleString() }} kW / {{ s.savingPct }}%</span>
          </div>
          <div class="ac-basis" v-if="s.basis">{{ tl('依据') }}: {{ s.basis }}</div>
          <div class="ac-actions" v-if="!adoptedCoolingIds.has(s.id) && !ignoredCoolingIds.has(s.id)">
            <button class="btn-sm primary" v-bind="authState('write')" @click="adoptCooling(s)">
              {{ tl('采纳') }}
            </button>
            <button class="btn-sm" v-bind="authState('write')" @click="ignoreCooling(s)">
              {{ tl('忽略') }}
            </button>
          </div>
          <div class="ac-state" v-else>
            <span class="tag" :class="adoptedCoolingIds.has(s.id) ? 'ok' : 'no'">
              {{ adoptedCoolingIds.has(s.id) ? tl('已采纳') : tl('已忽略') }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import Panel from '@/components/common/Panel.vue'
import { lineOption, pieOption, ringOption } from '@/components/charts/options'
import {
  getEnergyOverview,
  adoptEnergyAdvice,
  getEnergyAdvice,
  type EnergyOverview,
  type EnergyAdviceAdoptRecord,
} from '@/api/energy'
import type { EnergySuggestion } from '@/types'
import type { EChartsOption } from '@/hooks/useECharts'
import { useToast } from '@/hooks/useToast'
import { usePermission, type PermAction } from '@/hooks/usePermission'
const { t: tl } = useI18n()
const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const loading = ref(true)
const err = ref('')
const data = ref<EnergyOverview | null>(null)
const adviceRecords = ref<EnergyAdviceAdoptRecord[]>([])
const adoptedIds = reactive(new Set<string>())
const ignoredIds = reactive(new Set<string>())

const advice = computed(() => data.value?.advice ?? null)

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

const loadForecastOption = computed<EChartsOption | null>(() => {
  const lf = data.value?.loadForecast
  if (!lf?.length) return null
  return lineOption(
    lf.map((t) => `${t.h}:00`),
    [
      {
        name: tl('实际负荷'),
        data: lf.map((t) => t.actual),
        color: '#3b82f6',
        area: true,
      },
      {
        name: tl('预测负荷'),
        data: lf.map((t) => t.pred),
        color: '#22e3ff',
        area: false,
        dashed: true,
      },
    ],
  )
})

const pueRingOption = computed<EChartsOption | null>(() => {
  if (!advice.value) return null
  const cur = advice.value.pue.current ?? 0
  // 以 2.0 为满量程映射占比
  const pct = Math.min(100, Math.round((cur / 2.0) * 100))
  return ringOption(pct, cur > 1.6 ? '#ff4d5e' : cur > 1.4 ? '#ffb020' : '#22e3ff')
})

const breakdownPieOption = computed<EChartsOption | null>(() => {
  const bd = advice.value?.breakdown
  if (!bd?.length) return null
  return pieOption(bd.map((b) => ({ name: b.id, value: b.kw })))
})

function prioClass(p: string) {
  return p === '高' ? 'crit' : p === '中' ? 'warn' : 'info'
}

async function adopt(s: EnergySuggestion) {
  try {
    await adoptEnergyAdvice({
      suggestionId: s.id,
      title: s.title,
      priority: s.priority,
      savingKw: s.savingKw,
      savingPct: s.savingPct,
      detail: s.detail,
      basis: s.basis,
      action: 'adopt',
      pueCurrent: advice.value?.pue.current ?? null,
      pueTarget: advice.value?.pue.target ?? null,
    })
    adoptedIds.add(s.id)
    toast.success(tl('已采纳节能建议'))
    await loadAdviceRecords()
  } catch (e: unknown) {
    toast.error((e as ErrorLike)?.message || String(e))
  }
}

async function ignore(s: EnergySuggestion) {
  try {
    await adoptEnergyAdvice({
      suggestionId: s.id,
      title: s.title,
      priority: s.priority,
      savingKw: s.savingKw,
      savingPct: s.savingPct,
      detail: s.detail,
      basis: s.basis,
      action: 'ignore',
      pueCurrent: advice.value?.pue.current ?? null,
      pueTarget: advice.value?.pue.target ?? null,
    })
    ignoredIds.add(s.id)
    toast.info(tl('已忽略该建议'))
    await loadAdviceRecords()
  } catch (e: unknown) {
    toast.error((e as ErrorLike)?.message || String(e))
  }
}

async function loadAdviceRecords() {
  try {
    const res = await getEnergyAdvice()
    adviceRecords.value = res.records
    res.records.forEach((r) => {
      if (r.action === 'adopt') adoptedIds.add(r.suggestionId)
      else if (r.action === 'ignore') ignoredIds.add(r.suggestionId)
    })
  } catch {
    /* 降级: 记录加载失败不阻断主页面 */
  }
}

/* ===== 制冷策略优化 (由制冷 AI 优化模块整合) ===== */
const adoptedCoolingIds = reactive(new Set<string>())
const ignoredCoolingIds = reactive(new Set<string>())

const coolingFeatures = [
  { key: 'atw', icon: '🌡', name: tl('冷冻水流量自适应'), desc: tl('依据冷负荷预测动态调节板换/水泵流量'), state: 'on', stateLabel: tl('运行中') },
  { key: 'setpoint', icon: '🎯', name: tl('全局设定值寻优'), desc: tl('以 PUE 最低为目标寻优冷冻水/回风设定值'), state: 'on', stateLabel: tl('运行中') },
  { key: 'ec', icon: '💨', name: tl('EC 风机群控'), desc: tl('依据温场分布联动调节末端风机转速'), state: 'warn', stateLabel: tl('部分启用') },
  { key: 'freecool', icon: '❄', name: tl('自然冷源利用'), desc: tl('室外湿球温度达标时优先开板式换热'), state: 'on', stateLabel: tl('运行中') },
]

const coolingVerify = {
  done: 2,
  total: 3,
  get pct() {
    return Math.round((this.done / this.total) * 100)
  },
  items: [
    { id: 'v1', state: 'done', stateLabel: tl('已验证'), name: tl('提高冷冻水供水温度 1℃'), note: tl('机房平均温度上升 0.6℃，制冷功率下降 4.2%') },
    { id: 'v2', state: 'done', stateLabel: tl('已验证'), name: tl('关闭冗余冷通道风机'), note: tl('末端风机功率下降 11%') },
    { id: 'v3', state: 'running', stateLabel: tl('验证中'), name: tl('板换自然冷源投入'), note: tl('预计节省冷机能耗 8%') },
  ],
}

const coolingSuggestions = [
  {
    id: 'c1',
    title: tl('冷冻水供水温度上调 1.5℃'),
    priority: '高',
    detail: tl('基于 AI 冷负荷预测，A/B 区服务器进出风温度均在安全阈值内，可上调供水温度以降低冷机压缩功。'),
    savingKw: 86,
    savingPct: 6.4,
    basis: tl('近 7 日温场与 IT 负载趋势'),
  },
  {
    id: 'c2',
    title: tl('B 区冗余冷通道风机降频'),
    priority: '中',
    detail: tl('B 区冷通道末端风机存在 30% 冗余风量，可统一降频至 70% 运行。'),
    savingKw: 22,
    savingPct: 2.1,
    basis: tl('末端风量-温度联动分析'),
  },
]

async function adoptCooling(s: EnergySuggestion) {
  try {
    await adoptEnergyAdvice({
      suggestionId: s.id,
      title: s.title,
      priority: s.priority,
      savingKw: s.savingKw,
      savingPct: s.savingPct,
      detail: s.detail,
      basis: (s as any).basis,
      action: 'adopt',
      category: 'cooling',
      pueCurrent: advice.value?.pue.current ?? null,
      pueTarget: advice.value?.pue.target ?? null,
    } as any)
    adoptedCoolingIds.add(s.id)
    toast.success(tl('已采纳制冷优化建议'))
    await loadAdviceRecords()
  } catch (e: unknown) {
    toast.error((e as ErrorLike)?.message || String(e))
  }
}

async function ignoreCooling(s: EnergySuggestion) {
  try {
    await adoptEnergyAdvice({
      suggestionId: s.id,
      title: s.title,
      priority: s.priority,
      savingKw: s.savingKw,
      savingPct: s.savingPct,
      detail: s.detail,
      basis: (s as any).basis,
      action: 'ignore',
      category: 'cooling',
      pueCurrent: advice.value?.pue.current ?? null,
      pueTarget: advice.value?.pue.target ?? null,
    } as any)
    ignoredCoolingIds.add(s.id)
    toast.info(tl('已忽略该建议'))
    await loadAdviceRecords()
  } catch (e: unknown) {
    toast.error((e as ErrorLike)?.message || String(e))
  }
}

onMounted(async () => {
  try {
    data.value = await getEnergyOverview()
    await loadAdviceRecords()
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || String(e)
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
.eff-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
}
.eff-list {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 20px;
}
.eff-item {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed rgba(126, 147, 184, 0.2);
  padding: 4px 0;
  font-size: 13px;
}
.eff-item .k {
  color: var(--muted, #7e93b8);
}
.eff-item .v {
  color: var(--strong, #fff);
  font-weight: 600;
}
.advice-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.sum-item {
  display: flex;
  flex-direction: column;
}
.sum-item .num {
  font-size: 24px;
  font-weight: 800;
  color: #22e3ff;
}
.sum-item .lbl {
  font-size: 12px;
  color: #7e93b8;
}
.advice-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.advice-card {
  border: 1px solid rgba(126, 147, 184, 0.18);
  border-radius: 10px;
  padding: 14px;
  background: rgba(15, 27, 51, 0.4);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.advice-card.adopted {
  border-color: rgba(34, 227, 255, 0.5);
}
.advice-card.ignored {
  opacity: 0.6;
}
.ac-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ac-title {
  font-weight: 600;
  color: #cfe0ff;
  font-size: 14px;
}
.ac-detail {
  font-size: 12.5px;
  color: #9fb2d4;
  line-height: 1.5;
  margin: 0;
}
.ac-meta {
  font-size: 12px;
  color: #7e93b8;
}
.ac-basis {
  font-size: 11px;
  color: #5a6c88;
  word-break: break-all;
}
.ac-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.ac-state {
  margin-top: 4px;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge.crit {
  background: rgba(255, 77, 94, 0.18);
  color: #ff4d5e;
}
.badge.warn {
  background: rgba(255, 176, 32, 0.18);
  color: #ffb020;
}
.badge.info {
  background: rgba(34, 227, 255, 0.18);
  color: #22e3ff;
}
.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
}
.tag.ok {
  background: rgba(34, 227, 255, 0.18);
  color: #22e3ff;
}
.tag.no {
  background: rgba(126, 147, 184, 0.18);
  color: #7e93b8;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th,
.tbl td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(126, 147, 184, 0.14);
}
.tbl th {
  color: #7e93b8;
  font-weight: 500;
}
.muted {
  color: #7e93b8;
}
.sm {
  font-size: 12px;
}
.ai-tag {
  font-style: normal;
  font-size: 11px;
  color: #22e3ff;
  border: 1px solid rgba(34, 227, 255, 0.4);
  border-radius: 999px;
  padding: 1px 8px;
  margin-left: 6px;
  vertical-align: middle;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.feature {
  display: flex;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(126, 147, 184, 0.16);
  border-radius: 10px;
  background: rgba(126, 147, 184, 0.05);
}
.f-icon {
  font-size: 20px;
  line-height: 1.4;
}
.f-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.f-name {
  color: #fff;
  font-weight: 600;
  font-size: 13px;
}
.f-desc {
  color: #7e93b8;
  font-size: 12px;
  line-height: 1.5;
}
.f-tag {
  align-self: flex-start;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
}
.f-tag.on {
  color: #34d399;
  background: rgba(52, 211, 153, 0.14);
}
.f-tag.warn {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.14);
}
.verify-block {
  border: 1px solid rgba(126, 147, 184, 0.16);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}
.vb-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #fff;
}
.progress {
  height: 8px;
  border-radius: 999px;
  background: rgba(126, 147, 184, 0.18);
  overflow: hidden;
  margin-bottom: 12px;
}
.progress > i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #22e3ff, #3b82f6);
  transition: width 0.4s ease;
}
.verify-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.verify-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #cdd9ee;
}
.v-state {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.v-state.done {
  color: #34d399;
  background: rgba(52, 211, 153, 0.14);
}
.v-state.running {
  color: #22e3ff;
  background: rgba(34, 227, 255, 0.14);
}
</style>
