<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ t.title }}</h1>
        <p class="page-sub">{{ t.sub }}</p>
      </div>
      <div class="page-actions">
        <input v-model="kw" class="inp" :placeholder="t.search" />
        <button class="btn green" @click="openEditor()">+ {{ t.newEntry }}</button>
      </div>
    </header>

    <section class="kpi-row">
      <div class="kpi"><span class="kpi-v">{{ insideCount }}</span><span class="kpi-l">{{ t.stillIn }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ items.length }}</span><span class="kpi-l">{{ t.history }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ personCount }}</span><span class="kpi-l">{{ t.person }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ itemCount }}</span><span class="kpi-l">{{ t.item }}</span></div>
    </section>

    <div class="seg">
      <button v-for="f in filters" :key="f.key" class="seg-btn" :class="{ active: fType === f.key }" @click="fType = f.key">{{ f.label }}</button>
    </div>

    <div class="list">
      <article v-for="r in filtered" :key="r.id" class="row-card" :class="{ inside: !r.outAt }">
        <div class="row-main">
          <div class="row-title">
            {{ r.name }}
            <span class="badge" :class="r.type === 'person' ? 'blue' : 'amber'">{{ r.type === 'person' ? t.person : t.item }}</span>
            <span v-if="!r.outAt" class="badge green">{{ t.stillIn }}</span>
          </div>
          <div class="row-sub">
            <span class="muted">{{ r.org || '—' }}</span> · <span class="muted">{{ t.area }}：{{ r.area || '—' }}</span> ·
            <span class="muted">{{ t.purpose }}：{{ r.purpose || '—' }}</span>
          </div>
          <div class="row-sub small">
            📥 {{ fmt(r.inAt) }} <template v-if="r.outAt"> → 📤 {{ fmt(r.outAt) }}</template>
            <span v-if="r.carriedBy"> · {{ t.carriedBy }}：{{ r.carriedBy }}</span>
          </div>
          <div v-if="r.carryIn || r.carryOut" class="row-sub small">
            <span v-if="r.carryIn">📦 {{ t.carryIn }}：{{ r.carryIn }}</span>
            <span v-if="r.carryOut"> · 📦 {{ t.carryOut }}：{{ r.carryOut }}</span>
          </div>
        </div>
        <div class="row-right">
          <button v-if="!r.outAt" class="btn sm green" @click="signOut(r)">{{ t.leave }}</button>
          <button class="btn sm ghost" @click="askRemove(r)">{{ t.del }}</button>
        </div>
      </article>
      <div v-if="!filtered.length" class="empty">{{ t.empty }}</div>
    </div>

    <div v-if="editor" class="mask" @click.self="editor = false">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>+ {{ t.newEntry }}</h2>
          <button class="x" @click="editor = false">×</button>
        </header>
        <div class="drawer-body">
          <div class="seg" style="margin-bottom:12px">
            <button class="seg-btn" :class="{ active: form.type === 'person' }" @click="form.type = 'person'">{{ t.person }}</button>
            <button class="seg-btn" :class="{ active: form.type === 'item' }" @click="form.type = 'item'">{{ t.item }}</button>
          </div>
          <label class="fld"><span>{{ t.name }}</span><input v-model="form.name" class="inp" :class="{ invalid: touched.name && errors.name }" :placeholder="t.namePlaceholder" @blur="validate('name', form)" /></label>
          <label class="fld"><span>{{ t.org }}</span><input v-model="form.org" class="inp" :placeholder="t.orgPlaceholder" /></label>
          <label class="fld"><span>{{ t.purpose }}</span><input v-model="form.purpose" class="inp" :placeholder="t.purposePlaceholder" /></label>
          <label class="fld"><span>{{ t.area }}</span><input v-model="form.area" class="inp" :placeholder="t.areaPlaceholder" /></label>
          <label class="fld"><span>{{ t.carriedBy }}</span><input v-model="form.carriedBy" class="inp" :placeholder="t.carriedByPlaceholder" /></label>
          <label class="fld"><span>{{ t.carryIn }}</span><input v-model="form.carryIn" class="inp" :placeholder="t.carryPlaceholder" /></label>
          <label class="fld"><span>{{ t.carryOut }}</span><input v-model="form.carryOut" class="inp" :placeholder="t.carryPlaceholder" /></label>
          <label class="fld"><span>{{ t.inAt }}</span><input v-model="form.inAt" class="inp" type="datetime-local" /></label>
          <div v-if="touched.name && errors.name" class="err">{{ errors.name }}</div>
          <div class="drawer-actions"><button class="btn green" :disabled="saving" @click="save">{{ t.save }}</button><button class="btn ghost" @click="editor = false">{{ t.cancel }}</button></div>
        </div>
      </aside>
    </div>

    <div v-if="showDel" class="confirm-mask" @click.self="showDel = false">
      <div class="confirm-box">
        <h3>{{ t.confirmDeleteTitle }}</h3>
        <p>{{ t.confirmDelete }}</p>
        <div class="confirm-actions">
          <button class="btn ghost" @click="showDel = false">{{ t.cancel }}</button>
          <button class="btn danger" @click="confirmRemove">{{ t.del }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/modules/auth'
import { useFormValidation, required } from '@/composables/useFormValidation'

type AType = 'person' | 'item'
export interface AccessRecord {
  id: string; type: AType; name: string; org: string; purpose: string
  area: string; carriedBy: string; carryIn: string; carryOut: string
  inAt: string; outAt: string
}

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('roomAccess') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})
const auth = useAuthStore()
const me = computed(() => auth.user?.username || 'me')

const LS = 'room_access'
function load(): AccessRecord[] {
  const seed = seedData()
  try { const s = JSON.parse(localStorage.getItem(LS) || 'null'); if (s && Array.isArray(s) && s.length) return s } catch {}
  localStorage.setItem(LS, JSON.stringify(seed)); return seed
}
function persist() { localStorage.setItem(LS, JSON.stringify(items.value)) }

const items = ref<AccessRecord[]>(load())
const kw = ref('')
const fType = ref<string>('all')
const filters = computed(() => [{ key: 'all', label: t.all }, { key: 'person', label: t.person }, { key: 'item', label: t.item }])

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  return items.value
    .filter(r => fType.value === 'all' || r.type === fType.value)
    .filter(r => !q || (r.name + r.org + r.area).toLowerCase().includes(q))
    .sort((a, b) => (b.inAt || '').localeCompare(a.inAt || ''))
})

const insideCount = computed(() => items.value.filter(r => !r.outAt).length)
const personCount = computed(() => items.value.filter(r => r.type === 'person').length)
const itemCount = computed(() => items.value.filter(r => r.type === 'item').length)

const editor = ref(false)
const saving = ref(false)
const { errors, touched, validate, validateAll, reset: resetForm } = useFormValidation({
  rules: { name: [required(t.name + ' 不能为空')] },
})
const form = ref<Partial<AccessRecord>>({ type: 'person', name: '', org: '', purpose: '', area: '', carriedBy: '', carryIn: '', carryOut: '', inAt: '', outAt: '' })

function openEditor() {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  form.value = { type: 'person', name: '', org: '', purpose: '', area: '', carriedBy: me.value, carryIn: '', carryOut: '', inAt: local, outAt: '' }
  resetForm(); editor.value = true
}
function genId() { return 'RA-' + Date.now().toString(36) }
function save() {
  if (!validateAll(form.value as unknown as Record<string, unknown>)) return
  const rec: AccessRecord = {
    id: genId(), type: (form.value.type as AType) || 'person', name: form.value.name!, org: form.value.org || '',
    purpose: form.value.purpose || '', area: form.value.area || '', carriedBy: form.value.carriedBy || '',
    carryIn: form.value.carryIn || '', carryOut: form.value.carryOut || '',
    inAt: (form.value.inAt || '').replace('T', ' '), outAt: '',
  }
  items.value = [rec, ...items.value]; persist(); editor.value = false
}
function signOut(r: AccessRecord) { r.outAt = new Date().toISOString().replace('T', ' ').slice(0, 16); persist() }
const showDel = ref(false)
const delTarget = ref<AccessRecord | null>(null)
function askRemove(r: AccessRecord) { delTarget.value = r; showDel.value = true }
function confirmRemove() {
  if (delTarget.value) { items.value = items.value.filter(x => x.id !== delTarget.value!.id); persist() }
  showDel.value = false; delTarget.value = null
}
function fmt(d?: string) { return d ? String(d).replace('T', ' ') : '—' }

function seedData(): AccessRecord[] {
  const now = Date.now()
  const iso = (h: number) => new Date(now - h * 36e5).toISOString().slice(0, 16).replace('T', ' ')
  return [
    { id: 'RA-1', type: 'person', name: '李伟', org: '维保外包', purpose: '空调保养', area: 'A 区机房', carriedBy: '张工', carryIn: '工具箱', carryOut: '', inAt: iso(3), outAt: '' },
    { id: 'RA-2', type: 'person', name: '王芳', org: '网络组', purpose: '交换机上线', area: '网络间', carriedBy: '赵敏', carryIn: '笔记本', carryOut: '', inAt: iso(26), outAt: iso(24) },
    { id: 'RA-3', type: 'item', name: '备用电源模块', org: '备件库', purpose: '更换 UPS 模块', area: '配电室', carriedBy: '孙磊', carryIn: '电源模块', carryOut: '旧模块', inAt: iso(50), outAt: iso(48) },
  ]
}
onMounted(() => {})
</script>

<style scoped>
.page { padding: 18px 22px 40px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; }
.page-sub { color: var(--muted); font-size: 13px; margin-top: 4px; }
.page-actions { display: flex; gap: 8px; align-items: center; }
.inp { background: var(--panel-2); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 7px 10px; width: 100%; box-sizing: border-box; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; }
.kpi-v { font-size: 24px; font-weight: 800; color: var(--cyan); } .kpi-l { font-size: 12px; color: var(--muted); margin-top: 4px; }
.seg { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 14px; }
.seg-btn { background: var(--panel-2); border: 1px solid var(--line); color: var(--muted); padding: 5px 12px; border-radius: 999px; cursor: pointer; font-size: 12px; }
.seg-btn.active { background: var(--cyan); color: #04121a; border-color: var(--cyan); font-weight: 600; }
.list { display: flex; flex-direction: column; gap: 10px; }
.row-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: flex; align-items: center; gap: 12px; }
.row-card.inside { border-color: rgba(34,197,94,.4); }
.row-main { flex: 1; }
.row-title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.row-sub { font-size: 12px; color: var(--muted); margin-top: 3px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.row-sub.small { font-size: 11px; }
.row-right { display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; }
.badge.green { background: rgba(34,197,94,.16); color: #4ade80; } .badge.blue { background: rgba(56,189,248,.16); color: #38bdf8; } .badge.amber { background: rgba(245,158,11,.16); color: #fbbf24; }
.muted { color: var(--muted); } .small { font-size: 11px; }
.empty { text-align: center; color: var(--muted); padding: 40px; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; justify-content: flex-end; z-index: 50; }
.drawer { width: 420px; max-width: 92vw; background: var(--panel); height: 100%; overflow-y: auto; padding: 18px 20px; }
.drawer-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.drawer-head h2 { font-size: 16px; }
.x { background: transparent; border: none; color: var(--muted); font-size: 18px; cursor: pointer; }
.fld { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); margin-bottom: 10px; }
.err { color: #f87171; font-size: 12px; }
.drawer-actions { display: flex; gap: 10px; margin-top: 12px; }
.btn { border: 1px solid var(--line); background: var(--panel-2); color: var(--text); border-radius: 8px; padding: 7px 12px; cursor: pointer; font-size: 13px; }
.btn.sm { padding: 4px 10px; font-size: 12px; } .btn.ghost { background: transparent; } .btn.green { background: var(--green); color: #04121a; border-color: var(--green); font-weight: 600; } .btn:disabled { opacity: .6; }
.btn.danger { background: #ef4444; color: #fff; border-color: #ef4444; font-weight: 600; }
.inp.invalid { border-color: #f87171; }
.confirm-mask { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 60; }
.confirm-box { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; width: 320px; max-width: 90vw; }
.confirm-box h3 { margin: 0 0 8px; font-size: 15px; color: var(--text); }
.confirm-box p { color: var(--muted); font-size: 13px; margin: 0 0 14px; }
.confirm-actions { display: flex; gap: 10px; justify-content: flex-end; }
@media (max-width: 980px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
</style>
