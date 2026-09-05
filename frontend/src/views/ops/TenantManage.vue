<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { getTenants, getTenantStats, createTenant, updateTenant, deleteTenant } from '../../api'
import type { TenantItem, TenantStats } from '../../types'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import AsyncSection from '@/components/common/AsyncSection.vue'

const { t } = useI18n()
const toast = useToast()

const tenants = ref<TenantItem[]>([])
const stats = ref<TenantStats | null>(null)
const total = ref(0)
const kw = ref('')
const statusFilter = ref('')

const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref<any>({})
/** 表单字段级错误 (提交前前端校验, 避免仅靠后端 422 兜底) */
const formErrs = ref<Record<string, string>>({})

const detailVisible = ref(false)
const detail = ref<TenantItem | null>(null)

const statusOptions = [
  { value: '', label: t('tenantManage.filterStatus') },
  { value: 'active', label: t('tenantManage.stActive') },
  { value: 'pending', label: t('tenantManage.stPending') },
  { value: 'expired', label: t('tenantManage.stExpired') },
]

const statusClass = (s: string) =>
  s === 'active' ? 'st-active' : s === 'pending' ? 'st-pending' : 'st-expired'

const healthClass = (h: string) =>
  h === 'over' ? 'hz-over' : h === 'warn' ? 'hz-warn' : 'hz-normal'

const healthLabel = (h: string) =>
  h === 'over'
    ? t('tenantManage.healthOver')
    : h === 'warn'
      ? t('tenantManage.healthWarn')
      : t('tenantManage.healthNormal')

const pct = (used: number, quota: number) =>
  quota ? Math.min(100, Math.round((used / quota) * 100)) : 0

const quotaBars = (tn: TenantItem) => [
  { label: t('tenantManage.usageCabinets'), used: tn.cabinets, quota: tn.quotaCabinets },
  { label: t('tenantManage.usageDevices'), used: tn.usedDevices, quota: tn.quotaDevices },
  { label: t('tenantManage.usagePower'), used: tn.usedPowerKw, quota: tn.quotaPowerKw },
  {
    label: t('tenantManage.usageBandwidth'),
    used: tn.usedBandwidthMbps,
    quota: tn.quotaBandwidthMbps,
  },
]

const barColor = (used: number, quota: number) => {
  if (!quota) return 'bg-slate-500'
  const r = used / quota
  if (r >= 1) return 'bg-rose-500'
  if (r >= 0.8) return 'bg-amber-500'
  return 'bg-emerald-500'
}

const totalRacks = computed(() => stats.value?.totalCabinets ?? 0)
const totalCap = 60 // 机房机柜总容量 (演示基线)
const occupancy = computed(() => (totalCap ? Math.round((totalRacks.value / totalCap) * 100) : 0))

const page = useAsyncPage<TenantItem[]>(
  async () => {
    const [listRes, statRes] = await Promise.all([
      getTenants(kw.value, statusFilter.value),
      getTenantStats(),
    ])
    tenants.value = (listRes.tenants || []) as TenantItem[]
    total.value = listRes.total ?? tenants.value.length
    stats.value = statRes
    return tenants.value
  },
  { isEmpty: (d) => !d || d.length === 0 },
)

function openAdd() {
  dialogMode.value = 'add'
  editingId.value = null
  form.value = {
    name: '',
    code: '',
    contact: '',
    phone: '',
    industry: '',
    contractNo: '',
    validFrom: '',
    validTo: '',
    status: 'active',
    rent: 0,
    cabinets: 0,
    quotaCabinets: 0,
    quotaDevices: 0,
    quotaPowerKw: 0,
    quotaBandwidthMbps: 0,
    usedDevices: 0,
    usedPowerKw: 0,
    usedBandwidthMbps: 0,
    uOccupied: 0,
    note: '',
  }
  formErrs.value = {}
  dialogVisible.value = true
}

function openEdit(tn: TenantItem) {
  dialogMode.value = 'edit'
  editingId.value = tn.id
  form.value = { ...tn }
  formErrs.value = {}
  dialogVisible.value = true
}

/** 提交前校验必填字段; 通过返回 true, 否则展示字段级错误 */
function validateForm(): boolean {
  const errs: Record<string, string> = {}
  if (!String(form.value.name ?? '').trim()) errs.name = t('tenantManage.nameRequired')
  formErrs.value = errs
  return Object.keys(errs).length === 0
}

async function save() {
  if (saving.value) return
  if (!validateForm()) return
  saving.value = true
  try {
    if (dialogMode.value === 'add') {
      await createTenant(form.value)
      toast.success(t('tenantManage.addSuccess'))
    } else {
      await updateTenant(editingId.value!, form.value)
      toast.success(t('tenantManage.updateSuccess'))
    }
    dialogVisible.value = false
    await page.reload()
  } catch (e) {
    toast.error(toErrorMessage(e, t('tenantManage.saveFailed')))
  } finally {
    saving.value = false
  }
}

async function remove(tn: TenantItem) {
  if (!(await useConfirm({ message: t('tenantManage.confirmDelete'), danger: true }))) return
  try {
    await deleteTenant(tn.id)
    toast.success(t('tenantManage.deleteSuccess'))
    await page.reload()
  } catch (e) {
    toast.error(toErrorMessage(e, t('tenantManage.deleteFailed')))
  }
}

function openDetail(tn: TenantItem) {
  detail.value = tn
  detailVisible.value = true
}

onMounted(() => page.reload())
</script>

<template>
  <div class="tm-page">
    <div class="tm-head">
      <div>
        <h2 class="tm-title">{{ t('tenantManage.title') }}</h2>
        <p class="tm-sub">{{ t('tenantManage.sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">+ {{ t('tenantManage.newTenant') }}</button>
    </div>

    <!-- 统计卡 (真实聚合) -->
    <div class="stat-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-val">{{ stats.total }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statTotal') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-val text-emerald-500">{{ stats.active }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statActive') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">{{ stats.totalCabinets }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statCabinets') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">{{ stats.totalPowerKw }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statPower') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-val text-amber-500">{{ stats.warnCount }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statWarn') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-val text-rose-500">{{ stats.overCount }}</div>
        <div class="stat-lbl">{{ t('tenantManage.statOver') }}</div>
      </div>
    </div>

    <!-- 出租率 -->
    <div class="occ-card">
      <div class="occ-head">
        <span>{{ t('tenantManage.occTitle') }}</span>
        <span class="occ-num">{{ occupancy }}%</span>
      </div>
      <div class="occ-bar"><div class="occ-fill" :style="{ width: occupancy + '%' }"></div></div>
      <div class="occ-legend">
        <span class="dot leased"></span>{{ t('tenantManage.leased') }} {{ totalRacks }}
        {{ t('tenantManage.racks') }} <span class="dot empty"></span>{{ t('tenantManage.empty') }}
        {{ totalCap - totalRacks }}
      </div>
    </div>

    <!-- 过滤 + 列表 -->
    <div class="tm-toolbar">
      <input
        class="inp"
        :placeholder="t('tenantManage.search')"
        v-model="kw"
        @input="page.reload"
      />
      <select class="inp" v-model="statusFilter" @change="page.reload">
        <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>

    <AsyncSection :page="page" @retry="page.reload">
      <div class="tm-grid">
        <div
          v-for="tn in tenants"
          :key="tn.id"
          class="tn-card"
          :class="healthClass(tn.health)"
          @click="openDetail(tn)"
        >
          <div class="tn-top">
            <div class="tn-name">{{ tn.name }}</div>
            <span class="tn-status" :class="statusClass(tn.status)">{{ tn.status }}</span>
          </div>
          <div class="tn-code">{{ tn.code }} · {{ tn.industry }}</div>

          <div class="tn-health">
            <span class="hz-badge" :class="healthClass(tn.health)">{{
              healthLabel(tn.health)
            }}</span>
          </div>

          <!-- 资源用量明细 + 配额进度条 -->
          <div class="quota-list">
            <div class="quota-row" v-for="q in quotaBars(tn)" :key="q.label">
              <div class="quota-meta">
                <span>{{ q.label }}</span>
                <span class="quota-num">{{ q.used }} / {{ q.quota }}</span>
              </div>
              <div class="quota-bar">
                <div
                  class="quota-fill"
                  :class="barColor(q.used, q.quota)"
                  :style="{ width: pct(q.used, q.quota) + '%' }"
                ></div>
              </div>
            </div>
          </div>

          <div class="tn-foot">
            <span>{{ t('tenantManage.contact') }}: {{ tn.contact }}</span>
            <span
              >{{ t('tenantManage.rent') }}: {{ tn.rent?.toLocaleString() }}/{{
                t('tenantManage.month')
              }}</span
            >
          </div>
          <div class="tn-actions" @click.stop>
            <button class="btn-sm" @click="openEdit(tn)">{{ t('tenantManage.edit') }}</button>
            <button class="btn-sm danger" @click="remove(tn)">{{ t('tenantManage.del') }}</button>
          </div>
        </div>
      </div>
    </AsyncSection>

    <!-- 新增/编辑对话框 -->
    <div v-if="dialogVisible" class="modal-mask" @click.self="dialogVisible = false">
      <div class="modal">
        <div class="modal-head">
          <span>{{
            dialogMode === 'add' ? t('tenantManage.newTenant') : t('tenantManage.editTenant')
          }}</span>
          <button class="x" @click="dialogVisible = false">×</button>
        </div>
        <div class="modal-body grid2">
          <label :class="{ 'has-err': !!formErrs.name }">
            {{ t('tenantManage.name') }}<span class="req">*</span>
            <input
              class="inp"
              v-model="form.name"
              :class="{ 'inp-err': !!formErrs.name }"
              @input="formErrs.name = ''"
            />
            <em v-if="formErrs.name" class="ferr">{{ formErrs.name }}</em>
          </label>
          <label>{{ t('tenantManage.contact') }}<input class="inp" v-model="form.contact" /></label>
          <label
            >{{ t('tenantManage.contactPhone') }}<input class="inp" v-model="form.phone"
          /></label>
          <label
            >{{ t('tenantManage.industry') }}<input class="inp" v-model="form.industry"
          /></label>
          <label
            >{{ t('tenantManage.contract') }}<input class="inp" v-model="form.contractNo"
          /></label>
          <label
            >{{ t('tenantManage.status') }}
            <select class="inp" v-model="form.status">
              <option value="active">{{ t('tenantManage.stActive') }}</option>
              <option value="pending">{{ t('tenantManage.stPending') }}</option>
              <option value="expired">{{ t('tenantManage.stExpired') }}</option>
            </select>
          </label>
          <label
            >{{ t('tenantManage.validFrom')
            }}<input class="inp" v-model="form.validFrom" placeholder="YYYY-MM-DD"
          /></label>
          <label
            >{{ t('tenantManage.validTo')
            }}<input class="inp" v-model="form.validTo" placeholder="YYYY-MM-DD"
          /></label>
          <label
            >{{ t('tenantManage.rent')
            }}<input class="inp" type="number" v-model.number="form.rent"
          /></label>
          <label
            >{{ t('tenantManage.cabinets')
            }}<input class="inp" type="number" v-model.number="form.cabinets"
          /></label>
          <label
            >{{ t('tenantManage.uOccupied')
            }}<input class="inp" type="number" v-model.number="form.uOccupied"
          /></label>
          <label
            >{{ t('tenantManage.quotaCabinets')
            }}<input class="inp" type="number" v-model.number="form.quotaCabinets"
          /></label>
          <label
            >{{ t('tenantManage.quotaDevices')
            }}<input class="inp" type="number" v-model.number="form.quotaDevices"
          /></label>
          <label
            >{{ t('tenantManage.quotaPowerKw')
            }}<input class="inp" type="number" v-model.number="form.quotaPowerKw"
          /></label>
          <label
            >{{ t('tenantManage.quotaBandwidthMbps')
            }}<input class="inp" type="number" v-model.number="form.quotaBandwidthMbps"
          /></label>
          <label
            >{{ t('tenantManage.usedDevices')
            }}<input class="inp" type="number" v-model.number="form.usedDevices"
          /></label>
          <label
            >{{ t('tenantManage.usedPowerKw')
            }}<input class="inp" type="number" v-model.number="form.usedPowerKw"
          /></label>
          <label
            >{{ t('tenantManage.usedBandwidthMbps')
            }}<input class="inp" type="number" v-model.number="form.usedBandwidthMbps"
          /></label>
          <label class="full"
            >{{ t('tenantManage.note')
            }}<textarea class="inp" v-model="form.note" rows="2"></textarea>
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="dialogVisible = false">
            {{ t('tenantManage.cancel') }}
          </button>
          <button class="btn-primary" :disabled="saving" @click="save">
            {{ t('tenantManage.save') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <div v-if="detailVisible" class="drawer-mask" @click.self="detailVisible = false">
      <div class="drawer" v-if="detail">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">
              {{ detail.name }}
              <span class="tn-status" :class="statusClass(detail.status)">{{ detail.status }}</span>
            </div>
            <div class="drawer-sub">{{ detail.code }} · {{ detail.industry }}</div>
          </div>
          <button class="x" @click="detailVisible = false">×</button>
        </div>
        <div class="drawer-body">
          <div class="sec">
            <div class="sec-t">{{ t('tenantManage.contact') }}</div>
            <div class="kv">
              <span>{{ t('tenantManage.contact') }}</span
              ><b>{{ detail.contact }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.contactPhone') }}</span
              ><b>{{ detail.phone }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.contract') }}</span
              ><b>{{ detail.contractNo }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.validFrom') }}</span
              ><b>{{ detail.validFrom }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.validTo') }}</span
              ><b>{{ detail.validTo }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.rent') }}</span
              ><b>{{ detail.rent?.toLocaleString() }} / {{ t('tenantManage.month') }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.note') }}</span
              ><b>{{ detail.note || '—' }}</b>
            </div>
          </div>

          <div class="sec">
            <div class="sec-t">
              {{ t('tenantManage.health') }} ·
              <span class="hz-badge" :class="healthClass(detail.health)">{{
                healthLabel(detail.health)
              }}</span>
            </div>
          </div>

          <div class="sec">
            <div class="sec-t">{{ t('tenantManage.quota') }}</div>
            <div class="kv">
              <span>{{ t('tenantManage.quotaCabinets') }}</span
              ><b>{{ detail.quotaCabinets }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.quotaDevices') }}</span
              ><b>{{ detail.quotaDevices }}</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.quotaPowerKw') }}</span
              ><b>{{ detail.quotaPowerKw }} kW</b>
            </div>
            <div class="kv">
              <span>{{ t('tenantManage.quotaBandwidthMbps') }}</span
              ><b>{{ detail.quotaBandwidthMbps }} Mbps</b>
            </div>
          </div>

          <div class="sec">
            <div class="sec-t">{{ t('tenantManage.usage') }}</div>
            <div class="usage-grid">
              <div class="usage-cell">
                <div class="u-val">
                  {{ detail.cabinets }}<small>/{{ detail.quotaCabinets }}</small>
                </div>
                <div class="u-lbl">{{ t('tenantManage.usageCabinets') }}</div>
                <div class="quota-bar">
                  <div
                    class="quota-fill"
                    :class="barColor(detail.cabinets, detail.quotaCabinets)"
                    :style="{ width: pct(detail.cabinets, detail.quotaCabinets) + '%' }"
                  ></div>
                </div>
              </div>
              <div class="usage-cell">
                <div class="u-val">
                  {{ detail.usedDevices }}<small>/{{ detail.quotaDevices }}</small>
                </div>
                <div class="u-lbl">{{ t('tenantManage.usageDevices') }}</div>
                <div class="quota-bar">
                  <div
                    class="quota-fill"
                    :class="barColor(detail.usedDevices, detail.quotaDevices)"
                    :style="{ width: pct(detail.usedDevices, detail.quotaDevices) + '%' }"
                  ></div>
                </div>
              </div>
              <div class="usage-cell">
                <div class="u-val">
                  {{ detail.usedPowerKw }}<small>/{{ detail.quotaPowerKw }}kW</small>
                </div>
                <div class="u-lbl">{{ t('tenantManage.usagePower') }}</div>
                <div class="quota-bar">
                  <div
                    class="quota-fill"
                    :class="barColor(detail.usedPowerKw, detail.quotaPowerKw)"
                    :style="{ width: pct(detail.usedPowerKw, detail.quotaPowerKw) + '%' }"
                  ></div>
                </div>
              </div>
              <div class="usage-cell">
                <div class="u-val">
                  {{ detail.usedBandwidthMbps }}<small>/{{ detail.quotaBandwidthMbps }}</small>
                </div>
                <div class="u-lbl">{{ t('tenantManage.usageBandwidth') }}</div>
                <div class="quota-bar">
                  <div
                    class="quota-fill"
                    :class="barColor(detail.usedBandwidthMbps, detail.quotaBandwidthMbps)"
                    :style="{
                      width: pct(detail.usedBandwidthMbps, detail.quotaBandwidthMbps) + '%',
                    }"
                  ></div>
                </div>
              </div>
            </div>
            <div class="kv" style="margin-top: 10px">
              <span>{{ t('tenantManage.usedU') }}</span
              ><b>{{ detail.uOccupied }}</b>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tm-page {
  padding: 18px 22px;
}
.tm-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.tm-title {
  font-size: 20px;
  margin: 0;
}
.tm-sub {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 9px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.stat-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px;
}
.stat-val {
  font-size: 26px;
  font-weight: 700;
}
.stat-lbl {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.occ-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
}
.occ-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 10px;
}
.occ-num {
  font-weight: 700;
}
.occ-bar {
  height: 12px;
  background: #1e293b;
  border-radius: 6px;
  overflow: hidden;
}
.occ-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #22d3ee);
}
.occ-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  margin-left: 6px;
}
.dot.leased {
  background: #2563eb;
}
.dot.empty {
  background: #475569;
}

.tm-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.inp {
  background: #0f172a;
  border: 1px solid #1e293b;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.tm-toolbar .inp {
  width: auto;
  min-width: 200px;
}

.tm-loading,
.tm-error,
.tm-empty {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}
.tm-error {
  color: #f87171;
}

.tm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.tn-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-left: 4px solid #334155;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: transform 0.12s;
}
.tn-card:hover {
  transform: translateY(-2px);
}
.tn-card.hz-warn {
  border-left-color: #f59e0b;
}
.tn-card.hz-over {
  border-left-color: #f43f5e;
}
.tn-card.hz-normal {
  border-left-color: #10b981;
}
.tn-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tn-name {
  font-size: 16px;
  font-weight: 600;
}
.tn-code {
  color: #94a3b8;
  font-size: 12px;
  margin: 4px 0 10px;
}
.tn-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}
.st-active {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}
.st-pending {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}
.st-expired {
  background: rgba(244, 63, 94, 0.15);
  color: #fb7185;
}

.tn-health {
  margin-bottom: 10px;
}
.hz-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}
.hz-normal {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}
.hz-warn {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}
.hz-over {
  background: rgba(244, 63, 94, 0.15);
  color: #fb7185;
}

.quota-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.quota-row {
  font-size: 12px;
}
.quota-meta {
  display: flex;
  justify-content: space-between;
  color: #cbd5e1;
  margin-bottom: 3px;
}
.quota-num {
  color: #94a3b8;
}
.quota-bar {
  height: 7px;
  background: #1e293b;
  border-radius: 4px;
  overflow: hidden;
}
.quota-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.tn-foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 10px;
}
.tn-actions {
  display: flex;
  gap: 8px;
}
.btn-sm {
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.btn-sm.danger {
  color: #fca5a5;
  border-color: #7f1d1d;
}

.modal-mask,
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.6);
  display: flex;
  z-index: 50;
}
.modal-mask {
  align-items: center;
  justify-content: center;
}
.modal {
  background: #0b1220;
  border: 1px solid #1e293b;
  border-radius: 14px;
  width: 720px;
  max-width: 92vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.modal-head,
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 18px;
  border-bottom: 1px solid #1e293b;
  font-weight: 600;
}
.modal-body {
  padding: 16px 18px;
  overflow: auto;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.grid2 label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #94a3b8;
}
.grid2 label.full {
  grid-column: 1 / -1;
}
.grid2 .req {
  color: #f87171;
  margin-left: 2px;
}
.inp-err {
  border-color: #f87171 !important;
}
.ferr {
  color: #f87171;
  font-size: 11px;
  font-style: normal;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid #1e293b;
}
.btn-ghost {
  background: transparent;
  border: 1px solid #334155;
  color: #e2e8f0;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}
.x {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 22px;
  cursor: pointer;
}

.drawer {
  margin-left: auto;
  width: 460px;
  max-width: 94vw;
  background: #0b1220;
  border-left: 1px solid #1e293b;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.drawer-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
.drawer-sub {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 4px;
}
.drawer-body {
  padding: 16px 18px;
  overflow: auto;
}
.sec {
  margin-bottom: 18px;
}
.sec-t {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 8px;
  border-left: 3px solid #2563eb;
  padding-left: 8px;
}
.kv {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed #1e293b;
  font-size: 13px;
}
.kv span {
  color: #94a3b8;
}
.usage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.usage-cell {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 10px;
}
.u-val {
  font-size: 18px;
  font-weight: 700;
}
.u-val small {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 400;
}
.u-lbl {
  font-size: 11px;
  color: #94a3b8;
  margin: 4px 0 6px;
}
</style>
