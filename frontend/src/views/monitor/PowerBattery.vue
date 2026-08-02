<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.battery') }}</h1>
      <span class="sub">{{ tl('电池监控') }} {{ tl('·') }} {{ tl('单体级监测') }} {{ tl('·') }} {{ tl('电压 / 温度 / 内阻 / 充放电') }}</span>
    </div>

    <!-- ======== 顶部 KPI ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="bat-groups" :label="tl('电池组数')" :value="s.groups?.length ?? 0" unit="组" quality="good" :online="true" />
      <MetricCard metric-name="bat-soc" :label="tl('平均 SOC')" :value="avgSoc" unit="%" :quality="avgSoc < 80 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="bat-backup" :label="tl('后备时间')" :value="s.backupMin" unit="min" :quality="s.backupMin < 10 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="bat-alarm" :label="tl('单体告警')" :value="cellAlarmCount" unit="节" :quality="cellAlarmCount > 0 ? 'uncertain' : 'good'" :online="true" />
    </div>
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="bat-voltage" :label="tl('平均组电压')" :value="avgGroupVoltage" unit="V" quality="good" :online="true" />
      <MetricCard metric-name="bat-current" :label="tl('平均充放电电流')" :value="avgCurrent" unit="A" quality="good" :online="true" />
      <MetricCard metric-name="bat-temp" :label="tl('最高单体温度')" :value="maxCellTemp" unit="°C" :quality="maxCellTemp > 35 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="bat-cells" :label="tl('监测单体总数')" :value="totalCells" unit="节" quality="good" :online="true" />
    </div>

    <!-- 加载 / 错误态 -->
    <template v-if="!s">
      <div class="card" v-if="!error">
        <div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div>
      </div>
      <div class="card" v-if="error">
        <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div>
      </div>
    </template>

    <template v-else>
      <!-- ======== 电池监控架构 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('电池监控末端·控制单元') }}</span>
          <span class="pill g">{{ tl('接入集成动环系统') }}</span>
        </div>
        <p class="arch-desc muted">{{ tl('电池监控末端通过 TA 单体采集模块对每节电池的电压、温度、内阻进行测量，TC 模块采集电池组的总电压、充放电电流与环境温度；电池控制单元（收敛模块）轮巡分析后，通过 RJ45/串口统一接口接入集成动环系统，统一实现动环告警、工单管理、运维管理与能效及成本优化。') }}</p>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('充放电状态') }}</span><span class="v">{{ allCdState }}</span></div>
          <div class="kv"><span class="k">{{ tl('后备时间') }}</span><span class="v mono" :class="s.backupMin < 10 ? 'a-text' : 'g-text'">{{ s.backupMin }} {{ tl('分钟') }}</span></div>
          <div class="kv"><span class="k">{{ tl('上次核容放电') }}</span><span class="v">{{ s.lastDischarge || '-' }}</span></div>
          <div class="kv"><span class="k">{{ tl('监测单体总数') }}</span><span class="v mono">{{ totalCells }} {{ tl('节') }}</span></div>
        </div>
        <div class="chips" style="margin-top:10px">
          <span class="chip" v-for="c in collectTargets" :key="c">{{ c }}</span>
        </div>
      </div>

      <!-- ======== 电池组概览 ======== -->
      <div class="card scroll-x" v-if="s.groups?.length">
        <div class="card-head">
          <span class="ct">{{ tl('电池组概览') }} ({{ tl('总电压·充放电电流·SOC') }})</span>
          <span class="pill" :class="cellAlarmCount === 0 ? 'g' : 'a'">{{ s.groups.length }} {{ tl('组') }} · {{ tl('告警单体') }} {{ cellAlarmCount }} {{ tl('节') }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('电池组') }}</th><th>{{ tl('类型') }}</th><th>{{ tl('状态') }}</th>
              <th>SOC</th><th>{{ tl('组总电压') }}(V)</th><th>{{ tl('充放电电流') }}(A)</th><th>{{ tl('充放电状态') }}</th>
              <th>{{ tl('最高温度') }}(°C)</th><th>{{ tl('最差单体') }}</th><th>{{ tl('内阻结论') }}</th><th>{{ tl('单体数') }}</th><th>{{ tl('告警单体') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="g in s.groups" :key="g.id">
              <td class="d-name">{{ g.id }}</td>
              <td class="muted">{{ g.type }}</td>
              <td><span class="tag" :class="g.state === '浮充' ? 'g' : 'a'">{{ g.state }}</span></td>
              <td class="mono" :class="g.soc < 80 ? 'a-text' : 'g-text'">{{ g.soc }}%</td>
              <td class="mono">{{ fmt(g.u, 1) }}</td>
              <td class="mono">{{ fmt(g.i, 2) }}</td>
              <td><span class="tag b">{{ g.cdState }}</span></td>
              <td class="mono" :class="g.maxT > 35 ? 'a-text' : ''">{{ g.maxT }}</td>
              <td class="mono muted">{{ g.worstCell }}</td>
              <td><span class="tag" :class="g.ir === '正常' ? 'g' : 'a'">{{ g.ir }}</span></td>
              <td class="mono">{{ g.cells?.length || 0 }}</td>
              <td class="mono" :class="groupAlarmCount(g) > 0 ? 'a-text' : ''">{{ groupAlarmCount(g) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 单体电池监测 (电压/温度/内阻) ======== -->
      <div class="card" v-if="s.groups?.length">
        <div class="card-head">
          <span class="ct">{{ tl('单体电池监测') }} ({{ tl('电压·温度·内阻') }})</span>
          <span class="pill g">{{ tl('TA 模块逐节采集') }}</span>
        </div>
        <p class="arch-desc muted" style="margin-bottom:12px">{{ tl('每个色块代表一节电池, 颜色按内阻/电压健康度着色 (绿=正常 / 橙=预警 / 红=告警)。点击色块查看该单体详细电压、温度、内阻。') }}</p>

        <div class="group-block" v-for="g in s.groups" :key="g.id">
          <div class="group-head">
            <span class="d-name">{{ g.id }}</span>
            <span class="muted">{{ g.type }}</span>
            <span class="tag" :class="g.ir === '正常' ? 'g' : 'a'">{{ tl('内阻') }}: {{ g.ir }}</span>
            <span class="tag b">{{ g.cells?.length || 0 }} {{ tl('节') }}</span>
            <span v-if="groupAlarmCount(g) > 0" class="tag a">{{ tl('告警') }} {{ groupAlarmCount(g) }} {{ tl('节') }}</span>
          </div>
          <!-- 单体色块网格 -->
          <div class="cell-grid">
            <div
              v-for="c in g.cells"
              :key="c.no"
              class="cell-box"
              :class="cellCls(c.level)"
              :title="`${g.id} ${c.no} | U:${c.u}V T:${c.t}°C IR:${c.ir}Ω`"
              @click="selectCell(g, c)"
            >
              <span class="cell-no">{{ c.no }}</span>
              <span class="cell-u">{{ fmt(c.u, c.u < 5 ? 2 : 1) }}V</span>
            </div>
          </div>
        </div>

        <!-- 选中单体详情 -->
        <div class="cell-detail" v-if="selectedCell">
          <div class="cell-detail-head">
            <span class="ct">{{ selectedGroup }} · {{ selectedCell.no }}</span>
            <span class="tag" :class="sigLevelTagCls(selectedCell.level)">{{ cellLevelLabel(selectedCell.level) }}</span>
            <button class="close-btn" @click="selectedCell = null">×</button>
          </div>
          <div class="cell-detail-grid">
            <div class="cd-item"><span class="k">{{ tl('单体电压') }}</span><span class="v mono">{{ fmt(selectedCell.u, selectedCell.u < 5 ? 3 : 2) }} V</span></div>
            <div class="cd-item"><span class="k">{{ tl('单体温度') }}</span><span class="v mono" :class="selectedCell.t > 35 ? 'a-text' : ''">{{ selectedCell.t }} °C</span></div>
            <div class="cd-item"><span class="k">{{ tl('单体内阻') }}</span><span class="v mono" :class="selectedCell.level === 'a' ? 'a-text' : ''">{{ selectedCell.ir }} Ω</span></div>
          </div>
        </div>
      </div>

      <!-- ======== 单体告警明细 ======== -->
      <div class="card scroll-x" v-if="s.cellAlarms?.length">
        <div class="card-head">
          <span class="ct">{{ tl('单体告警明细') }}</span>
          <span class="pill a">{{ s.cellAlarms.length }} {{ tl('条') }}</span>
        </div>
        <table>
          <thead>
            <tr><th>{{ tl('电池组') }}</th><th>{{ tl('单体') }}</th><th>{{ tl('告警项') }}</th><th>{{ tl('级别') }}</th><th>{{ tl('发生时间') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(a, i) in s.cellAlarms" :key="i">
              <td class="d-name">{{ a.g }}</td>
              <td class="mono">{{ a.cell }}</td>
              <td class="muted">{{ a.item }}</td>
              <td><span class="tag a">{{ a.lv }}</span></td>
              <td class="mono muted">{{ a.ts }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 知识库: 阈值 ======== -->
      <div class="card" v-if="s.knowledge?.thresholds?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('设计 / 告警阈值') }}</div>
        <div class="kv-grid">
          <div class="kv" v-for="t in s.knowledge.thresholds" :key="t.k">
            <span class="k">{{ t.k }}</span>
            <span class="v">{{ t.v }}</span>
            <span v-if="t.note" class="note muted">{{ t.note }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 架构 ======== -->
      <div class="card" v-if="s.knowledge?.arch">
        <div class="section-title"><span class="bar"></span>{{ tl('系统架构与组成') }}</div>
        <p class="arch-desc muted">{{ s.knowledge.arch.design }}</p>
        <div class="chips">
          <span class="chip" v-for="c in s.knowledge.arch.components" :key="c">{{ c }}</span>
        </div>
        <p class="redundancy muted" v-if="s.knowledge.arch.redundancy">{{ tl('冗余配置') }}：{{ s.knowledge.arch.redundancy }}</p>
      </div>

      <!-- ======== 知识库: 控制逻辑 ======== -->
      <div class="card" v-for="g in (s.knowledge?.logic || [])" :key="g.title">
        <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
        <div class="logic-list">
          <div class="logic-step" v-for="st in g.steps" :key="st.step">
            <span class="step-no">{{ st.step }}</span>
            <span class="step-text">{{ st.text }}</span>
            <span v-if="st.ok !== undefined" class="ok" :class="st.ok ? 'ok-y' : 'ok-n'">{{ st.ok ? tl('满足') : tl('未满足') }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 故障锁定 ======== -->
      <div class="card scroll-x" v-if="s.knowledge?.faults?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('故障锁定知识库') }}</div>
        <table>
          <thead><tr><th style="width:50px">{{ tl('序号') }}</th><th>{{ tl('故障') }}</th><th>{{ tl('锁定 / 影响') }}</th><th>{{ tl('处置动作') }}</th><th style="width:80px">{{ tl('复位') }}</th></tr></thead>
          <tbody>
            <tr v-for="f in s.knowledge.faults" :key="f.no">
              <td class="mono">{{ f.no }}</td>
              <td class="d-name">{{ f.fault }}</td>
              <td class="muted">{{ f.lock }}</td>
              <td class="muted">{{ f.action }}</td>
              <td><span class="tag" :class="f.manualReset ? 'a' : 'g'">{{ f.manualReset ? tl('人工复位') : tl('自动') }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="knote muted" v-if="s.knowledge?.note">{{ s.knowledge.note }}</p>

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('电池监控') }} · {{ tl('单体级监测') }} | {{ tl('电池组') }} {{ s.groups?.length || 0 }} {{ tl('组') }} · {{ tl('单体') }} {{ totalCells }} {{ tl('节') }} · {{ tl('平均SOC') }} {{ avgSoc }}% · {{ tl('后备') }} {{ s.backupMin }}min · {{ tl('告警单体') }} {{ cellAlarmCount }} {{ tl('节') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerBatteryDetailed, type BatterySummary, type BatteryGroupView, type BatteryCellView } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<BatterySummary | null>(null)
const error = ref('')
const selectedCell = ref<BatteryCellView | null>(null)
const selectedGroup = ref('')

const groups = computed(() => s.value?.groups ?? [])

const avgSoc = computed(() => avgNum(groups.value.map((g) => g.soc)))
const avgGroupVoltage = computed(() => avgNum(groups.value.map((g) => g.u)))
const avgCurrent = computed(() => avgNum(groups.value.map((g) => g.i)))
const maxCellTemp = computed(() => {
  let max = 0
  for (const g of groups.value) for (const c of g.cells ?? []) if (c.t > max) max = c.t
  return max
})
const totalCells = computed(() => groups.value.reduce((sum, g) => sum + (g.cells?.length ?? 0), 0))
const cellAlarmCount = computed(() =>
  groups.value.reduce((sum, g) => sum + (g.cells ?? []).filter((c) => c.level === 'a' || c.level === 'r').length, 0),
)
const allCdState = computed(() => {
  const states = new Set(groups.value.map((g) => g.cdState))
  return [...states].join(' / ') || '-'
})

// PLC 采集对象
const collectTargets = computed(() => [
  '单体电压 (TA)', '单体温度 (TA)', '单体内阻 (TA)',
  '组总电压 (TC)', '充放电电流 (TC)', '环境温度 (TC)',
  'SOC 估算', '收敛模块轮巡', '超限自动告警', '干接点联动',
])

// ---- 工具函数 ----
function avgNum(list: number[]): number {
  const vals = list.filter((v) => v != null && Number.isFinite(v))
  if (!vals.length) return 0
  return Number((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1))
}

function fmt(v: number | undefined | null, dp = 2): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Number(v).toFixed(dp)
}

function groupAlarmCount(g: BatteryGroupView): number {
  return (g.cells ?? []).filter((c) => c.level === 'a' || c.level === 'r').length
}

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

function selectCell(g: BatteryGroupView, c: BatteryCellView) {
  selectedGroup.value = g.id
  selectedCell.value = c
}

async function load() {
  error.value = ''
  try {
    s.value = await getPowerBatteryDetailed()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
/* ----------  card / head / pill ---------- */
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }

.arch-desc { font-size: 12px; line-height: 1.7; margin: 0 0 10px; }

/* ----------  chips ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 11px; padding: 2px 9px; border-radius: 12px; background: rgba(34,227,255,0.08); color: var(--cyan); border: 1px solid rgba(34,227,255,0.25); }

/* ----------  table ---------- */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10.5px; letter-spacing: .5px; padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid var(--td-line); color: var(--txt); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }

.d-name { font-weight: 500; color: var(--txt); }
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }
.g-text { color: var(--green); }
.a-text { color: var(--amber); }
.r-text { color: var(--red); }

/* ----------  tag ---------- */
.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: var(--blue); border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* ----------  单体色块网格 ---------- */
.group-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); margin-bottom: 12px; }
.group-block:last-of-type { margin-bottom: 0; }
.group-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.group-head .d-name { font-size: 13px; }

.cell-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(54px, 1fr)); gap: 4px; }
.cell-box { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4px 2px; border-radius: 4px; cursor: pointer; transition: transform .12s, box-shadow .12s; border: 1px solid transparent; }
.cell-box:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.cell-no { font-size: 9px; opacity: .85; }
.cell-u { font-size: 10px; font-weight: 600; font-variant-numeric: tabular-nums; }
.cell-g { background: rgba(43,212,122,.18); color: var(--green); border-color: rgba(43,212,122,.3); }
.cell-a { background: rgba(255,176,32,.22); color: var(--amber); border-color: rgba(255,176,32,.45); }
.cell-r { background: rgba(255,77,94,.22); color: var(--red); border-color: rgba(255,77,94,.5); }

/* 选中单体详情 */
.cell-detail { margin-top: 12px; border: 1px solid var(--cyan); border-radius: 8px; padding: 10px 14px; background: rgba(34,227,255,.06); }
.cell-detail-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.cell-detail-head .tag { margin-left: auto; }
.close-btn { margin-left: 12px; background: transparent; border: 1px solid var(--td-line); color: var(--txt2); border-radius: 6px; cursor: pointer; font-size: 14px; line-height: 1; padding: 2px 7px; }
.close-btn:hover { border-color: var(--red); color: var(--red); }
.cell-detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.cd-item { display: flex; flex-direction: column; gap: 2px; }
.cd-item .k { font-size: 11px; color: var(--txt3); }
.cd-item .v { font-size: 15px; font-weight: 700; }

/* ----------  kv-grid ---------- */
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); }
.v { font-size: 13px; color: var(--txt); font-weight: 600; }
.note { font-size: 10px; }

/* ----------  知识库 ---------- */
.section-title { font-size: 13px; font-weight: 700; color: var(--cyan); margin: 0 0 10px; display: flex; align-items: center; gap: 8px; }
.section-title::before { content: ""; width: 4px; height: 14px; border-radius: 2px; background: var(--cyan); }
.section-title .bar { display: none; }
.logic-list { display: flex; flex-direction: column; gap: 8px; }
.logic-step { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--txt); line-height: 1.5; }
.step-no { flex: 0 0 auto; width: 20px; height: 20px; border-radius: 50%; background: var(--cyan); color: #061021; font-size: 11px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.step-text { flex: 1; }
.ok { flex: 0 0 auto; font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.ok-y { background: rgba(43,212,122,.15); color: var(--green); }
.ok-n { background: rgba(255,77,94,.15); color: var(--red); }
.redundancy { font-size: 12px; margin: 10px 0 0; }
.knote { font-size: 12px; font-style: italic; text-align: center; margin-top: 12px; }

/* ----------  layout ---------- */
.grid { display: grid; gap: 12px; }

/* ----------  misc ---------- */
.flex { display: flex; }
.center { align-items: center; }
.muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; }
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
