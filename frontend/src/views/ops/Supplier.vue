<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <button class="btn-primary" @click="openCreate">{{ t.newSupplier }}</button>
      </div>
    </div>

    <!-- 概览 -->
    <div class="grid cols-4">
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.total }}</div>
        <div class="text-2xl font-semibold" style="color:var(--txt-strong)">{{ suppliers.length }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.avgScore }}</div>
        <div class="text-2xl font-semibold" style="color:var(--blue)">{{ avgScore }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.excellent }}</div>
        <div class="text-2xl font-semibold" style="color:var(--green)">{{ suppliers.filter(s => s.score >= 85).length }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.needImprove }}</div>
        <div class="text-2xl font-semibold" style="color:var(--red)">{{ suppliers.filter(s => s.score < 70).length }}</div>
      </div>
    </div>

    <!-- 列表 -->
    <div class="grid cols-3">
      <div v-for="s in suppliers" :key="s.id" class="card flex flex-col">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold cell-strong">{{ s.name }}</h3>
            <p class="text-xs mt-1" style="color:var(--txt2)">{{ t.category }}: {{ s.category }}</p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold" :style="{ color: scoreColor(s.score) }">{{ s.score }}</div>
            <div class="text-xs" style="color:var(--txt3)">{{ t.score }}</div>
          </div>
        </div>
        <div class="mt-3 text-xs space-y-1 flex-1" style="color:var(--txt2)">
          <div>{{ t.contact }}: {{ s.contact }} / {{ s.phone }}</div>
          <div>{{ t.contractNo }}: {{ s.contractNo }}</div>
          <div>{{ t.validTo }}: {{ s.validTo }}</div>
          <div>{{ t.sla }}: {{ s.sla }}</div>
        </div>
        <!-- 评分维度 -->
        <div class="mt-3 space-y-1">
          <div v-for="dim in dims" :key="dim.k" class="flex items-center gap-2 text-xs" style="color:var(--txt2)">
            <span style="width:64px">{{ t['dim_' + dim.k] || dim.k }}</span>
            <div class="flex-1 pbar"><i :style="{ width: (s.detail[dim.k] || 0) + '%' }"></i></div>
            <span style="width:32px;text-align:right">{{ s.detail[dim.k] || 0 }}</span>
          </div>
        </div>
        <div class="mt-3 flex gap-2">
          <button class="btn-primary flex-1" @click="rate(s)">{{ t.rate }}</button>
          <button class="btn-ghost" @click="edit(s)">{{ t.edit }}</button>
          <button class="btn-danger" @click="remove(s.id)">{{ t.del }}</button>
        </div>
      </div>
    </div>
    <div v-if="!suppliers.length" class="card empty-box">{{ t.empty }}</div>

    <!-- 弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ editing ? t.editSupplier : t.newSupplier }}</h3>
        <div class="space-y">
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.name }}</span><input v-model="form.name" class="inp" :placeholder="t.namePlaceholder" /></div>
            <div class="field"><span>{{ t.category }}</span><input v-model="form.category" class="inp" :placeholder="t.categoryPlaceholder" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.contact }}</span><input v-model="form.contact" class="inp" /></div>
            <div class="field"><span>{{ t.phone }}</span><input v-model="form.phone" class="inp" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.contractNo }}</span><input v-model="form.contractNo" class="inp" /></div>
            <div class="field"><span>{{ t.validTo }}</span><input v-model="form.validTo" type="date" class="inp" /></div>
          </div>
          <div class="field"><span>{{ t.sla }}</span><input v-model="form.sla" class="inp" :placeholder="t.slaPlaceholder" /></div>
          <div v-if="editing">
            <label class="block text-xs" style="margin-bottom:8px;color:var(--txt2)">{{ t.rateDims }}</label>
            <div class="space-y-2">
              <div v-for="dim in dims" :key="dim.k" class="flex items-center gap-2" style="color:var(--txt2)">
                <span style="width:80px;font-size:12px">{{ t['dim_' + dim.k] || dim.k }}</span>
                <input type="range" min="0" max="100" v-model.number="form.detail[dim.k]" class="flex-1 inp" style="padding:0" />
                <span style="width:32px;text-align:right;font-size:12px">{{ form.detail[dim.k] }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showModal = false">{{ t.cancel }}</button>
          <button class="btn-primary" @click="save">{{ t.save }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('supplier') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

interface Supplier {
  id: string; name: string; category: string; contact: string; phone: string
  contractNo: string; validTo: string; sla: string; score: number
  detail: Record<string, number>
}

const KEY = 'w9_suppliers'
const dims = [
  { k: 'quality' },
  { k: 'response' },
  { k: 'price' },
  { k: 'sla' },
  { k: 'cooperation' },
]
const suppliers = ref<Supplier[]>([])
const showModal = ref(false)
const editing = ref(false)
const form = ref<Supplier>(blank())

function blank(): Supplier {
  return { id: '', name: '', category: '', contact: '', phone: '', contractNo: '', validTo: '', sla: '', score: 0, detail: { quality: 80, response: 80, price: 80, sla: 80, cooperation: 80 } }
}

function load() {
  suppliers.value = JSON.parse(localStorage.getItem(KEY) || 'null') || seed()
  localStorage.setItem(KEY, JSON.stringify(suppliers.value))
}
function seed(): Supplier[] {
  return [
    { id: 'sp1', name: '华信电力', category: '供配电运维', contact: '王工', phone: '13800000001', contractNo: 'HT-2025-PW-01', validTo: '2026-12-31', sla: '故障 4h 到场', score: 92, detail: { quality: 95, response: 90, price: 88, sla: 94, cooperation: 91 } },
    { id: 'sp2', name: '云网通信', category: '网络集成', contact: '李经理', phone: '13800000002', contractNo: 'HT-2025-NW-03', validTo: '2026-06-30', sla: '故障 2h 响应', score: 81, detail: { quality: 82, response: 85, price: 78, sla: 83, cooperation: 77 } },
    { id: 'sp3', name: '安盾消防', category: '消防维保', contact: '赵工', phone: '13800000003', contractNo: 'HT-2025-FR-02', validTo: '2025-12-31', sla: '月度巡检', score: 68, detail: { quality: 70, response: 65, price: 72, sla: 66, cooperation: 67 } },
    { id: 'sp4', name: '数擎存储', category: '存储/备份', contact: '陈工', phone: '13800000004', contractNo: 'HT-2025-ST-05', validTo: '2027-03-31', sla: '7x24 支持', score: 88, detail: { quality: 90, response: 87, price: 84, sla: 89, cooperation: 90 } },
  ]
}

const avgScore = computed(() => {
  if (!suppliers.value.length) return '—'
  return (suppliers.value.reduce((a, s) => a + s.score, 0) / suppliers.value.length).toFixed(1)
})
function scoreColor(s: number) {
  return s >= 85 ? 'var(--green)' : s >= 70 ? 'var(--blue)' : 'var(--red)'
}

function openCreate() {
  editing.value = false
  form.value = blank()
  showModal.value = true
}
function edit(s: Supplier) {
  editing.value = true
  form.value = { ...s, detail: { ...s.detail } }
  showModal.value = true
}
function save() {
  const d = form.value.detail
  form.value.score = Math.round((d.quality + d.response + d.price + d.sla + d.cooperation) / 5)
  if (editing.value) {
    const i = suppliers.value.findIndex(s => s.id === form.value.id)
    if (i >= 0) suppliers.value[i] = { ...form.value }
  } else {
    suppliers.value.push({ ...form.value, id: 'sp' + Date.now() })
  }
  localStorage.setItem(KEY, JSON.stringify(suppliers.value))
  showModal.value = false
}
function remove(id: string) {
  suppliers.value = suppliers.value.filter(s => s.id !== id)
  localStorage.setItem(KEY, JSON.stringify(suppliers.value))
}
function rate(s: Supplier) {
  const q = Number(prompt(t.promptQuality, String(s.detail.quality))) || s.detail.quality
  const r = Number(prompt(t.promptResponse, String(s.detail.response))) || s.detail.response
  const p = Number(prompt(t.promptPrice, String(s.detail.price))) || s.detail.price
  const sl = Number(prompt(t.promptSla, String(s.detail.sla))) || s.detail.sla
  const c = Number(prompt(t.promptCoop, String(s.detail.cooperation))) || s.detail.cooperation
  s.detail = { quality: q, response: r, price: p, sla: sl, cooperation: c }
  s.score = Math.round((q + r + p + sl + c) / 5)
  localStorage.setItem(KEY, JSON.stringify(suppliers.value))
}

onMounted(load)
</script>
