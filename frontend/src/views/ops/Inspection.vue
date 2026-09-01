<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.inspect') }}</h1>
      <span class="sub">{{ tl('巡检路线与异常闭环') }}</span>
    </div>

    <!-- 统计卡片 -->
    <AsyncSection :page="page" @retry="page.reload">
      <div class="grid cols-5" v-if="stats">
        <MetricCard
          metric-name="inspect-routes"
          :label="tl('巡检路线')"
          :value="stats.totalRoutes"
          unit=""
          quality="good"
          :online="true"
        />
        <MetricCard
          metric-name="inspect-active"
          :label="tl('启用路线')"
          :value="stats.activeRoutes"
          unit=""
          quality="good"
          :online="true"
        />
        <MetricCard
          metric-name="inspect-today"
          :label="tl('巡检发现')"
          :value="stats.todayRecords"
          unit="条"
          quality="good"
          :online="true"
        />
        <MetricCard
          metric-name="inspect-complete"
          :label="tl('启用率')"
          :value="Number(stats.completionRate.toFixed(1))"
          unit="%"
          :quality="stats.completionRate > 80 ? 'good' : 'uncertain'"
          :online="true"
          :severity="stats.completionRate < 60 ? 'warn' : 'normal'"
        />
        <MetricCard
          metric-name="inspect-fail"
          :label="tl('未启用')"
          :value="Math.max(0, stats.totalRoutes - stats.activeRoutes)"
          unit="条"
          :quality="stats.totalRoutes - stats.activeRoutes ? 'bad' : 'good'"
          :online="true"
          :severity="stats.totalRoutes - stats.activeRoutes ? 'crit' : 'normal'"
        />
      </div>

      <!-- 巡检路线 + 记录 -->
      <div class="grid cols-4-6" style="margin-top: 16px">
        <!-- 路线列表 -->
        <Panel>
          <div class="panel-head">
            <h5 class="section-title">{{ tl('巡检路线') }}</h5>
            <button class="btn-sm primary" v-bind="authState('write')" @click="openRouteCreate">
              {{ tl('新建') }}
            </button>
          </div>
          <div class="route-list" v-if="routes.length">
            <div
              v-for="r in routes"
              :key="r.id"
              class="route-row"
              :class="{ active: selectedRouteId === r.id }"
              @click="selectRoute(r.id)"
            >
              <div class="r-main">
                <span class="r-name">{{ r.name || r.code || '#' + r.id }}</span>
                <span class="r-code">{{ r.code }}</span>
              </div>
              <div class="r-tags">
                <span class="pill-tag" :class="freqCls(r.freq)">{{ freqLabel(r.freq) }}</span>
                <span class="pill-tag" :class="isActive(r.state) ? 'g' : 'm'">{{
                  isActive(r.state) ? tl('已启用') : tl('已停用')
                }}</span>
              </div>
              <div class="r-ops" @click.stop>
                <button class="link" v-bind="authState('write')" @click="openRouteEdit(r)">
                  {{ tl('编辑') }}
                </button>
                <button class="link danger" v-bind="authState('write')" @click="removeRoute(r)">
                  {{ tl('删除') }}
                </button>
              </div>
            </div>
          </div>
          <div class="empty" v-else>{{ tl('暂无巡检路线') }}</div>
        </Panel>

        <!-- 记录列表 (巡检发现) -->
        <Panel>
          <div class="panel-head">
            <h5 class="section-title">{{ selectedRouteName || tl('巡检记录') }}</h5>
            <button class="btn-sm primary" v-bind="authState('write')" @click="openFindingCreate">
              {{ tl('新建发现') }}
            </button>
          </div>
          <div class="record-table" v-if="records.length">
            <div class="tbl-head">
              <span class="col w-route">{{ tl('路线') }}</span>
              <span class="col w-item">{{ tl('发现项') }}</span>
              <span class="col w-lv">{{ tl('级别') }}</span>
              <span class="col w-time">{{ tl('时间') }}</span>
              <span class="col w-action">{{ tl('处置') }}</span>
            </div>
            <div v-for="rec in records" :key="rec.id" class="tbl-row" @click="openFinding(rec)">
              <span class="col w-route">{{ rec.route || '-' }}</span>
              <span class="col w-item">{{ rec.item || '-' }}</span>
              <span class="col w-lv">
                <span class="pill-tag" :class="lvCls(rec.lv)">{{ lvLabel(rec.lv) }}</span>
              </span>
              <span class="col w-time muted">{{ rec.ts || '-' }}</span>
              <span class="col w-action muted">{{ rec.action || '-' }}</span>
            </div>
          </div>
          <div class="empty" v-else>{{ tl('暂无记录') }}</div>
        </Panel>
      </div>
    </AsyncSection>

    <!-- 路线管理抽屉 -->
    <div class="drawer-mask" v-if="routeDrawer" @click.self="closeRouteDrawer">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ routeForm.id ? tl('编辑巡检路线') : tl('新建巡检路线') }}</span>
          <button class="x" @click="closeRouteDrawer">✕</button>
        </div>
        <div class="form">
          <label
            >{{ tl('路线编码') }}
            <input v-model.trim="routeForm.code" class="ipt" :placeholder="tl('留空自动生成')" />
          </label>
          <label
            >{{ tl('路线名称') }}
            <input v-model.trim="routeForm.name" class="ipt" :placeholder="tl('如 1#机房周巡检')" />
          </label>
          <div class="row">
            <label
              >{{ tl('频次') }}
              <select v-model="routeForm.freq" class="ipt">
                <option value="每日">{{ tl('每日') }}</option>
                <option value="每周">{{ tl('每周') }}</option>
                <option value="每月">{{ tl('每月') }}</option>
              </select>
            </label>
            <label
              >{{ tl('状态') }}
              <select v-model="routeForm.state" class="ipt">
                <option value="active">{{ tl('已启用') }}</option>
                <option value="disabled">{{ tl('已停用') }}</option>
              </select>
            </label>
          </div>
          <label
            >{{ tl('备注') }}
            <textarea v-model.trim="routeForm.description" class="ipt" rows="2"></textarea>
          </label>
          <div v-if="routeErr" class="err">{{ routeErr }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="closeRouteDrawer">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="routeSaving" @click="saveRoute">
              {{ routeSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 巡检发现抽屉 -->
    <div class="drawer-mask" v-if="findingDrawer" @click.self="closeFindingDrawer">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ findingForm.id ? tl('编辑巡检发现') : tl('新建巡检发现') }}</span>
          <button class="x" @click="closeFindingDrawer">✕</button>
        </div>
        <div class="form">
          <label
            >{{ tl('所属路线') }}
            <input
              v-model.trim="findingForm.route"
              class="ipt"
              :placeholder="tl('如 1#机房周巡检 / 设备编码')"
            />
          </label>
          <label
            >{{ tl('发现项') }}
            <textarea
              v-model.trim="findingForm.item"
              class="ipt"
              rows="3"
              :placeholder="tl('巡检发现的具体内容与设备')"
            ></textarea>
          </label>
          <div class="row">
            <label
              >{{ tl('级别') }}
              <select v-model="findingForm.lv" class="ipt">
                <option value="info">{{ tl('提示') }}</option>
                <option value="warn">{{ tl('警告') }}</option>
                <option value="crit">{{ tl('严重') }}</option>
              </select>
            </label>
            <label
              >{{ tl('时间') }}
              <input v-model.trim="findingForm.ts" class="ipt" placeholder="YYYY-MM-DD HH:MM" />
            </label>
          </div>
          <label
            >{{ tl('处置动作') }}
            <textarea
              v-model.trim="findingForm.action"
              class="ipt"
              rows="3"
              :placeholder="tl('已采取的处置或整改动作')"
            ></textarea>
          </label>
          <div v-if="findingErr" class="err">{{ findingErr }}</div>
          <div class="drawer-foot">
            <button
              v-if="findingForm.id"
              class="btn-sm danger"
              v-bind="authState('write')"
              :disabled="findingSaving"
              @click="removeFinding"
            >
              {{ tl('删除') }}
            </button>
            <span class="spacer"></span>
            <button class="btn-sm" @click="closeFindingDrawer">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="findingSaving" @click="saveFinding">
              {{ findingSaving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import Panel from '@/components/common/Panel.vue'
import {
  getInspectionRoutes,
  getInspectionRecords,
  getInspectionStats,
  createInspectionRoute,
  updateInspectionRoute,
  deleteInspectionRoute,
  createInspectionFinding,
  updateInspectionFinding,
  deleteInspectionFinding,
  type RouteView,
  type FindingView,
  type InspectionStats,
  type RouteCreatePayload,
  type FindingCreatePayload,
} from '@/api/inspection'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'
const { t: tl } = useI18n()
const toast = useToast()
const { can, denyTip } = usePermission()

function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const routes = ref<RouteView[]>([])
const records = ref<FindingView[]>([])
const stats = ref<InspectionStats | null>(null)
const selectedRouteId = ref<number | null>(null)
const selectedRouteName = ref('')

// ---- 文案助手 ----
function freqLabel(f: string) {
  if (!f) return ''
  if (f === '每日' || f === 'daily') return tl('每日')
  if (f === '每周' || f === 'weekly') return tl('每周')
  if (f === '每月' || f === 'monthly') return tl('每月')
  return f
}
function freqCls(f: string) {
  if (f === '每日' || f === 'daily') return 'a'
  if (f === '每周' || f === 'weekly') return 'b'
  return ''
}
function isActive(state: string) {
  return state === 'active' || state === '进行中' || state === '已完成' || state === 'enabled'
}
function lvLabel(lv: string) {
  if (lv === 'crit') return tl('严重')
  if (lv === 'warn') return tl('警告')
  return tl('提示')
}
function lvCls(lv: string) {
  if (lv === 'crit') return 'r'
  if (lv === 'warn') return 'a'
  return 'm'
}

// ---- 路线抽屉 ----
const routeDrawer = ref(false)
const routeSaving = ref(false)
const routeErr = ref('')
const routeForm = ref<Partial<RouteView> & RouteCreatePayload>({
  code: '',
  name: '',
  description: '',
  freq: '每日',
  state: 'active',
  note: '',
})

function openRouteCreate() {
  routeForm.value = { code: '', name: '', description: '', freq: '每日', state: 'active', note: '' }
  routeErr.value = ''
  routeDrawer.value = true
}
function openRouteEdit(r: RouteView) {
  routeForm.value = {
    id: r.id,
    code: r.code,
    name: r.name ?? '',
    description: r.description ?? '',
    freq: r.freq || '每日',
    state: r.state || 'active',
    note: r.note ?? '',
  }
  routeErr.value = ''
  routeDrawer.value = true
}
function closeRouteDrawer() {
  routeDrawer.value = false
}

async function saveRoute() {
  const f = routeForm.value
  if (!f.name) {
    routeErr.value = tl('路线名称为必填')
    return
  }
  routeSaving.value = true
  routeErr.value = ''
  try {
    const payload: RouteCreatePayload = {
      code: f.code || undefined,
      name: f.name,
      description: f.description || '',
      freq: f.freq || '每日',
      state: f.state || 'active',
      note: f.note || '',
    }
    if (f.id != null) await updateInspectionRoute(f.id, payload)
    else await createInspectionRoute(payload)
    routeDrawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (e: unknown) {
    routeErr.value = toErrorMessage(e) || tl('保存失败')
  } finally {
    routeSaving.value = false
  }
}

async function removeRoute(r: RouteView) {
  const ok = await useConfirm({
    title: tl('删除巡检路线'),
    message: `${tl('确认删除路线')} ${r.name || r.code}?`,
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteInspectionRoute(r.id)
    },
  })
  if (ok) {
    await page.reload()
    toast.success(tl('已删除'))
  }
}

// ---- 发现抽屉 ----
const findingDrawer = ref(false)
const findingSaving = ref(false)
const findingErr = ref('')
const findingForm = ref<Partial<FindingView> & FindingCreatePayload>({
  route: '',
  item: '',
  ts: '',
  lv: 'info',
  action: '',
})

function openFindingCreate() {
  const sel = routes.value.find((x) => x.id === selectedRouteId.value)
  findingForm.value = {
    id: undefined,
    route: sel ? sel.name || sel.code : '',
    item: '',
    ts: '',
    lv: 'info',
    action: '',
  }
  findingErr.value = ''
  findingDrawer.value = true
}
function openFinding(f: FindingView) {
  findingForm.value = {
    id: f.id,
    route: f.route || '',
    item: f.item || '',
    ts: f.ts || '',
    lv: f.lv || 'info',
    action: f.action || '',
  }
  findingErr.value = ''
  findingDrawer.value = true
}
function closeFindingDrawer() {
  findingDrawer.value = false
}

async function saveFinding() {
  const f = findingForm.value
  if (!f.item) {
    findingErr.value = tl('发现项为必填')
    return
  }
  findingSaving.value = true
  findingErr.value = ''
  try {
    const payload: FindingCreatePayload = {
      route: f.route || '',
      item: f.item,
      ts: f.ts || '',
      lv: f.lv || 'info',
      action: f.action || '',
    }
    if (f.id != null) await updateInspectionFinding(f.id, payload)
    else await createInspectionFinding(payload)
    findingDrawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (e: unknown) {
    findingErr.value = toErrorMessage(e) || tl('保存失败')
  } finally {
    findingSaving.value = false
  }
}

async function removeFinding() {
  if (findingForm.value.id == null) return
  const ok = await useConfirm({
    title: tl('删除巡检发现'),
    message: tl('确认删除该条发现记录？'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteInspectionFinding(findingForm.value.id as number)
    },
  })
  if (ok) {
    findingDrawer.value = false
    await page.reload()
    toast.success(tl('已删除'))
  }
}

// ---- 选择路线 / 刷新发现 ----
async function selectRoute(id: number) {
  if (selectedRouteId.value === id) {
    selectedRouteId.value = null
    selectedRouteName.value = ''
  } else {
    selectedRouteId.value = id
    const r = routes.value.find((x) => x.id === id)
    selectedRouteName.value = r?.name ?? ''
  }
  await refreshRecords()
}

async function refreshRecords() {
  try {
    const all = await getInspectionRecords()
    const code = selectedRouteName.value
    records.value = code ? all.filter((f) => f.route === code) : all
  } catch {
    records.value = []
  }
}

const page = useAsyncPage<RouteView[]>(
  async () => {
    const [r, s] = await Promise.all([getInspectionRoutes(), getInspectionStats()])
    routes.value = r
    stats.value = s
    if (r.length) {
      if (!selectedRouteId.value || !r.find((x) => x.id === selectedRouteId.value)) {
        selectedRouteId.value = r[0].id
        selectedRouteName.value = r[0].name ?? r[0].code
      }
    } else {
      selectedRouteId.value = null
      selectedRouteName.value = ''
    }
    await refreshRecords()
    return routes.value
  },
  { isEmpty: (d) => !d || d.length === 0 },
)

onMounted(() => page.reload())
</script>

<style scoped>
.route-list,
.record-table {
  max-height: 420px;
  overflow-y: auto;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.route-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 8px;
  cursor: pointer;
  border-radius: 6px;
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
  font-size: 13px;
}
.route-row:hover {
  background: var(--bg2);
}
.route-row.active {
  background: rgba(64, 150, 255, 0.08);
  border-left: 3px solid var(--blue);
}
.r-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.r-tags {
  display: flex;
  gap: 6px;
  align-items: center;
}
.r-ops {
  display: flex;
  gap: 8px;
}
.r-name {
  font-weight: 500;
}
.r-code {
  color: var(--muted);
  font-size: 11px;
}
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
  white-space: nowrap;
}
.pill-tag.g {
  background: rgba(82, 196, 26, 0.12);
  color: var(--green);
}
.pill-tag.a {
  background: rgba(250, 173, 20, 0.12);
  color: var(--amber);
}
.pill-tag.r {
  background: rgba(255, 77, 79, 0.12);
  color: var(--red);
}
.pill-tag.b {
  background: rgba(64, 150, 255, 0.12);
  color: var(--blue);
}
.pill-tag.m {
  background: rgba(255, 255, 255, 0.06);
  color: var(--muted);
}

.tbl-head,
.tbl-row {
  display: flex;
  align-items: center;
  padding: 9px 8px;
  font-size: 12.5px;
}
.tbl-head {
  font-weight: 600;
  color: var(--muted);
  border-bottom: 2px solid var(--border);
  font-size: 12px;
  position: sticky;
  top: 0;
  background: var(--panel);
}
.tbl-row {
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
  cursor: pointer;
}
.tbl-row:hover {
  background: var(--bg2);
}
.col {
  flex-shrink: 0;
}
.w-route {
  width: 110px;
}
.w-item {
  flex: 1;
  min-width: 120px;
}
.w-lv {
  width: 64px;
}
.w-time {
  width: 130px;
}
.w-action {
  width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
}
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text2);
  cursor: pointer;
  font-size: 12px;
}
.btn-sm.primary {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
  font-weight: 600;
}
.btn-sm.danger {
  background: transparent;
  color: var(--red);
  border-color: var(--red);
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
.link {
  background: none;
  border: none;
  color: var(--blue);
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
  width: 440px;
  max-width: 92vw;
  background: var(--card-bg);
  padding: 18px;
  border-radius: 12px;
  overflow: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
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
  color: var(--text2);
}
.form .row {
  display: flex;
  gap: 12px;
}
.form .row label {
  flex: 1;
}
.ipt {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--text);
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
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}
.spacer {
  flex: 1;
}
</style>
