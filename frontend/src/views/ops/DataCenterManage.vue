<template>
  <div class="dc-manage">
    <div class="view-head">
      <h1>{{ tl('datacenter.title') }}</h1>
      <span class="sub">{{ tl('datacenter.sub') }}</span>
      <button class="btn-sm primary" style="margin-left: auto" @click="openCreate" :disabled="!canAdmin">{{ tl('datacenter.newDc') }}</button>
    </div>

    <!-- KPI -->
    <div class="kpis">
      <div class="kpi"><span class="kv">{{ kpis.total }}</span><span class="kl">{{ tl('datacenter.title') }}</span></div>
      <div class="kpi"><span class="kv">{{ kpis.power.toFixed(1) }}</span><span class="kl">{{ tl('datacenter.kpiPower') }} (MW)</span></div>
      <div class="kpi"><span class="kv">{{ kpis.cooling.toFixed(1) }}</span><span class="kl">{{ tl('datacenter.kpiCooling') }} (MW)</span></div>
      <div class="kpi"><span class="kv">{{ kpis.rack }}</span><span class="kl">{{ tl('datacenter.kpiRack') }}</span></div>
    </div>

    <!-- 卡片网格 -->
    <div class="cards">
      <div v-for="d in list" :key="d.id" class="card" :class="{ cur: d.isCurrent }">
        <div class="card-top">
          <div>
            <div class="c-name">{{ d.name }}</div>
            <div class="c-code mono">{{ d.code }}</div>
          </div>
          <span v-if="d.isCurrent" class="tag g">{{ tl('datacenter.current') }}</span>
          <span v-else class="tag" :class="d.status === '下线' ? 'r' : 'b'">{{ d.status }}</span>
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
          <button class="btn-sm" @click="openEdit(d)" :disabled="!canAdmin">{{ tl('common.edit') }}</button>
          <button class="btn-sm danger" @click="remove(d)" :disabled="!canAdmin">{{ tl('datacenter.delete') }}</button>
          <router-link class="btn-sm" :to="{ path: '/ops/datacenter/compare' }">{{ tl('datacenter.compare') }}</router-link>
        </div>
      </div>
      <div v-if="!list.length" class="empty">{{ tl('common.error') }}</div>
    </div>

    <!-- 抽屉 -->
    <div class="drawer-mask" v-if="drawer" @click.self="drawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ editId ? tl('datacenter.edit') || '编辑' : tl('datacenter.newDc') }}</span>
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
  type Idc,
  type IdcCreate,
} from '@/api/idc'
import { useDatacenterStore } from '@/stores/datacenter'

const { t: tl } = useI18n()
const toast = useToast()
const { can } = usePermission()
const canAdmin = computed(() => can('admin'))
const dcStore = useDatacenterStore()

const list = ref<Idc[]>([])
const drawer = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)

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
    power: arr.reduce((a, b) => a + b.powerCapacityMw, 0),
    cooling: arr.reduce((a, b) => a + b.coolingCapacityMw, 0),
    rack: arr.reduce((a, b) => a + b.rackCapacity, 0),
  }
})

function load() {
  listIdcs().then((r) => {
    list.value = r || []
    dcStore.setIdcList(list.value.map((i) => ({ id: i.id, name: i.name, region: i.region, status: i.status })))
  }).catch(() => toast.error('加载数据中心失败'))
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

function remove(d: Idc) {
  if (!confirm(tl('datacenter.confirmDelete'))) return
  deleteIdc(d.id)
    .then(() => {
      toast.success(tl('datacenter.deleted'))
      load()
    })
    .catch((e: any) => toast.error(e?.detail || '删除失败'))
}

onMounted(load)
</script>

<style scoped>
.dc-manage { display: flex; flex-direction: column; gap: 14px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.kv { font-size: 22px; font-weight: 700; color: var(--cyan); display: block; }
.kl { font-size: 12px; color: var(--muted); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; transition: border-color .15s, transform .1s; }
.card:hover { border-color: var(--cyan); transform: translateY(-2px); }
.card.cur { border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan) inset; }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; }
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
.btn-sm:hover { color: var(--cyan); border-color: var(--cyan); }
.btn-sm.primary { color: #04121a; background: var(--cyan); border-color: var(--cyan); font-weight: 600; }
.btn-sm.danger { color: var(--red); border-color: rgba(255,77,94,.35); }
.drawer-mask { position: fixed; inset: 0; background: rgba(6,11,20,.6); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; padding: 6vh 16px; z-index: 40; }
.drawer { width: 460px; max-width: 92vw; background: var(--card-bg); max-height: 88vh; overflow: auto; padding: 18px; border-radius: 14px; box-shadow: -8px 0 24px rgba(0,0,0,.3); }
.drawer-head { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; margin-bottom: 14px; color: var(--txt-strong); }
.x { background: none; border: none; color: var(--muted); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 10px; }
.form .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
label { font-size: 12px; color: var(--txt2); display: flex; flex-direction: column; gap: 4px; }
.drawer-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.empty { text-align: center; color: var(--muted); padding: 30px; font-size: 13px; grid-column: 1 / -1; }
</style>
