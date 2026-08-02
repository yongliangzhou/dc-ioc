<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }} {{ tl('·') }} {{ tl('nav.securityIds') }}</h1>
      <span class="sub">{{ tl('防入侵系统') }} {{ tl('·') }} {{ tl('周界电子围栏/振动光纤 + 室内红外/玻璃破碎') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="ids-perim-zones" :label="tl('周界防区')" :value="s.perimeter.zones" unit="区" quality="good" :online="true" />
      <MetricCard metric-name="ids-perim-armed" :label="tl('周界布防')" :value="s.perimeter.armed" unit="区" :quality="s.perimeter.armed === s.perimeter.zones ? 'good' : 'uncertain'" :online="true" />
      <MetricCard metric-name="ids-indoor" :label="tl('室内探测器')" :value="s.indoor.ir + s.indoor.glass" unit="个" quality="good" :online="true" />
      <MetricCard metric-name="ids-alarm" :label="tl('周界告警')" :value="s.perimeter.alarm" unit="起" :quality="s.perimeter.alarm ? 'bad' : 'good'" :online="true" :severity="s.perimeter.alarm ? 'crit' : 'normal'" />
    </div>

    <template v-if="s">
      <!-- 周界 + 室内 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('防入侵探测') }}</span>
          <span class="pill" :class="s.perimeter.alarm ? 'r' : 'g'">{{ tl('周界') }} {{ s.perimeter.type }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('周界类型') }}</span><span class="v">{{ s.perimeter.type }}</span></div>
          <div class="kv"><span class="k">{{ tl('周界防区/布防') }}</span><span class="v" :class="s.perimeter.armed === s.perimeter.zones ? 'g-text' : 'a-text'">{{ s.perimeter.armed }}/{{ s.perimeter.zones }}</span></div>
          <div class="kv"><span class="k">{{ tl('室内被动红外') }}</span><span class="v">{{ s.indoor.ir }} {{ tl('个') }}</span></div>
          <div class="kv"><span class="k">{{ tl('玻璃破碎') }}</span><span class="v">{{ s.indoor.glass }} {{ tl('个') }}</span></div>
          <div class="kv"><span class="k">{{ tl('室内布防状态') }}</span><span class="v">{{ s.indoor.armed }}</span></div>
          <div class="kv"><span class="k">{{ tl('联动策略') }}</span><span class="v">{{ s.linkage }}</span></div>
        </div>
        <div class="chips" style="margin-top:8px">
          <span class="chip" v-for="c in archComponents" :key="c">{{ c }}</span>
        </div>
        <p class="arch-desc muted" v-if="s.knowledge?.arch?.design">{{ s.knowledge.arch.design }}</p>
      </div>

      <!-- 事件 -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('入侵报警事件') }}</span><span class="pill" :class="s.perimeter.alarm ? 'r' : 'g'">{{ s.events.length }} {{ tl('条') }}</span></div>
        <div class="evt-list">
          <div class="evt-row" v-for="(e, i) in s.events" :key="i">
            <span class="evt-time mono">{{ e.ts }}</span>
            <span class="evt-zone">{{ e.zone }}</span>
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
import { getSecurityIdsDetailed, type IdsSummary } from '@/api/security'
const { t: tl } = useI18n()

const s = ref<IdsSummary | null>(null)
const error = ref('')

const archComponents = computed(() => s.value?.knowledge?.arch?.components ?? [])

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
    s.value = await getSecurityIdsDetailed()
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
.pill.r { background: rgba(255,77,94,0.12); color: var(--red); }
.arch-desc { font-size: 12px; line-height: 1.7; margin: 8px 0 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 11px; padding: 2px 9px; border-radius: 12px; background: rgba(34,227,255,0.08); color: var(--cyan); border: 1px solid rgba(34,227,255,0.25); }
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); } .v { font-size: 13px; color: var(--txt); font-weight: 600; }
.g-text { color: var(--green); } .a-text { color: var(--amber); } .note { font-size: 10px; }

.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }

.evt-list { border-top: 1px solid var(--border); padding-top: 6px; }
.evt-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 12px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,.04)); }
.evt-time { color: var(--txt3); } .evt-zone { color: var(--cyan); font-weight: 500; } .evt-desc { flex: 1; color: var(--txt2); }

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
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }

.flex { display: flex; } .center { align-items: center; } .muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; } .grid { display: grid; gap: 12px; }
</style>
