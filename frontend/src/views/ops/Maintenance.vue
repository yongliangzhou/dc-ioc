<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.maintain') }}</h1>
      <span class="sub">{{ tl('维保计划与执行日历') }}</span>
    </div>

    <AsyncSection :page="page" @retry="page.reload">
      <div class="grid cols-5" v-if="stats">
      <MetricCard
        metric-name="mnt-plans"
        :label="tl('维保计划')"
        :value="stats.totalPlans"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="mnt-active"
        :label="tl('进行中')"
        :value="stats.activePlans"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="mnt-overdue"
        :label="tl('逾期')"
        :value="stats.overduePlans"
        unit="项"
        :quality="stats.overduePlans ? 'bad' : 'good'"
        :severity="stats.overduePlans ? 'crit' : 'normal'"
        :online="true"
      />
      <MetricCard
        metric-name="mnt-records"
        :label="tl('执行记录')"
        :value="stats.totalRecords"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="mnt-completed"
        :label="tl('已完成')"
        :value="stats.completedRecords"
        unit="条"
        quality="good"
        :online="true"
      />
    </div>

    <div class="grid cols-4-6" style="margin-top: 16px">
      <!-- 维保计划 -->
      <Panel>
        <div class="panel-head">
          <h5 class="section-title">{{ tl('维保计划') }}</h5>
          <button class="btn-sm primary" v-bind="authState('write')" @click="openPlanCreate">
            {{ tl('新建计划') }}
          </button>
        </div>
        <div class="plan-list" v-if="plans.length">
          <div
            v-for="p in plans"
            :key="p.id"
            class="plan-row"
            :class="{ sel: selectedPlanId === p.id }"
            @click="selectPlan(p.id)"
          >
            <div class="p-top">
              <div>
                <span class="p-name">{{ p.name }}</span>
                <span class="p-code">{{ p.code }}</span>
              </div>
              <span class="pill-tag" :class="p.status === 'active' ? 'b' : p.status === 'paused' ? 'a' : ''">
                {{ statusLabel(p.status) }}
              </span>
            </div>
            <div class="p-meta">
              <span class="p-eq">{{ p.equipmentCode }}</span>
              <span class="pill-tag" :class="freqCls(p.frequency)">{{
                freqLabel(p.frequency)
              }}</span>
              <span class="pill-tag" :class="p.overdue ? 'r' : 'g'">
                {{ fmtDate(p.nextDueDate) }}
              </span>
              <span class="p-ops" @click.stop>
                <button class="link" v-bind="authState('write')" @click="openPlanEdit(p)">{{ tl('编辑') }}</button>
                <button class="link danger" v-bind="authState('write')" @click="removePlan(p)">{{ tl('删除') }}</button>
              </span>
            </div>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无计划, 点击右上角新建') }}</div>
      </Panel>

      <!-- 执行记录 -->
      <Panel>
        <div class="panel-head">
          <h5 class="section-title">{{ selectedPlanName || tl('执行记录') }}</h5>
          <button class="btn-sm primary" v-bind="authState('write')" @click="openRecCreate">
            {{ tl('录入记录') }}
          </button>
        </div>
        <div class="tbl" v-if="records.length">
          <div class="tbl-head">
            <span class="col w-by">{{ tl('维保人') }}</span>
            <span class="col w-time">{{ tl('时间') }}</span>
            <span class="col w-stat">{{ tl('状态') }}</span>
            <span class="col w-res">{{ tl('结果') }}</span>
            <span class="col w-desc">{{ tl('内容') }}</span>
            <span class="col w-op">{{ tl('操作') }}</span>
          </div>
          <div v-for="r in records" :key="r.id" class="tbl-row">
            <span class="col w-by">{{ r.maintainedBy }}</span>
            <span class="col w-time muted">{{ r.startedAt }}</span>
            <span class="col w-stat"
              ><span class="pill-tag" :class="r.status === 'completed' ? 'g' : 'a'">{{
                r.status === 'completed' ? tl('已完成') : tl('进行中')
              }}</span></span
            >
            <span class="col w-res"
              ><span class="pill-tag" :class="r.result === 'pass' ? 'g' : 'r'">{{
                r.result || '-'
              }}</span></span
            >
            <span class="col w-desc muted">{{ r.actionDescription || '-' }}</span>
            <span class="col w-op p-ops">
              <button class="link" v-bind="authState('write')" @click="openRecEdit(r)">{{ tl('编辑') }}</button>
              <button class="link danger" v-bind="authState('write')" @click="removeRec(r)">{{ tl('删除') }}</button>
            </span>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无记录') }}</div>
      </Panel>
    </div>
    </AsyncSection>

    <!-- 执行记录抽屉 -->
    <div class="drawer-mask" v-if="recDrawer" @click.self="recDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ recForm.id ? tl('编辑维保记录') : tl('录入维保记录') }}</span>
          <button class="x" @click="recDrawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('维保人') }}
            <input v-model.trim="recForm.maintainedBy" class="ipt" :placeholder="tl('如 李四')" />
          </label>
          <div class="row">
            <label>{{ tl('状态') }}
              <select v-model="recForm.status" class="ipt">
                <option value="completed">{{ tl('已完成') }}</option>
                <option value="in_progress">{{ tl('进行中') }}</option>
              </select>
            </label>
            <label>{{ tl('结果') }}
              <select v-model="recForm.result" class="ipt">
                <option value="pass">{{ tl('合格') }}</option>
                <option value="fail">{{ tl('不合格') }}</option>
                <option value="partial">{{ tl('部分合格') }}</option>
              </select>
            </label>
          </div>
          <label>{{ tl('开始时间') }}
            <input v-model.trim="recForm.startedAt" class="ipt" type="datetime-local" />
          </label>
          <label>{{ tl('维保内容') }}
            <textarea v-model.trim="recForm.actionDescription" class="ipt" rows="2"></textarea>
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

    <!-- 计划抽屉 -->
    <div class="drawer-mask" v-if="planDrawer" @click.self="planDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ planForm.id ? tl('编辑维保计划') : tl('新建维保计划') }}</span>
          <button class="x" @click="planDrawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('计划编号') }}
            <input v-model.trim="planForm.code" class="ipt" :placeholder="tl('留空自动生成 PM-xxxxxx')" />
          </label>
          <label>{{ tl('计划名称') }}
            <input v-model.trim="planForm.name" class="ipt" :placeholder="tl('如 机房空调季度保养')" />
          </label>
          <label>{{ tl('关联设备') }}
            <input v-model.trim="planForm.equipmentCode" class="ipt" :placeholder="tl('设备编号, 选填')" />
          </label>
          <div class="row">
            <label>{{ tl('周期') }}
              <select v-model="planForm.frequency" class="ipt">
                <option value="daily">{{ tl('日') }}</option>
                <option value="weekly">{{ tl('周') }}</option>
                <option value="monthly">{{ tl('月') }}</option>
                <option value="quarterly">{{ tl('季') }}</option>
                <option value="yearly">{{ tl('年') }}</option>
              </select>
            </label>
            <label>{{ tl('状态') }}
              <select v-model="planForm.status" class="ipt">
                <option value="active">{{ tl('启用') }}</option>
                <option value="paused">{{ tl('暂停') }}</option>
                <option value="done">{{ tl('已完成') }}</option>
              </select>
            </label>
          </div>
          <label>{{ tl('责任人') }}
            <input v-model.trim="planForm.owner" class="ipt" :placeholder="tl('如 王工')" />
          </label>
          <label>{{ tl('下次到期') }}
            <input v-model.trim="planForm.nextDueDate" class="ipt" type="datetime-local" />
          </label>
          <label>{{ tl('说明') }}
            <textarea v-model.trim="planForm.description" class="ipt" rows="2"></textarea>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import {
  getMaintenancePlanList,
  getMaintenanceRecords,
  getMaintenanceStats,
  createMaintenanceRecord,
  updateMaintenanceRecord,
  deleteMaintenanceRecord,
  createMaintenancePlan,
  updateMaintenancePlan,
  deleteMaintenancePlan,
  type PlanView,
  type RecordView,
  type MaintenanceStats,
  type RecordCreate,
  type PlanCreate,
} from '@/api/maintenance'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'
const { t: tl } = useI18n()
const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const plans = ref<PlanView[]>([])
const records = ref<RecordView[]>([])
const stats = ref<MaintenanceStats | null>(null)
const selectedPlanId = ref<number | string | null>(null)
const selectedPlanName = ref('')

// 记录抽屉
const recDrawer = ref(false)
const recSaving = ref(false)
const recErr = ref('')
const recForm = ref<Partial<RecordView> & RecordCreate>({
  maintainedBy: '', status: 'completed', result: 'pass', startedAt: '', actionDescription: '', notes: '',
})

function freqLabel(f: string) {
  const m: Record<string, string> = {
    daily: '天',
    weekly: '周',
    monthly: '月',
    quarterly: '季',
    yearly: '年',
  }
  return m[f] || f
}
function freqCls(f: string) {
  return f === 'daily' ? 'a' : f === 'weekly' ? 'b' : ''
}
function statusLabel(s: string) {
  const m: Record<string, string> = {
    active: '启用',
    paused: '暂停',
    done: '已完成',
  }
  return m[s] || s
}
function fmtDate(d: string | null) {
  if (!d) return '-'
  return d
}

function openRecCreate() {
  recForm.value = {
    maintainedBy: '', status: 'completed', result: 'pass',
    startedAt: '', actionDescription: '', notes: '',
  }
  recErr.value = ''
  recDrawer.value = true
}
function openRecEdit(r: RecordView) {
  recForm.value = {
    id: r.id,
    maintainedBy: r.maintainedBy,
    status: r.status,
    result: r.result ?? 'pass',
    startedAt: (r.startedAt || '').replace(' ', 'T'),
    actionDescription: r.actionDescription ?? '',
    notes: r.notes ?? '',
  }
  recErr.value = ''
  recDrawer.value = true
}
async function saveRec() {
  const f = recForm.value
  if (!f.maintainedBy) {
    recErr.value = tl('维保人为必填')
    return
  }
  recSaving.value = true
  recErr.value = ''
  try {
    const payload: RecordCreate = {
      planCode: selectedPlanId.value ? `PM-${selectedPlanId.value}` : undefined,
      planName: selectedPlanName.value,
      maintainedBy: f.maintainedBy,
      status: f.status || 'completed',
      result: f.result || 'pass',
      startedAt: (f.startedAt || '').replace('T', ' '),
      actionDescription: f.actionDescription || '',
      notes: f.notes || '',
    }
    if (f.id != null) await updateMaintenanceRecord(f.id, payload)
    else await createMaintenanceRecord(payload)
    recDrawer.value = false
    records.value = await getMaintenanceRecords(selectedPlanId.value ?? undefined)
    await page.reload()
    toast.success(tl('已保存'))
  } catch (e: unknown) {
    recErr.value = toErrorMessage(e) || tl('保存失败')
  } finally {
    recSaving.value = false
  }
}
async function removeRec(r: RecordView) {
  const ok = await useConfirm({
    title: tl('删除维保记录'),
    message: tl('确认删除该维保记录?'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => { await deleteMaintenanceRecord(r.id) },
  })
  if (ok) {
    records.value = await getMaintenanceRecords(selectedPlanId.value ?? undefined)
    await page.reload()
    toast.success(tl('已删除'))
  }
}

// 计划抽屉
const planDrawer = ref(false)
const planSaving = ref(false)
const planErr = ref('')
const planForm = ref<Partial<PlanView> & PlanCreate>({
  code: '', name: '', equipmentCode: '', description: '', frequency: 'monthly', nextDueDate: '', status: 'active', owner: '',
})

function openPlanCreate() {
  planForm.value = { code: '', name: '', equipmentCode: '', description: '', frequency: 'monthly', nextDueDate: '', status: 'active', owner: '' }
  planErr.value = ''
  planDrawer.value = true
}
function openPlanEdit(p: PlanView) {
  planForm.value = {
    id: Number(p.id), code: p.code, name: p.name, equipmentCode: p.equipmentCode,
    description: p.description ?? '', frequency: p.frequency, nextDueDate: p.nextDueDate ?? '',
    status: p.status, owner: p.owner,
  }
  planErr.value = ''
  planDrawer.value = true
}
async function savePlan() {
  const f = planForm.value
  if (!f.name) {
    planErr.value = tl('计划名称为必填')
    return
  }
  planSaving.value = true
  planErr.value = ''
  try {
    const payload: PlanCreate = {
      code: f.code || `PM-${Date.now().toString().slice(-6)}`,
      name: f.name,
      equipmentCode: f.equipmentCode || '',
      description: f.description || '',
      frequency: f.frequency || 'monthly',
      nextDueDate: (f.nextDueDate || '').replace('T', ' '),
      status: f.status || 'active',
      owner: f.owner || '',
    }
    if (f.id != null) await updateMaintenancePlan(Number(f.id), payload)
    else await createMaintenancePlan(payload)
    planDrawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (e: unknown) {
    planErr.value = toErrorMessage(e) || tl('保存失败')
  } finally {
    planSaving.value = false
  }
}
async function removePlan(p: PlanView) {
  const ok = await useConfirm({
    title: tl('删除维保计划'),
    message: tl('确认删除该维保计划? 已产生的执行记录不会被删除。'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => { await deleteMaintenancePlan(Number(p.id)) },
  })
  if (ok) {
    await page.reload()
    toast.success(tl('已删除'))
  }
}

async function selectPlan(id: number | string) {
  if (selectedPlanId.value === id) {
    selectedPlanId.value = null
    selectedPlanName.value = ''
  } else {
    selectedPlanId.value = id
    const p = plans.value.find((x) => x.id === id)
    selectedPlanName.value = p?.name ?? ''
  }
  records.value = await getMaintenanceRecords(selectedPlanId.value ?? undefined)
}

const page = useAsyncPage<PlanView[]>(
  async () => {
    const [p, s] = await Promise.all([getMaintenancePlanList(), getMaintenanceStats()])
    plans.value = p
    stats.value = s
    if (p.length) {
      if (selectedPlanId.value == null || !p.find((x) => x.id === selectedPlanId.value)) {
        selectedPlanId.value = p[0].id
        selectedPlanName.value = p[0].name
      }
      records.value = await getMaintenanceRecords(`PM-${selectedPlanId.value}`)
    }
    return plans.value
  },
  { isEmpty: (d) => !d || d.length === 0 },
)
</script>

<style scoped>
.plan-list {
  max-height: 360px;
  overflow-y: auto;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.p-ops {
  display: flex;
  gap: 8px;
}
.plan-row {
  padding: 10px 8px;
  cursor: pointer;
  border-radius: 6px;
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.plan-row:hover {
  background: var(--bg2);
}
.plan-row.sel {
  background: rgba(64, 150, 255, 0.08);
  border-left: 3px solid var(--blue);
}
.p-name {
  font-weight: 500;
  font-size: 13px;
}
.p-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.p-ops {
  display: flex;
  gap: 8px;
}
.p-code {
  color: var(--muted);
  font-size: 11px;
  margin-left: 8px;
}
.p-meta {
  font-size: 11.5px;
  margin-top: 4px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.p-eq {
  color: var(--blue);
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
.pill-tag.a {
  background: rgba(250, 173, 20, 0.12);
  color: var(--amber);
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
.w-by {
  width: 70px;
}
.w-time {
  width: 170px;
}
.w-stat {
  width: 70px;
}
.w-res {
  width: 60px;
}
.w-desc {
  flex: 1;
}
.w-op {
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
