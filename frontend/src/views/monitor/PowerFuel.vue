<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.fuel') }}</h1>
      <span class="sub">{{ tl('燃油监控') }} {{ tl('·') }} {{ tl('PLC 供回油控制') }} {{ tl('·') }} {{ tl('油位 / 阀门状态 / 油泵告警与保护') }}</span>
    </div>

    <!-- ======== 顶部 KPI: 系统总体 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="fuel-total" :label="tl('设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="fuel-online" :label="tl('在线率')" :value="onlinePercent" unit="%" :quality="alarmCount > 0 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="fuel-main-level" :label="tl('主油罐平均油位')" :value="avgMainLevel" unit="%" :quality="avgMainLevel < 30 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="fuel-endurance" :label="tl('满载续航')" :value="s.endurance" unit="h" :quality="s.endurance < 8 ? 'uncertain' : 'good'" :online="true" />
    </div>
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="fuel-day-level" :label="tl('日用油箱平均油位')" :value="avgDayLevel" unit="%" :quality="avgDayLevel < 30 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="fuel-pump-run" :label="tl('运行油泵')" :value="pumpRunCount" :unit="tl('台') + ' / ' + (s.pumps?.length || 0)" quality="good" :online="true" />
      <MetricCard metric-name="fuel-pressure" :label="tl('管道压力')" :value="s.pipeline?.pressure ?? 0" unit="MPa" :quality="(s.pipeline?.pressure ?? 0) > 0.5 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="fuel-alarm" :label="tl('告警/异常')" :value="alarmCount" unit="项" :quality="alarmCount > 0 ? 'uncertain' : 'good'" :online="true" />
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
      <!-- ======== 燃油监控 PLC 架构 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('燃油监控 PLC 控制系统') }}</span>
          <span class="pill g">{{ tl('接入集成动环系统') }}</span>
        </div>
        <p class="arch-desc muted">{{ tl('燃油监控 PLC 通过与储油罐、供油泵、油管道阀门、日用油箱、回油泵等设备通讯，实时采集油箱油罐的油位、阀门的开合状态、油泵的告警以及保护装置等信息，统一接入集成动环系统，实现动环告警、供油联锁控制与运维管理。') }}</p>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('管道状态') }}</span><span class="v">{{ s.pipeline?.state || '-' }}</span></div>
          <div class="kv"><span class="k">{{ tl('伴热') }}</span><span class="v">{{ s.pipeline?.tracing || '-' }}</span></div>
          <div class="kv"><span class="k">{{ tl('应急供油合同') }}</span><span class="v">{{ s.contract || '-' }}</span></div>
          <div class="kv"><span class="k">{{ tl('满载续航') }}</span><span class="v mono" :class="s.endurance < 8 ? 'a-text' : 'g-text'">{{ s.endurance }} {{ tl('小时') }}</span></div>
        </div>
        <div class="chips" style="margin-top:10px">
          <span class="chip" v-for="c in collectTargets" :key="c">{{ c }}</span>
        </div>
      </div>

      <!-- ======== 主油罐 (油位·阀门·四段开关·保护) ======== -->
      <div class="card" v-if="s.mainTanks?.length">
        <div class="card-head">
          <span class="ct">{{ tl('室外储油罐') }} ({{ tl('油位·阀门·保护') }})</span>
          <span class="pill" :class="mainAllOk ? 'g' : 'a'">{{ s.mainTanks.length }} {{ tl('座') }} · {{ tl('正常') }} {{ mainOkCount }}/{{ s.mainTanks.length }}</span>
        </div>
        <div class="tank-grid">
          <div class="tank-block" v-for="t in s.mainTanks" :key="t.id">
            <div class="tank-head">
              <span class="d-name">{{ t.id }}</span>
              <span class="tag" :class="t.leak === '正常' ? 'g' : 'r'">{{ tl('渗漏') }}: {{ t.leak }}</span>
            </div>
            <!-- 油位 + 容量 -->
            <div class="level-row">
              <div class="level-bar">
                <div class="level-fill" :class="levelCls(t.level)" :style="{ width: t.level + '%' }"></div>
                <span class="level-mark" v-for="mk in [10, 30, 70, 90]" :key="mk" :style="{ left: mk + '%' }"></span>
              </div>
              <span class="level-val mono" :class="levelCls(t.level)">{{ t.level }}%</span>
            </div>
            <div class="tank-meta">
              <span class="muted">{{ tl('容量') }} {{ fmtEnergy(t.cap) }} L</span>
              <span class="muted">{{ tl('油温') }} {{ fmt(t.t, 1) }}°C</span>
              <span class="muted">{{ tl('水分') }} {{ t.water }}</span>
            </div>
            <!-- 四段液位开关 -->
            <div class="sub-title">{{ tl('油位四段开关') }}</div>
            <div class="sig-list">
              <span class="sig" v-for="sw in t.switches" :key="sw.name">
                <span class="sig-k">{{ sw.th }}</span>
                <span class="sig-v" :class="sigLevelCls(sw.level)">{{ sw.state }}</span>
              </span>
            </div>
            <!-- 阀门开合状态 -->
            <div class="sub-title">{{ tl('阀门开合状态') }}</div>
            <div class="sig-list">
              <span class="sig" v-for="v in t.valves" :key="v.name">
                <span class="sig-k">{{ v.name }}</span>
                <span class="sig-v" :class="valveCls(v.state)">{{ v.state }}</span>
              </span>
            </div>
            <!-- 保护装置 -->
            <div class="sub-title">{{ tl('保护装置') }}</div>
            <div class="sig-list">
              <span class="sig" v-for="p in t.protections" :key="p.name">
                <span class="sig-k">{{ p.name }}</span>
                <span class="sig-v" :class="sigLevelCls(p.level)">{{ p.state }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 日用油箱 ======== -->
      <div class="card" v-if="s.dayTanks?.length">
        <div class="card-head">
          <span class="ct">{{ tl('日用油箱') }} ({{ tl('油位·阀门·保护') }})</span>
          <span class="pill" :class="dayAllOk ? 'g' : 'a'">{{ s.dayTanks.length }} {{ tl('台') }} · {{ tl('正常') }} {{ dayOkCount }}/{{ s.dayTanks.length }}</span>
        </div>
        <div class="tank-grid">
          <div class="tank-block" v-for="d in s.dayTanks" :key="d.id">
            <div class="tank-head">
              <span class="d-name">{{ d.id }}</span>
              <span class="tag" :class="d.leak === '正常' ? 'g' : 'r'">{{ tl('渗漏') }}: {{ d.leak }}</span>
            </div>
            <div class="level-row">
              <div class="level-bar">
                <div class="level-fill" :class="levelCls(d.level)" :style="{ width: d.level + '%' }"></div>
                <span class="level-mark" v-for="mk in [10, 30, 70, 90]" :key="mk" :style="{ left: mk + '%' }"></span>
              </div>
              <span class="level-val mono" :class="levelCls(d.level)">{{ d.level }}%</span>
            </div>
            <div class="tank-meta">
              <span class="muted">{{ tl('容量') }} {{ fmtEnergy(d.cap) }} L</span>
            </div>
            <div class="sub-title">{{ tl('油位四段开关') }}</div>
            <div class="sig-list">
              <span class="sig" v-for="sw in d.switches" :key="sw.name">
                <span class="sig-k">{{ sw.th }}</span>
                <span class="sig-v" :class="sigLevelCls(sw.level)">{{ sw.state }}</span>
              </span>
            </div>
            <div class="sub-title">{{ tl('进油阀状态') }}</div>
            <div class="sig-list">
              <span class="sig">
                <span class="sig-k">{{ d.valve?.name }}</span>
                <span class="sig-v" :class="valveCls(d.valve?.state)">{{ d.valve?.state }}</span>
              </span>
            </div>
            <div class="sub-title">{{ tl('保护装置') }}</div>
            <div class="sig-list">
              <span class="sig" v-for="p in d.protections" :key="p.name">
                <span class="sig-k">{{ p.name }}</span>
                <span class="sig-v" :class="sigLevelCls(p.level)">{{ p.state }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 供油泵 / 回油泵 (告警 + 保护) ======== -->
      <div class="card" v-if="s.pumps?.length">
        <div class="card-head">
          <span class="ct">{{ tl('供油泵 / 回油泵') }} ({{ tl('告警·保护装置') }})</span>
          <span class="pill" :class="pumpAllOk ? 'g' : 'a'">{{ s.pumps.length }} {{ tl('台') }} · {{ tl('运行') }} {{ pumpRunCount }}/{{ s.pumps.length }}</span>
        </div>
        <div class="pump-grid">
          <div class="pump-block" v-for="p in s.pumps" :key="p.id">
            <div class="pump-head">
              <span class="d-status" :class="pumpStateDotCls(p.state)">●</span>
              <span class="d-name">{{ p.id }}</span>
              <span class="tag" :class="pumpStateCls(p.state)">{{ p.state }}</span>
              <span class="pump-mode muted">{{ p.mode }}</span>
            </div>
            <!-- 油泵告警 -->
            <div class="sub-title">{{ tl('运行告警') }}</div>
            <div class="sig-list" v-if="p.alarms?.length">
              <span class="sig" v-for="a in p.alarms" :key="a.name">
                <span class="sig-k">{{ a.name }}</span>
                <span class="sig-v" :class="sigLevelCls(a.level)">{{ a.value }}</span>
              </span>
            </div>
            <!-- 保护装置 -->
            <div class="sub-title">{{ tl('保护装置') }} ({{ p.protections?.length || 0 }}{{ tl('项') }})</div>
            <div class="sig-list" v-if="p.protections?.length">
              <span class="sig" v-for="pr in p.protections" :key="pr.name">
                <span class="sig-k">{{ pr.name }}</span>
                <span class="sig-v" :class="sigLevelCls(pr.level)">{{ pr.state }}</span>
              </span>
            </div>
          </div>
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
        {{ tl('燃油监控') }} · {{ tl('PLC 供回油控制') }} | {{ tl('主油罐') }} {{ s.mainTanks?.length || 0 }} {{ tl('座') }} · {{ tl('日用油箱') }} {{ s.dayTanks?.length || 0 }} {{ tl('台') }} · {{ tl('油泵') }} {{ s.pumps?.length || 0 }} {{ tl('台') }} · {{ tl('续航') }} {{ s.endurance }}h · {{ tl('告警') }} {{ alarmCount }} {{ tl('项') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerFuelDetailed, type FuelSummary } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<FuelSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})

// 油位均值
const avgMainLevel = computed(() => avgNum((s.value?.mainTanks ?? []).map((t) => t.level)))
const avgDayLevel = computed(() => avgNum((s.value?.dayTanks ?? []).map((t) => t.level)))

// 油泵运行
const pumpRunCount = computed(() => (s.value?.pumps ?? []).filter((p) => p.state === '运行').length)
const pumpAllOk = computed(() => {
  const list = s.value?.pumps ?? []
  return list.length > 0 && list.every((p) => p.state !== '故障')
})

// 主油罐/日用油箱正常统计
const mainOkCount = computed(
  () => (s.value?.mainTanks ?? []).filter((t) => t.leak === '正常' && t.level >= 20 && t.level <= 95).length,
)
const mainAllOk = computed(() => {
  const list = s.value?.mainTanks ?? []
  return list.length > 0 && mainOkCount.value === list.length
})
const dayOkCount = computed(
  () => (s.value?.dayTanks ?? []).filter((t) => t.leak === '正常' && t.level >= 20 && t.level <= 95).length,
)
const dayAllOk = computed(() => {
  const list = s.value?.dayTanks ?? []
  return list.length > 0 && dayOkCount.value === list.length
})

// 告警/异常总数: 油泵告警 + 阀门异常 + 油位越限 + 渗漏
const alarmCount = computed(() => {
  if (!s.value) return 0
  let n = 0
  for (const p of s.value.pumps ?? []) {
    n += (p.alarms ?? []).filter((a) => a.level === 'a' || a.level === 'r').length
    n += (p.protections ?? []).filter((pr) => pr.level === 'a' || pr.level === 'r').length
  }
  for (const t of [...(s.value.mainTanks ?? []), ...(s.value.dayTanks ?? [])]) {
    if (t.leak !== '正常') n++
    n += (t.protections ?? []).filter((pr) => pr.level === 'a' || pr.level === 'r').length
  }
  return n
})

// PLC 采集对象
const collectTargets = computed(() => [
  '储油罐油位', '日用油箱油位', '油位四段开关', '进/出油阀门开合',
  '供油泵状态', '回油泵状态', '油泵告警', '保护装置',
  '管道压力', '伴热状态', '渗漏监测', '动环告警联动',
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

function fmtEnergy(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Math.round(v).toLocaleString()
}

function levelCls(level: number): string {
  if (level >= 90 || level < 20) return 'r'
  if (level < 30 || level > 85) return 'a'
  return 'g'
}

function pumpStateCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '故障') return 'r'
  if (st === '备用') return 'b'
  return 'a'
}
function pumpStateDotCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '故障') return 'r'
  if (st === '备用') return 'm'
  return 'a'
}

function valveCls(state?: string): string {
  // 阀门: 开启=正常出油(绿), 闭合=关闭(蓝)
  if (state === '开启') return 'sig-g'
  if (state === '闭合') return 'sig-b'
  return 'sig-a'
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
    s.value = await getPowerFuelDetailed()
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

/* ----------  油罐/油箱块 ---------- */
.tank-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.tank-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.tank-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

/* 油位条 */
.level-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.level-bar { position: relative; flex: 1; height: 18px; border-radius: 4px; background: var(--track); overflow: hidden; }
.level-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; transition: width .3s; }
.level-fill.g { background: linear-gradient(90deg, rgba(43,212,122,.5), rgba(43,212,122,.85)); }
.level-fill.a { background: linear-gradient(90deg, rgba(255,176,32,.5), rgba(255,176,32,.85)); }
.level-fill.r { background: linear-gradient(90deg, rgba(255,77,94,.5), rgba(255,77,94,.85)); }
.level-mark { position: absolute; top: 0; bottom: 0; width: 1px; background: rgba(255,255,255,.25); }
.level-val { font-size: 14px; font-weight: 700; min-width: 50px; text-align: right; }
.level-val.g { color: var(--green); }
.level-val.a { color: var(--amber); }
.level-val.r { color: var(--red); }
.tank-meta { display: flex; gap: 14px; font-size: 11px; margin-bottom: 4px; }

/* ----------  油泵块 ---------- */
.pump-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.pump-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.pump-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.pump-head .tag { margin-left: auto; }
.pump-mode { font-size: 11px; }
.d-status { font-size: 8px; }
.d-status.g { color: var(--green); }
.d-status.r { color: var(--red); }
.d-status.a { color: var(--amber); }
.d-status.m { color: var(--muted); }

/* ----------  子标题 + 信号列表 ---------- */
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
@media (max-width: 1180px) { .tank-grid, .pump-grid { grid-template-columns: 1fr; } }

/* ----------  misc ---------- */
.flex { display: flex; }
.center { align-items: center; }
.muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; }
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
