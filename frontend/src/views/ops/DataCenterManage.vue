<template>
  <div class="dc-manage">
    <div class="view-head">
      <h1>{{ tl('datacenter.title') }}</h1>
      <span class="sub">{{ tl('datacenter.sub') }}</span>
      <div class="head-actions">
        <button class="btn-sm" @click="load" :disabled="loading">{{ tl('datacenter.refresh') }}</button>
        <button class="btn-sm" @click="openOpLog" :disabled="loading">{{ tl('datacenter.opLog') }}</button>
        <button class="btn-sm danger" @click="batchDelete" :disabled="!canAdmin || selectedIds.length === 0">{{ tl('datacenter.batchDelete') }} ({{ selectedIds.length }})</button>
        <button class="btn-sm primary" @click="openCreate" :disabled="!canAdmin">{{ tl('datacenter.newDc') }}</button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpis">
      <div class="kpi"><span class="kv">{{ kpis.total }}</span><span class="kl">{{ tl('datacenter.kpiTotal') }}</span></div>
      <div class="kpi"><span class="kv">{{ kpis.enabled }}</span><span class="kl">{{ tl('datacenter.enabled') }}</span></div>
      <div class="kpi"><span class="kv">{{ kpis.power.toFixed(1) }}</span><span class="kl">{{ tl('datacenter.kpiPower') }} (MW)</span></div>
      <div class="kpi"><span class="kv">{{ kpis.rack }}</span><span class="kl">{{ tl('datacenter.kpiRack') }}</span></div>
    </div>

    <!-- 选择工具条 -->
    <div class="toolbar" v-if="canAdmin">
      <label class="chk"><input type="checkbox" :checked="allSelected" @change="toggleAll" /> {{ tl('datacenter.selectAll') }}</label>
      <span class="sel-info">{{ tl('datacenter.selected', { n: selectedIds.length }) }}</span>
      <button class="btn-xs" v-if="selectedIds.length" @click="clearSel">{{ tl('datacenter.clearSel') }}</button>
    </div>

    <!-- 卡片网格 -->
    <div class="cards">
      <div v-for="d in list" :key="d.id" class="card" :class="{ cur: d.isCurrent, sel: selectedIds.includes(d.id) }">
        <div class="card-top">
          <label v-if="canAdmin" class="chk card-chk"><input type="checkbox" :checked="selectedIds.includes(d.id)" @change="toggleOne(d.id)" /></label>
          <div>
            <div class="c-name">{{ d.name }}</div>
            <div class="c-code mono">{{ d.code }}</div>
          </div>
          <span v-if="d.isCurrent" class="tag g">{{ tl('datacenter.current') }}</span>
          <span v-else class="tag" :class="statusClass(d.status)">{{ statusLabel(d.status) }}</span>
        </div>
        <div class="c-region">{{ d.region }} · {{ d.address || '—' }}</div>
        <div class="c-metrics">
          <div><span>{{ d.powerCapacityMw.toFixed(1) }}</span><label>{{ tl('datacenter.kpiPower') }}</label></div>
          <div><span>{{ d.coolingCapacityMw.toFixed(1) }}</span><label>{{ tl('datacenter.kpiCooling') }}</label></div>
          <div><span>{{ d.rackCapacity }}</span><label>{{ tl('datacenter.kpiRack') }}</label></div>
          <div><span>{{ d.capacityKw }}</span><label>{{ tl('datacenter.capKw') }}</label></div>
        </div>
        <div class="c-desc">{{ d.description || '—' }}</div>
        <div class="c-actions">
          <button v-if="!d.isCurrent" class="btn-sm" @click="setCurrent(d)" :disabled="!canAdmin">{{ tl('datacenter.setCurrent') }}</button>
          <button class="btn-sm" @click="toggleStatus(d)" :disabled="!canAdmin">{{ d.status === 'disabled' || d.status === '下线' ? tl('datacenter.enable') : tl('datacenter.disable') }}</button>
          <button class="btn-sm" @click="openServices(d)" :disabled="loading">{{ tl('datacenter.services') }}</button>
          <button class="btn-sm" @click="openEdit(d)" :disabled="!canAdmin">{{ tl('common.edit') }}</button>
          <button class="btn-sm danger" @click="remove(d)" :disabled="!canAdmin || d.isCurrent">{{ tl('datacenter.delete') }}</button>
          <router-link class="btn-sm" :to="{ path: '/ops/datacenter/compare' }">{{ tl('datacenter.compare') }}</router-link>
        </div>
      </div>
      <div v-if="!list.length" class="empty">{{ tl('common.error') }}</div>
    </div>

    <!-- 新建/编辑抽屉 -->
    <div class="drawer-mask" v-if="drawer" @click.self="drawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ editId ? tl('datacenter.edit') : tl('datacenter.newDc') }}</span>
          <button class="x" @click="drawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('datacenter.code') }}<input v-model.trim="form.code" class="ipt" :disabled="!!editId" /></label>
          <label>{{ tl('datacenter.name') }}<input v-model.trim="form.name" class="ipt" /></label>
          <div class="row">
            <label>{{ tl('datacenter.region') }}<input v-model.trim="form.region" class="ipt" /></label>
            <label>{{ tl('datacenter.status') }}>
              <select v-model="form.status" class="ipt">
                <option>运营</option><option>建设</option><option>下线</option>
              </select>
            </label>
          </div>
          <label>{{ tl('datacenter.address') }}<input v-model.trim="form.address" class="ipt" /></label>
          <div class="row">
            <label>{{ tl('datacenter.powerMw') }}<input v-model.number="form.powerCapacityMw" class="ipt" type="number" /></label>
            <label>{{ tl('datacenter.coolingMw') }}<input v-model.number="form.coolingCapacityMw" class="ipt" type="number" /></label>
          </div>
          <div class="row">
            <label>{{ tl('datacenter.rackCap') }}<input v-model.number="form.rackCapacity" class="ipt" type="number" /></label>
            <label>{{ tl('datacenter.capKw') }}<input v-model.number="form.capacityKw" class="ipt" type="number" /></label>
          </div>
          <label>{{ tl('datacenter.rooms') }}<input v-model.number="form.rooms" class="ipt" type="number" /></label>
          <label>{{ tl('datacenter.desc') }}><textarea v-model.trim="form.description" class="ipt" rows="2"></textarea></label>
        </div>
        <div class="drawer-foot">
          <button class="btn-sm" @click="drawer = false">{{ tl('common.cancel') }}</button>
          <button class="btn-sm primary" @click="save" :disabled="saving">{{ saving ? tl('common.loading') : tl('thingModel.save') }}</button>
        </div>
      </div>
    </div>

    <!-- 操作日志抽屉 -->
    <div class="drawer-mask" v-if="opLogOpen" @click.self="opLogOpen = false">
      <div class="drawer wide">
        <div class="drawer-head">
          <span>{{ tl('datacenter.opLog') }}</span>
          <button class="x" @click="opLogOpen = false">✕</button>
        </div>
        <div class="log-list">
          <div class="log-row ah">
            <span>{{ tl('datacenter.opTime') }}</span>
            <span>{{ tl('datacenter.opAction') }}</span>
            <span>{{ tl('datacenter.opTarget') }}</span>
            <span>{{ tl('datacenter.opOperator') }}</span>
            <span>{{ tl('datacenter.opDetail') }}</span>
          </div>
          <div v-for="r in opLogs" :key="r.id" class="log-row">
            <span class="mono">{{ r.ts }}</span>
            <span><span class="tag sm" :class="actionClass(r.action)">{{ actionLabel(r.action) }}</span></span>
            <span>{{ r.target }}</span>
            <span>{{ r.operator }}</span>
            <span class="muted">{{ r.detail || '—' }}</span>
          </div>
          <div v-if="!opLogs.length" class="empty">{{ tl('datacenter.opLogEmpty') }}</div>
        </div>
      </div>
    </div>

    <!-- 关联服务抽屉 -->
    <div class="drawer-mask" v-if="svcOpen" @click.self="svcOpen = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ tl('datacenter.services') }} · {{ svcName }}</span>
          <button class="x" @click="svcOpen = false">✕</button>
        </div>
        <div class="svc-summary" v-if="services">
          <div><b>{{ services.totalDevices }}</b><label>{{ tl('datacenter.serviceTotalDevices') }}</label></div>
          <div><b class="ok">{{ services.onlineDevices }}</b><label>{{ tl('datacenter.serviceOnlineDevices') }}</label></div>
        </div>
        <div class="svc-list">
          <div v-for="s in services?.services || []" :key="s.key" class="svc-row">
            <div class="svc-name">{{ s.name }}</div>
            <div class="svc-metrics">
              <span>{{ tl('datacenter.serviceDevices') }}: <b>{{ s.deviceCount }}</b></span>
              <span class="ok">{{ tl('datacenter.serviceOnline') }}: <b>{{ s.onlineCount }}</b></span>
              <span :class="s.alarmCount ? 'warn' : ''">{{ tl('datacenter.serviceAlarm') }}: <b>{{ s.alarmCount }}</b></span>
            </div>
          </div>
          <div v-if="!services || !services.services.length" class="empty">{{ tl('datacenter.serviceEmpty') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/hooks/useToast'
import { usePermission } from '@/hooks/usePermission'
import {
  listIdcs,
  setIdcCurrent,
  createIdc,
  updateIdc,
  deleteIdc,
  batchDeleteIdcs,
  toggleIdcStatus,
  getIdcServices,
  getIdcOpLogs,
  type Idc,
  type IdcCreate,
  type IdcOpLog,
  type IdcServicesResp,
} from '@/api/idc'
import { useDatacenterStore } from '@/stores/datacenter'

const { t: tl } = useI18n()
const toast = useToast()
const { can } = usePermission()
const canAdmin = computed(() => can('admin'))
const dcStore = useDatacenterStore()

const list = ref<Idc[]>([])
const loading = ref(false)
const drawer = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)

const selectedIds = ref<number[]>([])
const opLogOpen = ref(false)
const opLogs = ref<IdcOpLog[]>([])
const svcOpen = ref(false)
const services = ref<IdcServicesResp | null>(null)
const svcName = ref('')

const blank = (): IdcCreate => ({
  code: '', name: '', region: '', address: '',
  powerCapacityMw: 0, coolingCapacityMw: 0, rackCapacity: 0, rooms: 0,
  status: '运营', capacityKw: 0, description: '',
})
const form = reactive(blank())

const kpis = computed(() => {
  const arr = list.value
  return {
    total: arr.length,
    enabled: arr.filter((i) => i.status !== 'disabled' && i.status !== '下线').length,
    power: arr.reduce((a, b) => a + b.powerCapacityMw, 0),
    rack: arr.reduce((a, b) => a + b.rackCapacity, 0),
  }
})

const allSelected = computed(() => list.value.length > 0 && selectedIds.value.length === list.value.length)
function toggleAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  selectedIds.value = checked ? list.value.map((i) => i.id) : []
}
function toggleOne(id: number) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}
function clearSel() { selectedIds.value = [] }

function statusClass(s: string) {
  if (s === 'disabled' || s === '下线') return 'r'
  if (s === '建设') return 'a'
  return 'b'
}
function statusLabel(s: string) {
  if (s === 'disabled') return tl('datacenter.statusDisabled')
  if (s === '下线') return tl('datacenter.statusOffline')
  if (s === '建设') return tl('datacenter.statusBuilding')
  return tl('datacenter.statusEnabled')
}
function actionClass(a: string) {
  if (a === 'delete') return 'r'
  if (a === 'toggle_status') return 'a'
  return 'b'
}
function actionLabel(a: string) {
  if (a === 'create') return tl('datacenter.actCreate')
  if (a === 'update') return tl('datacenter.actUpdate')
  if (a === 'delete') return tl('datacenter.actDelete')
  if (a === 'toggle_status') return tl('datacenter.actToggle')
  return a
}

function load() {
  loading.value = true
  listIdcs()
    .then((r) => {
      list.value = r || []
      dcStore.setIdcList(list.value.map((i) => ({ id: i.id, name: i.name, region: i.region, status: i.status })))
    })
    .catch(() => toast.error('加载数据中心失败'))
    .finally(() => (loading.value = false))
}

function openCreate() {
  editId.value = null
  Object.assign(form, blank())
  drawer.value = true
}
function openEdit(d: Idc) {
  editId.value = d.id
  Object.assign(form, {
    code: d.code, name: d.name, region: d.region, address: d.address,
    powerCapacityMw: d.powerCapacityMw, coolingCapacityMw: d.coolingCapacityMw,
    rackCapacity: d.rackCapacity, rooms: d.rooms, status: d.status,
    capacityKw: d.capacityKw, description: d.description,
  })
  drawer.value = true
}

function save() {
  if (!form.code || !form.name) {
    toast.warning(tl('datacenter.code') + ' / ' + tl('datacenter.name'))
    return
  }
  saving.value = true
  const op = editId.value ? updateIdc(editId.value, { ...form }) : createIdc({ ...form })
  op.then(() => {
    toast.success(tl('datacenter.saved'))
    drawer.value = false
    load()
  })
    .catch((e: any) => toast.error(e?.detail || '保存失败'))
    .finally(() => (saving.value = false))
}

function setCurrent(d: Idc) {
  setIdcCurrent(d.id)
    .then((r) => {
      toast.success(tl('datacenter.switchOk'))
      dcStore.setCurrentIdc(r.id)
      load()
    })
    .catch((e: any) => toast.error(e?.detail || '切换失败'))
}

function toggleStatus(d: Idc) {
  const willDisable = d.status !== 'disabled' && d.status !== '下线'
  const act = willDisable ? tl('datacenter.disable') : tl('datacenter.enable')
  if (!confirm(tl('datacenter.confirmToggle', { name: d.name, act }))) return
  toggleIdcStatus(d.id)
    .then((r) => {
      toast.success(tl('datacenter.toggleOk', { txt: r.status === 'disabled' ? tl('datacenter.disabled') : tl('datacenter.enabled') }))
      load()
    })
    .catch((e: any) => toast.error(e?.detail || '操作失败'))
}

function remove(d: Idc) {
  if (!confirm(tl('datacenter.confirmDelete'))) return
  deleteIdc(d.id)
    .then(() => {
      toast.success(tl('datacenter.deleted'))
      selectedIds.value = selectedIds.value.filter((i) => i !== d.id)
      load()
    })
    .catch((e: any) => toast.error(e?.detail || '删除失败'))
}

function batchDelete() {
  if (!selectedIds.value.length) return
  if (!confirm(tl('datacenter.confirmBatchDelete', { n: selectedIds.value.length }))) return
  batchDeleteIdcs(selectedIds.value)
    .then((r) => {
      toast.success(tl('datacenter.batchDeleted', { n: r.deleted }))
      if (r.skipped.length) toast.warning(tl('datacenter.batchSkipped', { n: r.skipped.length }))
      selectedIds.value = []
      load()
    })
    .catch((e: any) => toast.error(e?.detail || '批量删除失败'))
}

function openOpLog() {
  getIdcOpLogs(50)
    .then((r) => { opLogs.value = r.items || [] })
    .catch(() => toast.error('加载操作日志失败'))
  opLogOpen.value = true
}

function openServices(d: Idc) {
  svcName.value = d.name
  services.value = null
  svcOpen.value = true
  getIdcServices(d.id)
    .then((r) => { services.value = r })
    .catch(() => toast.error('加载关联服务失败'))
}

onMounted(load)
</script>

<style scoped>
.dc-manage { display: flex; flex-direction: column; gap: 14px; }
.view-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.view-head h1 { font-size: 18px; margin: 0; }
.view-head .sub { color: var(--muted); font-size: 12px; }
.head-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.kv { font-size: 22px; font-weight: 700; color: var(--cyan); display: block; }
.kl { font-size: 12px; color: var(--muted); }
.toolbar { display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--txt2); flex-wrap: wrap; }
.sel-info { color: var(--cyan); }
.chk { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; color: var(--txt2); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; transition: border-color .15s, transform .1s; }
.card:hover { border-color: var(--cyan); transform: translateY(-2px); }
.card.cur { border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan) inset; }
.card.sel { border-color: var(--amber); }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.card-chk { margin-right: 2px; }
.c-name { font-weight: 700; color: var(--txt-strong); font-size: 15px; }
.c-code { font-size: 11px; color: var(--muted); margin-top: 2px; }
.c-region { font-size: 12px; color: var(--txt2); margin: 8px 0; }
.c-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 10px 0; }
.c-metrics div { background: var(--track); border-radius: 8px; padding: 8px; text-align: center; }
.c-metrics span { font-size: 15px; font-weight: 700; color: var(--txt-strong); display: block; }
.c-metrics label { font-size: 10px; color: var(--muted); }
.c-desc { font-size: 12px; color: var(--txt2); min-height: 18px; margin-bottom: 10px; }
.c-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.btn-sm { color: var(--txt2); border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 5px 10px; font-size: 12px; cursor: pointer; text-decoration: none; display: inline-block; }
.btn-sm:hover:not(:disabled) { color: var(--cyan); border-color: var(--cyan); }
.btn-sm:disabled { opacity: .45; cursor: not-allowed; }
.btn-sm.primary { color: #04121a; background: var(--cyan); border-color: var(--cyan); font-weight: 600; }
.btn-sm.danger { color: var(--red); border-color: rgba(255,77,94,.35); }
.btn-xs { color: var(--txt2); border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 3px 8px; font-size: 11px; cursor: pointer; }
.drawer-mask { position: fixed; inset: 0; background: rgba(6,11,20,.6); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; padding: 6vh 16px; z-index: 40; }
.drawer { width: 460px; max-width: 92vw; background: var(--card-bg); max-height: 88vh; overflow: auto; padding: 18px; border-radius: 14px; box-shadow: -8px 0 24px rgba(0,0,0,.3); }
.drawer.wide { width: 640px; }
.drawer-head { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; margin-bottom: 14px; color: var(--txt-strong); }
.x { background: none; border: none; color: var(--muted); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 10px; }
.form .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
label { font-size: 12px; color: var(--txt2); display: flex; flex-direction: column; gap: 4px; }
.ipt { background: var(--track); border: 1px solid var(--line); border-radius: 8px; padding: 7px 9px; color: var(--txt-strong); font-size: 13px; }
.drawer-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.empty { text-align: center; color: var(--muted); padding: 30px; font-size: 13px; grid-column: 1 / -1; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--txt2); }
.tag.g { color: var(--cyan); border-color: var(--cyan); }
.tag.b { color: #38bdf8; border-color: rgba(56,189,248,.4); }
.tag.a { color: var(--amber); border-color: rgba(245,158,11,.4); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); }
.tag.sm { font-size: 10px; padding: 1px 6px; }
.log-list, .svc-list { display: flex; flex-direction: column; }
.log-row { display: grid; grid-template-columns: 1.3fr .8fr 1.2fr .7fr 1fr; gap: 8px; padding: 8px; border-top: 1px solid var(--line); font-size: 12px; color: var(--txt2); align-items: center; }
.log-row.ah { color: var(--muted); font-weight: 600; border-top: none; }
.mono { font-family: monospace; font-size: 11px; }
.muted { color: var(--muted); }
.svc-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 12px; }
.svc-summary div { background: var(--track); border-radius: 8px; padding: 10px; text-align: center; }
.svc-summary b { font-size: 18px; display: block; color: var(--txt-strong); }
.svc-summary label { color: var(--muted); }
.svc-row { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-top: 1px solid var(--line); }
.svc-name { font-weight: 600; color: var(--txt-strong); }
.svc-metrics { display: flex; gap: 12px; font-size: 12px; color: var(--txt2); }
.svc-metrics .ok { color: var(--green); }
.svc-metrics .warn { color: var(--amber); }

@media (max-width: 720px) {
  .kpis { grid-template-columns: repeat(2, 1fr); }
  .head-actions { margin-left: 0; width: 100%; }
  .cards { grid-template-columns: 1fr; }
  .log-row { grid-template-columns: 1fr 1fr; }
  .log-row.ah { display: none; }
}
</style>
