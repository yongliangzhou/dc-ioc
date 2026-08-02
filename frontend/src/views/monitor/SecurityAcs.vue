<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }} {{ tl('·') }} {{ tl('nav.securityAcs') }}</h1>
      <span class="sub">{{ tl('门禁管理') }} {{ tl('·') }} {{ tl('分级分区授权 · 防尾随 · 消防联动') }}</span>
    </div>

    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="acs-total" :label="tl('门禁总数')" :value="s.total" unit="樘" quality="good" :online="true" />
      <MetricCard metric-name="acs-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="acs-events" :label="tl('今日刷卡')" :value="s.todayEvents" unit="次" quality="good" :online="true" />
      <MetricCard metric-name="acs-denied" :label="tl('拒绝/异常')" :value="s.denied + s.openAbnormal" unit="次" :quality="(s.denied + s.openAbnormal) ? 'uncertain' : 'good'" :online="true" :severity="(s.denied + s.openAbnormal) ? 'warn' : 'normal'" />
    </div>

    <template v-if="s">
      <!-- 平台架构 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.securityAcs') }} {{ tl('·') }} {{ tl('分级授权') }}</span>
          <span class="pill" :class="s.openAbnormal ? 'a' : 'g'">{{ tl('门磁异常') }} {{ s.openAbnormal }} · {{ tl('访客') }} {{ s.visitors }}</span>
        </div>
        <div class="kv-grid">
          <div class="kv"><span class="k">{{ tl('今日刷卡事件') }}</span><span class="v">{{ s.todayEvents }} {{ tl('次') }}</span></div>
          <div class="kv"><span class="k">{{ tl('今日拒绝/告警') }}</span><span class="v" :class="s.denied ? 'a-text' : 'g-text'">{{ s.denied }} {{ tl('次') }}</span></div>
          <div class="kv"><span class="k">{{ tl('门磁异常开启') }}</span><span class="v" :class="s.openAbnormal ? 'a-text' : 'g-text'">{{ s.openAbnormal }} {{ tl('樘') }}</span></div>
          <div class="kv"><span class="k">{{ tl('在线访客') }}</span><span class="v">{{ s.visitors }} {{ tl('人') }}</span></div>
        </div>
        <div class="chips" style="margin-top:8px">
          <span class="chip" v-for="c in archComponents" :key="c">{{ c }}</span>
        </div>
        <p class="arch-desc muted" v-if="s.knowledge?.arch?.design">{{ s.knowledge.arch.design }}</p>
      </div>

      <!-- 分级分区 -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('授权区域分级') }}</span>
          <span class="pill g">{{ s.areas.length }} {{ tl('级区') }} · {{ s.total }} {{ tl('门') }}</span>
        </div>
        <div class="area-grid">
          <div class="area-block" v-for="a in s.areas" :key="a.id">
            <div class="area-head">
              <span class="d-name">{{ a.id }}</span>
              <span class="tag b">{{ a.doors }} {{ tl('门') }}</span>
            </div>
            <div class="area-auth"><span class="muted">{{ tl('认证方式') }}</span><span class="auth-val">{{ a.auth }}</span></div>
          </div>
        </div>
      </div>

      <!-- 出入事件 -->
      <div class="card">
        <div class="card-head"><span class="ct">{{ tl('出入控制事件') }}</span><span class="pill g">{{ s.events.length }} {{ tl('条') }}</span></div>
        <div class="evt-list">
          <div class="evt-row" v-for="(e, i) in s.events" :key="i">
            <span class="evt-time mono">{{ e.ts }}</span>
            <span class="evt-door">{{ e.door }}</span>
            <span class="evt-person">{{ e.person }}</span>
            <span class="evt-act">{{ e.act }}</span>
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
import { getSecurityAcsDetailed, type AcsSummary } from '@/api/security'
const { t: tl } = useI18n()

const s = ref<AcsSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})
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
    s.value = await getSecurityAcsDetailed()
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
.arch-desc { font-size: 12px; line-height: 1.7; margin: 8px 0 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 11px; padding: 2px 9px; border-radius: 12px; background: rgba(34,227,255,0.08); color: var(--cyan); border: 1px solid rgba(34,227,255,0.25); }
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); } .v { font-size: 13px; color: var(--txt); font-weight: 600; }
.g-text { color: var(--green); } .a-text { color: var(--amber); } .note { font-size: 10px; }

.area-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.area-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.area-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.area-auth { display: flex; flex-direction: column; gap: 2px; }
.auth-val { font-size: 13px; font-weight: 600; color: var(--cyan); }

.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: var(--blue); border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

.evt-list { border-top: 1px solid var(--border); padding-top: 6px; }
.evt-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 12px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,.04)); }
.evt-time { color: var(--txt3); } .evt-door { color: var(--cyan); font-weight: 500; }
.evt-person { color: var(--txt); } .evt-act { flex: 1; color: var(--txt2); }

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
@media (max-width: 1180px) { .area-grid { grid-template-columns: 1fr; } }
</style>
