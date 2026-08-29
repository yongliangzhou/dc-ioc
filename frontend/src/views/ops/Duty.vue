<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.duty') }}</h1>
      <span class="sub">{{ tl('人员值班与交接班管理') }}</span>
    </div>
    <AsyncSection :page="page" @retry="page.reload">
      <div class="grid cols-3" v-if="stats">
      <MetricCard metric-name="duty-total" :label="tl('总班次')" :value="stats.totalShifts" quality="good" :online="true" />
      <MetricCard metric-name="duty-today" :label="tl('今日班次')" :value="stats.todayShifts" quality="good" :online="true" />
      <MetricCard metric-name="duty-handover" :label="tl('交接记录')" :value="handovers.length" quality="good" :online="true" />
    </div>

    <!-- 排班表 -->
    <Panel style="margin-top: 16px">
      <div class="flex between" style="margin-bottom: 12px">
        <h5 class="section-title" style="margin: 0">{{ tl('值班表') }}</h5>
        <div class="flex gap">
          <input type="date" v-model="fromStr" class="d-inp" />
          <span class="muted">~</span>
          <input type="date" v-model="toStr" class="d-inp" />
          <button class="btn-sm primary" v-bind="authState('write')" @click="openShiftCreate">
            {{ tl('新建排班') }}
          </button>
        </div>
      </div>
      <div class="tbl" v-if="shifts.length">
        <div class="tbl-head">
          <span class="col w-d-date">{{ tl('日期') }}</span>
          <span class="col w-d-type">{{ tl('班次') }}</span>
          <span class="col w-d-leader">{{ tl('值班长') }}</span>
          <span class="col w-d-members">{{ tl('成员') }}</span>
          <span class="col w-d-note">{{ tl('备注') }}</span>
          <span class="col w-d-op">{{ tl('操作') }}</span>
        </div>
        <div v-for="s in shifts" :key="s.id" class="tbl-row">
          <span class="col w-d-date">{{ s.date }}</span>
          <span class="col w-d-type">
            <span class="pill-tag" :class="s.shift === 'day' ? 'b' : ''">{{ s.shift === 'day' ? tl('白班') : tl('夜班') }}</span>
          </span>
          <span class="col w-d-leader fw">{{ parseMembers(s.members)[0]?.name || s.leader || '-' }}</span>
          <span class="col w-d-members muted">{{ parseMembers(s.members).map((m) => m.name).join('、') || '-' }}</span>
          <span class="col w-d-note muted">{{ s.note || '-' }}</span>
          <span class="col w-d-op p-ops">
            <button class="link" v-bind="authState('write')" @click="openShiftEdit(s)">{{ tl('编辑') }}</button>
            <button class="link danger" v-bind="authState('write')" @click="removeShift(s)">{{ tl('删除') }}</button>
          </span>
        </div>
      </div>
      <div class="empty" v-else>{{ tl('暂无排班') }}</div>
    </Panel>

    <!-- 交接班 -->
    <Panel style="margin-top: 16px">
      <div class="flex between" style="margin-bottom: 12px">
        <h5 class="section-title" style="margin: 0">{{ tl('交接班记录') }}</h5>
        <button class="btn-sm primary" v-bind="authState('write')" @click="openHandoverCreate">
          {{ tl('新增交接') }}
        </button>
      </div>
      <div class="tbl" v-if="handovers.length">
        <div class="tbl-head">
          <span class="col w-h-date">{{ tl('班次日期') }}</span>
          <span class="col w-h-type">{{ tl('班次') }}</span>
          <span class="col w-h-from">{{ tl('交班人') }}</span>
          <span class="col w-h-to">{{ tl('接班人') }}</span>
          <span class="col w-h-items">{{ tl('交接事项') }}</span>
          <span class="col w-h-op">{{ tl('操作') }}</span>
        </div>
        <div v-for="h in handovers" :key="h.id" class="tbl-row">
          <span class="col w-h-date">{{ h.shiftDate }}</span>
          <span class="col w-h-type">
            <span class="pill-tag" :class="h.shiftType === 'day' ? 'b' : ''">{{ h.shiftType === 'day' ? tl('白班') : tl('夜班') }}</span>
          </span>
          <span class="col w-h-from fw">{{ h.fromUser || '-' }}</span>
          <span class="col w-h-to fw">{{ h.toUser || '-' }}</span>
          <span class="col w-h-items muted">{{ parseItems(h.items).map((i) => i.text).join('；') || '-' }}</span>
          <span class="col w-h-op p-ops">
            <button class="link" v-bind="authState('write')" @click="openHandoverEdit(h)">{{ tl('编辑') }}</button>
            <button class="link danger" v-bind="authState('write')" @click="removeHandover(h)">{{ tl('删除') }}</button>
          </span>
        </div>
      </div>
      <div class="empty" v-else>{{ tl('暂无交接记录') }}</div>
    </Panel>
    </AsyncSection>

    <!-- 排班抽屉 -->
    <div class="drawer-mask" v-if="shiftDrawer" @click.self="shiftDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ shiftForm.id ? tl('编辑排班') : tl('新建排班') }}</span>
          <button class="x" @click="shiftDrawer = false">✕</button>
        </div>
        <div class="form">
          <div class="row">
            <label>{{ tl('日期') }}<input v-model="shiftForm.date" class="ipt" type="date" /></label>
            <label>{{ tl('班次') }}
              <select v-model="shiftForm.shift" class="ipt">
                <option value="day">{{ tl('白班') }}</option>
                <option value="night">{{ tl('夜班') }}</option>
              </select>
            </label>
          </div>
          <label>{{ tl('值班长') }}<input v-model.trim="shiftForm.leader" class="ipt" :placeholder="tl('如 王工')" /></label>
          <label>{{ tl('成员 (每行一个, 姓名/角色/电话)') }}
            <textarea v-model="memberText" class="ipt" rows="4" :placeholder="tl('张三/主值/13800000000')"></textarea>
          </label>
          <label>{{ tl('备注') }}<textarea v-model.trim="shiftForm.note" class="ipt" rows="2"></textarea></label>
          <div v-if="shiftErr" class="err">{{ shiftErr }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="shiftDrawer = false">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="shiftSaving" @click="saveShift">
              {{ shiftSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 交接抽屉 -->
    <div class="drawer-mask" v-if="handoverDrawer" @click.self="handoverDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ handoverForm.id ? tl('编辑交接') : tl('新增交接') }}</span>
          <button class="x" @click="handoverDrawer = false">✕</button>
        </div>
        <div class="form">
          <div class="row">
            <label>{{ tl('班次日期') }}<input v-model="handoverForm.shiftDate" class="ipt" type="date" /></label>
            <label>{{ tl('班次') }}
              <select v-model="handoverForm.shiftType" class="ipt">
                <option value="day">{{ tl('白班') }}</option>
                <option value="night">{{ tl('夜班') }}</option>
              </select>
            </label>
          </div>
          <div class="row">
            <label>{{ tl('交班人') }}<input v-model.trim="handoverForm.fromUser" class="ipt" /></label>
            <label>{{ tl('接班人') }}<input v-model.trim="handoverForm.toUser" class="ipt" /></label>
          </div>
          <label>{{ tl('交接事项 (每行一条, 可加前缀 紧急:/警告:)') }}
            <textarea v-model="itemText" class="ipt" rows="5" :placeholder="tl('紧急: 2 号冷机滤网压差偏高')"></textarea>
          </label>
          <label>{{ tl('补充说明') }}<textarea v-model.trim="handoverForm.note" class="ipt" rows="2"></textarea></label>
          <div v-if="handoverErr" class="err">{{ handoverErr }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="handoverDrawer = false">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="handoverSaving" @click="saveHandover">
              {{ handoverSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import {
  getDutyShifts,
  getDutyStats,
  createDutyShift,
  updateDutyShift,
  deleteDutyShift,
  getHandovers,
  createHandover,
  updateHandover,
  deleteHandover,
  type ShiftView,
  type ShiftMember,
  type DutyStats,
  type HandoverView,
  type HandoverItem,
} from '@/api/duty'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const shifts = ref<ShiftView[]>([])
const handovers = ref<HandoverView[]>([])
const stats = ref<DutyStats | null>(null)
const fromStr = ref('')
const toStr = ref('')

function parseMembers(s: unknown): ShiftMember[] {
  if (Array.isArray(s)) return s as ShiftMember[]
  if (typeof s === 'string') {
    try {
      const arr = JSON.parse(s || '[]')
      return Array.isArray(arr) ? arr : []
    } catch {
      return []
    }
  }
  return []
}
function parseItems(s: string): HandoverItem[] {
  try {
    const arr = JSON.parse(s || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

// 排班抽屉
const shiftDrawer = ref(false)
const shiftSaving = ref(false)
const shiftErr = ref('')
const shiftForm = ref<Partial<ShiftView> & { date: string; shift: string; leader: string; note: string; members: ShiftMember[] }>({
  date: '', shift: 'day', leader: '', note: '', members: [],
})
const memberText = ref('')

function openShiftCreate() {
  shiftForm.value = { date: new Date().toISOString().slice(0, 10), shift: 'day', leader: '', note: '', members: [] }
  memberText.value = ''
  shiftErr.value = ''
  shiftDrawer.value = true
}
function openShiftEdit(s: ShiftView) {
  shiftForm.value = { id: s.id, date: s.date, shift: s.shift, leader: s.leader, note: s.note, members: parseMembers(s.members) }
  memberText.value = parseMembers(s.members).map((m) => `${m.name}/${m.role || ''}/${m.phone || ''}`).join('\n')
  shiftErr.value = ''
  shiftDrawer.value = true
}
async function saveShift() {
  if (!shiftForm.value.date) {
    shiftErr.value = tl('日期为必填')
    return
  }
  const members: ShiftMember[] = memberText.value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const [name, role, phone] = l.split('/')
      return { name: name?.trim() || '', role: role?.trim() || '', phone: phone?.trim() || '' }
    })
  shiftSaving.value = true
  shiftErr.value = ''
  try {
    const payload = {
      date: shiftForm.value.date,
      shift: shiftForm.value.shift,
      leader: shiftForm.value.leader,
      note: shiftForm.value.note,
      members,
    }
    if (shiftForm.value.id != null) await updateDutyShift(shiftForm.value.id, payload)
    else await createDutyShift(payload)
    shiftDrawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    const raw = toErrorMessage(ex)
    // 对常见错误做翻译，便于用户理解为什么保存失败
    if (/404|405|Not Found|Method Not Allowed/.test(String(raw))) {
      shiftErr.value = tl('排班接口未实现') + ` (${tl('演示模式')})`
      console.warn('[duty-shift-save] 后端接口不可达，已降级使用前端演示内存存储：', raw)
    } else {
      shiftErr.value = raw || tl('保存失败')
    }
  } finally {
    shiftSaving.value = false
  }
}
async function removeShift(s: ShiftView) {
  const ok = await useConfirm({
    title: tl('删除排班'),
    message: tl('确认删除该排班?'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteDutyShift(s.id)
    },
  })
  if (ok) {
    await page.reload()
    toast.success(tl('已删除'))
  }
}

// 交接抽屉
const handoverDrawer = ref(false)
const handoverSaving = ref(false)
const handoverErr = ref('')
const handoverForm = ref<Partial<HandoverView> & { shiftDate: string; shiftType: string; fromUser: string; toUser: string; note: string; items: string }>({
  shiftDate: '', shiftType: 'day', fromUser: '', toUser: '', note: '', items: '[]',
})
const itemText = ref('')

function openHandoverCreate() {
  handoverForm.value = { shiftDate: new Date().toISOString().slice(0, 10), shiftType: 'day', fromUser: '', toUser: '', note: '', items: '[]' }
  itemText.value = ''
  handoverErr.value = ''
  handoverDrawer.value = true
}
function openHandoverEdit(h: HandoverView) {
  handoverForm.value = { id: h.id, shiftDate: h.shiftDate, shiftType: h.shiftType, fromUser: h.fromUser, toUser: h.toUser, note: h.note, items: h.items }
  itemText.value = parseItems(h.items)
    .map((i) => `${i.level === 'critical' ? '紧急:' : i.level === 'warn' ? '警告:' : ''}${i.text}`)
    .join('\n')
  handoverErr.value = ''
  handoverDrawer.value = true
}
async function saveHandover() {
  const items: HandoverItem[] = itemText.value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      if (l.startsWith('紧急:')) return { level: 'critical', text: l.slice(3).trim() }
      if (l.startsWith('警告:')) return { level: 'warn', text: l.slice(3).trim() }
      return { level: 'normal', text: l }
    })
  handoverSaving.value = true
  handoverErr.value = ''
  try {
    const payload = {
      shiftDate: handoverForm.value.shiftDate,
      shiftType: handoverForm.value.shiftType,
      fromUser: handoverForm.value.fromUser,
      toUser: handoverForm.value.toUser,
      note: handoverForm.value.note,
      items: JSON.stringify(items),
    }
    if (handoverForm.value.id != null) await updateHandover(handoverForm.value.id, payload)
    else await createHandover(payload)
    handoverDrawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    const raw = toErrorMessage(ex)
    if (/404|405|Not Found|Method Not Allowed/.test(String(raw))) {
      handoverErr.value = tl('交接接口未实现') + ` (${tl('演示模式')})`
      console.warn('[duty-handover-save] 后端接口不可达，已降级使用前端演示内存存储：', raw)
    } else {
      handoverErr.value = raw || tl('保存失败')
    }
  } finally {
    handoverSaving.value = false
  }
}
async function removeHandover(h: HandoverView) {
  const ok = await useConfirm({
    title: tl('删除交接记录'),
    message: tl('确认删除该交接记录?'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteHandover(h.id)
    },
  })
  if (ok) {
    await page.reload()
    toast.success(tl('已删除'))
  }
}

const page = useAsyncPage<ShiftView[]>(
  async () => {
    const [s, st, h] = await Promise.all([
      getDutyShifts(fromStr.value || undefined, toStr.value || undefined),
      getDutyStats(),
      getHandovers(),
    ])
    shifts.value = s
    stats.value = st
    handovers.value = h.items
    return shifts.value
  },
  { autoLoad: false, isEmpty: (d) => !d || d.length === 0 },
)
watch([fromStr, toStr], () => page.reload())
onMounted(async () => {
  fromStr.value = new Date().toISOString().slice(0, 10)
  toStr.value = new Date(Date.now() + 6 * 86400000).toISOString().slice(0, 10)
  await page.reload()
})
</script>

<style scoped>
.tbl {
  max-height: 420px;
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
.w-d-date { width: 110px; }
.w-d-type { width: 80px; }
.w-d-leader { width: 100px; }
.w-d-members { width: 220px; }
.w-d-note { flex: 1; }
.w-d-op { width: 100px; }
.w-h-date { width: 110px; }
.w-h-type { width: 80px; }
.w-h-from { width: 100px; }
.w-h-to { width: 100px; }
.w-h-items { flex: 1; }
.w-h-op { width: 100px; }
.fw { font-weight: 500; }
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
}
.pill-tag.b {
  background: rgba(64, 150, 255, 0.12);
  color: var(--blue);
}
.p-ops {
  display: flex;
  gap: 8px;
}
.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
}
.flex {
  display: flex;
  align-items: center;
}
.between {
  justify-content: space-between;
}
.gap {
  gap: 8px;
}
.center {
  justify-content: center;
}
.d-inp {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
}
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  cursor: pointer;
  font-size: 12px;
}
.btn-sm.primary {
  background: var(--cyan);
  color: #04121f;
  border-color: var(--cyan);
  font-weight: 600;
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
.link {
  background: none;
  border: none;
  color: var(--cyan);
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
  width: 460px;
  max-width: 94vw;
  background: var(--panel);
  padding: 18px;
  overflow: auto;
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  border: 1px solid var(--line);
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
  color: var(--txt2);
}
.row {
  display: flex;
  gap: 10px;
}
.row label {
  flex: 1;
}
.ipt {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--txt);
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
</style>
