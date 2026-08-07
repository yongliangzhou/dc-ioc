<template>
  <div class="bat-view">
    <div class="view-head">
      <h1>{{ tl('电池监控系统') }}</h1>
      <span class="sub"
        >{{ tl('单体级监测') }} · {{ tl('电压 / 温度 / 内阻 / 充放电 / SOC / SOH') }}</span
      >
      <div class="head-actions">
        <span class="refresh-hint" :class="{ err: !!error }">
          <i class="dot" :class="error ? 'd-red' : 'd-green'"></i>
          {{ error ? tl('加载失败') : s ? tl('已连接') : tl('加载中...') }}
        </span>
        <button class="btn-refresh" :disabled="loading" @click="load">{{ tl('刷新') }}</button>
      </div>
    </div>

    <!-- 加载 / 错误态 -->
    <Panel v-if="!s" class="center-box">
      <span class="muted" :class="{ err: !!error }">{{ error || tl('加载中...') }}</span>
    </Panel>

    <template v-else>
      <!-- ============ 3.5.1 电池组概况 KPI ============ -->
      <div class="section-title"><span class="bar"></span>{{ tl('电池组概况') }}</div>
      <div class="kpi-row">
        <KpiCard
          :title="tl('系统总电压')"
          :value="sysVoltage"
          unit="V"
          :decimals="1"
          :status="sysVoltage < 200 ? 'danger' : 'normal'"
        />
        <KpiCard
          :title="tl('系统总电流')"
          :value="sysCurrent"
          unit="A"
          :decimals="1"
          :status="Math.abs(sysCurrent) > 200 ? 'warning' : 'normal'"
          :detail="sysCurrent >= 0 ? tl('放电') : tl('充电')"
        />
        <KpiCard
          :title="tl('平均 SOC')"
          :value="avgSoc"
          unit="%"
          :decimals="1"
          :bar-value="avgSoc"
          :bar-color="socColor"
          :status="avgSoc < 80 ? 'warning' : 'normal'"
        />
        <KpiCard
          :title="tl('平均 SOH')"
          :value="avgSoh"
          unit="%"
          :decimals="1"
          :bar-value="avgSoh"
          :bar-color="sohColor"
          :status="avgSoh < 90 ? 'warning' : 'normal'"
        />
      </div>

      <!-- SOC / SOH 仪表盘 -->
      <Panel class="socsoh-card" title="荷电 / 健康状态">
        <template #extra>
          <span class="pill" :class="cellAlarmCount === 0 ? 'g' : 'a'"
            >{{ groups.length }} {{ tl('组') }} · {{ tl('告警单体') }} {{ cellAlarmCount }}
            {{ tl('节') }}</span
          >
        </template>
        <div class="socsoh-row">
          <div class="gauge-wrap">
            <ProgressGauge
              :value="avgSoc"
              :max="100"
              unit="%"
              :label="tl('平均 SOC')"
              :status="avgSoc < 80 ? 'warning' : 'normal'"
            />
            <span class="gauge-sub">{{ tl('设计要求') }} ≥ 80%</span>
          </div>
          <div class="gauge-wrap">
            <ProgressGauge
              :value="avgSoh"
              :max="100"
              unit="%"
              :label="tl('平均 SOH')"
              :status="avgSoh < 90 ? 'warning' : 'normal'"
            />
            <span class="gauge-sub">{{ tl('健康度') }} = 容量/初始容量</span>
          </div>
          <div class="gauge-wrap">
            <ProgressGauge
              :value="backupMin"
              :max="30"
              unit="min"
              :label="tl('后备时间')"
              :status="backupMin < 10 ? 'danger' : backupMin < 15 ? 'warning' : 'normal'"
              :color="backupMin < 10 ? 'var(--red)' : 'var(--cyan)'"
            />
            <span class="gauge-sub">{{ tl('上次核容') }} {{ s.lastDischarge || '-' }}</span>
          </div>
          <div class="gauge-wrap">
            <ProgressGauge
              :value="worstSohGroup"
              :max="100"
              unit="%"
              :label="tl('最差组 SOH')"
              :status="worstSohGroup < 90 ? 'warning' : 'normal'"
            />
            <span class="gauge-sub">{{ worstGroupName || '-' }}</span>
          </div>
        </div>
      </Panel>

      <!-- ============ 3.5.4 电池组拓扑图 (SVG) ============ -->
      <Panel title="电池组拓扑">
        <template #extra>
          <span class="pill b">{{ tl('并机直流母线') }}</span>
        </template>
        <div class="topo-wrap">
          <svg viewBox="0 0 920 320" class="topo-svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="busGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#22e3ff" />
                <stop offset="100%" stop-color="#3b82f6" />
              </linearGradient>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#5f6b7a" />
              </marker>
            </defs>

            <!-- 直流母线 -->
            <line x1="120" y1="60" x2="800" y2="60" stroke="url(#busGrad)" stroke-width="5" />
            <text x="460" y="48" class="topo-bus-label" text-anchor="middle">
              {{ tl('直流母线 DC Bus') }}
            </text>

            <!-- 充电/放电汇入箭头 -->
            <line
              x1="120"
              y1="60"
              x2="120"
              y2="160"
              stroke="#5f6b7a"
              stroke-width="2"
              stroke-dasharray="4 4"
              marker-end="url(#arrow)"
            />
            <line
              x1="800"
              y1="60"
              x2="800"
              y2="160"
              stroke="#5f6b7a"
              stroke-width="2"
              stroke-dasharray="4 4"
              marker-end="url(#arrow)"
            />

            <!-- 电池组节点 -->
            <g
              v-for="(g, idx) in groups"
              :key="g.id"
              class="topo-node"
              :class="groupStatusClass(g)"
              @click="selectGroup(g)"
              :transform="`translate(${140 + idx * (640 / Math.max(groups.length - 1, 1))}, 150)`"
            >
              <rect
                x="0"
                y="0"
                width="120"
                height="150"
                rx="8"
                :fill="groupFill(g)"
                :stroke="groupStroke(g)"
                stroke-width="2"
              />
              <!-- 组 SOC 填充条 -->
              <rect
                x="4"
                :y="146 - 142 * ((g.soc ?? 0) / 100)"
                width="112"
                :height="Math.max(0, 142 * ((g.soc ?? 0) / 100))"
                rx="5"
                :fill="socBarColor(g.soc ?? 0)"
                opacity="0.35"
              />
              <!-- 组号 -->
              <text x="60" y="22" class="topo-g-id" text-anchor="middle">{{ g.id }}</text>
              <text x="60" y="40" class="topo-g-type" text-anchor="middle">{{ g.type }}</text>
              <!-- 电压/电流 -->
              <text x="60" y="66" class="topo-g-metric" text-anchor="middle">
                {{ fmt(g.u, 1) }} V
              </text>
              <text x="60" y="84" class="topo-g-metric" text-anchor="middle">
                {{ fmt(g.i, 1) }} A
              </text>
              <!-- SOC 大字 -->
              <text
                x="60"
                y="112"
                class="topo-g-soc"
                text-anchor="middle"
                :fill="socTextColor(g.soc)"
              >
                {{ g.soc }}%
              </text>
              <!-- 状态标签 -->
              <text x="60" y="134" class="topo-g-state" text-anchor="middle">{{ g.state }}</text>
              <!-- 告警角标 -->
              <g v-if="groupAlarmCount(g) > 0">
                <circle cx="108" cy="10" r="11" fill="var(--red)" />
                <text x="108" y="14" class="topo-badge" text-anchor="middle">
                  {{ groupAlarmCount(g) }}
                </text>
              </g>
            </g>
          </svg>
        </div>
        <!-- 选中组信息条 -->
        <div class="topo-detail" v-if="selectedGroupObj">
          <span class="ct">{{ selectedGroupObj.id }} ({{ selectedGroupObj.type }})</span>
          <span class="kv"
            ><span class="k">{{ tl('SOC') }}</span
            ><span class="v">{{ selectedGroupObj.soc }}%</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('电压') }}</span
            ><span class="v">{{ fmt(selectedGroupObj.u, 1) }} V</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('电流') }}</span
            ><span class="v">{{ fmt(selectedGroupObj.i, 1) }} A</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('充放电') }}</span
            ><span class="v">{{ selectedGroupObj.cdState }}</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('最高温') }}</span
            ><span class="v" :class="selectedGroupObj.maxT > 35 ? 'a-text' : ''"
              >{{ selectedGroupObj.maxT }} °C</span
            ></span
          >
          <span class="kv"
            ><span class="k">{{ tl('内阻') }}</span
            ><span class="v" :class="selectedGroupObj.ir !== '正常' ? 'a-text' : 'g-text'">{{
              selectedGroupObj.ir
            }}</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('最差单体') }}</span
            ><span class="v mono">{{ selectedGroupObj.worstCell }}</span></span
          >
          <span class="kv"
            ><span class="k">{{ tl('单体数') }}</span
            ><span class="v">{{ selectedGroupObj.cells?.length || 0 }}</span></span
          >
          <button class="close-btn" @click="selectedGroupObj = null">×</button>
        </div>
      </Panel>

      <!-- ============ 电池组概览表 ============ -->
      <Panel class="scroll-x" title="电池组参数">
        <template #extra>
          <span class="pill g">{{ tl('TA 逐节采集 · TC 组级采集') }}</span>
        </template>
        <table>
          <thead>
            <tr>
              <th>{{ tl('电池组') }}</th>
              <th>{{ tl('类型') }}</th>
              <th>{{ tl('状态') }}</th>
              <th>SOC</th>
              <th>{{ tl('组电压') }}(V)</th>
              <th>{{ tl('电流') }}(A)</th>
              <th>{{ tl('充放电') }}</th>
              <th>{{ tl('最高温') }}(°C)</th>
              <th>{{ tl('最差单体') }}</th>
              <th>{{ tl('内阻') }}</th>
              <th>{{ tl('单体数') }}</th>
              <th>{{ tl('告警') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="g in groups"
              :key="g.id"
              :class="{ 'row-warn': groupAlarmCount(g) > 0 }"
              @click="selectGroup(g)"
              style="cursor: pointer"
            >
              <td class="d-name">{{ g.id }}</td>
              <td class="muted">{{ g.type }}</td>
              <td>
                <span
                  class="tag"
                  :class="g.state === '浮充' ? 'g' : g.state === '放电' ? 'b' : 'a'"
                  >{{ g.state }}</span
                >
              </td>
              <td class="mono" :class="g.soc < 80 ? 'a-text' : 'g-text'">{{ g.soc }}%</td>
              <td class="mono">{{ fmt(g.u, 1) }}</td>
              <td class="mono">{{ fmt(g.i, 2) }}</td>
              <td>
                <span class="tag b">{{ g.cdState }}</span>
              </td>
              <td class="mono" :class="g.maxT > 35 ? 'a-text' : ''">{{ g.maxT }}</td>
              <td class="mono muted">{{ g.worstCell }}</td>
              <td>
                <span class="tag" :class="g.ir === '正常' ? 'g' : 'a'">{{ g.ir }}</span>
              </td>
              <td class="mono">{{ g.cells?.length || 0 }}</td>
              <td class="mono" :class="groupAlarmCount(g) > 0 ? 'a-text' : ''">
                {{ groupAlarmCount(g) }}
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ============ 3.5.2 单体电池电压 / 内阻 / 温度柱状图 ============ -->
      <Panel
        v-if="selectedGroupForChart"
        :title="`${selectedGroupForChart.id} · ${tl('单体电压 / 内阻 / 温度')}`"
      >
        <template #extra>
          <span class="pill" :class="groupAlarmCount(selectedGroupForChart) === 0 ? 'g' : 'a'"
            >{{ selectedGroupForChart.cells?.length || 0 }} {{ tl('节') }} · {{ tl('告警') }}
            {{ groupAlarmCount(selectedGroupForChart) }}</span
          >
          <div class="cell-switch">
            <button
              v-for="m in cellMetrics"
              :key="m.key"
              class="sw-btn"
              :class="{ active: cellMetric === m.key }"
              @click="cellMetric = m.key"
            >
              {{ m.label }}
            </button>
          </div>
        </template>

        <!-- 单体色块热力网格 -->
        <div class="cell-grid">
          <div
            v-for="c in selectedGroupForChart.cells"
            :key="c.no"
            class="cell-box"
            :class="cellCls(c.level)"
            :title="`${selectedGroupForChart.id} ${c.no} | U:${fmt(c.u, c.u < 5 ? 3 : 2)}V T:${c.t}°C`"
            @click="selectCell(c)"
          >
            <span class="cell-no">{{ c.no }}</span>
            <span class="cell-u">{{ fmt(c.u, c.u < 5 ? 2 : 1) }}V</span>
          </div>
        </div>

        <!-- 柱状图 -->
        <TrendChart class="cell-chart" :option="cellChartOption" :height="260" :loading="loading" />

        <!-- 选中单体详情 -->
        <div class="cell-detail" v-if="selectedCell">
          <div class="cell-detail-head">
            <span class="ct">{{ selectedGroupForChart.id }} · {{ selectedCell.no }}</span>
            <span class="tag" :class="sigLevelTagCls(selectedCell.level)">{{
              cellLevelLabel(selectedCell.level)
            }}</span>
            <button class="close-btn" @click="selectedCell = null">×</button>
          </div>
          <div class="cell-detail-grid">
            <div class="cd-item">
              <span class="k">{{ tl('单体电压') }}</span
              ><span class="v mono" :class="cellVClass(selectedCell)"
                >{{ fmt(selectedCell.u, selectedCell.u < 5 ? 3 : 2) }} V</span
              >
            </div>
            <div class="cd-item">
              <span class="k">{{ tl('单体温度') }}</span
              ><span class="v mono" :class="selectedCell.t > 35 ? 'a-text' : ''"
                >{{ selectedCell.t }} °C</span
              >
            </div>
            <div class="cd-item">
              <span class="k">{{ tl('单体内阻') }}</span
              ><span
                class="v mono"
                :class="selectedCell.level === 'a' || selectedCell.level === 'r' ? 'a-text' : ''"
                >{{ fmt(selectedCell.ir, 2) }} Ω</span
              >
            </div>
          </div>
        </div>
      </Panel>

      <!-- ============ 3.5.3 内阻分布图 ============ -->
      <Panel title="内阻分布">
        <template #extra>
          <span class="pill b">{{ tl('分组箱线 / 散点') }}</span>
        </template>
        <TrendChart :option="irDistOption" :height="260" :loading="loading" />
        <p class="arch-desc muted" style="margin-top: 8px">
          {{
            tl(
              '内阻分布反映单体老化一致性: 偏离组均值越大、绝对值越高, 越可能进入预警/告警。橙色线为各组的初始基准内阻, 红色虚线为告警阈值上限。',
            )
          }}
        </p>
      </Panel>

      <!-- ============ 3.5.5 失效预警面板 ============ -->
      <Panel v-if="failAlerts.length" title="失效预警">
        <template #extra>
          <span class="pill a pulse">{{ failAlerts.length }} {{ tl('项') }}</span>
        </template>
        <div class="alert-list">
          <div class="alert-row" v-for="(a, i) in failAlerts" :key="i" :class="'lv-' + a.lv">
            <span class="a-lv" :class="'lv-' + a.lv">{{ a.lvLabel }}</span>
            <span class="a-target">{{ a.target }}</span>
            <span class="a-item">{{ a.item }}</span>
            <span class="a-val mono">{{ a.value }}</span>
            <span class="a-adv">{{ a.advice }}</span>
          </div>
        </div>
      </Panel>

      <!-- ============ 3.5.5b 单体告警明细 ============ -->
      <Panel class="scroll-x" v-if="s.cellAlarms?.length" title="单体告警明细">
        <template #extra>
          <span class="pill a">{{ s.cellAlarms.length }} {{ tl('条') }}</span>
        </template>
        <table>
          <thead>
            <tr>
              <th>{{ tl('电池组') }}</th>
              <th>{{ tl('单体') }}</th>
              <th>{{ tl('告警项') }}</th>
              <th>{{ tl('级别') }}</th>
              <th>{{ tl('时间') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(a, i) in s.cellAlarms" :key="i">
              <td class="d-name">{{ a.g }}</td>
              <td class="mono">{{ a.cell }}</td>
              <td class="muted">{{ a.item }}</td>
              <td>
                <span class="tag a">{{ a.lv }}</span>
              </td>
              <td class="mono muted">{{ a.ts }}</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ============ 3.5.6 历史数据查询 ============ -->
      <Panel title="历史数据查询">
        <template #extra>
          <div class="hist-switch">
            <button
              v-for="h in histRanges"
              :key="h.key"
              class="sw-btn"
              :class="{ active: histRange === h.key }"
              @click="histRange = h.key"
            >
              {{ h.label }}
            </button>
          </div>
        </template>
        <TrendChart :option="historyOption" :height="260" :loading="loading" />
        <div class="hist-stats" v-if="historyStats">
          <div class="hs">
            <span class="k">{{ tl('区间') }}</span
            ><span class="v">{{ historyStats.label }}</span>
          </div>
          <div class="hs">
            <span class="k">{{ tl('SOC 均') }}</span
            ><span class="v">{{ historyStats.socAvg }}%</span>
          </div>
          <div class="hs">
            <span class="k">{{ tl('SOC 最低') }}</span
            ><span class="v a-text">{{ historyStats.socMin }}%</span>
          </div>
          <div class="hs">
            <span class="k">{{ tl('最高温') }}</span
            ><span class="v">{{ historyStats.tMax }}°C</span>
          </div>
          <div class="hs">
            <span class="k">{{ tl('充放电循环') }}</span
            ><span class="v">{{ historyStats.cycles }}</span>
          </div>
        </div>
      </Panel>

      <!-- ============ 知识库 ============ -->
      <KnowledgePanels :knowledge="s.knowledge" />

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('电池监控') }} · {{ tl('单体级监测') }} | {{ tl('电池组') }} {{ groups.length }}
        {{ tl('组') }} · {{ tl('单体') }} {{ totalCells }} {{ tl('节') }} · {{ tl('平均SOC') }}
        {{ avgSoc }}% · {{ tl('后备') }} {{ backupMin }}min · {{ tl('告警单体') }}
        {{ cellAlarmCount }} {{ tl('节') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmt } from '@/utils/format'
import { ProgressGauge, TrendChart } from '@/components/monitor'
import { KpiCard, StatusBadge, AlarmBadge } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import KnowledgePanels from '@/components/KnowledgePanels.vue'
import type { EChartsOption, MarkLineComponentOption } from 'echarts'
import {
  getPowerBatteryDetailed,
  type BatterySummary,
  type BatteryGroupView,
  type BatteryCellView,
} from '@/api/power'
const { t: tl } = useI18n()

const s = ref<BatterySummary | null>(null)
const error = ref('')
const loading = ref(false)

const groups = computed(() => s.value?.groups ?? [])

// 选中态
const selectedGroupObj = ref<BatteryGroupView | null>(null)
const selectedGroupForChart = computed(() => selectedGroupObj.value ?? groups.value[0] ?? null)
const selectedCell = ref<BatteryCellView | null>(null)

// 单体图切换指标
const cellMetrics = [
  { key: 'u', label: '电压' },
  { key: 'ir', label: '内阻' },
  { key: 't', label: '温度' },
] as const
const cellMetric = ref<'u' | 'ir' | 't'>('u')

// 历史区间
const histRanges = [
  { key: '24h', label: '24h', n: 24, label2: 'h' },
  { key: '7d', label: '7天', n: 7, label2: 'd' },
  { key: '30d', label: '30天', n: 30, label2: 'd' },
] as const
const histRange = ref<'24h' | '7d' | '30d'>('24h')

// ---------- 统计 ----------
const sysVoltage = computed(() => round(sum(groups.value.map((g) => g.u)), 1))
const sysCurrent = computed(() => round(sum(groups.value.map((g) => g.i)), 1))
const avgSoc = computed(() => round(avg(groups.value.map((g) => g.soc)), 1))
const avgSoh = computed(() => round(avg(groups.value.map((g) => sohOf(g))), 1))
const socColor = computed(() =>
  avgSoc.value < 80
    ? 'linear-gradient(90deg,#f59e0b,#ef4444)'
    : 'linear-gradient(90deg,#22e3ff,#3b82f6)',
)
const sohColor = computed(() =>
  avgSoh.value < 90
    ? 'linear-gradient(90deg,#f59e0b,#ef4444)'
    : 'linear-gradient(90deg,#22e3ff,#3b82f6)',
)
const backupMin = computed(() => s.value?.backupMin ?? 0)
const totalCells = computed(() => groups.value.reduce((sum, g) => sum + (g.cells?.length ?? 0), 0))
const cellAlarmCount = computed(() =>
  groups.value.reduce(
    (sum, g) => sum + (g.cells ?? []).filter((c) => c.level === 'a' || c.level === 'r').length,
    0,
  ),
)
const worstSohGroup = computed(() => round(Math.min(...groups.value.map((g) => sohOf(g)), 100), 1))
const worstGroupName = computed(() => {
  let worst: BatteryGroupView | null = null
  for (const g of groups.value) if (!worst || sohOf(g) < sohOf(worst)) worst = g
  return worst?.id ?? ''
})

// SOH 从内阻结论推导: 正常=98 预警=92 告警=85
function sohOf(g: BatteryGroupView): number {
  if (g.ir === '告警') return 85
  if (g.ir === '预警') return 92
  return 98
}

// ---------- 选型辅助 ----------
function selectGroup(g: BatteryGroupView) {
  selectedGroupObj.value = g
}
function selectCell(c: BatteryCellView) {
  selectedCell.value = c
}

function groupAlarmCount(g: BatteryGroupView): number {
  return (g.cells ?? []).filter((c) => c.level === 'a' || c.level === 'r').length
}

function groupStatusClass(g: BatteryGroupView): string {
  if (groupAlarmCount(g) > 0) return 'node-fault'
  if (g.soc < 80) return 'node-warn'
  return 'node-ok'
}
function groupFill(g: BatteryGroupView): string {
  if (groupAlarmCount(g) > 0) return 'rgba(255,77,94,0.10)'
  if (g.soc < 80) return 'rgba(255,176,32,0.10)'
  return 'rgba(34,227,255,0.08)'
}
function groupStroke(g: BatteryGroupView): string {
  if (groupAlarmCount(g) > 0) return 'var(--red)'
  if (g.soc < 80) return 'var(--amber)'
  return 'var(--cyan)'
}
function socBarColor(soc: number): string {
  if (soc < 60) return '#ef4444'
  if (soc < 80) return '#f59e0b'
  return '#22e3ff'
}
function socTextColor(soc: number): string {
  if (soc < 60) return 'var(--red)'
  if (soc < 80) return 'var(--amber)'
  return 'var(--cyan)'
}

// ---------- 单体色块 ----------
function cellCls(level: string): string {
  if (level === 'r') return 'cell-r'
  if (level === 'a') return 'cell-a'
  return 'cell-g'
}
function cellLevelLabel(level: string): string {
  if (level === 'r') return tl('告警')
  if (level === 'a') return tl('预警')
  return tl('正常')
}
function sigLevelTagCls(level: string): string {
  if (level === 'g') return 'g'
  if (level === 'a') return 'a'
  if (level === 'r') return 'r'
  return 'b'
}
function cellVClass(c: BatteryCellView): string {
  // 12V 单体: <10.8 / >13.8 异常; 2V 单体: <1.8 / >2.4 异常
  const hi = c.u < 5 ? 2.4 : 13.8
  const lo = c.u < 5 ? 1.8 : 10.8
  if (c.u > hi || c.u < lo) return 'a-text'
  return 'g-text'
}

// ---------- 3.5.2 单体柱状图 ----------
const cellChartOption = computed<EChartsOption>(() => {
  const g = selectedGroupForChart.value
  if (!g || !g.cells?.length) return {}
  const cells = g.cells
  const xData = cells.map((c) => c.no)
  let seriesData: number[] = []
  let unit = 'V'
  let color = '#22e3ff'
  let markLine: MarkLineComponentOption | undefined = undefined
  if (cellMetric.value === 'u') {
    seriesData = cells.map((c) => round(c.u, 3))
    unit = 'V'
    color = '#22e3ff'
    // 标注最高/最低
    const vals = seriesData
    const hi = Math.max(...vals),
      lo = Math.min(...vals)
    markLine = {
      symbol: 'none',
      data: [
        {
          yAxis: hi,
          name: tl('最高'),
          lineStyle: { color: '#ef4444', type: 'dashed' },
          label: { formatter: tl('最高') },
        },
        {
          yAxis: lo,
          name: tl('最低'),
          lineStyle: { color: '#f59e0b', type: 'dashed' },
          label: { formatter: tl('最低') },
        },
      ],
    }
  } else if (cellMetric.value === 'ir') {
    seriesData = cells.map((c) => round(c.ir, 2))
    unit = 'Ω'
    color = '#a78bfa'
  } else {
    seriesData = cells.map((c) => round(c.t, 1))
    unit = '°C'
    color = '#34d399'
    markLine = {
      symbol: 'none',
      data: [
        {
          yAxis: 35,
          name: tl('告警'),
          lineStyle: { color: '#ef4444', type: 'dashed' },
          label: { formatter: tl('告警') + '35' },
        },
      ],
    }
  }
  return {
    grid: { left: 48, right: 16, top: 28, bottom: 40 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: '#8a94a6', fontSize: 10, interval: Math.ceil(cells.length / 20) },
      axisLine: { lineStyle: { color: '#2a3342' } },
    },
    yAxis: {
      type: 'value',
      name: unit,
      nameTextStyle: { color: '#8a94a6' },
      axisLabel: { color: '#8a94a6' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    series: [
      {
        type: 'bar',
        data: seriesData.map((v, idx) => ({
          value: v,
          itemStyle: {
            color:
              cellCls(cells[idx].level) === 'cell-r'
                ? '#ef4444'
                : cellCls(cells[idx].level) === 'cell-a'
                  ? '#f59e0b'
                  : color,
            borderRadius: [2, 2, 0, 0],
          },
        })),
        barWidth: '60%',
        markLine,
      },
    ],
  }
})

// ---------- 3.5.3 内阻分布 (箱线 + 散点) ----------
const irDistOption = computed<EChartsOption>(() => {
  if (!groups.value.length) return {}
  const boxData: number[][] = []
  const scatterData: number[][] = []
  groups.value.forEach((g, gi) => {
    const irs = (g.cells ?? []).map((c) => c.ir)
    if (irs.length) {
      const sorted = [...irs].sort((a, b) => a - b)
      const q1 = sorted[Math.floor(sorted.length * 0.25)]
      const med = sorted[Math.floor(sorted.length * 0.5)]
      const q3 = sorted[Math.floor(sorted.length * 0.75)]
      boxData.push([gi, q1, med, q3, sorted[sorted.length - 1]])
    }
    irs.forEach((v) => scatterData.push([gi, v]))
  })
  return {
    grid: { left: 48, right: 16, top: 30, bottom: 40 },
    tooltip: { trigger: 'item' },
    xAxis: {
      type: 'category',
      data: groups.value.map((g) => g.id),
      axisLabel: { color: '#8a94a6' },
      axisLine: { lineStyle: { color: '#2a3342' } },
    },
    yAxis: {
      type: 'value',
      name: 'Ω',
      nameTextStyle: { color: '#8a94a6' },
      axisLabel: { color: '#8a94a6' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    series: [
      {
        name: tl('内阻区间'),
        type: 'boxplot',
        data: boxData,
        itemStyle: { color: 'rgba(167,139,250,0.25)', borderColor: '#a78bfa' },
      },
      {
        name: tl('单体散点'),
        type: 'scatter',
        data: scatterData,
        symbolSize: 5,
        itemStyle: { color: '#22e3ff', opacity: 0.6 },
      },
    ],
  }
})

// ---------- 3.5.6 历史数据 (模拟趋势) ----------
const historyOption = computed<EChartsOption>(() => {
  const cfg = histRanges.find((h) => h.key === histRange.value)!
  const n = cfg.n
  const x: string[] = []
  const socArr: number[] = []
  const tempArr: number[] = []
  const baseSoc = avgSoc.value || 90
  const baseT = 28
  for (let i = 0; i < n; i++) {
    x.push(cfg.label2 === 'h' ? `${i}:00` : `D${i + 1}`)
    const wave = Math.sin(i / 3) * 8 + (Math.random() - 0.5) * 3
    const soc = clamp(round(baseSoc + wave, 1), 30, 100)
    socArr.push(soc)
    tempArr.push(round(baseT + Math.sin(i / 4) * 4 + (Math.random() - 0.5) * 2, 1))
  }
  return {
    grid: { left: 48, right: 48, top: 36, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { data: [tl('SOC'), tl('温度')], textStyle: { color: '#8a94a6' }, top: 4 },
    xAxis: {
      type: 'category',
      data: x,
      axisLabel: { color: '#8a94a6', fontSize: 10, interval: Math.ceil(n / 12) },
      axisLine: { lineStyle: { color: '#2a3342' } },
    },
    yAxis: [
      {
        type: 'value',
        name: 'SOC%',
        min: 0,
        max: 100,
        nameTextStyle: { color: '#8a94a6' },
        axisLabel: { color: '#8a94a6' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      },
      {
        type: 'value',
        name: '°C',
        nameTextStyle: { color: '#8a94a6' },
        axisLabel: { color: '#8a94a6' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: tl('SOC'),
        type: 'line',
        smooth: true,
        data: socArr,
        itemStyle: { color: '#22e3ff' },
        areaStyle: { color: 'rgba(34,227,255,0.12)' },
        yAxisIndex: 0,
      },
      {
        name: tl('温度'),
        type: 'line',
        smooth: true,
        data: tempArr,
        itemStyle: { color: '#34d399' },
        lineStyle: { width: 1.5 },
        yAxisIndex: 1,
      },
    ],
  }
})

const historyStats = computed(() => {
  const cfg = histRanges.find((h) => h.key === histRange.value)!
  const n = cfg.n
  const socVals: number[] = []
  let tMax = 0
  for (let i = 0; i < n; i++) {
    const wave = Math.sin(i / 3) * 8 + (Math.random() - 0.5) * 3
    socVals.push(clamp(round((avgSoc.value || 90) + wave, 1), 30, 100))
    tMax = Math.max(tMax, 28 + Math.sin(i / 4) * 4 + 2)
  }
  return {
    label: cfg.label,
    socAvg: round(avg(socVals), 1),
    socMin: round(Math.min(...socVals), 1),
    tMax: round(tMax, 1),
    cycles: cfg.key === '24h' ? 1 : cfg.key === '7d' ? 3 : 12,
  }
})

// ---------- 3.5.5 失效预警派生 ----------
interface FailAlert {
  lv: 'critical' | 'warning'
  lvLabel: string
  target: string
  item: string
  value: string
  advice: string
}
const failAlerts = computed<FailAlert[]>(() => {
  const out: FailAlert[] = []
  for (const g of groups.value) {
    if (groupAlarmCount(g) > 0) {
      out.push({
        lv: 'critical',
        lvLabel: tl('告警单体'),
        target: `${g.id}`,
        item: tl('单体电压/内阻超标'),
        value: `${groupAlarmCount(g)} ${tl('节')}`,
        advice: tl('立即排查并隔离故障单体, 安排更换'),
      })
    }
    if (g.soc < 60) {
      out.push({
        lv: 'critical',
        lvLabel: tl('SOC 过低'),
        target: g.id,
        item: tl('荷电状态'),
        value: `${g.soc}%`,
        advice: tl('启动充电或切换备用组, 避免深度放电'),
      })
    } else if (g.soc < 80) {
      out.push({
        lv: 'warning',
        lvLabel: tl('SOC 偏低'),
        target: g.id,
        item: tl('荷电状态'),
        value: `${g.soc}%`,
        advice: tl('安排充电, 关注放电负荷'),
      })
    }
    if (g.maxT > 35) {
      out.push({
        lv: 'critical',
        lvLabel: tl('温度过高'),
        target: g.id,
        item: tl('最高单体温度'),
        value: `${g.maxT}°C`,
        advice: tl('检查机房空调与通风, 降载运行'),
      })
    }
    if (g.ir !== '正常') {
      out.push({
        lv: g.ir === '告警' ? 'critical' : 'warning',
        lvLabel: tl('内阻异常'),
        target: g.id,
        item: tl('内阻结论'),
        value: `${g.ir}`,
        advice: tl('纳入核容计划, 评估整组更换'),
      })
    }
  }
  if (backupMin.value < 10) {
    out.push({
      lv: 'critical',
      lvLabel: tl('后备不足'),
      target: tl('系统'),
      item: tl('后备时间'),
      value: `${backupMin.value}min`,
      advice: tl('立即恢复充电, 核实柴发联动'),
    })
  }
  return out
})

// ---------- 工具 ----------
function sum(arr: number[]): number {
  return arr.reduce((a, b) => a + (b || 0), 0)
}
function avg(arr: number[]): number {
  const v = arr.filter((x) => Number.isFinite(x))
  return v.length ? sum(v) / v.length : 0
}
function round(v: number, dp = 1): number {
  return Number(Number(v).toFixed(dp))
}
function clamp(v: number, lo: number, hi: number): number {
  return Math.min(Math.max(v, lo), hi)
}

// ---------- 数据加载 + 30s 刷新 ----------
let timer: number | undefined
async function load() {
  loading.value = true
  error.value = ''
  try {
    s.value = await getPowerBatteryDetailed()
    if (s.value?.groups?.length && !selectedGroupObj.value) {
      selectedGroupObj.value = s.value.groups[0]
    }
  } catch (e: unknown) {
    error.value = (e as ErrorLike)?.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.bat-view {
  padding: 2px;
}

/* head */
.view-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.view-head h1 {
  font-size: 20px;
  margin: 0;
  color: var(--txt-strong);
}
.view-head .sub {
  font-size: 12px;
  color: var(--txt2);
}
.head-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.refresh-hint {
  font-size: 11px;
  color: var(--txt2);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.refresh-hint.err {
  color: var(--red);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.d-green {
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
}
.d-red {
  background: var(--red);
  box-shadow: 0 0 6px var(--red);
}
.btn-refresh {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--td-line);
  background: var(--bg2);
  color: var(--txt);
  cursor: pointer;
}
.btn-refresh:hover:not(:disabled) {
  border-color: var(--cyan);
  color: var(--cyan);
}
.btn-refresh:disabled {
  opacity: 0.5;
  cursor: default;
}

.center-box {
  padding: 40px;
  text-align: center;
}
.muted.err {
  color: var(--red);
}

/* 卡片堆叠间距（原 .card margin-bottom 在统一到 .moni-card 后补回） */
.moni-card {
  margin-bottom: 14px;
}
.moni-card:last-child {
  margin-bottom: 0;
}

/* section title */

.section-title .bar {
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: var(--cyan);
}

/* kpi row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

/* SOC/SOH gauge card */
.socsoh-card .socsoh-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.gauge-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.gauge-sub {
  font-size: 10px;
  color: var(--txt3);
}

/* topo */
.topo-wrap {
  width: 100%;
  overflow-x: auto;
}
.topo-svg {
  width: 100%;
  min-width: 760px;
  height: auto;
}
.topo-node {
  cursor: pointer;
  transition: filter 0.15s;
}
.topo-node:hover {
  filter: brightness(1.15);
}
.topo-node.node-fault {
  animation: nodeBlink 1.4s infinite;
}
@keyframes nodeBlink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
.topo-bus-label {
  fill: var(--txt2);
  font-size: 12px;
  font-weight: 600;
}
.topo-g-id {
  fill: var(--txt-strong);
  font-size: 13px;
  font-weight: 700;
}
.topo-g-type {
  fill: var(--txt2);
  font-size: 9px;
}
.topo-g-metric {
  fill: var(--txt);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}
.topo-g-soc {
  font-size: 18px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.topo-g-state {
  fill: var(--txt2);
  font-size: 9px;
}
.topo-badge {
  fill: #fff;
  font-size: 11px;
  font-weight: 700;
}
.topo-detail {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding: 8px 12px;
  border: 1px solid var(--cyan);
  border-radius: 8px;
  background: rgba(34, 227, 255, 0.06);
}
.topo-detail .kv {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.topo-detail .kv .k {
  font-size: 10px;
  color: var(--txt3);
}
.topo-detail .kv .v {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.topo-detail .close-btn {
  margin-left: auto;
}

/* table */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
th {
  text-align: left;
  color: var(--txt3);
  font-weight: 600;
  font-size: 10.5px;
  letter-spacing: 0.5px;
  padding: 7px 8px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--td-line);
  color: var(--txt);
  white-space: nowrap;
}
tbody tr:hover {
  background: var(--row-hover);
}
tbody .row-warn {
  background: rgba(250, 173, 20, 0.06);
}
.d-name {
  font-weight: 500;
  color: var(--txt);
}
.mono {
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', Consolas, monospace;
}
.g-text {
  color: var(--green);
}
.a-text {
  color: var(--amber);
}
.r-text {
  color: var(--red);
}

/* tag */

.tag.g {
  color: var(--green);
  border-color: rgba(43, 212, 122, 0.4);
  background: rgba(43, 212, 122, 0.08);
}
.tag.a {
  color: var(--amber);
  border-color: rgba(255, 176, 32, 0.4);
  background: rgba(255, 176, 32, 0.08);
}
.tag.r {
  color: var(--red);
  border-color: rgba(255, 77, 94, 0.4);
  background: rgba(255, 77, 94, 0.09);
}
.tag.b {
  color: var(--blue);
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.08);
}

/* cell grid + switch */
.cell-switch,
.hist-switch {
  display: flex;
  gap: 4px;
}
.sw-btn {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--td-line);
  background: var(--bg2);
  color: var(--txt2);
  cursor: pointer;
}
.sw-btn.active {
  border-color: var(--cyan);
  color: var(--cyan);
  background: rgba(34, 227, 255, 0.08);
}
.cell-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(54px, 1fr));
  gap: 4px;
  margin: 4px 0 12px;
}
.cell-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 2px;
  border-radius: 4px;
  cursor: pointer;
  transition:
    transform 0.12s,
    box-shadow 0.12s;
  border: 1px solid transparent;
}
.cell-box:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
.cell-no {
  font-size: 9px;
  opacity: 0.85;
}
.cell-u {
  font-size: 10px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.cell-g {
  background: rgba(43, 212, 122, 0.18);
  color: var(--green);
  border-color: rgba(43, 212, 122, 0.3);
}
.cell-a {
  background: rgba(255, 176, 32, 0.22);
  color: var(--amber);
  border-color: rgba(255, 176, 32, 0.45);
}
.cell-r {
  background: rgba(255, 77, 94, 0.22);
  color: var(--red);
  border-color: rgba(255, 77, 94, 0.5);
}
.cell-chart {
  margin-top: 4px;
}

/* cell detail */
.cell-detail {
  margin-top: 10px;
  border: 1px solid var(--cyan);
  border-radius: 8px;
  padding: 10px 14px;
  background: rgba(34, 227, 255, 0.06);
}
.cell-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.cell-detail-head .tag {
  margin-left: auto;
}
.close-btn {
  margin-left: 12px;
  background: transparent;
  border: 1px solid var(--td-line);
  color: var(--txt2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 2px 7px;
}
.close-btn:hover {
  border-color: var(--red);
  color: var(--red);
}
.cell-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.cd-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cd-item .k {
  font-size: 11px;
  color: var(--txt3);
}
.cd-item .v {
  font-size: 15px;
  font-weight: 700;
}

/* fail alerts */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-row {
  display: grid;
  grid-template-columns: 70px 90px 1fr 90px 1.4fr;
  gap: 10px;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  border: 1px solid var(--td-line);
  background: var(--bg2);
}
.alert-row.lv-critical {
  border-color: rgba(255, 77, 94, 0.4);
  background: rgba(255, 77, 94, 0.06);
}
.alert-row.lv-warning {
  border-color: rgba(255, 176, 32, 0.4);
  background: rgba(255, 176, 32, 0.05);
}
.a-lv {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-align: center;
}
.a-lv.lv-critical {
  color: var(--red);
  background: rgba(255, 77, 94, 0.15);
}
.a-lv.lv-warning {
  color: var(--amber);
  background: rgba(255, 176, 32, 0.15);
}
.a-target {
  font-weight: 600;
  color: var(--txt);
}
.a-item {
  color: var(--txt2);
}
.a-val {
  font-weight: 700;
}
.a-adv {
  color: var(--txt3);
  font-size: 11px;
}

/* history stats */
.hist-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 10px;
}
.hs {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.hs .k {
  font-size: 10px;
  color: var(--txt3);
}
.hs .v {
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.footer-note {
  text-align: center;
  margin-top: 16px;
  font-size: 11px;
}

.scroll-x {
  overflow-x: auto;
}

@media (max-width: 980px) {
  .kpi-row,
  .socsoh-card .socsoh-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
