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
          <button class="btn-sm primary" v-bind="authState('write')" @click="openTpl()">
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
              <button class="btn-sm primary" v-bind="authState('write')" @click="finish(t)">
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
      <div v-if="editing" class="drawer" @click.self="editing = null">
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
            <button class="btn-sm primary" v-bind="authState('write')" @click="saveTpl">
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
import { useAsyncPage } from '@/composables/useAsyncPage'
import AsyncSection from '@/components/common/AsyncSection.vue'

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
  const payload = {
    code: editing.value.code || editing.value.name,
    freq: editing.value.freq,
    note: editing.value.description ?? undefined,
  }
  if (editing.value.id) await updateInspectionRoute(editing.value.id, payload)
  else await createInspectionRoute(payload)
  editing.value = null
  await routesPage.reload()
}
async function delTpl(r: RouteView) {
  if (r.id) await deleteInspectionRoute(r.id)
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
  color: #e2e8f0;
}
.sub {
  color: #64748b;
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
  background: #0f172a;
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
  color: #cbd5e1;
  font-size: 15px;
}
.btn-sm {
  color: #cbd5e1;
  border: 1px solid var(--line);
  background: transparent;
  border-radius: 8px;
  padding: 5px 12px;
  cursor: pointer;
}
.btn-sm.primary {
  background: var(--cyan);
  color: #06121f;
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
  color: #94a3b8;
  background: transparent;
  border: none;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.seg button.on {
  background: var(--cyan);
  color: #06121f;
  font-weight: 700;
}
.tpl-list,
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tpl-item {
  background: #1e293b;
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
  color: #e2e8f0;
  font-weight: 600;
  flex: 1;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 20px;
}
.pill.g {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
.pill.a {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}
.tpl-desc {
  color: #64748b;
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
  color: #f87171;
}
.task-item {
  background: #1e293b;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  border-left: 3px solid #64748b;
}
.task-item.todo {
  border-left-color: #f59e0b;
}
.task-item.doing {
  border-left-color: #38bdf8;
}
.task-item.done {
  border-left-color: #22c55e;
}
.task-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-name {
  color: #e2e8f0;
  font-weight: 600;
}
.task-status {
  font-size: 12px;
}
.task-status.todo {
  color: #f59e0b;
}
.task-status.doing {
  color: #38bdf8;
}
.task-status.done {
  color: #22c55e;
}
.task-meta {
  color: #64748b;
  font-size: 12px;
  margin: 6px 0;
}
.task-ops {
  margin-top: 8px;
}
.empty {
  color: #64748b;
  text-align: center;
  padding: 24px;
  font-size: 13px;
}
.drawer {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.6);
  display: flex;
  justify-content: flex-end;
  z-index: 50;
}
.drawer-card {
  width: 400px;
  max-width: 90vw;
  height: 100%;
  background: #0f172a;
  border-left: 1px solid #1e293b;
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
  color: #e2e8f0;
  font-size: 15px;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
  font-size: 13px;
  color: #94a3b8;
}
.fld input,
.fld select,
.fld textarea {
  background: #1e293b;
  border: 1px solid var(--line);
  color: #e2e8f0;
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
  color: var(--muted);
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
