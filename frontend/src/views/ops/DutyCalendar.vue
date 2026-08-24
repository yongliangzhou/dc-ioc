<template>
  <div class="duty-cal">
    <div class="view-head">
      <h1>{{ tl('排班日历') }}</h1>
      <span class="sub">{{ tl('值班安排 · 日/夜班可视化') }}</span>
      <div class="cal-tools">
        <button class="btn-sm" @click="prevMonth">‹</button>
        <span class="cur">{{ year }} - {{ String(month + 1).padStart(2, '0') }}</span>
        <button class="btn-sm" @click="nextMonth">›</button>
        <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate()">{{ tl('新建排班') }}</button>
      </div>
    </div>

    <div class="legend">
      <span><i class="dot day" /> {{ tl('白班') }}</span>
      <span><i class="dot night" /> {{ tl('夜班') }}</span>
    </div>

    <div class="week-head">
      <span v-for="w in weekNames" :key="w">{{ w }}</span>
    </div>
    <div class="cal-grid">
      <div
        v-for="cell in cells"
        :key="cell.key"
        class="cal-cell"
        :class="{ muted: !cell.inMonth }"
        @click="openCreate(cell.date)"
      >
        <div class="d-num">{{ cell.day }}</div>
        <div class="shifts">
          <div v-for="s in shiftsOf(cell.date)" :key="s.id" class="shift-pill" :class="s.shift">
            <b>{{ s.shift === 'day' ? tl('白') : tl('夜') }}</b>
            {{ leaderOf(s) }}
            <span class="cnt">({{ (s.members || []).length }})</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑/新建抽屉 -->
    <transition name="slide">
      <div v-if="editing" class="drawer" @click.self="closeEditor">
        <div class="drawer-card">
          <div class="drawer-head">
            <h3>{{ editing.id ? tl('编辑排班') : tl('新建排班') }} · {{ editing.date }}</h3>
            <button class="x" @click="closeEditor">✕</button>
          </div>
          <label class="fld">
            <span>{{ tl('班次') }}</span>
            <select v-model="editing.shift">
              <option value="day">{{ tl('白班') }}</option>
              <option value="night">{{ tl('夜班') }}</option>
            </select>
          </label>
          <label class="fld">
            <span>{{ tl('值班长') }}</span>
            <input v-model="editing.leader" type="text" placeholder="姓名" />
          </label>
          <label class="fld">
            <span>{{ tl('成员') }}（每行一个，可加|角色）</span>
            <textarea v-model="membersText" rows="4" placeholder="张三|运维工程师&#10;李四|巡检"></textarea>
          </label>
          <label class="fld">
            <span>{{ tl('备注') }}</span>
            <input v-model="editing.note" type="text" />
          </label>
          <div class="drawer-actions">
            <button class="btn-sm danger" v-if="editing.id" v-bind="authState('write')" @click="remove">{{ tl('删除') }}</button>
            <button class="btn-sm primary" v-bind="authState('write')" @click="save">{{ tl('保存') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDutyShifts, createDutyShift, updateDutyShift, deleteDutyShift, type ShiftView, type ShiftMember } from '@/api/duty'
import { usePermission, type PermAction } from '@/hooks/usePermission'

const { t: tl } = useI18n()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const weekNames = [tl('日'), tl('一'), tl('二'), tl('三'), tl('四'), tl('五'), tl('六')]
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth())
const shifts = ref<ShiftView[]>([])
const editing = ref<ShiftView | null>(null)
const membersText = ref('')

function parseMembers(members: ShiftMember[] | undefined): string[] {
  return (members || []).map((m) => m.name)
}
function leaderOf(s: ShiftView) {
  return s.leader || parseMembers(s.members)[0] || '-'
}
function shiftsOf(date: string): ShiftView[] {
  return shifts.value.filter((s) => (s.date || '').slice(0, 10) === date)
}

const cells = computed(() => {
  const first = new Date(year.value, month.value, 1)
  const startDay = first.getDay()
  const daysInMonth = new Date(year.value, month.value + 1, 0).getDate()
  const out: { key: string; date: string; day: number; inMonth: boolean }[] = []
  // 前置上个月
  for (let i = startDay - 1; i >= 0; i--) {
    const d = new Date(year.value, month.value, -i)
    out.push({ key: 'p' + i, date: iso(d), day: d.getDate(), inMonth: false })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dt = new Date(year.value, month.value, d)
    out.push({ key: 'm' + d, date: iso(dt), day: d, inMonth: true })
  }
  // 补齐到 6 行
  while (out.length % 7 !== 0) {
    const last = out[out.length - 1]
    const d = new Date(year.value, month.value, Number(last.day) + 1)
    out.push({ key: 'n' + out.length, date: iso(d), day: d.getDate(), inMonth: false })
  }
  return out
})

function iso(d: Date) {
  return d.toISOString().slice(0, 10)
}

function prevMonth() {
  if (month.value === 0) { month.value = 11; year.value-- } else month.value--
  load()
}
function nextMonth() {
  if (month.value === 11) { month.value = 0; year.value++ } else month.value++
  load()
}

function openCreate(date?: string) {
  editing.value = {
    id: 0,
    date: date || iso(new Date(year.value, month.value, 1)),
    shift: 'day',
    members: [],
    leader: '',
    note: '',
  }
  membersText.value = ''
}
function openEdit(s: ShiftView) {
  editing.value = { ...s }
  membersText.value = (s.members || []).map((m) => (m.role ? `${m.name}|${m.role}` : m.name)).join('\n')
}
function closeEditor() {
  editing.value = null
}
function save() {
  if (!editing.value) return
  const members: ShiftMember[] = membersText.value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const [name, role] = l.split('|')
      return { name, role: role || undefined }
    })
  const payload = { date: editing.value.date, shift: editing.value.shift, leader: editing.value.leader, note: editing.value.note, members }
  if (editing.value.id) {
    updateDutyShift(editing.value.id, payload).then(load)
  } else {
    createDutyShift(payload).then(load)
  }
  closeEditor()
}
function remove() {
  if (editing.value?.id) deleteDutyShift(editing.value.id).then(load)
  closeEditor()
}

async function load() {
  const from = iso(new Date(year.value, month.value, 1))
  const to = iso(new Date(year.value, month.value + 1, 0))
  try {
    shifts.value = await getDutyShifts(from, to)
  } catch {
    shifts.value = []
  }
}

onMounted(load)
</script>

<style scoped>
.duty-cal { padding: 16px 20px 32px; }
.view-head { display: flex; align-items: center; gap: 14px; }
.view-head h1 { font-size: 20px; margin: 0; color: #e2e8f0; }
.sub { color: #64748b; font-size: 13px; }
.cal-tools { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.cal-tools .cur { color: #cbd5e1; font-size: 14px; min-width: 70px; text-align: center; }
.btn-sm { color: #cbd5e1; border: 1px solid var(--line); background: transparent; border-radius: 8px; padding: 5px 12px; cursor: pointer; }
.btn-sm.primary { background: var(--cyan); color: #06121f; border-color: var(--cyan); font-weight: 700; }
.legend { display: flex; gap: 16px; margin: 14px 0; font-size: 12px; color: #94a3b8; }
.legend .dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-right: 5px; }
.dot.day { background: #22d3ee; } .dot.night { background: #6366f1; }
.week-head, .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.week-head { margin-bottom: 6px; }
.week-head span { text-align: center; color: #64748b; font-size: 12px; padding: 6px 0; }
.cal-cell { background: #0f172a; border: 1px solid var(--line); border-radius: 10px; min-height: 96px; padding: 6px; cursor: pointer; transition: border-color .15s; }
.cal-cell:hover { border-color: var(--cyan); }
.cal-cell.muted { opacity: .4; }
.d-num { font-size: 13px; color: #94a3b8; margin-bottom: 4px; }
.shifts { display: flex; flex-direction: column; gap: 4px; }
.shift-pill { font-size: 11px; padding: 3px 6px; border-radius: 6px; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shift-pill.day { background: rgba(34,211,238,.15); border-left: 3px solid #22d3ee; }
.shift-pill.night { background: rgba(99,102,241,.15); border-left: 3px solid #6366f1; }
.shift-pill b { margin-right: 3px; }
.shift-pill .cnt { color: #64748b; }
.drawer { position: fixed; inset: 0; background: rgba(2,6,23,.6); display: flex; justify-content: flex-end; z-index: 50; }
.drawer-card { width: 380px; max-width: 90vw; height: 100%; background: #0f172a; border-left: 1px solid #1e293b; padding: 22px; overflow-y: auto; }
.drawer-head { display: flex; justify-content: space-between; align-items: flex-start; }
.drawer-head h3 { margin: 0 0 4px; color: #e2e8f0; font-size: 15px; }
.fld { display: flex; flex-direction: column; gap: 6px; margin: 14px 0; font-size: 13px; color: #94a3b8; }
.fld input, .fld select, .fld textarea { background: #1e293b; border: 1px solid var(--line); color: #e2e8f0; border-radius: 8px; padding: 8px 10px; font-family: inherit; }
.drawer-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 18px; }
.x { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 16px; }
.slide-enter-active, .slide-leave-active { transition: opacity .2s; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
</style>
