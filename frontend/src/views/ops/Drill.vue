<template>
  <div>
    <div class="view-head"><h1>{{ tl('nav.drill') }}</h1><span class="sub">{{ tl('应急预案与演练评估') }}</span></div>
    <div class="grid cols-5" v-if="stats">
      <MetricCard metric-name="drill-plans" :label="tl('演练方案')" :value="stats.totalPlans" quality="good" :online="true" />
      <MetricCard metric-name="drill-records" :label="tl('演练次数')" :value="stats.totalRecords" quality="good" :online="true" />
      <MetricCard metric-name="drill-avg" :label="tl('平均分')" :value="Number(stats.avgScore.toFixed(1))" unit="分" :quality="stats.avgScore >= 80 ? 'good' : 'uncertain'" :online="true" />
      <MetricCard metric-name="drill-pass" :label="tl('通过')" :value="stats.passedCount" quality="good" :online="true" />
      <MetricCard metric-name="drill-fail" :label="tl('未通过')" :value="stats.failedCount" :quality="stats.failedCount ? 'bad' : 'good'" :severity="stats.failedCount ? 'crit' : 'normal'" :online="true" />
    </div>
    <div class="grid cols-4-6" style="margin-top:16px">
      <div class="card"><h5 class="section-title">{{ tl('演练方案') }}</h5>
        <div class="p-list" v-if="plans.length">
          <div v-for="p in plans" :key="p.id" class="p-row" :class="{ sel: selId === p.id }" @click="sel(p.id)">
            <div><span class="p-n">{{ p.name }}</span><span class="p-c">{{ p.code }}</span></div>
            <div class="p-m"><span class="pill-tag b">{{ p.scenario }}</span><span class="muted">{{ p.participants || '-' }}</span></div>
          </div>
        </div><div class="empty" v-else>{{ tl('暂无方案') }}</div>
      </div>
      <div class="card"><h5 class="section-title">{{ selName || tl('演练记录') }}</h5>
        <div class="tbl" v-if="records.length">
          <div class="tbl-head"><span class="col w-drill-by">{{ tl('执行人') }}</span><span class="col w-drill-time">{{ tl('时间') }}</span><span class="col w-drill-score">{{ tl('评分') }}</span><span class="col w-drill-result">{{ tl('结果') }}</span></div>
          <div v-for="r in records" :key="r.id" class="tbl-row"><span class="col w-drill-by">{{ r.executedBy }}</span><span class="col w-drill-time muted">{{ r.startedAt }}</span><span class="col w-drill-score" :style="{ color: r.score != null && r.score >= 80 ? 'var(--green)' : 'var(--red)' }">{{ r.score || '-' }}</span><span class="col w-drill-result"><span class="pill-tag" :class="r.result === 'pass' ? 'g' : 'r'">{{ r.result || '-' }}</span></span></div>
        </div><div class="empty" v-else>{{ tl('暂无记录') }}</div>
      </div>
    </div>
    <div class="card" v-if="!plans.length && !e"><div class="flex center" style="padding:40px"><span class="muted">{{ tl('common.loading') }}</span></div></div>
    <div class="card" v-if="e"><div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ e }}</span></div></div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'; import { useI18n } from 'vue-i18n'; const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import { getDrillPlans, getDrillRecords, getDrillStats, type DrillPlanView, type DrillRecordView, type DrillStats } from '@/api/drill'
const plans = ref<DrillPlanView[]>([]); const records = ref<DrillRecordView[]>([]); const stats = ref<DrillStats | null>(null); const e = ref(''); const selId = ref<number | null>(null); const selName = ref('')
async function sel(id: number) { selId.value = selId.value === id ? null : id; selName.value = plans.value.find(x => x.id === id)?.name ?? ''; records.value = await getDrillRecords(selId.value ?? undefined) }
async function load() { try { const [p, s] = await Promise.all([getDrillPlans(), getDrillStats()]); plans.value = p; stats.value = s; if (p.length) { selId.value = p[0].id; selName.value = p[0].name; records.value = await getDrillRecords(p[0].id) } } catch (ex: any) { e.value = ex?.message || String(ex) } }
onMounted(load)
</script>
<style scoped>
.section-title { margin: 0 0 12px; font-size: 14px; font-weight: 600; }
.p-list { max-height: 360px; overflow-y: auto; }
.p-row { padding: 10px 8px; cursor: pointer; border-radius: 6px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.p-row:hover { background: var(--bg2); } .p-row.sel { background: rgba(64,150,255,0.08); border-left: 3px solid var(--blue); }
.p-n { font-weight: 500; font-size: 13px; } .p-c { color: var(--muted); font-size: 11px; margin-left: 8px; }
.p-m { font-size: 11.5px; margin-top: 4px; display: flex; gap: 8px; align-items: center; }
.pill-tag { font-size: 10.5px; padding: 1px 8px; border-radius: 9px; background: var(--bg2); }
.pill-tag.g { background: rgba(82,196,26,0.12); color: var(--green); } .pill-tag.r { background: rgba(255,77,79,0.12); color: var(--red); } .pill-tag.b { background: rgba(64,150,255,0.12); color: var(--blue); }
.tbl { max-height: 330px; overflow-y: auto; } .tbl-head, .tbl-row { display: flex; align-items: center; padding: 9px 6px; font-size: 12.5px; }
.tbl-head { font-weight: 600; color: var(--muted); border-bottom: 2px solid var(--border); font-size: 12px; } .tbl-row { border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.col { flex-shrink: 0; } .w-drill-by { width: 80px; } .w-drill-time { width: 170px; } .w-drill-score { width: 60px; } .w-drill-result { width: 60px; }
.empty { text-align: center; padding: 32px; color: var(--muted); font-size: 13px; } .muted { color: var(--muted); }
</style>
