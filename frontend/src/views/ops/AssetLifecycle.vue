<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M3 7l9-4 9 4v10l-9 4-9-4V7z" stroke-linejoin="round"/>
          <path d="M3 7l9 4 9-4M12 11v10" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <div class="tabs">
          <button v-for="tb in tabs" :key="tb.k"
            class="tab" :class="{ active: activeTab === tb.k }"
            @click="activeTab = tb.k">{{ tb.label }}</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-box"><div class="spinner"></div><span>{{ t.loading }}</span></div>

    <!-- 生命周期 -->
    <div v-else-if="activeTab === 'life'">
      <div class="grid cols-5">
        <div v-for="s in stages" :key="s.key" class="card" style="padding:14px">
          <div class="text-xs" :class="s.cls">{{ s.label }}</div>
          <div class="text-2xl font-semibold" style="color:var(--txt-strong)">{{ stageCount(s.key) }}</div>
        </div>
      </div>
      <div class="flex gap-2 mb-3 flex-wrap">
        <select v-model="fStage" class="inp w-40">
          <option value="all">{{ t.allStage }}</option>
          <option v-for="s in stages" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <select v-model="fDomain" class="inp w-44">
          <option value="all">{{ t.allDomain }}</option>
          <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
        </select>
        <input v-model="kw" class="inp flex-1" style="min-width:180px" :placeholder="t.search" />
      </div>
      <div class="card">
        <table class="w-full">
          <thead>
            <tr>
              <th>{{ t.colCode }}</th>
              <th>{{ t.colName }}</th>
              <th>{{ t.colDomain }}</th>
              <th>{{ t.colModel }}</th>
              <th>{{ t.colRunHours }}</th>
              <th>{{ t.colWarranty }}</th>
              <th>{{ t.colStage }}</th>
              <th>{{ t.colProgress }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in filtered" :key="e.id">
              <td class="mono">{{ e.code }}</td>
              <td class="cell-strong">{{ e.name }}</td>
              <td>{{ e.domain }}</td>
              <td>{{ e.vendor }} {{ e.model }}</td>
              <td>{{ e.runHours.toLocaleString() }} h</td>
              <td>
                <span class="tag" :class="warrantyTag(e)">
                  {{ e.warrantyMonths > 0 ? t.monthsLeft.replace('{n}', String(e.warrantyMonths)) : t.expired }}
                </span>
              </td>
              <td>
                <span class="tag" :class="stageTag(e.stage)">{{ stageLabel(e.stage) }}</span>
              </td>
              <td style="min-width:120px">
                <div class="pbar"><i :style="{ width: lifePct(e) + '%' }"></i></div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filtered.length" class="empty-box">{{ t.empty }}</div>
      </div>
    </div>

    <!-- 型号库 -->
    <div v-else>
      <div class="card-head">
        <div class="card-title">{{ t.modelLib }}</div>
        <button class="btn-primary" @click="openCreate">{{ t.newModel }}</button>
      </div>
      <div class="grid cols-3">
        <div v-for="m in modelLib" :key="m.id" class="card flex flex-col">
          <div class="flex items-start justify-between">
            <div>
              <h4 class="font-semibold cell-strong">{{ m.vendor }} {{ m.model }}</h4>
              <p class="text-xs" style="margin-top:3px;color:var(--txt2)">{{ t.category }}: {{ m.category }}</p>
            </div>
            <span class="pill">{{ m.count }} {{ t.units }}</span>
          </div>
          <div class="grid grid-cols-1 gap-1 flex-1" style="margin-top:10px;color:var(--txt2);font-size:12px">
            <div>{{ t.spec }}: {{ m.spec || '—' }}</div>
            <div>{{ t.power }}: {{ m.power || '—' }}</div>
            <div>{{ t.notes }}: {{ m.notes || '—' }}</div>
          </div>
          <div class="flex gap-2" style="margin-top:12px">
            <button class="btn-ghost" @click="edit(m)">{{ t.edit }}</button>
            <button class="btn-danger" @click="remove(m.id)">{{ t.del }}</button>
          </div>
        </div>
      </div>
      <div v-if="!modelLib.length" class="card empty-box">{{ t.empty }}</div>

      <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
        <div class="modal">
          <h3>{{ editing ? t.editModel : t.newModel }}</h3>
          <div class="space-y">
            <div class="grid cols-2" style="gap:12px">
              <div class="field"><span>{{ t.vendor }}</span><input v-model="form.vendor" class="inp" /></div>
              <div class="field"><span>{{ t.model }}</span><input v-model="form.model" class="inp" /></div>
            </div>
            <div class="field"><span>{{ t.category }}</span><input v-model="form.category" class="inp" :placeholder="t.catPlaceholder" /></div>
            <div class="grid cols-2" style="gap:12px">
              <div class="field"><span>{{ t.spec }}</span><input v-model="form.spec" class="inp" :placeholder="t.specPlaceholder" /></div>
              <div class="field"><span>{{ t.power }}</span><input v-model="form.power" class="inp" :placeholder="t.powerPlaceholder" /></div>
            </div>
            <div class="field"><span>{{ t.notes }}</span><textarea v-model="form.notes" rows="2" class="inp" :placeholder="t.notesPlaceholder"></textarea></div>
          </div>
          <div class="modal-actions">
            <button class="btn-ghost" @click="showModal = false">{{ t.cancel }}</button>
            <button class="btn-primary" @click="save">{{ t.save }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { listEquipment } from '@/api'
import type { Equipment } from '@/types'

const { tm } = useI18n()
const t = (tm('assetLifecycle') || {}) as Record<string, any>

const tabs = [
  { k: 'life', label: '' },
  { k: 'lib', label: '' },
]
const activeTab = ref<string>('life')
const loading = ref(false)

interface Row extends Equipment {
  runHours: number
  warrantyMonths: number
  stage: 'procure' | 'stock' | 'active' | 'expired' | 'retire'
  lifePctVal: number
}
const rows = ref<Row[]>([])
const fStage = ref('all')
const fDomain = ref('all')
const kw = ref('')

const KEY_LIB = 'c01_model_lib'
interface ModelEntry { id: string; vendor: string; model: string; category: string; spec: string; power: string; notes: string; count: number }
const modelLib = ref<ModelEntry[]>([])
const showModal = ref(false)
const editing = ref(false)
const form = ref<ModelEntry>(blank())

function blank(): ModelEntry {
  return { id: '', vendor: '', model: '', category: '', spec: '', power: '', notes: '', count: 0 }
}

const stages = [
  { key: 'procure', label: '', cls: 'text-purple-600' },
  { key: 'stock', label: '', cls: 'text-gray-500' },
  { key: 'active', label: '', cls: 'text-green-600' },
  { key: 'expired', label: '', cls: 'text-orange-600' },
  { key: 'retire', label: '', cls: 'text-red-600' },
]
const domains = computed(() => Array.from(new Set(rows.value.map(r => r.domain))))

// 保修期 60 个月，按 run_hours 估算已用月份（假设 24x365 满负荷 ≈ 8760h/年）
function derive(r: Equipment): Row {
  const runHours = r.run_hours || 0
  const usedMonths = Math.round((runHours / 8760) * 12)
  const warrantyMonths = Math.max(-12, 60 - usedMonths)
  let stage: Row['stage'] = 'active'
  if (r.status === '故障' || r.status === '退役') stage = 'retire'
  else if (warrantyMonths <= 0) stage = 'expired'
  else if (r.status === '待机' || r.status === '维保') stage = 'stock'
  else if (usedMonths < 3) stage = 'procure'
  return {
    ...r,
    runHours,
    warrantyMonths,
    stage,
    lifePctVal: Math.min(100, Math.round((usedMonths / 60) * 100)),
  }
}

function stageCount(k: string) { return rows.value.filter(r => r.stage === k).length }
function stageLabel(k: string) { return { procure: t.stProcure, stock: t.stStock, active: t.stActive, expired: t.stExpired, retire: t.stRetire }[k] || k }
function stageTag(k: string) {
  return {
    procure: 'b',
    stock: '',
    active: 'g',
    expired: 'a',
    retire: 'r',
  }[k] || ''
}
function warrantyTag(e: Row) {
  return e.warrantyMonths > 12 ? 'g' : e.warrantyMonths > 0 ? 'a' : 'r'
}
function lifePct(e: Row) { return e.lifePctVal }

const filtered = computed(() =>
  rows.value.filter(r =>
    (fStage.value === 'all' || r.stage === fStage.value) &&
    (fDomain.value === 'all' || r.domain === fDomain.value) &&
    (r.name.includes(kw.value) || r.code.includes(kw.value) || (r.model || '').includes(kw.value))
  )
)

function loadLib() {
  modelLib.value = JSON.parse(localStorage.getItem(KEY_LIB) || 'null') || buildLibFromRows()
  localStorage.setItem(KEY_LIB, JSON.stringify(modelLib.value))
}
// 从真实设备聚合初始型号库
function buildLibFromRows(): ModelEntry[] {
  const map = new Map<string, ModelEntry>()
  rows.value.forEach(r => {
    const key = `${r.vendor}|${r.model}`
    if (!map.has(key)) map.set(key, { id: 'ml' + map.size, vendor: r.vendor, model: r.model, category: r.category, spec: '', power: '', notes: '', count: 0 })
    map.get(key)!.count++
  })
  return Array.from(map.values())
}
function openCreate() {
  editing.value = false
  form.value = blank()
  showModal.value = true
}
function edit(m: ModelEntry) {
  editing.value = true
  form.value = { ...m }
  showModal.value = true
}
function save() {
  if (editing.value) {
    const i = modelLib.value.findIndex(m => m.id === form.value.id)
    if (i >= 0) modelLib.value[i] = { ...form.value }
  } else {
    modelLib.value.push({ ...form.value, id: 'ml' + Date.now(), count: 0 })
  }
  localStorage.setItem(KEY_LIB, JSON.stringify(modelLib.value))
  showModal.value = false
}
function remove(id: string) {
  modelLib.value = modelLib.value.filter(m => m.id !== id)
  localStorage.setItem(KEY_LIB, JSON.stringify(modelLib.value))
}

async function load() {
  loading.value = true
  try {
    const res = await listEquipment({ size: 1000 })
    rows.value = (res.items || []).map(derive)
    if (!localStorage.getItem(KEY_LIB)) loadLib()
    else modelLib.value = JSON.parse(localStorage.getItem(KEY_LIB) || '[]')
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
