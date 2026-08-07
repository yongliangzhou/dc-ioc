<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.drill') }}</h1>
      <span class="sub">{{ tl('应急预案与演练评估') }}</span>
    </div>
    <div class="grid cols-5" v-if="stats">
      <MetricCard
        metric-name="drill-plans"
        :label="tl('演练方案')"
        :value="stats.totalPlans"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="drill-records"
        :label="tl('演练次数')"
        :value="stats.totalRecords"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="drill-avg"
        :label="tl('平均分')"
        :value="Number(stats.avgScore.toFixed(1))"
        unit="分"
        :quality="stats.avgScore >= 80 ? 'good' : 'uncertain'"
        :online="true"
      />
      <MetricCard
        metric-name="drill-pass"
        :label="tl('通过')"
        :value="stats.passedCount"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="drill-fail"
        :label="tl('未通过')"
        :value="stats.failedCount"
        :quality="stats.failedCount ? 'bad' : 'good'"
        :severity="stats.failedCount ? 'crit' : 'normal'"
        :online="true"
      />
    </div>
    <div class="grid cols-4-6" style="margin-top: 16px">
      <Panel
        ><div class="panel-head">
          <h5 class="section-title">{{ tl('演练方案') }}</h5>
          <button class="btn-sm primary" v-bind="authState('write')" @click="openPlanCreate">
            {{ tl('新建') }}
          </button>
        </div>
        <div class="p-list" v-if="plans.length">
          <div
            v-for="p in plans"
            :key="p.id"
            class="p-row"
            :class="{ sel: selId === p.id }"
            @click="sel(p.id)"
          >
            <div class="p-info">
              <span class="p-n">{{ p.name }}</span
              ><span class="p-c">{{ p.code }}</span>
            </div>
            <div class="p-m">
              <span class="pill-tag b">{{ p.scenario }}</span
              ><span class="muted">{{ p.participants || '-' }}</span>
            </div>
            <div class="p-ops" @click.stop>
              <button class="link" v-bind="authState('write')" @click="openPlanEdit(p)">{{ tl('编辑') }}</button>
              <button class="link danger" v-bind="authState('write')" @click="removePlan(p)">{{ tl('删除') }}</button>
            </div>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无方案') }}</div>
      </Panel>
      <Panel
        ><div class="panel-head">
          <h5 class="section-title">{{ selName || tl('演练记录') }}</h5>
          <button class="btn-sm primary" v-bind="authState('write')" :disabled="!selId" @click="openRecCreate">
            {{ tl('录入') }}
          </button>
        </div>
        <div class="tbl" v-if="records.length">
          <div class="tbl-head">
            <span class="col w-drill-by">{{ tl('执行人') }}</span
            ><span class="col w-drill-time">{{ tl('时间') }}</span
            ><span class="col w-drill-score">{{ tl('评分') }}</span
            ><span class="col w-drill-result">{{ tl('结果') }}</span
            ><span class="col w-drill-op">{{ tl('操作') }}</span>
          </div>
          <div v-for="r in records" :key="r.id" class="tbl-row">
            <span class="col w-drill-by">{{ r.executedBy }}</span
            ><span class="col w-drill-time muted">{{ r.startedAt }}</span
            ><span
              class="col w-drill-score"
              :style="{ color: r.score != null && r.score >= 80 ? 'var(--green)' : 'var(--red)' }"
              >{{ r.score || '-' }}</span
            ><span class="col w-drill-result"
              ><span class="pill-tag" :class="r.result === 'pass' ? 'g' : 'r'">{{
                r.result || '-'
              }}</span></span
            >
            <span class="col w-drill-op p-ops">
              <button class="link" v-bind="authState('write')" @click="openRecEdit(r)">{{ tl('编辑') }}</button>
              <button class="link danger" v-bind="authState('write')" @click="removeRec(r)">{{ tl('删除') }}</button>
            </span>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无记录') }}</div>
      </Panel>
    </div>

    <!-- 方案抽屉 -->
    <div class="drawer-mask" v-if="planDrawer" @click.self="planDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ planForm.id ? tl('编辑演练方案') : tl('新建演练方案') }}</span>
          <button class="x" @click="planDrawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('方案编码') }}
            <input v-model.trim="planForm.code" class="ipt" :placeholder="tl('留空自动生成')" />
          </label>
          <label>{{ tl('方案名称') }}
            <input v-model.trim="planForm.name" class="ipt" :placeholder="tl('如 市电失电应急演练')" />
          </label>
          <div class="row">
            <label>{{ tl('类型') }}
              <select v-model="planForm.type" class="ipt">
                <option value="电力">电力</option>
                <option value="暖通">暖通</option>
                <option value="消防">消防</option>
                <option value="网络">网络</option>
                <option value="综合">综合</option>
              </select>
            </label>
            <label>{{ tl('状态') }}
              <select v-model="planForm.state" class="ipt">
                <option value="计划中">计划中</option>
                <option value="进行中">进行中</option>
                <option value="已完成">已完成</option>
              </select>
            </label>
          </div>
          <label>{{ tl('计划日期') }}
            <input v-model.trim="planForm.date" class="ipt" type="date" />
          </label>
          <label>{{ tl('备注') }}
            <textarea v-model.trim="planForm.note" class="ipt" rows="2"></textarea>
          </label>
          <div v-if="planErr" class="err">{{ planErr }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="planDrawer = false">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="planSaving" @click="savePlan">
              {{ planSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 记录抽屉 -->
    <div class="drawer-mask" v-if="recDrawer" @click.self="recDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ recForm.id ? tl('编辑演练记录') : tl('录入演练记录') }}</span>
          <button class="x" @click="recDrawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('执行人') }}
            <input v-model.trim="recForm.executedBy" class="ipt" :placeholder="tl('如 张三')" />
          </label>
          <div class="row">
            <label>{{ tl('评分') }}
              <input v-model.number="recForm.score" class="ipt" type="number" min="0" max="100" />
            </label>
            <label>{{ tl('结果') }}
              <select v-model="recForm.result" class="ipt">
                <option value="pass">通过</option>
                <option value="fail">未通过</option>
                <option value="partial">部分通过</option>
              </select>
            </label>
          </div>
          <label>{{ tl('开始时间') }}
            <input v-model.trim="recForm.startedAt" class="ipt" type="datetime-local" />
          </label>
          <label>{{ tl('备注') }}
            <textarea v-model.trim="recForm.notes" class="ipt" rows="2"></textarea>
          </label>
          <div v-if="recErr" class="err">{{ recErr }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="recDrawer = false">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="recSaving" @click="saveRec">
              {{ recSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <Panel v-if="!plans.length && !e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div></Panel
    >
    <Panel v-if="e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ e }}</span>
      </div></Panel
    >
  </div>
</template>
<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import {
  getDrillPlans,
  getDrillRecords,
  getDrillStats,
  createDrillPlan,
  updateDrillPlan,
  deleteDrillPlan,
  createDrillRecord,
  updateDrillRecord,
  deleteDrillRecord,
  type DrillPlanView,
  type DrillRecordView,
  type DrillStats,
  type DrillPlanCreate,
  type DrillRecordCreate,
} from '@/api/drill'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'
const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}
const plans = ref<DrillPlanView[]>([])
const records = ref<DrillRecordView[]>([])
const stats = ref<DrillStats | null>(null)
const e = ref('')
const selId = ref<number | null>(null)
const selName = ref('')

// 方案抽屉
const planDrawer = ref(false)
const planSaving = ref(false)
const planErr = ref('')
const planForm = ref<Partial<DrillPlanView> & DrillPlanCreate>({
  code: '', name: '', type: '电力', date: '', state: '计划中', note: '',
})
// 记录抽屉
const recDrawer = ref(false)
const recSaving = ref(false)
const recErr = ref('')
const recForm = ref<Partial<DrillRecordView> & DrillRecordCreate>({
  executedBy: '', score: null, result: 'pass', startedAt: '', notes: '',
})

async function sel(id: number) {
  selId.value = selId.value === id ? null : id
  selName.value = plans.value.find((x) => x.id === id)?.name ?? ''
  records.value = await getDrillRecords(selId.value ?? undefined)
}

function openPlanCreate() {
  planForm.value = { code: '', name: '', type: '电力', date: '', state: '计划中', note: '' }
  planErr.value = ''
  planDrawer.value = true
}
function openPlanEdit(p: DrillPlanView) {
  planForm.value = {
    id: p.id, code: p.code, name: p.name,
    type: p.scenario, date: '', state: p.state ?? '计划中', note: p.description ?? '',
  }
  planErr.value = ''
  planDrawer.value = true
}
async function savePlan() {
  const f = planForm.value
  if (!f.name) {
    planErr.value = tl('方案名称为必填')
    return
  }
  planSaving.value = true
  planErr.value = ''
  try {
    const payload: DrillPlanCreate = {
      code: f.code || undefined,
      name: f.name,
      type: f.type || '电力',
      date: (f.date || '').split('T')[0],
      state: f.state || '计划中',
      note: f.note || '',
    }
    if (f.id != null) await updateDrillPlan(f.id, payload)
    else await createDrillPlan(payload)
    planDrawer.value = false
    await load()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    planErr.value = (ex as ErrorLike)?.message || tl('保存失败')
  } finally {
    planSaving.value = false
  }
}
async function removePlan(p: DrillPlanView) {
  const ok = await useConfirm({
    title: tl('删除演练方案'),
    message: `${tl('确认删除方案')} ${p.name}?`,
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => { await deleteDrillPlan(p.id) },
  })
  if (ok) {
    if (selId.value === p.id) { selId.value = null; records.value = [] }
    await load()
    toast.success(tl('已删除'))
  }
}

function openRecCreate() {
  recForm.value = { executedBy: '', score: null, result: 'pass', startedAt: '', notes: '' }
  recErr.value = ''
  recDrawer.value = true
}
function openRecEdit(r: DrillRecordView) {
  recForm.value = {
    id: r.id, executedBy: r.executedBy, score: r.score, result: r.result ?? 'pass',
    startedAt: (r.startedAt || '').replace(' ', 'T'), notes: r.notes ?? '',
  }
  recErr.value = ''
  recDrawer.value = true
}
async function saveRec() {
  const f = recForm.value
  if (!f.executedBy) {
    recErr.value = tl('执行人为必填')
    return
  }
  recSaving.value = true
  recErr.value = ''
  try {
    const payload: DrillRecordCreate = {
      planId: selId.value ?? undefined,
      planName: selName.value,
      executedBy: f.executedBy,
      score: f.score ?? undefined,
      result: f.result || 'pass',
      startedAt: (f.startedAt || '').replace('T', ' '),
      notes: f.notes || '',
    }
    if (f.id != null) await updateDrillRecord(f.id, payload)
    else await createDrillRecord(payload)
    recDrawer.value = false
    records.value = await getDrillRecords(selId.value ?? undefined)
    await load()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    recErr.value = (ex as ErrorLike)?.message || tl('保存失败')
  } finally {
    recSaving.value = false
  }
}
async function removeRec(r: DrillRecordView) {
  const ok = await useConfirm({
    title: tl('删除演练记录'),
    message: tl('确认删除该演练记录?'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => { await deleteDrillRecord(r.id) },
  })
  if (ok) {
    records.value = await getDrillRecords(selId.value ?? undefined)
    await load()
    toast.success(tl('已删除'))
  }
}

async function load() {
  try {
    const [p, s] = await Promise.all([getDrillPlans(), getDrillStats()])
    plans.value = p
    stats.value = s
    if (p.length && (selId.value == null || !p.find((x) => x.id === selId.value))) {
      selId.value = p[0].id
      selName.value = p[0].name
      records.value = await getDrillRecords(p[0].id)
    } else if (selId.value != null) {
      records.value = await getDrillRecords(selId.value)
    }
  } catch (ex: unknown) {
    e.value = (ex as ErrorLike)?.message || String(ex)
  }
}
onMounted(load)
</script>
<style scoped>
.p-list {
  max-height: 360px;
  overflow-y: auto;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.p-row {
  padding: 10px 8px;
  cursor: pointer;
  border-radius: 6px;
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.p-row:hover {
  background: var(--bg2);
}
.p-row.sel {
  background: rgba(64, 150, 255, 0.08);
  border-left: 3px solid var(--blue);
}
.p-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.p-ops {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.p-n {
  font-weight: 500;
  font-size: 13px;
}
.p-c {
  color: var(--muted);
  font-size: 11px;
  margin-left: 8px;
}
.p-m {
  font-size: 11.5px;
  margin-top: 4px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
}
.pill-tag.g {
  background: rgba(82, 196, 26, 0.12);
  color: var(--green);
}
.pill-tag.r {
  background: rgba(255, 77, 79, 0.12);
  color: var(--red);
}
.pill-tag.b {
  background: rgba(64, 150, 255, 0.12);
  color: var(--blue);
}
.tbl {
  max-height: 330px;
  overflow-y: auto;
}
.tbl-head,
.tbl-row {
  display: flex;
  align-items: center;
  padding: 9px 6px;
  font-size: 12.5px;
}
.tbl-head {
  font-weight: 600;
  color: var(--muted);
  border-bottom: 2px solid var(--border);
  font-size: 12px;
}
.tbl-row {
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.col {
  flex-shrink: 0;
}
.w-drill-by {
  width: 80px;
}
.w-drill-time {
  width: 170px;
}
.w-drill-score {
  width: 60px;
}
.w-drill-result {
  width: 60px;
}
.w-drill-op {
  width: 100px;
}
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text2);
  cursor: pointer;
  font-size: 12px;
}
.btn-sm.primary {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
  font-weight: 600;
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
.link {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.link.danger {
  color: var(--red);
}
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 40;
}
.drawer {
  width: 420px;
  max-width: 92vw;
  background: var(--card-bg);
  height: 100%;
  padding: 18px;
  overflow: auto;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.3);
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}
.x {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text2);
}
.ipt {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
}
.err {
  color: var(--red);
  font-size: 12px;
}
.drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
}
</style>
