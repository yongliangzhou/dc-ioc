<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.maintain') }}</h1>
      <span class="sub">{{ tl('维保计划与执行日历') }}</span>
    </div>

    <div class="grid cols-5" v-if="stats">
      <MetricCard metric-name="mnt-plans" :label="tl('维保计划')" :value="stats.totalPlans" quality="good" :online="true" />
      <MetricCard metric-name="mnt-active" :label="tl('进行中')" :value="stats.activePlans" quality="good" :online="true" />
      <MetricCard metric-name="mnt-overdue" :label="tl('逾期')" :value="stats.overduePlans" unit="项" :quality="stats.overduePlans ? 'bad' : 'good'" :severity="stats.overduePlans ? 'crit' : 'normal'" :online="true" />
      <MetricCard metric-name="mnt-records" :label="tl('执行记录')" :value="stats.totalRecords" unit="条" quality="good" :online="true" />
      <MetricCard metric-name="mnt-completed" :label="tl('已完成')" :value="stats.completedRecords" unit="条" quality="good" :online="true" />
    </div>

    <div class="grid cols-4-6" style="margin-top:16px">
      <!-- 维保计划 -->
      <div class="card">
        <h5 class="section-title">{{ tl('维保计划') }}</h5>
        <div class="plan-list" v-if="plans.length">
          <div v-for="p in plans" :key="p.id" class="plan-row" :class="{ sel: selectedPlanId === p.id }" @click="selectPlan(p.id)">
            <div>
              <span class="p-name">{{ p.name }}</span>
              <span class="p-code">{{ p.code }}</span>
            </div>
            <div class="p-meta">
              <span class="p-eq">{{ p.equipmentCode }}</span>
              <span class="pill-tag" :class="freqCls(p.frequency)">{{ freqLabel(p.frequency) }}</span>
              <span class="pill-tag" :class="p.nextDueDate && isOverdue(p.nextDueDate) ? 'r' : 'g'">
                {{ fmtDate(p.nextDueDate) }}
              </span>
            </div>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无计划') }}</div>
      </div>

      <!-- 执行记录 -->
      <div class="card">
        <h5 class="section-title">{{ selectedPlanName || tl('执行记录') }}</h5>
        <div class="tbl" v-if="records.length">
          <div class="tbl-head">
            <span class="col w-by">{{ tl('维保人') }}</span>
            <span class="col w-time">{{ tl('时间') }}</span>
            <span class="col w-stat">{{ tl('状态') }}</span>
            <span class="col w-res">{{ tl('结果') }}</span>
            <span class="col w-desc">{{ tl('内容') }}</span>
          </div>
          <div v-for="r in records" :key="r.id" class="tbl-row">
            <span class="col w-by">{{ r.maintainedBy }}</span>
            <span class="col w-time muted">{{ r.startedAt }}</span>
            <span class="col w-stat"><span class="pill-tag" :class="r.status === 'completed' ? 'g' : 'a'">{{ r.status === 'completed' ? tl('已完成') : tl('进行中') }}</span></span>
            <span class="col w-res"><span class="pill-tag" :class="r.result === 'pass' ? 'g' : 'r'">{{ r.result || '-' }}</span></span>
            <span class="col w-desc muted">{{ r.actionDescription || '-' }}</span>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无记录') }}</div>
      </div>
    </div>

    <div class="card" v-if="!plans.length && !error"><div class="flex center" style="padding:40px"><span class="muted">{{ tl('common.loading') }}</span></div></div>
    <div class="card" v-if="error"><div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('common.error') }}: {{ error }}</span></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getMaintenancePlans, getMaintenanceRecords, getMaintenanceStats, type PlanView, type RecordView, type MaintenanceStats } from '@/api/maintenance'
const { t: tl } = useI18n()

const plans = ref<PlanView[]>([])
const records = ref<RecordView[]>([])
const stats = ref<MaintenanceStats | null>(null)
const error = ref('')
const selectedPlanId = ref<number | null>(null)
const selectedPlanName = ref('')

function freqLabel(f: string) { const m: Record<string, string> = { daily: '天', weekly: '周', monthly: '月', quarterly: '季', yearly: '年' }; return m[f] || f }
function freqCls(f: string) { return f === 'daily' ? 'a' : f === 'weekly' ? 'b' : '' }
function fmtDate(d: string | null) { if (!d) return '-'; return d }
function isOverdue(d: string | null) { if (!d) return false; return new Date(d) < new Date() }

async function selectPlan(id: number) {
  if (selectedPlanId.value === id) { selectedPlanId.value = null; selectedPlanName.value = ''; }
  else { selectedPlanId.value = id; const p = plans.value.find(x => x.id === id); selectedPlanName.value = p?.name ?? ''; }
  records.value = await getMaintenanceRecords(selectedPlanId.value ?? undefined)
}

async function load() {
  error.value = ''
  try {
    const [p, s] = await Promise.all([getMaintenancePlans(), getMaintenanceStats()])
    plans.value = p; stats.value = s
    if (p.length) { selectedPlanId.value = p[0].id; selectedPlanName.value = p[0].name; records.value = await getMaintenanceRecords(p[0].id) }
  } catch (e: any) { error.value = e?.message || String(e) }
}
onMounted(load)
</script>

<style scoped>
.section-title { margin: 0 0 12px; font-size: 14px; font-weight: 600; }
.plan-list { max-height: 360px; overflow-y: auto; }
.plan-row { padding: 10px 8px; cursor: pointer; border-radius: 6px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.plan-row:hover { background: var(--bg2); }
.plan-row.sel { background: rgba(64,150,255,0.08); border-left: 3px solid var(--blue); }
.p-name { font-weight: 500; font-size: 13px; }
.p-code { color: var(--muted); font-size: 11px; margin-left: 8px; }
.p-meta { font-size: 11.5px; margin-top: 4px; display: flex; gap: 8px; align-items: center; }
.p-eq { color: var(--blue); }
.pill-tag { font-size: 10.5px; padding: 1px 8px; border-radius: 9px; background: var(--bg2); }
.pill-tag.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill-tag.a { background: rgba(250,173,20,0.12); color: var(--amber); }
.pill-tag.r { background: rgba(255,77,79,0.12); color: var(--red); }
.pill-tag.b { background: rgba(64,150,255,0.12); color: var(--blue); }
.tbl { max-height: 330px; overflow-y: auto; }
.tbl-head, .tbl-row { display: flex; align-items: center; padding: 9px 6px; font-size: 12.5px; }
.tbl-head { font-weight: 600; color: var(--muted); border-bottom: 2px solid var(--border); font-size: 12px; }
.tbl-row { border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.col { flex-shrink: 0; }
.w-by { width: 70px; } .w-time { width: 170px; } .w-stat { width: 70px; } .w-res { width: 60px; } .w-desc { flex: 1; }
.empty { text-align: center; padding: 32px; color: var(--muted); font-size: 13px; }
.muted { color: var(--muted); }
</style>
