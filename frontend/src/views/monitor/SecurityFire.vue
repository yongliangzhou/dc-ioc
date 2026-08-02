<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }} {{ tl('·') }} {{ tl('nav.securityFire') }}</h1>
      <span class="sub">{{ tl('消防报警') }} {{ tl('·') }} {{ tl('烟感/温感/极早期 VESDA/气体灭火/应急疏散') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="fire-points" :label="tl('探测点位')" :value="s.points" unit="点" quality="good" :online="true" />
      <MetricCard metric-name="fire-fault" :label="tl('故障点')" :value="s.faultPoints" unit="点" :quality="s.faultPoints ? 'uncertain' : 'good'" :online="true" :severity="s.faultPoints ? 'warn' : 'normal'" />
      <MetricCard metric-name="fire-gas" :label="tl('气体灭火')" :value="s.gas.ready" unit="区" :quality="s.gas.ready === s.gas.zones ? 'good' : 'uncertain'" :online="true" />
      <MetricCard metric-name="fire-host" :label="tl('主机状态')" :value="passRate" unit="%" quality="good" :online="true" />
    </div>

    <template v-if="s">
      <!-- 主机 + 回路 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('消防报警主机') }}</span>
          <span class="pill" :class="s.faultPoints ? 'a' : 'g'">{{ s.hostState }} · {{ s.loops }} {{ tl('回路') }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('主机状态') }}</span><span class="v" :class="s.hostState.includes('正常') ? 'g-text' : 'a-text'">{{ s.hostState }}</span></div>
          <div class="kv"><span class="k">{{ tl('回路数') }}</span><span class="v">{{ s.loops }}</span></div>
          <div class="kv"><span class="k">{{ tl('探测点位') }}</span><span class="v">{{ s.points }}</span></div>
          <div class="kv"><span class="k">{{ tl('故障点位') }}</span><span class="v" :class="s.faultPoints ? 'a-text' : 'g-text'">{{ s.faultPoints }}</span></div>
        </div>
      </div>

      <!-- 探测器分类 -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('探测器分类') }}</span><span class="pill g">{{ s.detectors.length }} {{ tl('类') }}</span></div>
        <div class="det-grid">
          <div class="det-block" v-for="d in s.detectors" :key="d.type">
            <div class="det-head">
              <span class="d-name">{{ d.type }}</span>
              <span class="tag" :class="d.fault ? 'a' : 'g'">{{ d.n - d.fault }}/{{ d.n }} {{ tl('正常') }}</span>
            </div>
            <div class="det-bar">
              <div class="det-fill" :class="d.fault ? 'a' : 'g'" :style="{ width: detPct(d) + '%' }"></div>
              <span class="det-val mono">{{ detPct(d) }}%</span>
            </div>
            <div class="det-meta muted" v-if="d.fault">{{ tl('故障点') }} {{ d.fault }}</div>
          </div>
        </div>
      </div>

      <!-- 极早期 VESDA -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('极早期吸气式探测 (VESDA)') }}</span><span class="pill g">{{ s.vesda.length }} {{ tl('采样管网') }}</span></div>
        <div class="vesda-grid">
          <div class="vesda-block" v-for="v in s.vesda" :key="v.id">
            <div class="vesda-head">
              <span class="d-name">{{ v.id }}</span>
              <span class="tag" :class="v.level === '轻微' ? 'a' : 'g'">{{ v.level }}</span>
            </div>
            <div class="vesda-val mono">{{ v.val }} <span class="muted">%</span></div>
            <div class="vesda-meta muted">{{ tl('烟雾浓度') }}</div>
          </div>
        </div>
      </div>

      <!-- 气体灭火 + 切非 + 应急照明 -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('气体灭火 / 切非 / 应急疏散') }}</span><span class="pill" :class="s.gas.ready === s.gas.zones ? 'g' : 'a'">{{ tl('药剂') }} {{ s.gas.agent }}</span></div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('气体灭火区') }}</span><span class="v">{{ s.gas.zones }} {{ tl('区') }} ({{ tl('就绪') }} {{ s.gas.ready }})</span></div>
          <div class="kv"><span class="k">{{ tl('已释放') }}</span><span class="v" :class="s.gas.released ? 'a-text' : 'g-text'">{{ s.gas.released }} {{ tl('区') }}</span></div>
          <div class="kv"><span class="k">{{ tl('切非联动') }}</span><span class="v">{{ s.qieFei.state }}</span></div>
          <div class="kv"><span class="k">{{ tl('最近演练') }}</span><span class="v">{{ s.qieFei.lastDrill }}</span></div>
          <div class="kv"><span class="k">{{ tl('应急照明') }}</span><span class="v">{{ s.emergency.lights }} {{ tl('盏') }} / {{ tl('正常') }} {{ s.emergency.ok }}</span></div>
          <div class="kv"><span class="k">{{ tl('蓄电池续航') }}</span><span class="v" :class="s.emergency.batteryOk >= 90 ? 'g-text' : 'a-text'">{{ s.emergency.batteryOk }}%</span></div>
          <div class="kv"><span class="k">{{ tl('疏散指示') }}</span><span class="v">{{ s.emergency.evacSigns }} {{ tl('个') }}</span></div>
          <div class="kv"><span class="k">{{ tl('联动逻辑') }}</span><span class="v">{{ s.qieFei.desc }}</span></div>
        </div>
      </div>

      <!-- 消防事件 -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('消防事件') }}</span><span class="pill g">{{ s.events.length }} {{ tl('条') }}</span></div>
        <div class="evt-list">
          <div class="evt-row" v-for="(e, i) in s.events" :key="i">
            <span class="evt-time mono">{{ e.ts }}</span>
            <span class="evt-desc">{{ e.desc }}</span>
            <span class="tag" :class="lvCls(e.lv)">{{ lvText(e.lv) }}</span>
          </div>
        </div>
      </div>

      <!-- 知识库 -->
      <div class="card" v-if="s.knowledge?.thresholds?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('设计 / 告警阈值') }}</div>
        <div class="kv-grid">
          <div class="kv" v-for="t in s.knowledge.thresholds" :key="t.k">
            <span class="k">{{ t.k }}</span><span class="v">{{ t.v }}</span><span v-if="t.note" class="note muted">{{ t.note }}</span>
          </div>
        </div>
      </div>
      <div class="card" v-for="g in (s.knowledge?.logic || [])" :key="g.title">
        <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
        <div class="logic-list">
          <div class="logic-step" v-for="st in g.steps" :key="st.step">
            <span class="step-no">{{ st.step }}</span><span class="step-text">{{ st.text }}</span>
            <span v-if="st.ok !== undefined" class="ok" :class="st.ok ? 'ok-y' : 'ok-n'">{{ st.ok ? tl('满足') : tl('未满足') }}</span>
          </div>
        </div>
      </div>
      <div class="card scroll-x" v-if="s.knowledge?.faults?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('故障锁定知识库') }}</div>
        <table>
          <thead><tr><th style="width:50px">{{ tl('序号') }}</th><th>{{ tl('故障') }}</th><th>{{ tl('锁定 / 影响') }}</th><th>{{ tl('处置动作') }}</th><th style="width:80px">{{ tl('复位') }}</th></tr></thead>
          <tbody>
            <tr v-for="f in s.knowledge.faults" :key="f.no">
              <td class="mono">{{ f.no }}</td><td class="d-name">{{ f.fault }}</td>
              <td class="muted">{{ f.lock }}</td><td class="muted">{{ f.action }}</td>
              <td><span class="tag" :class="f.manualReset ? 'a' : 'g'">{{ f.manualReset ? tl('人工复位') : tl('自动') }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="knote muted" v-if="s.knowledge?.note">{{ s.knowledge.note }}</p>
    </template>

    <div class="card" v-if="!s && !error">
      <div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div>
    </div>
    <div class="card" v-if="error">
      <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getSecurityFireDetailed, type FireSummary } from '@/api/security'
const { t: tl } = useI18n()

const s = ref<FireSummary | null>(null)
const error = ref('')

const passRate = computed(() => {
  if (!s.value || !s.value.points) return 100
  return Number((((s.value.points - s.value.faultPoints) / s.value.points) * 100).toFixed(1))
})
function detPct(d: { n: number; fault: number }): number {
  if (!d.n) return 0
  return Number((((d.n - d.fault) / d.n) * 100).toFixed(0))
}
function lvCls(lv: string): string {
  if (lv === 'r' || lv === 'crit') return 'r'
  if (lv === 'a' || lv === 'warn') return 'a'
  return 'g'
}
function lvText(lv: string): string {
  if (lv === 'r' || lv === 'crit') return tl('严重')
  if (lv === 'a' || lv === 'warn') return tl('告警')
  return tl('信息')
}

async function load() {
  error.value = ''
  try {
    s.value = await getSecurityFireDetailed()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); } .v { font-size: 13px; color: var(--txt); font-weight: 600; }
.g-text { color: var(--green); } .a-text { color: var(--amber); } .note { font-size: 10px; }

.det-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.det-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.det-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.det-bar { position: relative; height: 18px; border-radius: 4px; background: var(--track); overflow: hidden; }
.det-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; transition: width .3s; }
.det-fill.g { background: linear-gradient(90deg, rgba(43,212,122,.5), rgba(43,212,122,.85)); }
.det-fill.a { background: linear-gradient(90deg, rgba(255,176,32,.5), rgba(255,176,32,.85)); }
.det-val { position: absolute; right: 6px; top: 0; line-height: 18px; font-size: 11px; font-weight: 700; }
.det-meta { font-size: 11px; margin-top: 4px; }

.vesda-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.vesda-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.vesda-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.vesda-val { font-size: 18px; font-weight: 700; color: var(--cyan); }
.vesda-meta { font-size: 11px; margin-top: 2px; }

.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }

.evt-list { border-top: 1px solid var(--border); padding-top: 6px; }
.evt-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 12px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,.04)); }
.evt-time { color: var(--txt3); } .evt-desc { flex: 1; color: var(--txt); }

.section-title { font-size: 13px; font-weight: 700; color: var(--cyan); margin: 0 0 10px; display: flex; align-items: center; gap: 8px; }
.section-title .bar { display: none; }
.logic-list { display: flex; flex-direction: column; gap: 8px; }
.logic-step { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--txt); line-height: 1.5; }
.step-no { flex: 0 0 auto; width: 20px; height: 20px; border-radius: 50%; background: var(--cyan); color: #061021; font-size: 11px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.step-text { flex: 1; }
.ok { flex: 0 0 auto; font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.ok-y { background: rgba(43,212,122,.15); color: var(--green); } .ok-n { background: rgba(255,77,94,.15); color: var(--red); }
.knote { font-size: 12px; font-style: italic; text-align: center; margin-top: 12px; }

table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10.5px; padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid var(--td-line); color: var(--txt); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }
.d-name { font-weight: 500; color: var(--txt); }
.muted { color: var(--txt2); }
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }

.flex { display: flex; } .center { align-items: center; } .scroll-x { overflow-x: auto; } .grid { display: grid; gap: 12px; }
@media (max-width: 1180px) { .det-grid, .vesda-grid { grid-template-columns: 1fr; } }
</style>
