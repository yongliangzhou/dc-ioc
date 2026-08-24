<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4" stroke-linecap="round"/>
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <div class="seg">
          <button class="seg-btn" :class="{ active: view === 'month' }" @click="view = 'month'">{{ t.month }}</button>
          <button class="seg-btn" :class="{ active: view === 'week' }" @click="view = 'week'">{{ t.week }}</button>
        </div>
        <button class="btn-ghost" @click="goToday">{{ t.today }}</button>
      </div>
    </div>

    <div class="legend">
      <span class="lg due"></span>{{ t.legendDue }}
      <span class="lg done"></span>{{ t.legendDone }}
    </div>

    <div v-if="loading" class="loading-box"><div class="spinner"></div><span>{{ loadingText }}</span></div>
    <div v-else class="cal">
      <div class="cal-grid" :class="{ week: view === 'week' }">
        <div v-for="d in weekHeads" :key="d" class="cal-dow">{{ d }}</div>
        <div
          v-for="cell in cells"
          :key="cell.key"
          class="cal-cell"
          :class="{ outside: cell.outside, today: cell.isToday }"
          @click="cell.isCurrent && openNew(cell.date)"
        >
          <div class="cell-date">
            <span>{{ cell.day }}</span>
            <span v-if="cell.isToday" class="today-dot"></span>
          </div>
          <div class="cell-events">
            <div v-for="ev in cell.events" :key="ev.id" class="ev" :class="ev.kind" :title="ev.title" @click.stop="openEv(ev)">
              <span class="ev-ic">{{ ev.kind === 'due' ? '!' : '✓' }}</span>{{ ev.title }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情/新建抽屉 -->
    <div v-if="drawer" class="modal-mask" @click.self="drawer = null">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>{{ drawerMode === 'new' ? t.clickNew : (drawer.kind === 'due' ? t.duePlans : t.records) }}</h2>
          <button class="x" @click="drawer = null" aria-label="close">×</button>
        </header>
        <div class="drawer-body">
          <template v-if="drawerMode === 'new'">
            <p class="content">{{ drawer.date }}</p>
            <div class="fld"><span>{{ tl('维保人') }}</span><input v-model="recForm.maintainedBy" class="inp" :placeholder="tl('如 李四')" /></div>
            <div class="fld"><span>{{ tl('计划名称') }}</span><input v-model="recForm.planName" class="inp" :placeholder="tl('如 机房空调季度保养')" /></div>
            <div class="fld"><span>{{ tl('维保内容') }}</span><textarea v-model="recForm.actionDescription" class="area" rows="2"></textarea></div>
            <div class="drawer-actions">
              <button class="btn-primary" :disabled="saving" @click="saveRec">{{ tl('保存') }}</button>
              <button class="btn-ghost" @click="drawer = null">{{ tl('取消') }}</button>
            </div>
          </template>
          <template v-else>
            <div class="row"><span>{{ tl('状态') }}：</span><b :class="drawer.kind === 'due' ? 'bad' : 'good'">{{ drawer.kind === 'due' ? t.duePlans : t.records }}</b></div>
            <div class="row"><span>{{ tl('维保人') }}：</span><b>{{ drawer.meta?.maintainedBy || drawer.meta?.owner || '—' }}</b></div>
            <div class="row"><span>{{ tl('时间') }}：</span><b>{{ drawer.date }}</b></div>
            <p class="content">{{ drawer.title }}</p>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/modules/auth'
import { getMaintenancePlanList, getMaintenanceRecords, createMaintenanceRecord } from '@/api/maintenance'

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('mntCalendar') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})
const tl = (k: string) => {
  const nav = (raw('nav') || {}) as any
  return (nav && typeof nav === 'object' && nav[k]) || k
}
const auth = useAuthStore()
const me = computed(() => auth.user?.username || 'me')

const view = ref<'month' | 'week'>('month')
const loading = ref(false)
const loadingText = (() => {
  const kc = (raw('knowledgeCollab') || {}) as any
  return (kc && typeof kc === 'object' && kc.loading) || 'Loading…'
})()
const today = new Date()
const cursor = ref(new Date(today.getFullYear(), today.getMonth(), today.getDate()))

interface CalEvent { id: string; kind: 'due' | 'done'; title: string; date: string; meta?: any }
const events = ref<CalEvent[]>([])

const weekHeads = ['一', '二', '三', '四', '五', '六', '日']

const cells = computed(() => {
  const base = cursor.value
  let start: Date
  if (view.value === 'week') {
    const dow = (base.getDay() + 6) % 7 // 周一=0
    start = new Date(base); start.setDate(base.getDate() - dow)
  } else {
    start = new Date(base.getFullYear(), base.getMonth(), 1)
    const dow = (start.getDay() + 6) % 7
    start.setDate(start.getDate() - dow)
  }
  const count = view.value === 'week' ? 7 : 42
  const arr: { key: string; day: number; date: string; outside: boolean; isToday: boolean; isCurrent: boolean; events: CalEvent[] }[] = []
  for (let i = 0; i < count; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i)
    const dateStr = d.toISOString().slice(0, 10)
    const isCurrentMonth = d.getMonth() === cursor.value.getMonth()
    arr.push({
      key: dateStr, day: d.getDate(), date: dateStr,
      outside: view.value === 'month' && !isCurrentMonth,
      isToday: dateStr === today.toISOString().slice(0, 10),
      isCurrent: true,
      events: events.value.filter(e => e.date === dateStr),
    })
  }
  return arr
})

async function load() {
  loading.value = true
  try {
    const [plans, recs] = await Promise.all([getMaintenancePlanList(), getMaintenanceRecords()])
    const evs: CalEvent[] = []
    for (const p of plans) {
      if (p.nextDueDate) {
        evs.push({ id: 'plan-' + p.id, kind: 'due', title: p.name, date: (p.nextDueDate as string).slice(0, 10), meta: p })
      }
    }
    for (const r of recs) {
      const d = (r.startedAt || '').slice(0, 10)
      if (d) evs.push({ id: 'rec-' + r.id, kind: 'done', title: r.planName || r.actionDescription || '维保记录', date: d, meta: r })
    }
    events.value = evs
  } catch {
    events.value = []
  } finally {
    loading.value = false
  }
}

const drawer = ref<CalEvent & { date: string } | null>(null)
const drawerMode = ref<'new' | 'view'>('view')
const saving = ref(false)
const recForm = ref({ maintainedBy: '', planName: '', actionDescription: '' })

function openEv(ev: CalEvent) { drawer.value = { ...ev }; drawerMode.value = 'view' }
function openNew(date: string) { drawer.value = { id: 'new', kind: 'done', title: '', date, meta: {} }; drawerMode.value = 'new'; recForm.value = { maintainedBy: me.value, planName: '', actionDescription: '' } }
function goToday() { cursor.value = new Date(today.getFullYear(), today.getMonth(), today.getDate()) }

async function saveRec() {
  if (!recForm.value.maintainedBy) return
  saving.value = true
  try {
    await createMaintenanceRecord({
      planName: recForm.value.planName,
      maintainedBy: recForm.value.maintainedBy,
      status: 'completed', result: 'pass',
      startedAt: (drawer.value!.date) + ' 09:00',
      actionDescription: recForm.value.actionDescription,
    })
    drawer.value = null
    await load()
  } finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.seg { display: inline-flex; gap: 4px; background: var(--bg2); border: 1px solid var(--line); border-radius: 999px; padding: 3px; }
.seg-btn { background: transparent; border: none; color: var(--txt2); padding: 5px 14px; border-radius: 999px; cursor: pointer; font-size: 12px; transition: .15s; }
.seg-btn.active { background: linear-gradient(90deg,var(--cyan),var(--blue)); color: #04121a; font-weight: 700; }
.legend { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--txt2); margin-bottom: 12px; }
.lg { width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-left: 12px; }
.lg.due { background: #fbbf24; } .lg.done { background: #4ade80; }
.cal { width: 100%; background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 10px; overflow-x: auto; }
.cal-grid { display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: 8px; min-width: 880px; }
.cal-dow { text-align: center; font-size: 12px; color: var(--txt2); padding: 6px 0; font-weight: 600; }
.cal-cell { min-height: 120px; background: var(--bg2); border: 1px solid var(--line); border-radius: 8px; padding: 6px; cursor: pointer; transition: border-color .15s; }
.cal-cell.outside { opacity: .45; }
.cal-cell.today { border-color: var(--cyan); box-shadow: var(--glow); }
.cal-cell:hover { border-color: var(--cyan); }
.cal-grid.week .cal-cell { min-height: 340px; }
.cell-date { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--txt2); }
.today-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); box-shadow: var(--glow); }
.cell-events { margin-top: 6px; display: flex; flex-direction: column; gap: 4px; }
.ev { font-size: 11px; padding: 2px 6px; border-radius: 6px; white-space: normal; word-break: break-word; display: flex; align-items: center; gap: 5px; }
.ev-ic { font-weight: 800; font-size: 10px; }
.ev.due { background: rgba(245,158,11,.16); color: #fbbf24; }
.ev.done { background: rgba(34,197,94,.14); color: #4ade80; }
.drawer { width: 420px; max-width: 92vw; background: var(--panel); height: 100%; overflow-y: auto; padding: 18px 20px; border-left: 1px solid var(--line); }
.drawer-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.drawer-head h2 { font-size: 16px; color: var(--txt-strong); }
.x { background: transparent; border: none; color: var(--txt2); font-size: 20px; cursor: pointer; line-height: 1; }
.x:hover { color: var(--txt-strong); }
.row { font-size: 13px; margin: 6px 0; color: var(--txt2); } .row b { color: var(--txt-strong); } .row b.bad { color: #fbbf24; } .row b.good { color: #4ade80; }
.content { font-size: 13px; line-height: 1.7; white-space: pre-wrap; background: var(--bg2); border-radius: 10px; padding: 12px; margin: 10px 0; color: var(--txt); }
.fld { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--txt2); margin-bottom: 10px; }
.inp { background: var(--bg2); border: 1px solid var(--line); color: var(--txt); border-radius: 8px; padding: 9px 11px; font-family: inherit; font-size: 13px; outline: none; transition: .15s; }
.inp:focus { border-color: var(--cyan); box-shadow: var(--glow); }
.area { background: var(--bg2); border: 1px solid var(--line); color: var(--txt); border-radius: 8px; padding: 10px; resize: vertical; font-family: inherit; font-size: 13px; outline: none; }
.area:focus { border-color: var(--cyan); box-shadow: var(--glow); }
.drawer-actions { display: flex; gap: 10px; margin-top: 12px; }
@media(max-width:720px){ .drawer{ width: 100%; } }
</style>
