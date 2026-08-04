<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.inspect') }}</h1>
      <span class="sub">{{ tl('巡检路线与异常闭环') }}</span>
    </div>

    <!-- 统计卡片 -->
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
        <h5 class="section-title">{{ tl('巡检路线') }}</h5>
        <div class="route-list" v-if="routes.length">
          <div
            v-for="r in routes"
            :key="r.id"
            class="route-row"
            :class="{ active: selectedRouteId === r.id }"
            @click="selectRoute(r.id)"
          >
            <span class="r-name">{{ r.name }}</span>
            <span class="r-code">{{ r.code }}</span>
            <span class="pill-tag" :class="freqCls(r.frequency)">{{ freqLabel(r.frequency) }}</span>
            <span class="pill-tag" :class="r.status === 'active' ? 'g' : 'm'">{{
              r.status === 'active' ? tl('已启用') : tl('已停用')
            }}</span>
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

    <!-- 加载 / 错误 -->
    <Panel v-if="!routes.length && !error">
      <div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div>
    </Panel>
    <Panel v-if="error">
      <div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ tl('common.error') }}: {{ error }}</span>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import {
  getInspectionRoutes,
  getInspectionRecords,
  getInspectionStats,
  getInspectionItems,
  type RouteView,
  type RecordView,
  type ItemView,
  type InspectionStats,
} from '@/api/inspection'
const { t: tl } = useI18n()

const routes = ref<RouteView[]>([])
const records = ref<RecordView[]>([])
const items = ref<ItemView[]>([])
const stats = ref<InspectionStats | null>(null)
const error = ref('')
const selectedRouteId = ref<number | null>(null)
const selectedRouteName = ref('')
const detailRecord = ref<RecordView | null>(null)

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
  } catch (_) {
    /* ignore */
  }
}

async function openRecord(rec: RecordView) {
  detailRecord.value = rec
  try {
    items.value = await getInspectionItems(rec.id)
  } catch (_) {
    items.value = []
  }
}

async function load() {
  error.value = ''
  try {
    const [r, s] = await Promise.all([getInspectionRoutes(), getInspectionStats()])
    routes.value = r
    stats.value = s
    if (r.length) {
      selectedRouteId.value = r[0].id
      selectedRouteName.value = r[0].name
      await refreshRecords()
    }
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

onMounted(load)
</script>

<style scoped>
.route-list,
.record-table,
.item-table {
  max-height: 360px;
  overflow-y: auto;
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
.r-name {
  font-weight: 500;
  flex: 1;
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
</style>
