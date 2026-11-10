<template>
  <div class="energy-db">
    <div class="view-head">
      <div class="vh-left">
        <h1>{{ tl('nav.energy') }}</h1>
        <span class="sub">{{
          tl('PUE 实时监控 · 7 日能耗趋势 · 制冷策略优化 · AI 节能与电量预测')
        }}</span>
      </div>
      <button class="ph-btn" :disabled="busy" @click="page.reload">
        <RefreshCw :size="13" :class="{ 'is-spin': busy }" />
        {{ busy ? '刷新中' : '刷新' }}
      </button>
      <button class="ph-btn" :disabled="busy || !weekTrend.length" @click="exportCsv">
        <Download :size="13" />
        {{ tl('导出 CSV') }}
      </button>
    </div>

    <AsyncSection
      :page="page"
      skeleton-variant="skeleton"
      :skeleton-rows="8"
      min-height="320px"
      empty-title="暂无能耗数据"
      empty-desc="后端未返回能耗总览，请确认采集服务已接入"
    >
      <template #empty-actions>
        <button class="link-btn" @click="page.reload">重新加载</button>
      </template>

      <!-- 采纳记录加载失败：不阻断主页面，但必须可见 -->
      <div v-if="recordsError" class="inline-warn">
        <AlertTriangle :size="13" />
        <span>节能建议采纳记录加载失败：{{ recordsError }}</span>
        <button class="link-btn" @click="loadAdviceRecords">重试</button>
      </div>

      <!-- KPI -->
      <div class="grid cols-auto-sm">
        <MetricCard
          metricName="pue"
          :label="tl('当前 PUE')"
          :value="ov.todayPue"
          unit=""
          :severity="
            (ov.todayPue ?? 2) > 1.6 ? 'crit' : (ov.todayPue ?? 2) > 1.4 ? 'warn' : 'normal'
          "
        />
        <MetricCard
          metricName="totalEnergy"
          :label="tl('当日总能耗')"
          :value="ov.todayTotalKwh"
          unit="kWh"
        />
        <MetricCard
          metricName="itEnergy"
          :label="tl('IT 设备能耗')"
          :value="ov.todayItKwh"
          unit="kWh"
        />
        <MetricCard
          metricName="coolEnergy"
          :label="tl('制冷能耗')"
          :value="ov.todayCoolingKwh"
          unit="kWh"
        />
      </div>

      <!-- ===== 7 日联动: 选中某一天, 两张 7 日图 + 明细卡同步 ===== -->
      <div class="day-bar">
        <span class="db-label">{{ tl('7 日联动') }}</span>
        <button class="db-chip" :class="{ on: selectedDay === null }" @click="selectedDay = null">
          {{ tl('全部') }}
        </button>
        <button
          v-for="d in weekTrend"
          :key="d.date"
          class="db-chip"
          :class="{ on: selectedDay === d.date }"
          @click="toggleDay(d.date)"
        >
          {{ d.date.slice(5) }}
        </button>
        <span class="db-hint muted sm">{{
          tl('点击趋势图数据点或选择日期，两张 7 日图与明细卡同步')
        }}</span>
      </div>

      <div v-if="selectedRow" class="day-detail">
        <div class="dd-item">
          <span class="dd-k">{{ selectedDay?.slice(5) }}</span>
        </div>
        <div class="dd-item">
          <span class="dd-k">PUE</span><span class="dd-v">{{ selectedRow.pue }}</span>
        </div>
        <div class="dd-item">
          <span class="dd-k">{{ tl('IT 能耗') }}</span
          ><span class="dd-v">{{ fmtKwh(selectedRow.itKwh) }} kWh</span>
        </div>
        <div class="dd-item">
          <span class="dd-k">{{ tl('制冷能耗') }}</span
          ><span class="dd-v">{{ fmtKwh(selectedRow.coolingKwh) }} kWh</span>
        </div>
        <div class="dd-item">
          <span class="dd-k">{{ tl('总能耗') }}</span
          ><span class="dd-v">{{ fmtKwh(selectedRow.totalKwh) }} kWh</span>
        </div>
        <div class="dd-item">
          <span class="dd-k">{{ tl('制冷占比') }}</span
          ><span class="dd-v">{{ coolingShareOfSelected }}%</span>
        </div>
        <button class="link-btn" @click="selectedDay = null">{{ tl('清除') }}</button>
      </div>

      <!-- PUE 趋势图 -->
      <Panel v-if="pueChartOption" :title="tl('PUE 7 日趋势')">
        <BaseChart
          :option="pueChartOption"
          height="260px"
          clickable
          @point-click="onDayPointClick"
        />
      </Panel>

      <!-- 能耗分解图 -->
      <Panel v-if="breakdownChartOption" :title="tl('7 日能耗分解')">
        <BaseChart
          :option="breakdownChartOption"
          height="260px"
          clickable
          @point-click="onDayPointClick"
        />
      </Panel>

      <!-- 未来 24h 负载预测 -->
      <Panel v-if="loadForecastOption" :title="tl('未来 24 小时负载预测 (kW)')">
        <template #extra>
          <DataBadge
            tone="partial"
            label="不参与日期联动"
            tip="该图为未来 24 小时维度，与上方 7 日历史趋势不在同一时间轴上，因此不随日期选择变化"
          />
        </template>
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
              <span
                >{{ tl('估算节能') }} ≈ {{ s.savingKw.toLocaleString() }} kW /
                {{ s.savingPct }}%</span
              >
            </div>
            <div class="ac-basis" v-if="s.basis">{{ tl('依据') }}: {{ s.basis }}</div>
            <div class="ac-actions" v-if="!adoptedIds.has(s.id) && !ignoredIds.has(s.id)">
              <button class="btn-sm btn-primary" v-bind="authState('write')" @click="adopt(s)">
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
              <td>
                <span class="badge" :class="prioClass(r.priority)">{{ r.priority }}</span>
              </td>
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

        <!-- 整块为前端静态示例内容，与真实冷机数据无关，必须显式标注 -->
        <MockDataBanner
          level="full"
          :note="`本区块（功能卡 / 验证进度 / 优化建议）为前端写死的静态示例内容，未接入实时冷负荷与温场数据，不可作为制冷设定值调整依据`"
        />

        <div class="feature-grid">
          <div class="feature" v-for="f in coolingFeatures" :key="f.key">
            <div class="f-icon"><component :is="f.icon" :size="18" /></div>
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
              <span
                >{{ tl('估算节能') }} ≈ {{ s.savingKw.toLocaleString() }} kW /
                {{ s.savingPct }}%</span
              >
            </div>
            <div class="ac-basis" v-if="s.basis">{{ tl('依据') }}: {{ s.basis }}</div>
            <div
              class="ac-actions"
              v-if="!adoptedCoolingIds.has(s.id) && !ignoredCoolingIds.has(s.id)"
            >
              <button
                class="btn-sm btn-primary"
                v-bind="authState('write')"
                @click="adoptCooling(s)"
              >
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
    </AsyncSection>
  </div>
</template>

<script setup lang="ts">
import { cssToken } from '@/assets/echarts-theme'
import { ref, computed, reactive } from 'vue'
import {
  RefreshCw,
  AlertTriangle,
  Download,
  Thermometer,
  Target,
  Fan,
  Snowflake,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import { downloadCsv, stampedName } from '@/utils/export'
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

const page = useAsyncPage<EnergyOverview | null>(() => getEnergyOverview(), {
  onSuccess: () => {
    void loadAdviceRecords()
  },
})
const data = page.data
// 顶层解构后模板会自动解包 Ref（page.busy 是嵌套引用，不会自动解包）
const { busy } = page
/** 安全访问：加载中 / 失败时也能渲染，避免模板里满屏 `data?.x` */
const ov = computed<Partial<EnergyOverview>>(() => page.data.value ?? {})
const adviceRecords = ref<EnergyAdviceAdoptRecord[]>([])
/** 采纳记录加载失败不阻断主页面，但必须可见（原实现 catch 全吞） */
const recordsError = ref('')
const adoptedIds = reactive(new Set<string>())
const ignoredIds = reactive(new Set<string>())

const advice = computed(() => data.value?.advice ?? null)

/* ===== 7 日联动 ===== */
const weekTrend = computed(() => data.value?.weekTrend ?? [])
const selectedDay = ref<string | null>(null)
const selectedRow = computed(() => {
  const d = selectedDay.value
  if (!d) return null
  return weekTrend.value.find((x) => x.date === d) ?? null
})
const coolingShareOfSelected = computed(() => {
  const r = selectedRow.value
  if (!r || !r.totalKwh) return '—'
  return ((r.coolingKwh / r.totalKwh) * 100).toFixed(1)
})
function toggleDay(date: string) {
  selectedDay.value = selectedDay.value === date ? null : date
}
function onDayPointClick(p: { dataIndex: number }) {
  const row = weekTrend.value[p?.dataIndex ?? -1]
  if (row) toggleDay(row.date)
}
/** 在两张 7 日图上标出选中日 */
function withDayMarker(opt: EChartsOption): EChartsOption {
  const row = selectedRow.value
  if (!row) return opt
  const series = (opt as unknown as { series?: Record<string, unknown>[] }).series
  if (series?.[0]) {
    series[0].markLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: cssToken('--amber'), type: 'dashed', width: 1 },
      label: { show: false },
      data: [{ xAxis: row.date.slice(5) }],
    }
  }
  return opt
}
function fmtKwh(v: number): string {
  return (v ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

const pueChartOption = computed<EChartsOption | null>(() => {
  if (!data.value?.weekTrend?.length) return null
  const d = data.value.weekTrend
  return withDayMarker(
    lineOption(
      d.map((t) => t.date.slice(5)),
      [{ name: 'PUE', data: d.map((t) => t.pue as number), color: cssToken('--cyan'), area: true }],
    ),
  )
})

const breakdownChartOption = computed<EChartsOption | null>(() => {
  if (!data.value?.weekTrend?.length) return null
  const d = data.value.weekTrend
  return withDayMarker(
    lineOption(
      d.map((t) => t.date.slice(5)),
      [
        { name: tl('IT 能耗'), data: d.map((t) => t.itKwh), color: cssToken('--blue'), area: true },
        {
          name: tl('制冷能耗'),
          data: d.map((t) => t.coolingKwh),
          color: cssToken('--cyan'),
          area: true,
        },
        {
          name: tl('其他'),
          data: d.map((t) => t.totalKwh - t.itKwh - t.coolingKwh),
          color: cssToken('--txt2'),
          area: false,
          dashed: true,
        },
      ],
    ),
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
        color: cssToken('--blue'),
        area: true,
      },
      {
        name: tl('预测负荷'),
        data: lf.map((t) => t.pred),
        color: cssToken('--cyan'),
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
  return ringOption(
    pct,
    cur > 1.6 ? cssToken('--red') : cur > 1.4 ? cssToken('--amber') : cssToken('--cyan'),
  )
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
    toast.error(toErrorMessage(e))
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
    toast.error(toErrorMessage(e))
  }
}

async function loadAdviceRecords() {
  recordsError.value = ''
  try {
    const res = await getEnergyAdvice()
    adviceRecords.value = res.records
    res.records.forEach((r) => {
      if (r.action === 'adopt') adoptedIds.add(r.suggestionId)
      else if (r.action === 'ignore') ignoredIds.add(r.suggestionId)
    })
  } catch (e: unknown) {
    // 不阻断主页面, 但失败必须可见 —— 否则"已采纳"状态会与实际不一致
    recordsError.value = toErrorMessage(e)
  }
}

/* 7 日能耗趋势导出 CSV（消费统一 export.ts，与告警/风险一致） */
const ENERGY_CSV_HEADERS = [
  '日期',
  'PUE',
  '总能耗(kWh)',
  'IT 能耗(kWh)',
  '制冷能耗(kWh)',
  '制冷占比(%)',
]
function exportCsv() {
  const rows = weekTrend.value.map((t) => [
    t.date,
    t.pue ?? '',
    t.totalKwh,
    t.itKwh,
    t.coolingKwh,
    t.totalKwh ? ((t.coolingKwh / t.totalKwh) * 100).toFixed(1) : '',
  ])
  downloadCsv(stampedName('能耗7日趋势'), ENERGY_CSV_HEADERS, rows)
  toast.success(`${tl('已导出')} ${rows.length} ${tl('条')}`)
}

/* ===== 制冷策略优化 (由制冷 AI 优化模块整合) ===== */
const adoptedCoolingIds = reactive(new Set<string>())
const ignoredCoolingIds = reactive(new Set<string>())

const coolingFeatures = [
  {
    key: 'atw',
    icon: Thermometer,
    name: tl('冷冻水流量自适应'),
    desc: tl('依据冷负荷预测动态调节板换/水泵流量'),
    state: 'on',
    stateLabel: tl('运行中'),
  },
  {
    key: 'setpoint',
    icon: Target,
    name: tl('全局设定值寻优'),
    desc: tl('以 PUE 最低为目标寻优冷冻水/回风设定值'),
    state: 'on',
    stateLabel: tl('运行中'),
  },
  {
    key: 'ec',
    icon: Fan,
    name: tl('EC 风机群控'),
    desc: tl('依据温场分布联动调节末端风机转速'),
    state: 'warn',
    stateLabel: tl('部分启用'),
  },
  {
    key: 'freecool',
    icon: Snowflake,
    name: tl('自然冷源利用'),
    desc: tl('室外湿球温度达标时优先开板式换热'),
    state: 'on',
    stateLabel: tl('运行中'),
  },
]

const coolingVerify = {
  done: 2,
  total: 3,
  get pct() {
    return Math.round((this.done / this.total) * 100)
  },
  items: [
    {
      id: 'v1',
      state: 'done',
      stateLabel: tl('已验证'),
      name: tl('提高冷冻水供水温度 1℃'),
      note: tl('机房平均温度上升 0.6℃，制冷功率下降 4.2%'),
    },
    {
      id: 'v2',
      state: 'done',
      stateLabel: tl('已验证'),
      name: tl('关闭冗余冷通道风机'),
      note: tl('末端风机功率下降 11%'),
    },
    {
      id: 'v3',
      state: 'running',
      stateLabel: tl('验证中'),
      name: tl('板换自然冷源投入'),
      note: tl('预计节省冷机能耗 8%'),
    },
  ],
}

const coolingSuggestions = [
  {
    id: 'c1',
    title: tl('冷冻水供水温度上调 1.5℃'),
    priority: '高',
    detail: tl(
      '基于 AI 冷负荷预测，A/B 区服务器进出风温度均在安全阈值内，可上调供水温度以降低冷机压缩功。',
    ),
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
    toast.error(toErrorMessage(e))
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
    toast.error(toErrorMessage(e))
  }
}

// 加载由 useAsyncPage 接管（首次加载 + 失败可重试），onSuccess 里顺带拉采纳记录
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
  border-bottom: 1px dashed var(--accent-16);
  padding: 4px 0;
  font-size: 13px;
}
.eff-item .k {
  color: var(--txt2);
}
.eff-item .v {
  color: var(--txt-strong);
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
  color: var(--cyan);
}
.sum-item .lbl {
  font-size: 12px;
  color: var(--txt2);
}
.advice-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.advice-card {
  border: 1px solid var(--accent-16);
  border-radius: 10px;
  padding: 14px;
  background: var(--accent-35);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.advice-card.adopted {
  border-color: var(--accent-50);
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
  color: var(--txt);
  font-size: 14px;
}
.ac-detail {
  font-size: 12.5px;
  color: var(--txt);
  line-height: 1.5;
  margin: 0;
}
.ac-meta {
  font-size: 12px;
  color: var(--txt2);
}
.ac-basis {
  font-size: 11px;
  color: var(--txt2);
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
  background: color-mix(in srgb, var(--red) 18%, transparent);
  color: var(--red);
}
.badge.warn {
  background: color-mix(in srgb, var(--amber) 18%, transparent);
  color: var(--amber);
}
.badge.info {
  background: color-mix(in srgb, var(--cyan) 18%, transparent);
  color: var(--cyan);
}
.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
}
.tag.ok {
  background: color-mix(in srgb, var(--cyan) 18%, transparent);
  color: var(--cyan);
}
.tag.no {
  background: var(--accent-16);
  color: var(--txt2);
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
  border-bottom: 1px solid var(--accent-12);
}
.tbl th {
  color: var(--txt2);
  font-weight: 500;
}
.muted {
  color: var(--txt2);
}
.sm {
  font-size: 12px;
}
.ai-tag {
  font-style: normal;
  font-size: 11px;
  color: var(--cyan);
  border: 1px solid var(--cyan-line);
  border-radius: 999px;
  padding: 1px 8px;
  margin-left: 6px;
  vertical-align: middle;
}
.feature-grid {
  display: grid;
  /* 自适应列: 增减功能卡无需改类名, 窄屏自动堆叠 */
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.feature {
  display: flex;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--accent-16);
  border-radius: 10px;
  background: var(--accent-08);
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
  color: var(--txt-strong);
  font-weight: 600;
  font-size: 13px;
}
.f-desc {
  color: var(--txt2);
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
  color: var(--green);
  background: color-mix(in srgb, var(--green) 14%, transparent);
}
.f-tag.warn {
  color: var(--amber);
  background: color-mix(in srgb, var(--amber) 14%, transparent);
}
.verify-block {
  border: 1px solid var(--accent-16);
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
  color: var(--txt-strong);
}
.progress {
  height: 8px;
  border-radius: 999px;
  background: var(--accent-16);
  overflow: hidden;
  margin-bottom: 12px;
}
.progress > i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--cyan), var(--blue));
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
  color: var(--txt);
}
.v-state {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.v-state.done {
  color: var(--green);
  background: color-mix(in srgb, var(--green) 14%, transparent);
}
.v-state.running {
  color: var(--cyan);
  background: color-mix(in srgb, var(--cyan) 14%, transparent);
}

/* ===== 本轮新增 ===== */
.view-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.vh-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.ph-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  color: var(--txt2);
  background: transparent;
  border: 1px solid var(--accent-35);
  transition: all 0.18s;
  white-space: nowrap;
  flex-shrink: 0;
}
.ph-btn:hover:not(:disabled) {
  color: var(--txt-strong);
  border-color: var(--cyan);
}
.ph-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.is-spin {
  animation: en-rotate 0.8s linear infinite;
}
@keyframes en-rotate {
  to {
    transform: rotate(360deg);
  }
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--cyan);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* 采纳记录加载失败提示 */
.inline-warn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: var(--amber);
  background: color-mix(in srgb, var(--amber) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--amber) 35%, transparent);
}

/* 7 日联动条 */
.day-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.db-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--cyan);
  margin-right: 2px;
}
.db-chip {
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--accent-35);
  background: transparent;
  color: var(--txt);
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.15s;
  font-variant-numeric: tabular-nums;
}
.db-chip:hover {
  color: var(--txt-strong);
  border-color: var(--cyan);
}
.db-chip.on {
  background: var(--accent-16);
  border-color: var(--cyan);
  color: var(--cyan);
  font-weight: 600;
}
.db-hint {
  margin-left: auto;
}

/* 选中日明细 */
.day-detail {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--cyan) 30%, transparent);
  background: var(--grid-line);
}
.dd-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dd-k {
  font-size: 11px;
  color: var(--txt2);
}
.dd-v {
  font-size: 15px;
  font-weight: 700;
  color: var(--txt-strong);
  font-variant-numeric: tabular-nums;
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .eff-wrap {
    flex-direction: column;
    align-items: stretch;
  }
  .eff-list {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
  .db-hint {
    display: none;
  }
}
@media (max-width: 720px) {
  .view-head {
    flex-direction: column;
    align-items: stretch;
  }
  .ph-btn {
    align-self: flex-start;
  }
  .day-detail {
    gap: 12px;
  }
}
</style>
