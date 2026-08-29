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
        metric-name="inspect-today"
        :label="tl('今日记录')"
        :value="stats.todayRecords"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="inspect-complete"
        :label="tl('完成率')"
        :value="Number(stats.completionRate.toFixed(1))"
        unit="%"
        :quality="stats.completionRate > 80 ? 'good' : 'uncertain'"
        :online="true"
        :severity="stats.completionRate < 60 ? 'warn' : 'normal'"
      />
      <MetricCard
        metric-name="inspect-pass"
        :label="tl('合格率')"
        :value="Number(stats.passRate.toFixed(1))"
        unit="%"
        :quality="stats.passRate > 80 ? 'good' : 'uncertain'"
        :online="true"
        :severity="stats.passRate < 60 ? 'warn' : 'normal'"
      />
      <MetricCard
        metric-name="inspect-fail"
        :label="tl('不合格')"
        :value="stats.failRecords"
        unit="条"
        :quality="stats.failRecords ? 'bad' : 'good'"
        :online="true"
        :severity="stats.failRecords ? 'crit' : 'normal'"
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
              <span class="r-name">{{ r.name }}</span>
              <span class="r-code">{{ r.code }}</span>
            </div>
            <div class="r-tags">
              <span class="pill-tag" :class="freqCls(r.frequency)">{{ freqLabel(r.frequency) }}</span>
              <span class="pill-tag" :class="r.status === 'active' ? 'g' : 'm'">{{
                r.status === 'active' ? tl('已启用') : tl('已停用')
              }}</span>
            </div>
            <div class="r-ops" @click.stop>
              <button class="link" v-bind="authState('write')" @click="openRouteEdit(r)">{{ tl('编辑') }}</button>
              <button class="link danger" v-bind="authState('write')" @click="removeRoute(r)">{{ tl('删除') }}</button>
            </div>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无巡检路线') }}</div>
      </Panel>

      <!-- 记录列表 -->
      <Panel>
        <h5 class="section-title">{{ selectedRouteName || tl('巡检记录') }}</h5>
        <div class="record-table" v-if="records.length">
          <div class="tbl-head">
            <span class="col w-inspector">{{ tl('巡检人') }}</span>
            <span class="col w-time">{{ tl('开始时间') }}</span>
            <span class="col w-status">{{ tl('状态') }}</span>
            <span class="col w-result">{{ tl('结果') }}</span>
            <span class="col w-items">{{ tl('项目') }}</span>
          </div>
          <div v-for="rec in records" :key="rec.id" class="tbl-row" @click="openRecord(rec)">
            <span class="col w-inspector">{{ rec.inspectorName }}</span>
            <span class="col w-time muted">{{ rec.startedAt }}</span>
            <span class="col w-status">
              <span
                class="pill-tag"
                :class="rec.status === 'completed' ? 'g' : rec.status === 'in_progress' ? 'a' : 'm'"
              >
                {{
                  rec.status === 'completed'
                    ? tl('已完成')
                    : rec.status === 'in_progress'
                      ? tl('进行中')
                      : tl('待开始')
                }}
              </span>
            </span>
            <span class="col w-result">
              <span
                class="pill-tag"
                :class="
                  rec.result === 'pass' ? 'g' : rec.result === 'fail' ? 'r' : rec.result ? 'a' : 'm'
                "
              >
                {{
                  rec.result === 'pass'
                    ? tl('合格')
                    : rec.result === 'fail'
                      ? tl('不合格')
                      : rec.result === 'partial'
                        ? tl('部分合格')
                        : '-'
                }}
              </span>
            </span>
            <span class="col w-items muted"
              >{{ rec.itemPassed }}/{{ rec.itemTotal }} {{ tl('通过') }}</span
            >
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无记录') }}</div>
      </Panel>
    </div>
    </AsyncSection>

    <!-- 巡检项目详情模态 -->
    <div class="modal-overlay" v-if="detailRecord" @click.self="detailRecord = null">
      <div class="modal-card">
        <h5>{{ detailRecord.routeName }} — {{ detailRecord.inspectorName }}</h5>
        <div class="modal-meta">
          <span>{{ detailRecord.startedAt }}</span>
          <span v-if="detailRecord.completedAt"> → {{ detailRecord.completedAt }}</span>
          <span class="pill-tag" :class="detailRecord.result === 'pass' ? 'g' : 'r'">{{
            detailRecord.result || '-'
          }}</span>
        </div>
        <div class="item-table" v-if="items.length">
          <div class="tbl-head">
            <span class="col w-device">{{ tl('设备') }}</span>
            <span class="col w-item">{{ tl('项目') }}</span>
            <span class="col w-chk">{{ tl('已检') }}</span>
            <span class="col w-item-result">{{ tl('结果') }}</span>
            <span class="col w-remark">{{ tl('备注') }}</span>
          </div>
          <div v-for="it in items" :key="it.id" class="tbl-row">
            <span class="col w-device">{{ it.equipmentCode }}</span>
            <span class="col w-item">{{ it.itemName }}</span>
            <span class="col w-chk">{{ it.checked ? '✅' : '⬜' }}</span>
            <span class="col w-item-result">
              <span
                class="pill-tag"
                :class="it.result === 'pass' ? 'g' : it.result === 'fail' ? 'r' : 'a'"
                >{{ it.result || '-' }}</span
              >
            </span>
            <span class="col w-remark muted">{{ it.remark || '-' }}</span>
          </div>
        </div>
        <div class="empty" v-else>{{ tl('暂无项目') }}</div>
        <button class="btn-close" @click="detailRecord = null">{{ tl('关闭') }}</button>
      </div>
    </div>

    <!-- 路线管理抽屉 -->
    <div class="drawer-mask" v-if="routeDrawer" @click.self="closeRouteDrawer">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ routeForm.id ? tl('编辑巡检路线') : tl('新建巡检路线') }}</span>
          <button class="x" @click="closeRouteDrawer">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('路线编码') }}
            <input v-model.trim="routeForm.code" class="ipt" :placeholder="tl('留空自动生成')" />
          </label>
          <label>{{ tl('路线名称') }}
            <input v-model.trim="routeForm.name" class="ipt" :placeholder="tl('如 1#机房周巡检')" />
          </label>
          <div class="row">
            <label>{{ tl('频次') }}
              <select v-model="routeForm.freq" class="ipt">
                <option value="每日">{{ tl('每日') }}</option>
                <option value="每周">{{ tl('每周') }}</option>
                <option value="每月">{{ tl('每月') }}</option>
              </select>
            </label>
            <label>{{ tl('状态') }}
              <select v-model="routeForm.state" class="ipt">
                <option value="active">{{ tl('已启用') }}</option>
                <option value="disabled">{{ tl('已停用') }}</option>
              </select>
            </label>
          </div>
          <label>{{ tl('备注') }}
            <textarea v-model.trim="routeForm.note" class="ipt" rows="2"></textarea>
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
  getInspectionItems,
  createInspectionRoute,
  updateInspectionRoute,
  deleteInspectionRoute,
  type RouteView,
  type RecordView,
  type ItemView,
  type InspectionStats,
  type RouteCreatePayload,
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
const records = ref<RecordView[]>([])
const items = ref<ItemView[]>([])
const stats = ref<InspectionStats | null>(null)
const selectedRouteId = ref<number | null>(null)
const selectedRouteName = ref('')
const detailRecord = ref<RecordView | null>(null)

// 路线抽屉
const routeDrawer = ref(false)
const routeSaving = ref(false)
const routeErr = ref('')
const routeForm = ref<Partial<RouteView> & RouteCreatePayload>({
  code: '', name: '', freq: '每日', state: 'active', note: '',
})

function freqLabel(f: string) {
  if (f === 'daily') return tl('每日')
  if (f === 'weekly') return tl('每周')
  if (f === 'monthly') return tl('每月')
  return f
}
function freqCls(f: string) {
  if (f === 'daily') return 'a'
  if (f === 'weekly') return 'b'
  return ''
}

function openRouteCreate() {
  routeForm.value = { code: '', name: '', freq: '每日', state: 'active', note: '' }
  routeErr.value = ''
  routeDrawer.value = true
}
function openRouteEdit(r: RouteView) {
  routeForm.value = {
    id: r.id,
    code: r.code,
    name: r.name,
    freq: r.frequency,
    state: r.status,
    note: r.description ?? '',
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
    message: `${tl('确认删除路线')} ${r.name}?`,
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
    records.value = await getInspectionRecords(selectedRouteId.value ?? undefined)
  } catch {
    /* ignore */
  }
}

async function openRecord(rec: RecordView) {
  detailRecord.value = rec
  try {
    items.value = await getInspectionItems(rec.id)
  } catch {
    items.value = []
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
        selectedRouteName.value = r[0].name
      }
      await refreshRecords()
    }
    return routes.value
  },
  { isEmpty: (d) => !d || d.length === 0 },
)

onMounted(() => page.reload())
</script>

<style scoped>
.route-list,
.record-table,
.item-table {
  max-height: 360px;
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
.w-inspector {
  width: 80px;
}
.w-time {
  width: 160px;
}
.w-status {
  width: 80px;
}
.w-result {
  width: 80px;
}
.w-items {
  width: 70px;
  text-align: right;
}
.w-device {
  width: 90px;
}
.w-item {
  width: 140px;
  flex: 1;
}
.w-chk {
  width: 50px;
}
.w-item-result {
  width: 70px;
}
.w-remark {
  width: 120px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  justify-content: center;
  align-items: center;
}
.modal-card {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 24px;
  width: 700px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
.modal-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 16px;
  font-size: 12px;
  color: var(--muted);
}
.btn-close {
  margin-top: 16px;
  padding: 6px 20px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text);
  cursor: pointer;
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
  width: 420px;
  max-width: 92vw;
  background: var(--card-bg);
  height: 100%;
  padding: 18px;
  overflow: auto;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.3);
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
  gap: 10px;
  margin-top: 6px;
}
</style>
