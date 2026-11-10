<template>
  <div class="insp-tpl">
    <div class="view-head">
      <h1>{{ tl('电子巡检') }}</h1>
      <span class="sub">{{ tl('巡检模板 · APP 任务下发') }}</span>
    </div>

    <div class="cols">
      <!-- 左：巡检模板 -->
      <section class="panel">
        <div class="panel-head">
          <h3>{{ tl('巡检模板') }}</h3>
          <button class="btn-sm btn-primary" v-bind="authState('write')" @click="openTpl()">
            {{ tl('新建模板') }}
          </button>
        </div>
        <AsyncSection
          :page="routesPage"
          @retry="routesPage.reload"
          :empty-title="tl('暂无模板')"
          :empty-desc="tl('点击右上角新建第一个巡检模板')"
        >
          <div class="tpl-list">
            <div v-for="r in routes" :key="r.id" class="tpl-item">
              <div class="tpl-main">
                <span class="tpl-name">{{ r.name }}</span>
                <span class="pill" :class="r.state === 'active' ? 'g' : 'a'">{{
                  r.freq || '-'
                }}</span>
              </div>
              <div class="tpl-desc">{{ r.description || '-' }}</div>
              <div class="tpl-ops">
                <button class="link" v-bind="authState('write')" @click="openTpl(r)">
                  {{ tl('编辑') }}
                </button>
                <button class="link" v-bind="authState('write')" @click="dispatchTask(r)">
                  {{ tl('下发任务') }}
                </button>
                <button class="link danger" v-bind="authState('write')" @click="delTpl(r)">
                  {{ tl('删除') }}
                </button>
              </div>
            </div>
          </div>
        </AsyncSection>
      </section>

      <!-- 右：APP 巡检任务 -->
      <section class="panel">
        <div class="panel-head">
          <h3>{{ tl('APP 巡检任务') }}</h3>
          <div class="seg">
            <button :class="{ on: taskFilter === 'all' }" @click="taskFilter = 'all'">
              {{ tl('全部') }}
            </button>
            <button :class="{ on: taskFilter === 'todo' }" @click="taskFilter = 'todo'">
              {{ tl('待接单') }}
            </button>
            <button :class="{ on: taskFilter === 'doing' }" @click="taskFilter = 'doing'">
              {{ tl('执行中') }}
            </button>
            <button :class="{ on: taskFilter === 'done' }" @click="taskFilter = 'done'">
              {{ tl('已完成') }}
            </button>
          </div>
        </div>
        <div class="task-list">
          <div v-for="t in filteredTasks" :key="t.id" class="task-item" :class="t.status">
            <div class="task-row">
              <span class="task-name">{{ t.routeName }}</span>
              <span class="task-status" :class="t.status">{{ statusText(t.status) }}</span>
            </div>
            <div class="task-meta">
              {{ tl('巡检员') }}: {{ t.inspector || '-' }} · {{ tl('计划') }}: {{ t.planDate }}
            </div>
            <div class="task-ops" v-if="t.status === 'todo'">
              <button class="btn-sm" v-bind="authState('write')" @click="accept(t)">
                {{ tl('接单') }}
              </button>
            </div>
            <div class="task-ops" v-else-if="t.status === 'doing'">
              <button class="btn-sm btn-primary" v-bind="authState('write')" @click="finish(t)">
                {{ tl('完成') }}
              </button>
            </div>
          </div>
          <div class="empty" v-if="!filteredTasks.length">{{ tl('暂无任务') }}</div>
        </div>
      </section>
    </div>

    <!-- 模板编辑抽屉 -->
    <transition name="slide">
      <div v-if="editing" class="modal as-drawer" @click.self="editing = null">
        <div class="drawer-card">
          <div class="drawer-head">
            <h3>{{ editing.id ? tl('编辑模板') : tl('新建模板') }}</h3>
            <button class="x" @click="editing = null">✕</button>
          </div>
          <label class="fld"
            ><span>{{ tl('模板名称') }}</span
            ><input v-model="editing.name"
          /></label>
          <label class="fld"
            ><span>{{ tl('编码') }}</span
            ><input v-model="editing.code" placeholder="PATROL-xxx"
          /></label>
          <label class="fld"
            ><span>{{ tl('频次') }}</span>
            <select v-model="editing.freq">
              <option value="每日">每日</option>
              <option value="每周">每周</option>
              <option value="每月">每月</option>
            </select>
          </label>
          <label class="fld"
            ><span>{{ tl('描述') }}</span
            ><textarea v-model="editing.description" rows="3" />
          </label>
          <label class="fld"
            ><span>{{ tl('状态') }}</span>
            <select v-model="editing.state">
              <option value="active">{{ tl('启用') }}</option>
              <option value="disabled">{{ tl('停用') }}</option>
            </select>
          </label>
          <div class="drawer-actions">
            <button
              class="btn-sm danger"
              v-if="editing.id"
              v-bind="authState('write')"
              @click="delTpl(editing)"
            >
              {{ tl('删除') }}
            </button>
            <button class="btn-sm btn-primary" v-bind="authState('write')" @click="saveTpl">
              {{ tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getInspectionRoutes,
  createInspectionRoute,
  updateInspectionRoute,
  deleteInspectionRoute,
  type RouteView,
} from '@/api/inspection'
import { usePermission, type PermAction } from '@/hooks/usePermission'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
const toast = useToast()

const { t: tl } = useI18n()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

// ===== 巡检模板 =====
const routes = ref<RouteView[]>([])
async function loadRoutes() {
  routes.value = await getInspectionRoutes()
  return routes.value
}
const routesPage = useAsyncPage<RouteView[]>(loadRoutes, { isEmpty: (d) => !d.length })
const editing = ref<RouteView | null>(null)

function openTpl(r?: RouteView) {
  editing.value = r
    ? { ...r }
    : { id: 0, code: '', name: '', description: '', freq: '每日', state: 'active' }
}
async function saveTpl() {
  if (!editing.value) return
  const name = (editing.value.name || '').trim()
  // 名称必填: 后端 RouteCreate 虽未强制, 但空名模板在列表不可辨识
  if (!name) {
    toast.error(tl('路线名称为必填'))
    return
  }
  const desc = editing.value.description || ''
  // code/name/description/freq/state 全量提交: 只发 code+note 会导致新建模板名称为空
  const payload = {
    code: (editing.value.code || '').trim() || name,
    name,
    description: desc,
    freq: editing.value.freq,
    state: editing.value.state || 'active',
    note: desc,
  }
  try {
    if (editing.value.id) await updateInspectionRoute(editing.value.id, payload)
    else await createInspectionRoute(payload)
    toast.success(tl('已保存'))
  } catch (e) {
    toast.error(toErrorMessage(e, tl('保存失败')))
    return
  }
  editing.value = null
  await routesPage.reload()
}
async function delTpl(r: RouteView) {
  if (!(await useConfirm({ message: tl('确认删除路线'), danger: true }))) return
  try {
    if (r.id) await deleteInspectionRoute(r.id)
    toast.success(tl('已删除'))
  } catch (e) {
    toast.error(toErrorMessage(e, tl('删除失败')))
    return
  }
  if (editing.value?.id === r.id) editing.value = null
  await routesPage.reload()
}

// ===== APP 巡检任务 (localStorage 模拟移动端派发) =====
interface InspectTask {
  id: number
  routeId: number
  routeName: string
  inspector: string
  planDate: string
  status: 'todo' | 'doing' | 'done'
  createdAt: string
}
const tasks = ref<InspectTask[]>([])
const taskFilter = ref<'all' | 'todo' | 'doing' | 'done'>('all')
const TASK_KEY = 'dcioc-inspect-tasks'

function loadTasks() {
  try {
    tasks.value = JSON.parse(localStorage.getItem(TASK_KEY) || '[]')
  } catch {
    tasks.value = []
  }
}
function saveTasks() {
  localStorage.setItem(TASK_KEY, JSON.stringify(tasks.value))
}
function dispatchTask(r: RouteView) {
  const t: InspectTask = {
    id: Date.now(),
    routeId: r.id,
    routeName: r.name,
    inspector: '',
    planDate: new Date().toISOString().slice(0, 10),
    status: 'todo',
    createdAt: new Date().toISOString(),
  }
  tasks.value.unshift(t)
  saveTasks()
}
function accept(t: InspectTask) {
  t.status = 'doing'
  t.inspector = t.inspector || '现场巡检员'
  saveTasks()
}
function finish(t: InspectTask) {
  t.status = 'done'
  saveTasks()
}
const filteredTasks = computed(() =>
  taskFilter.value === 'all'
    ? tasks.value
    : tasks.value.filter((t) => t.status === taskFilter.value),
)
function statusText(s: string) {
  return { todo: tl('待接单'), doing: tl('执行中'), done: tl('已完成') }[s] || s
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.insp-tpl {
  padding: 16px 20px 32px;
}
.view-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.view-head h1 {
  font-size: 20px;
  margin: 0;
  color: var(--txt-strong);
}
.sub {
  color: var(--txt2);
  font-size: 13px;
}
.cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
  align-items: start;
}
.panel {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.panel-head h3 {
  margin: 0;
  color: var(--txt);
  font-size: 15px;
}
.btn-sm {
  color: var(--txt);
  border: 1px solid var(--line);
  background: transparent;
  border-radius: 8px;
  padding: 5px 12px;
  cursor: pointer;
}
.btn-sm.primary {
  background: var(--cyan);
  color: var(--txt3);
  border-color: var(--cyan);
  font-weight: 700;
}
.seg {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
.seg button {
  color: var(--txt2);
  background: transparent;
  border: none;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.seg button.on {
  background: var(--cyan);
  color: var(--txt3);
  font-weight: 700;
}
.tpl-list,
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tpl-item {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
}
.tpl-main {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tpl-name {
  color: var(--txt-strong);
  font-weight: 600;
  flex: 1;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 20px;
}
.pill.g {
  background: color-mix(in srgb, var(--green) 15%, transparent);
  color: var(--green);
}
.pill.a {
  background: var(--accent-16);
  color: var(--txt2);
}
.tpl-desc {
  color: var(--txt2);
  font-size: 12px;
  margin: 6px 0;
}
.tpl-ops {
  display: flex;
  gap: 12px;
}
.link {
  background: none;
  border: none;
  color: var(--cyan);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
}
.link.danger {
  color: var(--red);
}
.task-item {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  border-left: 3px solid var(--line);
}
.task-item.todo {
  border-left-color: var(--amber-line);
}
.task-item.doing {
  border-left-color: var(--blue-line);
}
.task-item.done {
  border-left-color: var(--green-line);
}
.task-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-name {
  color: var(--txt-strong);
  font-weight: 600;
}
.task-status {
  font-size: 12px;
}
.task-status.todo {
  color: var(--amber);
}
.task-status.doing {
  color: var(--blue);
}
.task-status.done {
  color: var(--green);
}
.task-meta {
  color: var(--txt2);
  font-size: 12px;
  margin: 6px 0;
}
.task-ops {
  margin-top: 8px;
}
.empty {
  color: var(--txt2);
  text-align: center;
  padding: 24px;
  font-size: 13px;
}
.as-drawer {
  position: fixed;
  inset: 0;
  background: var(--accent-50);
  display: flex;
  justify-content: flex-end;
  z-index: 50;
}
.drawer-card {
  width: 400px;
  max-width: 90vw;
  height: 100%;
  background: var(--bg2);
  border-left: 1px solid var(--line);
  padding: 22px;
  overflow-y: auto;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}
.drawer-head h3 {
  margin: 0;
  color: var(--txt-strong);
  font-size: 15px;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
  font-size: 13px;
  color: var(--txt2);
}
.fld input,
.fld select,
.fld textarea {
  background: var(--bg2);
  border: 1px solid var(--line);
  color: var(--txt-strong);
  border-radius: 8px;
  padding: 8px 10px;
  font-family: inherit;
}
.drawer-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 16px;
}
.x {
  background: none;
  border: none;
  color: var(--txt2);
  cursor: pointer;
  font-size: 16px;
}
.slide-enter-active,
.slide-leave-active {
  transition: opacity 0.2s;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}
</style>
