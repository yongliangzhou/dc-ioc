<template>
  <div class="health-report">
    <div class="hr-head">
      <div>
        <h1>{{ t.title }}</h1>
        <span class="sub">{{ t.sub }}</span>
      </div>
      <div class="hr-actions">
        <select v-model="month" class="inp hr-month">
          <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
        </select>
        <button class="btn btn-primary" :disabled="loading" @click="generate">
          {{ loading ? t.loading : t.generate }}
        </button>
        <button v-if="report" class="btn btn-ghost" @click="exportPdf">{{ t.exportPdf }}</button>
      </div>
    </div>

    <MockDataBanner :level="mockLevel" :reason="mockReason" />

    <!-- 部分数据源失败显式露出 (不再静默吞掉), 可一键重试失败项 -->
    <ErrorBanner
      v-if="anyHealthError"
      :count="healthErrorCount"
      :labels="failedSourceLabels"
      @retry="health.reloadFailed"
    />

    <div v-if="!report" class="empty-tip">{{ t.emptyHint }}</div>

    <div v-else class="hr-stack">
      <!-- 总分 + 雷达 -->
      <Panel :title="t.overview" class="hr-overview">
        <div class="hr-overview-body">
          <div class="score-ring">
            <svg viewBox="0 0 36 36" class="ring-svg">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--line)" stroke-width="3" />
              <circle
                cx="18"
                cy="18"
                r="15.9"
                fill="none"
                :stroke="scoreColor(report.score)"
                stroke-width="3"
                :stroke-dasharray="`${report.score} 100`"
                stroke-linecap="round"
              />
            </svg>
            <div class="ring-center">
              <span class="ring-score" :style="{ color: scoreColor(report.score) }">{{
                report.score
              }}</span>
              <span class="ring-label">{{ t.score }}</span>
            </div>
          </div>

          <!-- 八维雷达图 (SVG 自绘, 轴数随域数量动态计算) -->
          <div class="radar-box">
            <div class="radar-title">{{ t.radarTitle }}</div>
            <svg
              viewBox="0 0 200 200"
              class="radar-svg"
              role="img"
              :aria-label="`${t.radarTitle} · ${t.radarHint}`"
            >
              <g transform="translate(100,100)">
                <polygon
                  v-for="ring in radarRings"
                  :key="ring"
                  :points="radarPoints(ring)"
                  fill="none"
                  stroke="var(--line)"
                  stroke-width="1"
                />
                <!-- 刻度数值：沿正上方轴标出 25/50/75/100，否则同心环无量化含义 -->
                <text
                  v-for="ring in radarRings"
                  :key="'tk' + ring"
                  x="3"
                  :y="axisY(0, ring) + 2"
                  font-size="6"
                  fill="var(--txt3, #8595ad)"
                >
                  {{ ring * 100 }}
                </text>
                <line
                  v-for="(d, i) in report.domains"
                  :key="'ax' + i"
                  :x1="0"
                  :y1="0"
                  :x2="axisX(i)"
                  :y2="axisY(i)"
                  stroke="var(--line)"
                  stroke-width="1"
                />
                <polygon
                  :points="radarDataPoints"
                  fill="rgba(37,99,235,0.18)"
                  stroke="var(--blue)"
                  stroke-width="2"
                />
                <circle
                  v-for="(d, i) in report.domains"
                  :key="'pt' + i"
                  :cx="axisX(i, d.score / 100)"
                  :cy="axisY(i, d.score / 100)"
                  r="2.5"
                  fill="var(--blue)"
                >
                  <title>{{ tipText(d) }}</title>
                </circle>
                <text
                  v-for="(d, i) in report.domains"
                  :key="'lb' + i"
                  :x="axisX(i, 1.18)"
                  :y="axisY(i, 1.18)"
                  font-size="8"
                  fill="var(--txt2)"
                  text-anchor="middle"
                  dominant-baseline="middle"
                >
                  {{ d.name }}
                </text>
              </g>
            </svg>
            <div class="radar-hint">{{ t.radarHint }}</div>
          </div>

          <div class="hr-summary">
            <div class="hr-grade">
              {{ t.grade }}:
              <span :style="{ color: scoreColor(report.score) }">{{ report.grade }}</span>
            </div>
            <p class="hr-summary-text">{{ report.summary }}</p>
            <div class="hr-meta">{{ t.genAt }}: {{ report.genAt }}</div>
            <div class="hr-meta sm">{{ t.weightHint }}</div>
            <div class="src-tags">
              <span
                v-for="src in report.sources"
                :key="src"
                class="tag"
                :class="src === 'realtime' ? 'g' : 'a'"
                >{{ t.sourceTag }}: {{ src === 'realtime' ? t.srcRealtime : t.srcLocal }}</span
              >
            </div>
          </div>
        </div>
      </Panel>

      <!-- 域评分（点击钻取） -->
      <Panel :title="t.domainScores" class="hr-domains-panel">
        <div class="grid cols-auto hr-domains">
          <div
            v-for="d in report.domains"
            :key="d.key"
            class="domain-card"
            role="button"
            tabindex="0"
            :title="t.clickDetail"
            @click="openDetail(d)"
            @keydown.enter.prevent="openDetail(d)"
          >
            <div class="domain-top">
              <span class="domain-name">{{ d.name }}</span>
              <span class="domain-score" :style="{ color: scoreColor(d.score) }">{{
                d.score
              }}</span>
            </div>
            <div
              class="domain-bar"
              role="progressbar"
              :aria-valuenow="d.score"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="d.name"
            >
              <i :style="{ width: d.score + '%', background: scoreColor(d.score) }"></i>
            </div>
            <p class="domain-note">{{ d.note }}</p>
            <div class="domain-more">{{ t.clickDetail }} ›</div>
          </div>
        </div>
      </Panel>

      <!-- 关键发现与建议 -->
      <div class="grid cols-2">
        <Panel :title="t.findings">
          <ul class="hr-list">
            <li v-for="(f, i) in report.findings" :key="i">{{ f }}</li>
          </ul>
        </Panel>
        <Panel :title="t.suggestions">
          <ul class="hr-list">
            <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
          </ul>
        </Panel>
      </div>
    </div>

    <!-- 评分构成钻取 -->
    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="modal-box">
        <div class="modal-head">
          <h3>{{ t.detailTitle }} · {{ detail.name }}</h3>
          <button
            class="modal-close"
            :title="tc('tooltipClose')"
            :aria-label="tc('tooltipClose')"
            @click="detail = null"
          >
            ✕
          </button>
        </div>
        <div class="modal-score" :style="{ color: scoreColor(detail.score) }">
          {{ detail.score }}<span class="modal-score-unit">{{ t.score }}</span>
        </div>
        <p class="modal-note">{{ detail.note }}</p>
        <ul class="modal-list">
          <li v-for="(line, i) in detail.breakdown" :key="i">· {{ line }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getActiveAlarms,
  getExternalDevices,
  getTickets,
  getDrills,
  getDrillRecords,
  getCabinets,
  listEquipment,
  getTenantStats,
} from '@/api'
import { useAsyncPageAll, useMockFlag } from '@/composables/useAsyncPage'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import Panel from '@/components/common/Panel.vue'
const { level: mockLevel, reason: mockReason, markPartial, markFull } = useMockFlag()

const { t: raw, tm } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (tm('healthReport') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})
/** 通用动作文案（common 命名空间），用于图标按钮的 title / aria-label */
const tc = (k: string) => (raw('common.' + k) as string) || ''

interface Domain {
  key: string
  name: string
  score: number
  note: string
  breakdown?: string[]
}
interface Report {
  month: string
  score: number
  grade: string
  summary: string
  genAt: string
  domains: Domain[]
  findings: string[]
  suggestions: string[]
  sources: string[]
}

const months = ref<string[]>([])
const month = ref('')
const report = ref<Report | null>(null)
const loading = ref(false)
const detail = ref<Domain | null>(null)

// 8 路并发数据源：单个失败不再静默吞掉，失败项由 ErrorBanner 显式露出且可一键重试
const SOURCE_LABELS: Record<string, string> = {
  alarms: '活跃告警',
  devices: '外部设备',
  tickets: '工单',
  drills: '演练计划',
  drillRecs: '演练记录',
  cabinets: '机柜台账',
  equip: '设备台账',
  tenantStats: '租户统计',
}
const health = useAsyncPageAll(
  {
    alarms: () => getActiveAlarms(),
    devices: () => getExternalDevices({ limit: 200 }),
    tickets: () => getTickets({}),
    drills: () => getDrills(),
    drillRecs: () => getDrillRecords(),
    cabinets: () => getCabinets({ size: 200 }),
    equip: () => listEquipment({ size: 200 }),
    tenantStats: () => getTenantStats(),
  },
  { autoLoad: false },
)
const anyHealthError = computed(() => health.anyError.value)
const healthErrorCount = computed(() => health.errorCount.value)
const failedSourceLabels = computed(() => health.failedKeys.value.map((k) => SOURCE_LABELS[k] ?? k))

function initMonths() {
  const now = new Date()
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    months.value.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  month.value = months.value[0]
}

function readLs(key: string, fallback: any) {
  try {
    return JSON.parse(localStorage.getItem(key) || 'null') || fallback
  } catch {
    return fallback
  }
}

// 安全取字符串
function s(v: any): string {
  return typeof v === 'string' ? v : ''
}
function clamp(v: number) {
  return Math.max(0, Math.min(100, Math.round(v)))
}
function pct(n: number, d: number) {
  return d ? Math.round((n / d) * 100) : 0
}

function scoreColor(v: number) {
  return v >= 85 ? '#16a34a' : v >= 70 ? '#2563eb' : v >= 60 ? '#d97706' : '#dc2626'
}

// 雷达图坐标 (轴数随域数量动态取, 当前 8 维; 不再写死 7 导致第 8 点与第一点重叠、多边形错位)
const AXIS_R = 80
/** 同心环刻度：图形与刻度标签共用同一数组，避免两处写死不一致 */
const radarRings = [0.25, 0.5, 0.75, 1]
function axisCount(): number {
  return report.value?.domains.length ?? 7
}
/** 雷达图数据点悬停文案：读出域名与具体分数 */
function tipText(d: Domain) {
  return String(t.scoreTooltip || '{name}: {score}')
    .replace('{name}', d.name)
    .replace('{score}', String(d.score))
}
function radarPoint(i: number, r: number) {
  const n = axisCount()
  const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n
  return { x: Math.cos(ang) * AXIS_R * r, y: Math.sin(ang) * AXIS_R * r }
}
function axisX(i: number, r = 1) {
  return radarPoint(i, r).x
}
function axisY(i: number, r = 1) {
  return radarPoint(i, r).y
}
function radarPoints(ring: number) {
  const n = axisCount()
  return Array.from({ length: n }, (_, i) => {
    const p = radarPoint(i, ring)
    return `${p.x},${p.y}`
  }).join(' ')
}
const radarDataPoints = computed(() =>
  (report.value?.domains ?? [])
    .map((d, i) => {
      const p = radarPoint(i, d.score / 100)
      return `${p.x},${p.y}`
    })
    .join(' '),
)

async function generate() {
  loading.value = true
  const sources = new Set<string>(['local'])
  try {
    // 并发拉取真实数据；单个失败由 useAsyncPageAll 记录到 failedKeys，不再被 .catch(() => null) 吞掉
    await health.reloadAll()
    const pages = health.pages as any
    const d = (k: string) => pages[k]?.data?.value ?? null
    const alarms = d('alarms')
    const devices = d('devices')
    const tickets = d('tickets')
    const drills = d('drills')
    const drillRecs = d('drillRecs')
    const cabinets = d('cabinets')
    const equip = d('equip')
    const tenantStats = d('tenantStats')
    if (alarms || devices || tickets || drills || drillRecs || cabinets || equip || tenantStats)
      sources.add('realtime')

    const hazards: any[] = readLs('w10_hazards', [])
    const suppliers: any[] = readLs('w9_suppliers', [])

    // 供配电：活跃告警 + 高危隐患
    const activeAlarms = alarms?.total ?? 0
    const hazHigh = hazards.filter((h: any) => h.level === 'high' && h.enabled).length
    const powerScore = clamp(92 - activeAlarms * 4 - hazHigh * 5)

    // 制冷：制冷类设备在线率
    const allDev: any[] = devices?.items ?? []
    const coolingDev = allDev.filter((d: any) =>
      /冷却|制冷|空调|chill|cool|crac|冷机/i.test(d.name || d.model || ''),
    )
    const coolingOff = coolingDev.filter(
      (d: any) => d.status === 'offline' || d.status === 'off',
    ).length
    const coolingRate = coolingDev.length
      ? pct(coolingDev.length - coolingOff, coolingDev.length)
      : 96
    const coolingScore = clamp(Math.round(coolingRate - coolingOff * 3))

    // 网络：外部设备在线率
    const netOff = allDev.filter((d: any) => d.status === 'offline' || d.status === 'off').length
    const netRate = allDev.length ? pct(allDev.length - netOff, allDev.length) : 98
    const networkScore = clamp(Math.round(netRate - netOff * 2))

    // 隐患治理
    const hazTotal = hazards.length || 20
    const hazScore = clamp(Math.max(40, 100 - hazHigh * 6))

    // 应急演练：优先用 stats 真实聚合（done/pass），否则用记录
    const drillStats = drills?.stats
    const drillPass =
      drillStats && drillStats.done
        ? drillStats.pass / drillStats.done
        : (() => {
            const recs: any[] = drillRecs?.records ?? []
            return recs.length
              ? recs.filter((d: any) => d.result === 'pass' || d.status === 'done').length /
                  recs.length
              : 0.85
          })()
    const drillScore = clamp(Math.round(55 + drillPass * 40))

    // 供应商
    const supScore = suppliers.length
      ? Math.round(
          suppliers.reduce((a: number, x: any) => a + (x.score || 0), 0) / suppliers.length,
        )
      : 82

    // 维修闭环：TicketCenter.stats.open 直接给未关闭数
    const repairOpen = tickets?.stats?.open ?? repairsOpenFromCache()
    const repairScore = clamp(Math.max(50, 100 - repairOpen * 8))

    // 容量与机房：基于租户统计的超限/预警数
    const overCount = tenantStats?.overCount ?? 0
    const warnCount = tenantStats?.warnCount ?? 0
    const occ = tenantStats
      ? Math.round(
          ((tenantStats.totalCabinets - warnCount) / Math.max(1, tenantStats.totalCabinets)) * 100,
        )
      : 75
    const capScore = clamp(Math.round(100 - overCount * 12 - warnCount * 4))

    const domains: Domain[] = [
      {
        key: 'power',
        name: s(t.dPower),
        score: powerScore,
        note: s(t.nPower).replace('{n}', String(hazHigh + activeAlarms)),
        breakdown: [
          s(t.fAlarmHigh).replace('{n}', String(activeAlarms)),
          `${t.dHazard}: ${hazHigh} high-risk`,
        ],
      },
      {
        key: 'cooling',
        name: s(t.dCooling),
        score: coolingScore,
        note: s(t.nCoolingReal)
          .replace('{r}', String(coolingRate))
          .replace('{n}', String(coolingOff)),
        breakdown: [`${coolingDev.length} cooling devices`, `${coolingOff} offline`],
      },
      {
        key: 'network',
        name: s(t.dNetwork),
        score: networkScore,
        note: s(t.nNetworkReal).replace('{r}', String(netRate)).replace('{n}', String(netOff)),
        breakdown: [`${allDev.length} devices`, `${netOff} offline`],
      },
      {
        key: 'hazard',
        name: s(t.dHazard),
        score: hazScore,
        note: s(t.nHazard).replace('{n}', String(hazHigh)),
        breakdown: [`${hazTotal} rules`, `${hazHigh} high-risk enabled`],
      },
      {
        key: 'drill',
        name: s(t.dDrill),
        score: drillScore,
        note: s(t.nDrill).replace('{r}', String(Math.round(drillPass * 100))),
        breakdown: [
          `${drills?.plans?.length ?? drillRecs?.records?.length ?? 0} drills`,
          `pass ${Math.round(drillPass * 100)}%`,
        ],
      },
      {
        key: 'supplier',
        name: s(t.dSupplier),
        score: clamp(supScore),
        note: s(t.nSupplier),
        breakdown: [`${suppliers.length} suppliers`, `avg ${supScore}`],
      },
      {
        key: 'repair',
        name: s(t.dRepair),
        score: repairScore,
        note: s(t.nRepair).replace('{n}', String(repairOpen)),
        breakdown: [`${repairOpen} open tickets`],
      },
      {
        key: 'capacity',
        name: s(t.dCapacity),
        score: capScore,
        note: s(t.nCapacity).replace('{r}', String(occ)),
        breakdown: [
          `occupancy ${occ}%`,
          `cabinets ${tenantStats?.totalCabinets ?? '?'}`,
          `over ${overCount} / warn ${warnCount}`,
        ],
      },
    ]

    // 加权总分
    const W: Record<string, number> = {
      power: 0.18,
      cooling: 0.18,
      network: 0.18,
      hazard: 0.09,
      drill: 0.09,
      supplier: 0.09,
      repair: 0.09,
      capacity: 0.1,
    }
    const score =
      Math.round(domains.reduce((a, d) => a + d.score * (W[d.key] ?? 0.1), 0) * 100) / 100

    const grade =
      score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : score >= 60 ? 'D' : 'E'

    const findings: string[] = []
    const suggestions: string[] = []
    if (hazHigh >= 4) {
      findings.push(s(t.fHighHazard).replace('{n}', String(hazHigh)))
      suggestions.push(s(t.sHighHazard))
    }
    if (activeAlarms >= 5) {
      findings.push(s(t.fAlarmHigh).replace('{n}', String(activeAlarms)))
      suggestions.push(s(t.sAlarm))
    }
    if (netRate < 95) {
      findings.push(s(t.fNetLow).replace('{n}', String(netOff)))
      suggestions.push(s(t.sNet))
    }
    if (coolingRate < 95) {
      findings.push(s(t.fCoolLow).replace('{n}', String(coolingOff)))
      suggestions.push(s(t.sCool))
    }
    if (drillPass < 0.8) {
      findings.push(s(t.fDrillLow))
      suggestions.push(s(t.sDrill))
    }
    if (repairOpen >= 3) {
      findings.push(s(t.fRepairOpen).replace('{n}', String(repairOpen)))
      suggestions.push(s(t.sRepair))
    }
    if (occ > 90) {
      findings.push(s(t.fCapHigh))
      suggestions.push(s(t.sCapacity))
    }
    if (suppliers.filter((x: any) => (x.score || 0) < 70).length) {
      findings.push(s(t.fSupLow))
      suggestions.push(s(t.sSup))
    }
    findings.push(s(t.fSummary).replace('{m}', month.value))
    suggestions.push(s(t.sReview))

    report.value = {
      month: month.value,
      score: Math.round(score),
      grade,
      summary:
        grade === 'A' || grade === 'B'
          ? s(t.sGood).replace('{g}', grade)
          : s(t.sWarn).replace('{g}', grade),
      genAt: new Date().toLocaleString(),
      domains,
      findings,
      suggestions,
      sources: Array.from(sources),
    }

    if (sources.has('realtime')) {
      markPartial('后端缺失指标用本地回退系数估算评分，其余来自实时接口')
    } else {
      markFull()
    }
  } finally {
    loading.value = false
  }
}

function repairsOpenFromCache() {
  const repairs: any[] = readLs('w9_repair_orders', [])
  return repairs.filter((r: any) => r.status !== 'closed').length
}

function openDetail(d: Domain) {
  detail.value = d
}

function exportPdf() {
  if (!report.value) return
  const r = report.value
  const lines = [
    `iHealth 月度健康报告 - ${r.month}`,
    `总分: ${r.score}  等级: ${r.grade}`,
    `生成时间: ${r.genAt}`,
    ``,
    `== 域评分 ==`,
    ...r.domains.map((d) => `${d.name}: ${d.score}  ${d.note}`),
    ``,
    `== 关键发现 ==`,
    ...r.findings,
    ``,
    `== 改进建议 ==`,
    ...r.suggestions,
  ]
  const text = lines.join('\n')
  // 优先尝试复制到剪贴板，便于粘贴到工单/知识库
  if (navigator.clipboard) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        // 同时触发打印对话框（打印友好样式）
        window.print()
      })
      .catch(() => window.print())
  } else {
    window.print()
  }
}

onMounted(() => {
  initMonths()
  generate()
})
</script>

<style scoped>
.health-report {
  color: var(--txt);
}

.hr-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.hr-head h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--txt-strong);
  margin: 0;
}
.hr-head .sub {
  display: block;
  font-size: 0.78rem;
  color: var(--txt2);
  margin-top: 4px;
  max-width: 62ch;
  line-height: 1.4;
}
.hr-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.hr-month {
  width: auto;
  min-width: 150px;
}

.empty-tip {
  padding: 48px 16px;
  text-align: center;
  color: var(--txt2);
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: var(--panel);
  font-size: 0.85rem;
}

/* 各区块竖向间距 */
.hr-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 概览：环形总分 + 雷达 + 摘要 */
.hr-overview-body {
  display: flex;
  align-items: center;
  gap: 28px;
  flex-wrap: wrap;
}
.score-ring {
  position: relative;
  width: 112px;
  height: 112px;
  flex: none;
}
.ring-svg {
  width: 112px;
  height: 112px;
  transform: rotate(-90deg);
}
.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-score {
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1;
}
.ring-label {
  font-size: 0.7rem;
  color: var(--txt2);
  margin-top: 3px;
}
.radar-box {
  flex: none;
}
.radar-title {
  font-size: 0.72rem;
  color: var(--txt2);
  margin-bottom: 4px;
  text-align: center;
}
.radar-svg {
  width: 184px;
  height: 184px;
}
.hr-summary {
  flex: 1;
  min-width: 220px;
}
.hr-grade {
  font-size: 0.85rem;
  color: var(--txt);
  font-weight: 600;
}
.hr-grade span {
  font-size: 1.05rem;
  font-weight: 800;
  margin-left: 4px;
}
.hr-summary-text {
  font-size: 0.8rem;
  color: var(--txt2);
  margin: 6px 0 0;
  line-height: 1.5;
}
.hr-meta {
  font-size: 0.72rem;
  color: var(--txt3, #8595ad);
  margin-top: 8px;
}
.hr-meta.sm {
  margin-top: 4px;
}
.src-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

/* 域评分卡片 */
.hr-domains {
  margin: 0;
}
.domain-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: 0.15s;
}
.domain-card:hover {
  border-color: var(--cyan);
  box-shadow: var(--glow);
}
.domain-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.domain-name {
  font-size: 0.82rem;
  color: var(--txt2);
}
.domain-score {
  font-size: 1.15rem;
  font-weight: 700;
}
.domain-bar {
  height: 6px;
  border-radius: 4px;
  background: var(--track);
  margin-top: 8px;
  overflow: hidden;
}
.domain-bar i {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s;
}
.domain-note {
  font-size: 0.72rem;
  color: var(--txt2);
  margin: 8px 0 0;
  line-height: 1.4;
}
.domain-more {
  font-size: 0.66rem;
  color: var(--txt3, #8595ad);
  margin-top: 6px;
}
.domain-card:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
}

/* 发现 / 建议列表 */
.hr-list {
  list-style: disc;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: var(--txt2);
  font-size: 0.8rem;
}
.hr-list li {
  line-height: 1.45;
}

/* 钻取弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: var(--mask, rgba(3, 8, 18, 0.62));
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 16px;
}
.modal-box {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: var(--glow);
  width: 100%;
  max-width: 420px;
  padding: 20px;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.modal-head h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--txt-strong);
  margin: 0;
}
.modal-close {
  background: none;
  border: none;
  color: var(--txt2);
  font-size: 1.1rem;
  cursor: pointer;
  line-height: 1;
}
.modal-score {
  font-size: 1.9rem;
  font-weight: 800;
  margin-bottom: 10px;
}
.modal-score-unit {
  font-size: 0.75rem;
  color: var(--txt2);
  margin-left: 4px;
}
.modal-note {
  font-size: 0.8rem;
  color: var(--txt2);
  margin-bottom: 10px;
  line-height: 1.5;
}
.modal-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.72rem;
  color: var(--txt2);
}

@media (max-width: 860px) {
  .hr-overview-body {
    gap: 18px;
  }
}

@media print {
  .modal-mask {
    display: none !important;
  }
}
</style>
