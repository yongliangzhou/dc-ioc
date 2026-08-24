<template>
  <div class="p-4 md:p-6">
    <div class="mb-4 flex items-center justify-between flex-wrap gap-2">
      <div>
        <h2 class="text-xl font-semibold text-gray-800">{{ t.title }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ t.sub }}</p>
      </div>
      <div class="flex gap-2 items-center">
        <select v-model="month" class="dc-input w-40">
          <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
        </select>
        <button class="dc-btn dc-btn-primary" :disabled="loading" @click="generate">
          {{ loading ? t.loading : t.generate }}
        </button>
        <button v-if="report" class="dc-btn" @click="exportPdf">{{ t.exportPdf }}</button>
      </div>
    </div>

    <div v-if="!report" class="bg-white rounded-lg shadow-sm border border-gray-100 p-8 text-center text-gray-400 text-sm">
      {{ t.emptyHint }}
    </div>

    <template v-else>
      <!-- 总分 + 雷达 -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-100 p-5 mb-4 flex items-center gap-6 flex-wrap">
        <div class="relative w-28 h-28 shrink-0">
          <svg viewBox="0 0 36 36" class="w-28 h-28 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" stroke-width="3" />
            <circle cx="18" cy="18" r="15.9" fill="none" :stroke="scoreColor(report.score)" stroke-width="3"
              :stroke-dasharray="`${(report.score / 100) * 100} 100`" stroke-linecap="round" />
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-2xl font-bold" :style="{ color: scoreColor(report.score) }">{{ report.score }}</span>
            <span class="text-xs text-gray-400">{{ t.score }}</span>
          </div>
        </div>

        <!-- 七维雷达图 (SVG 自绘) -->
        <div class="shrink-0">
          <div class="text-xs text-gray-500 mb-1">{{ t.radarTitle }}</div>
          <svg viewBox="0 0 200 200" class="w-44 h-44">
            <g transform="translate(100,100)">
              <polygon
                v-for="ring in [0.25, 0.5, 0.75, 1]" :key="ring"
                :points="radarPoints(ring)" fill="none" stroke="#e5e7eb" stroke-width="1"
              />
              <line
                v-for="(d, i) in report.domains" :key="'ax' + i"
                :x1="0" :y1="0" :x2="axisX(i)" :y2="axisY(i)" stroke="#e5e7eb" stroke-width="1"
              />
              <polygon
                :points="radarDataPoints" fill="rgba(37,99,235,0.18)" stroke="#2563eb" stroke-width="2"
              />
              <circle
                v-for="(d, i) in report.domains" :key="'pt' + i"
                :cx="axisX(i, d.score / 100)" :cy="axisY(i, d.score / 100)" r="2.5" fill="#2563eb"
              />
              <text
                v-for="(d, i) in report.domains" :key="'lb' + i"
                :x="axisX(i, 1.18)" :y="axisY(i, 1.18)" font-size="8" fill="#64748b"
                text-anchor="middle" dominant-baseline="middle"
              >{{ d.name }}</text>
            </g>
          </svg>
        </div>

        <div class="flex-1 min-w-[220px]">
          <div class="text-sm font-medium text-gray-700">{{ t.grade }}:
            <span class="text-lg font-bold" :style="{ color: scoreColor(report.score) }">{{ report.grade }}</span>
          </div>
          <p class="text-sm text-gray-600 mt-1">{{ report.summary }}</p>
          <div class="text-xs text-gray-400 mt-2">{{ t.genAt }}: {{ report.genAt }}</div>
          <div class="text-[11px] text-gray-400 mt-1">{{ t.weightHint }}</div>
          <div class="flex flex-wrap gap-1 mt-2">
            <span
              v-for="src in report.sources" :key="src"
              class="px-2 py-0.5 rounded text-[11px] border"
              :class="src === 'realtime' ? 'border-emerald-300 text-emerald-600 bg-emerald-50' : 'border-amber-300 text-amber-600 bg-amber-50'"
            >{{ t.sourceTag }}: {{ src === 'realtime' ? t.srcRealtime : t.srcLocal }}</span>
          </div>
        </div>
      </div>

      <!-- 域评分（点击钻取） -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-4">
        <div
          v-for="d in report.domains" :key="d.key"
          class="bg-white rounded-lg shadow-sm border border-gray-100 p-4 cursor-pointer hover:border-blue-300 transition"
          @click="openDetail(d)"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-600">{{ d.name }}</span>
            <span class="text-lg font-semibold" :style="{ color: scoreColor(d.score) }">{{ d.score }}</span>
          </div>
          <div class="h-1.5 bg-gray-100 rounded mt-2 overflow-hidden">
            <div class="h-full rounded" :style="{ width: d.score + '%', background: scoreColor(d.score) }"></div>
          </div>
          <p class="text-xs text-gray-500 mt-2">{{ d.note }}</p>
        </div>
      </div>

      <!-- 关键发现与建议 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t.findings }}</h3>
          <ul class="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li v-for="(f, i) in report.findings" :key="i">{{ f }}</li>
          </ul>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ t.suggestions }}</h3>
          <ul class="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>
    </template>

    <!-- 评分构成钻取 -->
    <div
      v-if="detail"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="detail = null"
    >
      <div class="bg-white rounded-lg shadow-lg w-full max-w-md p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-base font-semibold text-gray-800">{{ t.detailTitle }} · {{ detail.name }}</h3>
          <button class="text-gray-400 hover:text-gray-600" @click="detail = null">✕</button>
        </div>
        <div class="text-3xl font-bold mb-3" :style="{ color: scoreColor(detail.score) }">
          {{ detail.score }}<span class="text-sm text-gray-400 ml-1">{{ t.score }}</span>
        </div>
        <p class="text-sm text-gray-600 mb-3">{{ detail.note }}</p>
        <ul class="text-xs text-gray-500 space-y-1">
          <li v-for="(line, i) in detail.breakdown" :key="i">· {{ line }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getActiveAlarms, getExternalDevices, getTickets, getDrills, getDrillRecords, getCabinets, listEquipment, getTenantStats } from '@/api'

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('healthReport') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

interface Domain { key: string; name: string; score: number; note: string; breakdown?: string[] }
interface Report {
  month: string; score: number; grade: string; summary: string; genAt: string
  domains: Domain[]; findings: string[]; suggestions: string[]
  sources: string[]
}

const months = ref<string[]>([])
const month = ref('')
const report = ref<Report | null>(null)
const loading = ref(false)
const detail = ref<Domain | null>(null)

function initMonths() {
  const now = new Date()
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    months.value.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  month.value = months.value[0]
}

function readLs(key: string, fallback: any) {
  try { return JSON.parse(localStorage.getItem(key) || 'null') || fallback } catch { return fallback }
}

// 安全取字符串
function s(v: any): string { return typeof v === 'string' ? v : '' }
function clamp(v: number) { return Math.max(0, Math.min(100, Math.round(v))) }
function pct(n: number, d: number) { return d ? Math.round((n / d) * 100) : 0 }

function scoreColor(v: number) {
  return v >= 85 ? '#16a34a' : v >= 70 ? '#2563eb' : v >= 60 ? '#d97706' : '#dc2626'
}

// 雷达图坐标
const AXIS_R = 80
function radarPoint(i: number, r: number) {
  const ang = -Math.PI / 2 + (i * 2 * Math.PI) / 7
  return { x: Math.cos(ang) * AXIS_R * r, y: Math.sin(ang) * AXIS_R * r }
}
function axisX(i: number, r = 1) { return radarPoint(i, r).x }
function axisY(i: number, r = 1) { return radarPoint(i, r).y }
function radarPoints(ring: number) {
  return Array.from({ length: 7 }, (_, i) => { const p = radarPoint(i, ring); return `${p.x},${p.y}` }).join(' ')
}
const radarDataPoints = computed(() =>
  (report.value?.domains ?? []).map((d, i) => {
    const p = radarPoint(i, d.score / 100); return `${p.x},${p.y}`
  }).join(' '),
)

async function generate() {
  loading.value = true
  const sources = new Set<string>(['local'])
  try {
    // 并行拉取真实数据
    const [alarms, devices, tickets, drills, drillRecs, cabinets, equip, tenantStats] = await Promise.all([
      getActiveAlarms().catch(() => null),
      getExternalDevices({ limit: 200 }).catch(() => null),
      getTickets({}).catch(() => null),
      getDrills().catch(() => null),
      getDrillRecords().catch(() => null),
      getCabinets({ size: 200 }).catch(() => null),
      listEquipment({ size: 200 }).catch(() => null),
      getTenantStats().catch(() => null),
    ])
    if (alarms || devices || tickets || drills || drillRecs || cabinets || equip || tenantStats) sources.add('realtime')

    const hazards: any[] = readLs('w10_hazards', [])
    const suppliers: any[] = readLs('w9_suppliers', [])

    // 供配电：活跃告警 + 高危隐患
    const activeAlarms = alarms?.total ?? 0
    const hazHigh = hazards.filter((h: any) => h.level === 'high' && h.enabled).length
    const powerScore = clamp(92 - activeAlarms * 4 - hazHigh * 5)

    // 制冷：制冷类设备在线率
    const allDev: any[] = devices?.items ?? []
    const coolingDev = allDev.filter((d: any) => /冷却|制冷|空调|chill|cool|crac|冷机/i.test(d.name || d.model || ''))
    const coolingOff = coolingDev.filter((d: any) => d.status === 'offline' || d.status === 'off').length
    const coolingRate = coolingDev.length ? pct(coolingDev.length - coolingOff, coolingDev.length) : 96
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
    const drillPass = drillStats && drillStats.done
      ? drillStats.pass / drillStats.done
      : (() => {
          const recs: any[] = drillRecs?.records ?? []
          return recs.length ? recs.filter((d: any) => d.result === 'pass' || d.status === 'done').length / recs.length : 0.85
        })()
    const drillScore = clamp(Math.round(55 + drillPass * 40))

    // 供应商
    const supScore = suppliers.length
      ? Math.round(suppliers.reduce((a: number, x: any) => a + (x.score || 0), 0) / suppliers.length)
      : 82

    // 维修闭环：TicketCenter.stats.open 直接给未关闭数
    const repairOpen = tickets?.stats?.open ?? repairsOpenFromCache()
    const repairScore = clamp(Math.max(50, 100 - repairOpen * 8))

    // 容量与机房：基于租户统计的超限/预警数
    const overCount = tenantStats?.overCount ?? 0
    const warnCount = tenantStats?.warnCount ?? 0
    const occ = tenantStats ? Math.round((tenantStats.totalCabinets - warnCount) / Math.max(1, tenantStats.totalCabinets) * 100) : 75
    const capScore = clamp(Math.round(100 - overCount * 12 - warnCount * 4))

    const domains: Domain[] = [
      {
        key: 'power', name: s(t.dPower), score: powerScore,
        note: s(t.nPower).replace('{n}', String(hazHigh + activeAlarms)),
        breakdown: [s(t.fAlarmHigh).replace('{n}', String(activeAlarms)), `${t.dHazard}: ${hazHigh} high-risk`],
      },
      {
        key: 'cooling', name: s(t.dCooling), score: coolingScore,
        note: s(t.nCoolingReal).replace('{r}', String(coolingRate)).replace('{n}', String(coolingOff)),
        breakdown: [`${coolingDev.length} cooling devices`, `${coolingOff} offline`],
      },
      {
        key: 'network', name: s(t.dNetwork), score: networkScore,
        note: s(t.nNetworkReal).replace('{r}', String(netRate)).replace('{n}', String(netOff)),
        breakdown: [`${allDev.length} devices`, `${netOff} offline`],
      },
      {
        key: 'hazard', name: s(t.dHazard), score: hazScore,
        note: s(t.nHazard).replace('{n}', String(hazHigh)),
        breakdown: [`${hazTotal} rules`, `${hazHigh} high-risk enabled`],
      },
      {
        key: 'drill', name: s(t.dDrill), score: drillScore,
        note: s(t.nDrill).replace('{r}', String(Math.round(drillPass * 100))),
        breakdown: [`${drills?.plans?.length ?? drillRecs?.records?.length ?? 0} drills`, `pass ${Math.round(drillPass * 100)}%`],
      },
      {
        key: 'supplier', name: s(t.dSupplier), score: clamp(supScore),
        note: s(t.nSupplier),
        breakdown: [`${suppliers.length} suppliers`, `avg ${supScore}`],
      },
      {
        key: 'repair', name: s(t.dRepair), score: repairScore,
        note: s(t.nRepair).replace('{n}', String(repairOpen)),
        breakdown: [`${repairOpen} open tickets`],
      },
      {
        key: 'capacity', name: s(t.dCapacity), score: capScore,
        note: s(t.nCapacity).replace('{r}', String(occ)),
        breakdown: [`occupancy ${occ}%`, `cabinets ${tenantStats?.totalCabinets ?? '?'}`, `over ${overCount} / warn ${warnCount}`],
      },
    ]

    // 加权总分
    const W: Record<string, number> = {
      power: 0.18, cooling: 0.18, network: 0.18, hazard: 0.09,
      drill: 0.09, supplier: 0.09, repair: 0.09, capacity: 0.10,
    }
    const score = Math.round(domains.reduce((a, d) => a + d.score * (W[d.key] ?? 0.1), 0) * 100) / 100

    const grade = score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : score >= 60 ? 'D' : 'E'

    const findings: string[] = []
    const suggestions: string[] = []
    if (hazHigh >= 4) { findings.push(s(t.fHighHazard).replace('{n}', String(hazHigh))); suggestions.push(s(t.sHighHazard)) }
    if (activeAlarms >= 5) { findings.push(s(t.fAlarmHigh).replace('{n}', String(activeAlarms))); suggestions.push(s(t.sAlarm)) }
    if (netRate < 95) { findings.push(s(t.fNetLow).replace('{n}', String(netOff))); suggestions.push(s(t.sNet)) }
    if (coolingRate < 95) { findings.push(s(t.fCoolLow).replace('{n}', String(coolingOff))); suggestions.push(s(t.sCool)) }
    if (drillPass < 0.8) { findings.push(s(t.fDrillLow)); suggestions.push(s(t.sDrill)) }
    if (repairOpen >= 3) { findings.push(s(t.fRepairOpen).replace('{n}', String(repairOpen))); suggestions.push(s(t.sRepair)) }
    if (occ > 90) { findings.push(s(t.fCapHigh)); suggestions.push(s(t.sCapacity)) }
    if (suppliers.filter((x: any) => (x.score || 0) < 70).length) { findings.push(s(t.fSupLow)); suggestions.push(s(t.sSup)) }
    findings.push(s(t.fSummary).replace('{m}', month.value))
    suggestions.push(s(t.sReview))

    report.value = {
      month: month.value,
      score: Math.round(score),
      grade,
      summary: grade === 'A' || grade === 'B' ? s(t.sGood).replace('{g}', grade) : s(t.sWarn).replace('{g}', grade),
      genAt: new Date().toLocaleString(),
      domains,
      findings,
      suggestions,
      sources: Array.from(sources),
    }
  } finally {
    loading.value = false
  }
}

function repairsOpenFromCache() {
  const repairs: any[] = readLs('w9_repair_orders', [])
  return repairs.filter((r: any) => r.status !== 'closed').length
}

function openDetail(d: Domain) { detail.value = d }

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
    navigator.clipboard.writeText(text).then(() => {
      // 同时触发打印对话框（打印友好样式）
      window.print()
    }).catch(() => window.print())
  } else {
    window.print()
  }
}

onMounted(() => { initMonths(); generate() })
</script>

<style scoped>
@media print {
  .fixed { display: none !important; }
}
</style>
