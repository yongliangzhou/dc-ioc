<template>
  <div class="dashboard-index">
    <!-- ========== Header ========== -->
    <div class="page-head">
      <div class="ph-left">
        <h2 class="page-title">驾驶舱总览</h2>
        <span class="ph-meta">
          {{ lastRefresh ? `最近刷新 ${lastRefresh} · 每 30 秒自动刷新` : '正在加载…' }}
        </span>
      </div>
      <button class="ph-refresh" :disabled="anyLoading" @click="refreshAll">
        <RefreshCw :size="13" :class="{ 'is-spin': anyLoading }" />
        {{ anyLoading ? '刷新中' : '手动刷新' }}
      </button>
    </div>

    <!-- ========== 部分失败汇总: 绝不允许静默降级 ========== -->
    <ErrorBanner
      :count="errorCount"
      :labels="failedLabels"
      :retrying="anyLoading"
      @retry="reloadFailed"
    />

    <!-- ========== Section 1: KPI（1 主 + 5 次） ========== -->
    <AsyncSection
      :page="overviewPage"
      @retry="overviewPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="3"
      min-height="128px"
      empty-title="暂无总览数据"
      empty-desc="后端未返回驾驶舱指标"
    >
      <div class="kpi-row">
        <!-- 主指标 -->
        <div class="kpi-primary">
          <div class="kp-head">
            <span class="kp-label">PUE</span>
            <DataBadge
              v-if="!hasRealTrends"
              tone="sample"
              label="趋势为示例"
              tip="迷你趋势与环比由前端基于当前 PUE 合成，后端暂无历史时序接口，不可作为能效考核依据"
            />
          </div>
          <div class="kp-value">{{ fmtNum(ov.pue) }}</div>
          <div class="kp-foot">
            <span class="kp-trend" :class="pueTrendPercent >= 0 ? 'up' : 'down'">
              {{ pueTrendPercent >= 0 ? '▲' : '▼' }} {{ Math.abs(pueTrendPercent).toFixed(1) }}%
            </span>
            <span class="kp-sub">较上一周期</span>
          </div>
          <div class="kp-spark">
            <TrendChart :series="pueSpark" :x-axis-data="pueSparklineX" :height="52" />
          </div>
        </div>

        <!-- 次指标 -->
        <KpiCard
          title="IT 负载"
          :value="fmtNum(ov.it_load_mw)"
          unit="MW"
          size="sm"
          subtitle="设计 4.8 MW"
          :bar-value="itLoadPct"
        />
        <KpiCard
          title="总负载"
          :value="fmtNum(ov.total_load_mw)"
          unit="MW"
          size="sm"
          :subtitle="`制冷占比 ${coolLoadPct}%`"
          :trend="totalLoadTrend"
        />
        <KpiCard
          title="制冷负载"
          :value="fmtNum(ov.cool_load_mw)"
          unit="MW"
          size="sm"
          subtitle="冷源贡献"
          :status="coolLoadStatus"
        />
        <KpiCard
          title="设备在线率"
          :value="fmtNum(ov.online_rate)"
          unit="%"
          size="sm"
          :subtitle="`${ov.online_devices ?? 0}/${ov.total_devices ?? 0} 台`"
          :bar-value="ov.online_rate || 0"
          :status="(ov.online_rate || 100) >= 95 ? 'normal' : 'warning'"
        />

        <!-- 次指标 · 告警（可点击跳转，最 actionable） -->
        <div class="kpi-cell alarm-cell" @click="goAlarms">
          <div class="alarm-kpi-top">
            <span class="alarm-kpi-label">活跃告警</span>
            <span class="alarm-kpi-val">{{ ov.today_alarms ?? 0 }}</span>
            <span class="alarm-kpi-unit">条</span>
          </div>
          <div class="alarm-kpi-badges">
            <AlarmBadge level="critical" :count="ov.alarms?.crit ?? 0" />
            <AlarmBadge level="warning" :count="ov.alarms?.warn ?? 0" />
            <AlarmBadge level="info" :count="ov.alarms?.info ?? 0" />
          </div>
        </div>
      </div>
    </AsyncSection>

    <!-- ========== Section 2: 关键趋势（可点选时段联动下方告警） ========== -->
    <div class="section-bar">
      <h3 class="section-title">关键趋势</h3>
      <div class="sb-actions">
        <DataBadge
          v-if="!hasRealTrends"
          tone="sample"
          tip="三条曲线均由前端基于当前指标合成示例数据（后端暂无历史时序接口），仅用于观察量级与趋势形态；点击曲线可选取时段筛选下方告警"
        />
        <button v-if="selectedHour" class="filter-chip" @click="selectedHour = null">
          时段 {{ selectedHour }} <span class="fc-x">×</span>
        </button>
      </div>
    </div>
    <AsyncSection
      :page="trendsPage"
      @retry="trendsPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="6"
      min-height="220px"
      empty-title="暂无趋势数据"
      empty-desc="后端未返回 KPI 趋势时序"
    >
      <div class="trends-grid">
        <div class="trend-card">
          <TrendChart
            title="PUE & WUE 趋势"
            :series="trendDatasets.pueWue"
            :x-axis-data="trendBaselineX"
            :height="200"
            clickable
            @point-click="onTrendPointClick"
          />
        </div>
        <div class="trend-card">
          <TrendChart
            title="IT / 总负载 / 制冷负载 (MW)"
            :series="trendDatasets.loads"
            :x-axis-data="trendBaselineX"
            :height="200"
            clickable
            @point-click="onTrendPointClick"
          />
        </div>
        <div class="trend-card">
          <TrendChart
            title="设备在线率 & 可用性 (%)"
            :series="trendDatasets.online"
            :x-axis-data="trendBaselineX"
            :height="200"
            clickable
            @point-click="onTrendPointClick"
          />
        </div>
      </div>
    </AsyncSection>

    <!-- ========== Section 3: 实时告警联动 ========== -->
    <div class="section-bar">
      <h3 class="section-title">
        实时告警联动 <span class="alarm-count-badge">{{ activeAlarms.length }} 条活跃</span>
      </h3>
      <button v-if="selectedHour" class="filter-chip" @click="selectedHour = null">
        已按时段 {{ selectedHour }} 过滤 <span class="fc-x">×</span>
      </button>
    </div>
    <AsyncSection
      :page="alarmsPage"
      @retry="alarmsPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="5"
      min-height="160px"
      empty-title="当前无活跃告警"
      empty-desc="所有监控对象运行正常"
    >
      <template #empty-actions>
        <button class="link-btn" @click="goAlarms">查看告警历史</button>
      </template>
      <div class="alarm-feed">
        <div v-if="!filteredAlarms.length" class="alarm-empty">
          时段 {{ selectedHour }} 内无告警
          <button class="link-btn" @click="selectedHour = null">清除筛选</button>
        </div>
        <div
          v-for="a in filteredAlarms.slice(0, 8)"
          :key="a.id ?? a.message"
          class="alarm-row"
          @click="goAlarms"
        >
          <AlarmBadge :level="a.level ?? 'info'" :count="0" />
          <span class="alarm-msg">{{ a.title || a.message }}</span>
          <span class="alarm-time">{{ formatAlarmTime(a.time || a.created_at) }}</span>
        </div>
      </div>
    </AsyncSection>

    <!-- ========== Section 4: 制冷系统总览 ========== -->
    <div class="section-bar">
      <h3 class="section-title">制冷系统总览</h3>
    </div>
    <AsyncSection
      :page="hvacPage"
      @retry="hvacPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="3"
      min-height="120px"
      empty-title="暂无暖通数据"
      empty-desc="后端未返回暖通总览"
    >
      <div class="cooling-entry-row">
        <div class="cooling-entry" @click="goMonitor('/monitor/hvac/chiller')">
          <KpiCard
            title="冷源 COP"
            :value="coolingStats.cop ?? '--'"
            size="sm"
            subtitle="冷源系统群控"
            :clickable="true"
          />
          <div class="entry-foot">
            <DataBadge
              v-if="coolingStats.cop == null"
              tone="partial"
              label="无运行机组"
              tip="系统 COP 取运行机组的平均单机 COP；当前没有处于运行状态的冷机，因此无法计算（待机/检修机的 cop 为 0，不计入）"
            />
            <span class="entry-hint">点击进入 → 冷源群控</span>
          </div>
        </div>

        <div class="cooling-entry" @click="goMonitor('/monitor/hvac/crac')">
          <KpiCard
            title="空调 SHR"
            :value="coolingStats.shr ?? '--'"
            size="sm"
            subtitle="精密空调末端"
            :clickable="true"
          />
          <div class="entry-foot">
            <DataBadge
              v-if="coolingStats.shr == null"
              tone="partial"
              label="样本不足"
              tip="系统 SHR 由运行机组的送/回风干球温度与相对湿度按 ASHRAE 简化式计算；当前无有效样本（可能无运行机组，或温湿度测点缺失/机组处于加湿工况）"
            />
            <span class="entry-hint">点击进入 → 空调末端</span>
          </div>
        </div>

        <div class="cooling-entry" @click="goMonitor('/monitor/hvac/liquid')">
          <KpiCard
            title="液冷 PUE 贡献"
            :value="coolingStats.pueC ?? '--'"
            size="sm"
            subtitle="液冷系统"
            :clickable="true"
          />
          <div class="entry-foot">
            <span class="entry-hint">点击进入 → 液冷系统</span>
          </div>
        </div>

        <div class="cooling-entry">
          <KpiCard
            title="自然冷却时"
            :value="fmtNum(freeCoolHours)"
            unit="h"
            size="sm"
            subtitle="本月累计"
            :bar-value="freeCoolPct"
          />
          <div class="entry-foot">
            <span class="entry-hint">占本月 {{ freeCoolPct }}%</span>
          </div>
        </div>
      </div>
    </AsyncSection>

    <!-- ========== Section 5: 业务域健康度 ========== -->
    <div class="section-bar">
      <h3 class="section-title">业务域健康度</h3>
    </div>
    <AsyncSection
      :page="overviewPage"
      @retry="overviewPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="4"
      min-height="150px"
      empty-title="暂无健康度数据"
      empty-desc="后端未返回总览指标"
    >
      <div class="domain-health-row">
        <div v-for="d in domainCards" :key="d.key" class="domain-card">
          <div class="domain-card-header">
            <StatusBadge :status="d.healthStatus" />
            <span class="domain-card-title">{{ d.title }}</span>
          </div>
          <div class="domain-card-inner">
            <div class="domain-ring">
              <svg viewBox="0 0 100 100" class="ring-svg">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#1e293b" stroke-width="8" />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  :stroke="d.ringColor"
                  stroke-width="8"
                  stroke-linecap="round"
                  :stroke-dasharray="`${d.ringRate * 2.64} 264`"
                  stroke-dashoffset="0"
                  transform="rotate(-90 50 50)"
                />
                <text
                  x="50"
                  y="52"
                  text-anchor="middle"
                  fill="#c8d6e5"
                  font-size="16"
                  font-weight="700"
                >
                  {{ d.ringRate }}%
                </text>
              </svg>
            </div>
            <div class="domain-stats">
              <div class="domain-stat-item">
                <StatusBadge :status="d.healthStatus" />
                <span>设备 {{ d.onlineRate }}% 在线</span>
                <DataBadge v-if="d.derived" tone="partial" label="派生" :tip="d.derivedTip" />
              </div>
              <div class="domain-stat-item">
                <StatusBadge :status="alarmSeverity" />
                <span>告警 {{ globalAlarmTotal }} 条</span>
                <DataBadge
                  tone="partial"
                  label="全局"
                  tip="分域告警数需后端按业务域聚合，当前未接入。此处展示的是全局活跃告警总数，并非该业务域的独立统计，请勿按域解读"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 脚注: 说清数据怎么来的, 而不是让人误以为是真实分域采集 -->
      <p class="section-note">
        <template v-if="hasRealDomain">
          分域在线率由后端按业务域<b>真实设备聚合</b>（暖通 / 电力 /
          安防分别统计各自注册设备的在线数），
          <b>非全局派生值</b>。
        </template>
        <template v-else>
          各域在线率由全局综合在线率派生（暖通 = 全局，电力 = 全局 − 1，安防 = 全局 + 1），
          <b>非真实分域采集</b>。
        </template>
        告警数为<b>全局活跃告警总数</b>（{{ globalAlarmTotal }} 条， 严重
        {{ ov.alarms?.crit ?? 0 }} · 警告 {{ ov.alarms?.warn ?? 0 }} · 提示
        {{ ov.alarms?.info ?? 0 }}），四个域显示同一数值， <b>不代表各域独立统计</b>——原页面硬编码的
        3/1/0/0 属虚构数据，已移除。
      </p>
    </AsyncSection>

    <!-- ========== Section 6: 校区总览 ========== -->
    <div class="section-bar">
      <h3 class="section-title">校区总览</h3>
    </div>
    <AsyncSection
      :page="campusPage"
      @retry="campusPage.reload"
      skeleton-variant="skeleton"
      :skeleton-rows="3"
      min-height="120px"
      empty-title="暂无校区数据"
      empty-desc="后端未返回校区对比数据"
    >
      <div class="campus-row">
        <div
          v-for="c in campuses"
          :key="c.code ?? c.id ?? c.name"
          class="campus-card"
          :class="{ 'is-active': selectedCampusCode === (c.code ?? c.id) }"
          @click="selectCampus(c)"
        >
          <div class="campus-status">
            <StatusBadge :status="computeCampusStatus(c)" />
          </div>
          <div class="campus-name">{{ c.name }}</div>
          <div class="campus-kpi-list">
            <div class="campus-kpi">
              <span>PUE</span><span class="v">{{ fmtNum(c.pue) }}</span>
            </div>
            <div class="campus-kpi">
              <span>在线率</span><span class="v">{{ fmtNum(c.online_rate) }}%</span>
            </div>
            <div class="campus-kpi">
              <span>IT负载</span><span class="v">{{ fmtNum(c.it_load_mw) }}MW</span>
            </div>
            <div class="campus-kpi">
              <span>告警</span><span class="v">{{ c.today_alarms ?? 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="selectedCampus" class="campus-detail">
        <div class="cd-head">
          <span class="cd-title">{{ selectedCampus.name }} · 明细</span>
          <button class="link-btn" @click="selectedCampus = null">收起</button>
        </div>
        <div class="cd-grid">
          <div class="cd-item">
            <span class="cd-k">PUE</span><span class="cd-v">{{ fmtNum(selectedCampus.pue) }}</span>
          </div>
          <div class="cd-item">
            <span class="cd-k">在线率</span>
            <span class="cd-v">{{ fmtNum(selectedCampus.online_rate) }}%</span>
          </div>
          <div class="cd-item">
            <span class="cd-k">IT 负载</span>
            <span class="cd-v">{{ fmtNum(selectedCampus.it_load_mw) }} MW</span>
          </div>
          <div class="cd-item">
            <span class="cd-k">今日告警</span>
            <span class="cd-v">{{ selectedCampus.today_alarms ?? 0 }} 条</span>
          </div>
        </div>
      </div>
    </AsyncSection>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw } from 'lucide-vue-next'
import { fmtNum } from '@/utils/format'
import {
  getDashboardOverview,
  getActiveAlarms,
  getCampusComparison,
  getOverviewTrends,
} from '@/api/index'
import { getHvacOverview } from '@/api/hvac'
import type { DashboardOverview, Alarm, CampusComparisonItem } from '@/types'
import type { HvacOverview } from '@/api/hvac'
import { KpiCard, StatusBadge, AlarmBadge } from '@dc-ioc/ui'
import TrendChart from '@/components/monitor/TrendChart.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { useAsyncPageAll } from '@/composables/useAsyncPage'
import { seeded as seededRnd, sampleSeries as genSeries } from '@/utils/sample'

const router = useRouter()

/* ------------------------------------------------------------------ */
/* 数据源: 4 路并发, 单源失败不影响其它区块渲染, 但必须显式露出          */
/* ------------------------------------------------------------------ */
const all = useAsyncPageAll({
  overview: () => getDashboardOverview(),
  alarms: () => getActiveAlarms(),
  campus: () => getCampusComparison(),
  hvac: () => getHvacOverview(),
  trends: () => getOverviewTrends(48),
})

const { errorCount, failedKeys, anyLoading, anyError, reloadAll, reloadFailed } = all
const overviewPage = all.pages.overview
const alarmsPage = all.pages.alarms
const campusPage = all.pages.campus
const hvacPage = all.pages.hvac
const trendsPage = all.pages.trends

const SOURCE_LABELS: Record<string, string> = {
  overview: '驾驶舱总览',
  alarms: '实时告警',
  campus: '校区对比',
  hvac: '暖通总览',
  trends: 'KPI 趋势',
}
const failedLabels = computed(() => failedKeys.value.map((k) => SOURCE_LABELS[k] ?? k))

/* ------------------------------------------------------------------ */
/* 派生数据                                                            */
/* ------------------------------------------------------------------ */
interface OverviewLike extends Partial<DashboardOverview> {
  [k: string]: unknown
}
interface CampusLike extends Partial<CampusComparisonItem> {
  name?: string
  code?: string
  id?: string
  pue?: number
  online_rate?: number
  it_load_mw?: number
  today_alarms?: number
  [k: string]: unknown
}

const ov = computed<OverviewLike>(() => (overviewPage.data.value ?? {}) as OverviewLike)
const activeAlarms = computed<Alarm[]>(() => alarmsPage.data.value?.items ?? [])
const campuses = computed<CampusLike[]>(() => {
  const list = campusPage.data.value?.comparisons
  return Array.isArray(list) ? (list as CampusLike[]) : []
})
const hvacData = computed<HvacOverview | undefined>(() => hvacPage.data.value)

/* ------------------------------------------------------------------ */
/* 制冷域指标                                                          */
/* ------------------------------------------------------------------ */
/**
 * 制冷域三项派生指标。
 *
 * COP / SHR 此前永远显示 '--'：旧代码从 `chiller.chillerGroups[].chiller.cop` 取值，
 * 而 chillerGroups 由后端 `raw.chillerGroups` 构造 —— 后端实际只返回 `chillers`，
 * 因此该数组恒为空。
 * 现改为读 api/hvac.ts 里派生的 `chiller.systemCop` / `crac.systemShr`：
 * 前者取运行机组的平均单机 COP，后者按送回风温湿度用 ASHRAE 简化式算显热比。
 * 无有效样本时为 null，卡片显示 '--' 并标注原因，不填假值。
 */
const coolingStats = computed(() => {
  const h = hvacData.value
  const cop = h?.chiller?.systemCop
  const shr = h?.crac?.systemShr
  const pueC = h?.liquidCooling?.pueContribution
  return {
    cop: typeof cop === 'number' && cop > 0 ? cop.toFixed(2) : null,
    shr: typeof shr === 'number' && shr > 0 ? shr.toFixed(2) : null,
    pueC: typeof pueC === 'number' && pueC > 0 ? pueC.toFixed(3) : null,
  }
})

const DESIGN_CAPACITY_MW = 4.8
const HOURS_PER_MONTH = 720

const itLoadPct = computed(() =>
  Math.min(((ov.value.it_load_mw ?? 0) / DESIGN_CAPACITY_MW) * 100, 100),
)
const coolLoadPct = computed(() => {
  const total = ov.value.total_load_mw ?? 0
  if (!total) return 0
  return +(((ov.value.cool_load_mw ?? 0) / total) * 100).toFixed(1)
})
const coolLoadStatus = computed<'normal' | 'warning'>(() =>
  coolLoadPct.value > 40 ? 'warning' : 'normal',
)
const freeCoolHours = computed(() => ov.value.free_cool_hours ?? 0)
const freeCoolPct = computed(
  () => +Math.min((freeCoolHours.value / HOURS_PER_MONTH) * 100, 100).toFixed(1),
)

/* ------------------------------------------------------------------ */
/* 业务域健康度                                                        */
/* ------------------------------------------------------------------ */

/**
 * 全局活跃告警总数。
 * 后端暂未按业务域聚合告警，四个域卡片展示同一数值，
 * 并用 DataBadge 标注「全局」+ 脚注说明，避免被当成各域独立统计。
 */
const globalAlarmTotal = computed(() => {
  const a = ov.value.alarms
  const sum = (a?.crit ?? 0) + (a?.warn ?? 0) + (a?.info ?? 0)
  return ov.value.today_alarms ?? sum
})
const alarmSeverity = computed<'success' | 'warning' | 'critical'>(() => {
  const n = globalAlarmTotal.value
  return n === 0 ? 'success' : n <= 5 ? 'warning' : 'critical'
})
/**
 * 分业务域在线率。
 * 后端（dc_aggregator.dashboard_overview）现按设备 domain 前缀真实聚合
 * hvac / power / security 三域各自的在线设备数 → 真实 rate。
 * 若某域未返回 domain_online（如无该域真实设备注册），回退到全局派生的 ±1 估算，
 * 并保留「派生」角标 + 脚注说明，绝不伪造为真实分域采集。
 */
interface DomainOnlineLike {
  online?: number
  total?: number
  rate?: number
}
const domainOnline = computed<Record<string, DomainOnlineLike>>(
  () => (ov.value.domain_online as Record<string, DomainOnlineLike>) ?? {},
)
const hasRealDomain = computed(() =>
  Object.values(domainOnline.value).some((d) => (d.total ?? 0) > 0),
)

const domainCards = computed(() => {
  const or = ov.value.online_rate ?? 100
  const level = (rate: number) =>
    rate >= 95 ? ('success' as const) : rate >= 85 ? ('warning' as const) : ('critical' as const)

  const realRate = (key: string): number | null => {
    const d = domainOnline.value[key]
    return d && (d.total ?? 0) > 0 ? (d.rate ?? 0) : null
  }

  const mk = (
    key: string,
    title: string,
    ringColor: string,
    fallbackRate: number,
    fallbackTip: string,
  ) => {
    const real = realRate(key)
    const isReal = real !== null
    const rate = isReal ? real! : fallbackRate
    const r = Math.max(0, Math.min(Math.round(rate), 100))
    return {
      key,
      title,
      ringColor,
      onlineRate: r,
      ringRate: r,
      healthStatus: level(r),
      derived: !isReal,
      derivedTip: isReal ? '在线率由后端按业务域真实设备聚合' : fallbackTip,
    }
  }

  return [
    mk('hvac', '暖通系统', '#05b896', or, '在线率直接取全局综合在线率，非暖通设备单独采集'),
    mk('power', '电力系统', '#f39c12', or - 1, '在线率 = 全局综合在线率 − 1，为派生估算值'),
    mk('security', '安防消防', '#3498db', or + 1, '在线率 = 全局综合在线率 + 1，为派生估算值'),
    {
      key: 'smartops',
      title: '数智运维',
      ringColor: '#9b59b6',
      onlineRate: 100,
      ringRate: 100,
      healthStatus: level(100),
      derived: true,
      derivedTip: '数智运维为软件域，无设备在线率概念，固定展示 100%',
    },
  ]
})

/* ------------------------------------------------------------------ */
/* 趋势数据: 优先后端真实时序 (kpi_history), 无数据回退前端合成示例      */
/* ------------------------------------------------------------------ */
interface KpiPointLike {
  ts?: string | null
  pue?: number
  wue?: number
  it_load_mw?: number
  total_load_mw?: number
  cool_load_mw?: number
  online_rate?: number
  availability?: number
}
const trendsPoints = computed<KpiPointLike[]>(
  () => (trendsPage.data.value?.points as KpiPointLike[] | undefined) ?? [],
)
const hasRealTrends = computed(() => trendsPoints.value.length >= 2)

const fmtTrendTs = (ts?: string | null): string => {
  if (!ts) return ''
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const pueSparklineX = computed(() => {
  if (hasRealTrends.value) return trendsPoints.value.slice(-30).map((p) => fmtTrendTs(p.ts))
  const arr: string[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    arr.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return arr
})
const pueSpark = computed(() => {
  const base = ov.value.pue || 1.25
  if (hasRealTrends.value) {
    return [
      {
        name: 'PUE',
        type: 'line' as const,
        data: trendsPoints.value.slice(-30).map((p) => p.pue ?? 0),
        color: '#05b896',
        smooth: true,
        areaStyle: { color: 'rgba(5,184,150,0.12)' },
        symbol: 'none' as const,
        symbolSize: 0,
      },
    ]
  }
  return [
    {
      name: 'PUE',
      type: 'line' as const,
      data: genSeries(base, 0.12, 30, base),
      color: '#05b896',
      smooth: true,
      areaStyle: { color: 'rgba(5,184,150,0.12)' },
      symbol: 'none' as const,
      symbolSize: 0,
    },
  ]
})

const trendBaselineX = computed(() => {
  if (hasRealTrends.value) return trendsPoints.value.map((p) => fmtTrendTs(p.ts))
  const arr: string[] = []
  for (let i = 47; i >= 0; i--) {
    const d = new Date()
    d.setHours(d.getHours() - i, 0, 0, 0)
    arr.push(`${String(d.getHours()).padStart(2, '0')}:00`)
  }
  return arr
})

const trendDatasets = computed(() => {
  const b = ov.value
  const pueBase = b.pue || 1.25
  const wueBase = b.wue || 1.8
  const itBase = b.it_load_mw || 2.1
  const totalBase = b.total_load_mw || 3.5
  const coolBase = b.cool_load_mw || 1.2
  const onRateBase = b.online_rate ?? 98
  const availBase = b.availability ?? 99.99

  if (hasRealTrends.value) {
    const pts = trendsPoints.value
    return {
      pueWue: [
        {
          name: 'PUE',
          type: 'line' as const,
          data: pts.map((p) => p.pue ?? 0),
          color: '#05b896',
          smooth: true,
          yAxisIndex: 0,
        },
        {
          name: 'WUE',
          type: 'line' as const,
          data: pts.map((p) => p.wue ?? 0),
          color: '#3498db',
          smooth: true,
          yAxisIndex: 1,
        },
      ],
      loads: [
        {
          name: 'IT负荷',
          type: 'line' as const,
          data: pts.map((p) => p.it_load_mw ?? 0),
          color: '#05b896',
          smooth: true,
        },
        {
          name: '总负荷',
          type: 'line' as const,
          data: pts.map((p) => p.total_load_mw ?? 0),
          color: '#f39c12',
          smooth: true,
        },
        {
          name: '制冷负荷',
          type: 'line' as const,
          data: pts.map((p) => p.cool_load_mw ?? 0),
          color: '#3498db',
          smooth: true,
        },
      ],
      online: [
        {
          name: '在线率',
          type: 'line' as const,
          data: pts.map((p) => p.online_rate ?? 0),
          color: '#05b896',
          smooth: true,
          yAxisIndex: 0,
        },
        {
          name: '可用性',
          type: 'line' as const,
          data: pts.map((p) => p.availability ?? 0),
          color: '#9b59b6',
          smooth: true,
          yAxisIndex: 1,
        },
      ],
    }
  }

  return {
    pueWue: [
      {
        name: 'PUE',
        type: 'line' as const,
        data: genSeries(pueBase, 0.12, 48, pueBase * 100),
        color: '#05b896',
        smooth: true,
        yAxisIndex: 0,
      },
      {
        name: 'WUE',
        type: 'line' as const,
        data: genSeries(wueBase, 0.2, 48, wueBase * 100 + 1),
        color: '#3498db',
        smooth: true,
        yAxisIndex: 1,
      },
    ],
    loads: [
      {
        name: 'IT负荷',
        type: 'line' as const,
        data: genSeries(itBase, 0.4, 48, itBase * 100 + 2),
        color: '#05b896',
        smooth: true,
      },
      {
        name: '总负荷',
        type: 'line' as const,
        data: genSeries(totalBase, 0.5, 48, totalBase * 100 + 3),
        color: '#f39c12',
        smooth: true,
      },
      {
        name: '制冷负荷',
        type: 'line' as const,
        data: genSeries(coolBase, 0.3, 48, coolBase * 100 + 4),
        color: '#3498db',
        smooth: true,
      },
    ],
    online: [
      {
        name: '在线率',
        type: 'line' as const,
        data: genSeries(onRateBase, 2, 48, onRateBase * 10 + 5),
        color: '#05b896',
        smooth: true,
        yAxisIndex: 0,
      },
      {
        name: '可用性',
        type: 'line' as const,
        data: genSeries(availBase, 0.02, 48, availBase * 10 + 6),
        color: '#9b59b6',
        smooth: true,
        yAxisIndex: 1,
      },
    ],
  }
})

/** 环比: 有真实趋势时取末两点差值, 否则回退基于当前值的合成值 */
const pueTrendPercent = computed(() => {
  const pts = trendsPoints.value
  if (hasRealTrends.value && pts.length >= 2) {
    const cur = pts[pts.length - 1].pue ?? 0
    const prev = pts[pts.length - 2].pue ?? cur
    return prev ? +(((cur - prev) / prev) * 100).toFixed(1) : 0
  }
  const base = ov.value.pue || 1.25
  const prev = +(base + (seededRnd(base * 100)() - 0.5) * 0.08).toFixed(3)
  return +(((base - prev) / (prev || 1)) * 100).toFixed(1)
})
const totalLoadTrend = computed(() => {
  const pts = trendsPoints.value
  if (hasRealTrends.value && pts.length >= 2) {
    const cur = pts[pts.length - 1].total_load_mw ?? 0
    const prev = pts[pts.length - 2].total_load_mw ?? cur
    return prev ? +(((cur - prev) / prev) * 100).toFixed(1) : 0
  }
  const b = ov.value.total_load_mw || 3.5
  const prev = +(b + (seededRnd(b * 100)() - 0.5) * 0.2).toFixed(2)
  return +(((b - prev) / (prev || 1)) * 100).toFixed(1)
})

/* ------------------------------------------------------------------ */
/* 趋势 → 告警 时段联动                                                */
/* ------------------------------------------------------------------ */
const selectedHour = ref<string | null>(null)

function onTrendPointClick(p: { x: string }) {
  if (!p?.x) return
  selectedHour.value = selectedHour.value === p.x ? null : p.x
}

function hourOf(t: string | undefined): string | null {
  if (!t) return null
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return null
  return `${String(d.getHours()).padStart(2, '0')}:00`
}

const filteredAlarms = computed(() => {
  const h = selectedHour.value
  if (!h) return activeAlarms.value
  return activeAlarms.value.filter((a) => hourOf(a.time || a.created_at) === h)
})

/* ------------------------------------------------------------------ */
/* 校区选择                                                           */
/* ------------------------------------------------------------------ */
const selectedCampus = ref<CampusLike | null>(null)
const selectedCampusCode = computed(() => selectedCampus.value?.code ?? selectedCampus.value?.id)
function selectCampus(c: CampusLike) {
  const key = c.code ?? c.id
  selectedCampus.value = selectedCampusCode.value === key ? null : c
}

/* ------------------------------------------------------------------ */
/* 交互                                                               */
/* ------------------------------------------------------------------ */
function goAlarms() {
  router.push('/ops/alarms')
}
function goMonitor(path: string) {
  router.push(path)
}
function formatAlarmTime(t: string | undefined): string {
  if (!t) return '--'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t.slice(0, 10)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
function computeCampusStatus(c: CampusLike): 'success' | 'warning' | 'critical' {
  const or = c.online_rate ?? 0
  if (or >= 95) return 'success'
  if (or >= 80) return 'warning'
  return 'critical'
}

/* ------------------------------------------------------------------ */
/* 刷新与轮询                                                          */
/* ------------------------------------------------------------------ */
const lastRefresh = ref('')
let timer: ReturnType<typeof setInterval> | undefined

// 仅在"一轮刷新完成且无失败"时打时间戳, 避免失败也显示"已刷新"
watch(
  () => anyLoading.value,
  (busy, prev) => {
    if (prev && !busy && !anyError.value) {
      lastRefresh.value = new Date().toLocaleTimeString('zh-CN')
    }
  },
)

function refreshAll() {
  return reloadAll()
}

onMounted(() => {
  timer = setInterval(() => {
    void reloadAll()
  }, 30_000)
})
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
})
</script>

<style scoped>
.dashboard-index {
  padding: 16px 20px 28px;
  max-width: 1560px;
  margin: 0 auto;
  color: #c8d6e5;
  font-size: 13px;
}

/* ===== Header ===== */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.ph-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #e8edf2;
  letter-spacing: 0.3px;
}
.ph-meta {
  font-size: 11px;
  color: #5a6a82;
}
.ph-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  color: #8892b0;
  background: transparent;
  border: 1px solid #1e293b;
  transition: all 0.18s;
  flex-shrink: 0;
}
.ph-refresh:hover:not(:disabled) {
  color: #e6edf3;
  border-color: #2a4a6a;
}
.ph-refresh:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.is-spin {
  animation: ph-rotate 0.8s linear infinite;
}
@keyframes ph-rotate {
  to {
    transform: rotate(360deg);
  }
}

/* ===== Section bar ===== */
.section-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 18px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #1e293b;
}
.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #e8edf2;
  white-space: nowrap;
}
.sb-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  cursor: pointer;
  color: #42a5f5;
  background: rgba(66, 165, 245, 0.12);
  border: 1px solid rgba(66, 165, 245, 0.4);
  transition: all 0.18s;
}
.filter-chip:hover {
  background: rgba(66, 165, 245, 0.22);
}
.fc-x {
  font-size: 13px;
  line-height: 1;
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #42a5f5;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ===== KPI: 1 主 + 5 次 (7 列栅格) ===== */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
  align-items: stretch;
}
.kpi-primary {
  grid-column: span 2;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #16273a, #0f1923);
  border: 1px solid #24405a;
  border-radius: 10px;
  padding: 12px 14px 10px;
  position: relative;
  overflow: hidden;
}
.kpi-primary::after {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(5, 184, 150, 0.6), transparent);
}
.kp-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.kp-label {
  font-size: 12px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}
.kp-value {
  font-size: 40px;
  font-weight: 800;
  line-height: 1;
  color: #05b896;
  font-variant-numeric: tabular-nums;
}
.kp-foot {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 8px;
}
.kp-trend {
  font-size: 12px;
  font-weight: 600;
}
.kp-trend.up {
  color: #ef4444;
}
.kp-trend.down {
  color: #22c55e;
}
.kp-sub {
  font-size: 11px;
  color: #64748b;
}
.kp-spark {
  margin-top: auto;
  padding-top: 6px;
}
.kpi-cell {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
}

/* 告警 KPI */
.alarm-cell {
  cursor: pointer;
  transition: border-color 0.15s;
}
.alarm-cell:hover {
  border-color: #e74c3c;
}
.alarm-kpi-top {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.alarm-kpi-label {
  font-size: 11px;
  color: #5a6a82;
}
.alarm-kpi-val {
  font-size: 26px;
  font-weight: 700;
  color: #e74c3c;
  margin-left: auto;
}
.alarm-kpi-unit {
  font-size: 12px;
  color: #5a6a82;
}
.alarm-kpi-badges {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* ===== 趋势 ===== */
.trends-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.trend-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 8px 10px;
}

/* ===== 告警流 ===== */
.alarm-feed {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 0 14px;
  max-height: 280px;
  overflow-y: auto;
}
.alarm-empty {
  padding: 16px 0;
  text-align: center;
  color: #3a5068;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.alarm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #15202b;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.15s;
}
.alarm-row:last-child {
  border-bottom: none;
}
.alarm-row:hover {
  background: #111d2a;
  margin: 0 -14px;
  padding-left: 14px;
  padding-right: 14px;
}
.alarm-msg {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.alarm-time {
  color: #3a5068;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.alarm-count-badge {
  font-size: 12px;
  font-weight: 400;
  color: #e74c3c;
  margin-left: 8px;
}

/* ===== 制冷入口 ===== */
.cooling-entry-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.cooling-entry {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.cooling-entry:hover {
  border-color: #05b89666;
}
.entry-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-wrap: wrap;
}
.entry-hint {
  font-size: 10px;
  color: #3a5068;
  text-align: right;
  margin-left: auto;
}

/* ===== 业务域健康度 ===== */
.domain-health-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.domain-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 12px 14px;
}
.domain-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.domain-card-title {
  font-size: 14px;
  font-weight: 600;
}
.domain-card-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.domain-ring {
  flex: 0 0 84px;
}
.ring-svg {
  width: 84px;
  height: 84px;
  display: block;
}
.domain-stats {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.domain-stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  flex-wrap: wrap;
}
.ds-muted {
  color: #5a6a82;
}
.section-note {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.7;
  color: #5a6a82;
}
.section-note b {
  color: #d9a441;
  font-weight: 600;
}

/* ===== 校区 ===== */
.campus-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.campus-card {
  background: #0f1923;
  border: 1px solid #1a2a3a;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.campus-card:hover {
  border-color: #2a4a6a;
}
.campus-card.is-active {
  border-color: #42a5f5;
  background: #101f2e;
}
.campus-status {
  margin-bottom: 4px;
}
.campus-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}
.campus-kpi-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.campus-kpi {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #5a6a82;
}
.campus-kpi .v {
  color: #c8d6e5;
  font-weight: 500;
}
.campus-detail {
  margin-top: 12px;
  background: #0f1923;
  border: 1px solid #24405a;
  border-radius: 10px;
  padding: 12px 14px;
}
.cd-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.cd-title {
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
}
.cd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}
.cd-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cd-k {
  font-size: 11px;
  color: #5a6a82;
}
.cd-v {
  font-size: 16px;
  font-weight: 700;
  color: #e6edf3;
  font-variant-numeric: tabular-nums;
}

/* ===== 响应式 ===== */
@media (max-width: 1440px) {
  .kpi-row {
    grid-template-columns: repeat(5, 1fr);
  }
  .kpi-primary {
    grid-column: span 5;
  }
}
@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .kpi-primary {
    grid-column: span 3;
  }
  .cooling-entry-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .domain-health-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .trends-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .dashboard-index {
    padding: 12px 12px 24px;
  }
  .page-head {
    flex-direction: column;
    align-items: stretch;
  }
  .ph-refresh {
    align-self: flex-start;
  }
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .kpi-primary {
    grid-column: span 2;
  }
  .kp-value {
    font-size: 32px;
  }
  .cooling-entry-row {
    grid-template-columns: 1fr;
  }
  .domain-health-row {
    grid-template-columns: 1fr;
  }
  .trends-grid {
    grid-template-columns: 1fr;
  }
  .section-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .sb-actions {
    justify-content: flex-start;
  }
}
</style>
