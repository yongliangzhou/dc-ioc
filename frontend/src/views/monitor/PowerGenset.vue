<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.genset') }}</h1>
      <span class="sub">{{ tl('柴发并机系统') }} {{ tl('·') }} {{ tl('PLC 并机控制') }} {{ tl('·') }} {{ tl('全电参量 / 开关状态 / 故障保护') }}</span>
    </div>

    <!-- ======== 顶部 KPI: 系统总体 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="genset-total" :label="tl('机组总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="genset-online" :label="tl('运行率')" :value="runningPercent" unit="%" :quality="faultUnitCount > 0 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="genset-load" :label="tl('平均负载率')" :value="s.avgLoadPercent ?? 0" unit="%" :quality="(s.avgLoadPercent ?? 0) > 85 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="genset-voltage" :label="tl('平均电压')" :value="avgVoltageKv" unit="kV" quality="good" :online="true" />
    </div>
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="genset-power" :label="tl('总有功')" :value="totalPower" unit="kW" quality="good" :online="true" />
      <MetricCard metric-name="genset-bus" :label="tl('并机母线')" :value="runningCount" :unit="tl('台并机带载')" :quality="runningCount > 0 ? 'good' : 'uncertain'" :online="true" />
      <MetricCard metric-name="genset-step" :label="tl('并机步骤')" :value="s.stepActive + 1" :unit="tl('步') + ' / ' + (s.parallelSteps?.length || 0)" quality="good" :online="true" />
      <MetricCard metric-name="genset-fault" :label="tl('故障/告警机组')" :value="faultUnitCount" unit="台" :quality="faultUnitCount > 0 ? 'uncertain' : 'good'" :online="true" />
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
      <!-- ======== 柴发并机 PLC 架构 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('柴发并机 PLC 控制系统') }}</span>
          <span class="pill g">{{ s.scheme || tl('N+1 并机') }}</span>
        </div>
        <p class="arch-desc muted">{{ tl('柴发并机 PLC 通过与单台柴油发电机控制器通讯，采集每台机组进线、出线的三相电压、三相电流、有功/无功功率、功率因数、电度等电参量，同时采集进线开关与输出断路器的分合状态、柴发故障以及保护装置信息，统一接入集成动环系统，实现动环告警、工单管理、运维管理与能效及成本优化。') }}</p>
        <p class="arch-desc muted" style="margin-bottom:6px">{{ s.busState }} · {{ s.autoMode }}</p>
        <div class="chips">
          <span class="chip" v-for="c in collectTargets" :key="c">{{ c }}</span>
        </div>
      </div>

      <!-- ======== 并机流程步骤 ======== -->
      <div class="card" v-if="s.parallelSteps?.length">
        <div class="card-head">
          <span class="ct">{{ tl('并机控制流程') }}</span>
          <span class="pill g">{{ tl('当前') }}：{{ s.parallelSteps[s.stepActive] || '-' }}</span>
        </div>
        <div class="step-flow">
          <template v-for="(st, i) in s.parallelSteps" :key="st">
            <div class="step-node" :class="stepCls(i)">
              <span class="step-idx">{{ i + 1 }}</span>
              <span class="step-label">{{ st }}</span>
            </div>
            <span class="step-arrow" v-if="i < s.parallelSteps.length - 1">→</span>
          </template>
        </div>
      </div>

      <!-- ======== 柴发机组监测 (全电参量 + 开关状态) ======== -->
      <div class="card scroll-x" v-if="s.units?.length">
        <div class="card-head">
          <span class="ct">{{ tl('柴发机组监测') }} ({{ tl('三相电参量·开关状态') }})</span>
          <span class="pill" :class="runningCount === s.units.length ? 'g' : 'a'">{{ s.units.length }} {{ tl('台') }} · {{ tl('运行') }} {{ runningCount }}/{{ s.units.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('机组') }}</th><th>{{ tl('状态') }}</th>
              <th>{{ tl('进线开关') }}</th><th>{{ tl('出线断路器') }}</th>
              <th>Ua (kV)</th><th>Ub (kV)</th><th>Uc (kV)</th>
              <th>Ia (A)</th><th>Ib (A)</th><th>Ic (A)</th>
              <th>P (kW)</th><th>Q (kVar)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('频率') }}(Hz)</th><th>{{ tl('电度') }}(kWh)</th>
              <th>{{ tl('转速') }}(rpm)</th><th>{{ tl('水温') }}(°C)</th><th>{{ tl('油压') }}(bar)</th><th>{{ tl('启动电池') }}(V)</th><th>{{ tl('运行') }}(h)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in s.units" :key="u.id">
              <td class="d-name">{{ u.id }}</td>
              <td><span class="tag" :class="unitStateCls(u.state)">{{ u.state }}</span></td>
              <td><span class="tag" :class="breakerCls(u.incomer)">{{ u.incomer }}</span></td>
              <td><span class="tag" :class="breakerCls(u.breaker)">{{ u.breaker }}</span></td>
              <td class="mono">{{ fmt(u.ua) }}</td><td class="mono">{{ fmt(u.ub) }}</td><td class="mono">{{ fmt(u.uc) }}</td>
              <td class="mono">{{ fmt(u.ia, 0) }}</td><td class="mono">{{ fmt(u.ib, 0) }}</td><td class="mono">{{ fmt(u.ic, 0) }}</td>
              <td class="mono">{{ fmt(u.p, 0) }}</td><td class="mono">{{ fmt(u.q, 0) }}</td>
              <td class="mono" :class="pfCls(u.pf)">{{ fmt(u.pf) }}</td>
              <td class="mono">{{ fmt(u.freq) }}</td>
              <td class="mono">{{ fmtEnergy(u.energy) }}</td>
              <td class="mono">{{ u.state === '运行' ? u.rpm : '-' }}</td>
              <td class="mono" :class="tempCls(u.waterT, 90, 95)">{{ u.state === '运行' ? u.waterT : '-' }}</td>
              <td class="mono" :class="u.oilP > 0 && u.oilP < 3 ? 'r-text' : ''">{{ u.oilP > 0 ? fmt(u.oilP, 1) : '-' }}</td>
              <td class="mono" :class="u.battU < 24 ? 'a-text' : ''">{{ fmt(u.battU, 1) }}</td>
              <td class="mono">{{ u.runHrs }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 机组故障与保护装置 ======== -->
      <div class="card" v-if="s.units?.length">
        <div class="card-head">
          <span class="ct">{{ tl('柴发故障与保护装置') }} ({{ tl('每台机组') }})</span>
          <span class="pill" :class="faultUnitCount === 0 ? 'g' : 'a'">{{ tl('告警机组') }} {{ faultUnitCount }}/{{ s.units.length }}</span>
        </div>
        <div class="unit-grid">
          <div class="unit-block" v-for="u in s.units" :key="u.id">
            <div class="unit-head">
              <span class="d-status" :class="unitStateDotCls(u.state)">●</span>
              <span class="d-name">{{ u.id }}</span>
              <span class="tag" :class="unitStateCls(u.state)">{{ u.state }}</span>
            </div>
            <!-- 故障遥信 -->
            <div class="sub-title">{{ tl('故障遥信') }}</div>
            <div class="sig-list" v-if="u.faults?.length">
              <span class="sig" v-for="f in u.faults" :key="f.name">
                <span class="sig-k">{{ f.name }}</span>
                <span class="sig-v" :class="sigLevelCls(f.level)">{{ f.value }}</span>
              </span>
            </div>
            <div class="sig-empty muted" v-else>{{ tl('无故障') }}</div>
            <!-- 保护装置 -->
            <div class="sub-title">{{ tl('保护装置') }} ({{ u.protections?.length || 0 }}{{ tl('项') }})</div>
            <div class="sig-list" v-if="u.protections?.length">
              <span class="sig" v-for="p in u.protections" :key="p.name">
                <span class="sig-k">{{ p.name }}</span>
                <span class="sig-v" :class="sigLevelCls(p.level)">{{ p.state }}</span>
              </span>
            </div>
            <div class="sig-empty muted" v-else>{{ tl('检修中·保护已退出') }}</div>
          </div>
        </div>
      </div>

      <!-- ======== 上次测试 ======== -->
      <div class="card" v-if="s.lastTest?.date">
        <div class="card-head">
          <span class="ct">{{ tl('上次并机测试') }}</span>
          <span class="pill g">{{ s.lastTest.result }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('测试日期') }}</span><span class="v mono">{{ s.lastTest.date }}</span></div>
          <div class="kv"><span class="k">{{ tl('测试类型') }}</span><span class="v">{{ s.lastTest.type }}</span></div>
          <div class="kv"><span class="k">{{ tl('持续时间') }}</span><span class="v mono">{{ s.lastTest.duration }}</span></div>
          <div class="kv"><span class="k">{{ tl('测试结果') }}</span><span class="v" :class="s.lastTest.result === '通过' ? 'g-text' : 'a-text'">{{ s.lastTest.result }}</span></div>
        </div>
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
        {{ tl('柴发并机系统') }} · {{ tl('PLC 并机控制') }} | {{ tl('机组') }} {{ s.total }} {{ tl('台') }} · {{ runningCount }} {{ tl('台运行') }} · {{ tl('总有功') }} {{ totalPower }} kW · {{ tl('告警机组') }} {{ faultUnitCount }} {{ tl('台') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerGensetDetailed, type GensetSummary } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<GensetSummary | null>(null)
const error = ref('')

const units = computed(() => s.value?.units ?? [])

const runningCount = computed(() => units.value.filter((u) => u.state === '运行').length)
const runningPercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((runningCount.value / s.value.total) * 100).toFixed(1))
})
// 故障/告警机组: 状态为维保, 或存在 a/r 级故障/保护
const faultUnitCount = computed(() =>
  units.value.filter((u) =>
    u.state === '维保' ||
    (u.faults?.some((f) => f.level === 'a' || f.level === 'r')) ||
    (u.protections?.some((p) => p.level === 'a' || p.level === 'r')),
  ).length,
)

const avgVoltageKv = computed(() => {
  const v = s.value?.avgVoltage
  return v != null ? Number((v / 1000).toFixed(2)) : 0
})

const totalPower = computed(() =>
  Number(units.value.reduce((sum, u) => sum + (u.p || 0), 0).toFixed(0)),
)

// 并机 PLC 采集对象
const collectTargets = computed(() => [
  '进线三相电压', '出线三相电流', '有功/无功功率', '功率因数', '电度',
  '进线开关分合', '输出断路器状态', '柴发故障遥信', '保护装置状态',
  '转速/水温/油压', '启动电池电压', '动环告警联动',
])

// ---- 工具函数 ----
function fmt(v: number | undefined | null, dp = 2): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Number(v).toFixed(dp)
}

function fmtEnergy(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Math.round(v).toLocaleString()
}

function isClosed(v?: string): boolean {
  const t = String(v ?? '').trim()
  return t.includes('合闸') || (t.includes('合') && !t.includes('分'))
}

function breakerCls(v: string): string {
  if (isClosed(v)) return 'g'
  if (v.includes('分闸') || v.includes('分')) return 'b'
  return 'a'
}

function unitStateCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '维保') return 'r'
  if (st === '备用') return 'b'
  return 'a'
}
function unitStateDotCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '维保') return 'r'
  if (st === '备用') return 'm'
  return 'a'
}

function stepCls(i: number): string {
  const active = s.value?.stepActive ?? 0
  if (i < active) return 'done'
  if (i === active) return 'active'
  return 'todo'
}

function pfCls(pf: number): string {
  if (pf >= 0.9) return 'g-text'
  if (pf >= 0.8) return 'a-text'
  return 'r-text'
}

function tempCls(t: number, warn: number, alarm: number): string {
  if (t >= alarm) return 'r-text'
  if (t >= warn) return 'a-text'
  return 'g-text'
}

function sigLevelCls(level: string): string {
  if (level === 'g') return 'sig-g'
  if (level === 'a') return 'sig-a'
  if (level === 'r') return 'sig-r'
  return 'sig-b'
}

async function load() {
  error.value = ''
  try {
    s.value = await getPowerGensetDetailed()
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

/* 文本色 */
.g-text { color: var(--green); }
.a-text { color: var(--amber); }
.r-text { color: var(--red); }

/* ----------  tag ---------- */
.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: var(--blue); border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* ----------  并机步骤流 ---------- */
.step-flow { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.step-node { display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border-radius: 16px; font-size: 11px; border: 1px solid var(--td-line); background: var(--bg2); }
.step-node .step-idx { width: 16px; height: 16px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; background: var(--track); color: var(--txt2); }
.step-node.done { color: var(--green); border-color: rgba(43,212,122,.35); }
.step-node.done .step-idx { background: var(--green); color: #061021; }
.step-node.active { color: var(--cyan); border-color: var(--cyan); background: rgba(34,227,255,.1); }
.step-node.active .step-idx { background: var(--cyan); color: #061021; }
.step-node.todo { color: var(--txt3); }
.step-arrow { color: var(--txt3); font-size: 12px; margin: 0 2px; }

/* ----------  机组故障/保护网格 ---------- */
.unit-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.unit-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.unit-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.unit-head .tag { margin-left: auto; }
.d-status { font-size: 8px; }
.d-status.g { color: var(--green); }
.d-status.r { color: var(--red); }
.d-status.a { color: var(--amber); }
.d-status.m { color: var(--muted); }
.sub-title { font-size: 11px; color: var(--cyan); font-weight: 600; margin: 8px 0 6px; padding-top: 6px; border-top: 1px dashed var(--td-line); }
.sub-title:first-of-type { border-top: none; padding-top: 0; }

.sig-list { display: flex; flex-wrap: wrap; gap: 5px; }
.sig { display: inline-flex; align-items: center; gap: 4px; font-size: 10.5px; padding: 2px 7px; border-radius: 4px; background: var(--panel); border: 1px solid var(--td-line); }
.sig-k { color: var(--txt3); }
.sig-v { font-weight: 600; }
.sig-g { color: var(--green); }
.sig-a { color: var(--amber); }
.sig-r { color: var(--red); }
.sig-b { color: var(--blue); }
.sig-empty { font-size: 11px; font-style: italic; }

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
@media (max-width: 1180px) { .unit-grid { grid-template-columns: 1fr; } }

/* ----------  misc ---------- */
.flex { display: flex; }
.center { align-items: center; }
.muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; }
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
