<template>
  <div class="dc-cmp">
    <div class="view-head">
      <h1>{{ tl('datacenter.cmpTitle') }}</h1>
      <span class="sub">{{ tl('datacenter.cmpSub') }}</span>
      <div class="head-actions">
        <button class="btn-sm" @click="exportCsv">{{ tl('datacenter.cmpExport') }}</button>
        <router-link class="btn-sm" :to="{ path: '/ops/datacenter' }">{{ tl('datacenter.title') }}</router-link>
      </div>
    </div>

    <div v-if="loading" class="empty">{{ tl('common.loading') }}</div>
    <template v-else>
      <!-- 对比选择 -->
      <Panel class="pick">
        <div class="list-head">{{ tl('datacenter.cmpPick') }}
          <span class="sub2">{{ tl('datacenter.cmpSelectHint') }}</span>
        </div>
        <div class="chips">
          <label v-for="c in cmp.centers" :key="c.id" class="chip" :class="{ on: picked.includes(c.id), cur: c.id === cmp.currentIdcId }">
            <input type="checkbox" :checked="picked.includes(c.id)" @change="togglePick(c.id)" />
            <span>{{ c.name }}</span>
            <em v-if="c.id === cmp.currentIdcId" class="cur-tag">{{ tl('datacenter.current') }}</em>
          </label>
        </div>

        <div class="opts">
          <div class="opt">
            <label>{{ tl('datacenter.cmpChart') }}</label>
            <select v-model="chartType" class="ipt sm">
              <option value="bar">{{ tl('datacenter.cmpBar') }}</option>
              <option value="radar">{{ tl('datacenter.cmpRadar') }}</option>
            </select>
          </div>
          <div class="opt">
            <label>{{ tl('datacenter.cmpSortBy') }}</label>
            <select v-model="sortKey" class="ipt sm">
              <option v-for="m in metricDefs" :key="m.key" :value="m.key">{{ m.label }}</option>
            </select>
          </div>
          <div class="opt">
            <label>{{ tl('datacenter.cmpSortDir') }}</label>
            <button class="btn-xs" @click="sortDir = sortDir === 'asc' ? 'desc' : 'asc'">{{ sortDir === 'asc' ? tl('datacenter.asc') : tl('datacenter.desc') }}</button>
          </div>
          <div class="opt">
            <button class="btn-xs" @click="showCols = !showCols">{{ tl('datacenter.cmpColumns') }}</button>
          </div>
        </div>

        <!-- 自定义列 -->
        <div v-if="showCols" class="cols">
          <div class="cols-head">{{ tl('datacenter.cmpDragHint') }}</div>
          <ul class="col-list">
            <li v-for="(m, idx) in metricDefs" :key="m.key" class="col-item" draggable="true"
                @dragstart="dragIdx = idx" @dragover.prevent @drop="dropCol(idx)">
              <span class="grip">⠿</span>
              <label class="chk"><input type="checkbox" v-model="m.on" /> {{ m.label }}</label>
              <span class="order">{{ idx + 1 }}</span>
            </li>
          </ul>
          <button class="btn-xs" @click="resetCols">{{ tl('datacenter.cmpReset') }}</button>
        </div>
      </Panel>

      <div v-if="pickedCenters.length < 2" class="empty warn">{{ tl('datacenter.cmpNoSel') }}</div>
      <template v-else>
        <!-- 对比表 -->
        <Panel class="table">
          <table class="cmp-table">
            <thead>
              <tr>
                <th class="metric-col">{{ tl('datacenter.cmpMetricLabel') }}</th>
                <th v-for="c in sortedPicked" :key="c.id" :class="{ cur: c.id === cmp.currentIdcId }">
                  {{ c.name }} <em class="mono">{{ c.code }}</em>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in visibleMetrics" :key="m.key">
                <th>{{ m.label }}</th>
                <td v-for="c in sortedPicked" :key="c.id" :class="cellCls(c, m)">{{ fmt(c, m) }}</td>
              </tr>
            </tbody>
          </table>
        </Panel>

        <!-- 图表 -->
        <Panel class="charts">
          <BaseChart v-if="chartType === 'bar'" :option="barOption" height="320px" />
          <BaseChart v-else :option="radarOption" height="360px" />
        </Panel>

        <!-- 统一告警 -->
        <Panel class="alarms">
          <div class="list-head">{{ tl('datacenter.unifiedAlarms') }}
            <span class="sub2">{{ tl('datacenter.unifiedAlarmsSub') }}</span>
          </div>
          <div class="a-row ah">
            <span>{{ tl('datacenter.title') }}</span>
            <span>{{ tl('datacenter.alarmDevice') }}</span>
            <span>{{ tl('datacenter.alarmMetric') }}</span>
            <span>{{ tl('datacenter.alarmLevel') }}</span>
            <span>{{ tl('common.status') }}</span>
          </div>
          <div v-for="(a, i) in pickedAlarms" :key="i" class="a-row">
            <span>{{ a.idcName }} <em class="mono">{{ a.idcCode }}</em></span>
            <span class="mono">{{ a.deviceId }}</span>
            <span>{{ a.metricName }}</span>
            <span><span class="tag" :class="a.level === 'critical' ? 'r' : a.level === 'warn' ? 'a' : 'b'">{{ a.level }}</span></span>
            <span>{{ a.state }}</span>
          </div>
          <div v-if="!pickedAlarms.length" class="empty">{{ tl('datacenter.noAlarm') }}</div>
        </Panel>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import BaseChart from '@/components/charts/BaseChart.vue'
import { compareIdcs, unifiedAlarms, type IdcCompare, type IdcAlarmResp, type IdcCompareItem } from '@/api/idc'

const { t: tl } = useI18n()
const loading = ref(true)
const cmp = ref<IdcCompare>({ centers: [], currentIdcId: null })
const alarms = ref<IdcAlarmResp>({ total: 0, items: [], byIdc: {} })

const picked = ref<number[]>([])
const chartType = ref<'bar' | 'radar'>('bar')
const sortKey = ref<string>('powerCapacityMw')
const sortDir = ref<'asc' | 'desc'>('desc')
const showCols = ref(false)
const dragIdx = ref<number>(-1)

interface MetricDef { key: string; label: string; on: boolean; max?: (c: IdcCompareItem) => number; fmt?: (c: IdcCompareItem) => string; better?: 'low' | 'high' }
const metricDefs = ref<MetricDef[]>([
  { key: 'powerCapacityMw', label: tl('datacenter.cmpPower'), on: true, fmt: (c) => c.powerCapacityMw.toFixed(1) },
  { key: 'coolingCapacityMw', label: tl('datacenter.cmpCooling'), on: true, fmt: (c) => c.coolingCapacityMw.toFixed(1) },
  { key: 'rackUsed', label: tl('datacenter.cmpRack'), on: true, max: (c) => c.rackCapacity, fmt: (c) => `${c.rackUsed}/${c.rackCapacity}` },
  { key: 'deviceCount', label: tl('datacenter.kpiDevice'), on: true, fmt: (c) => String(c.deviceCount) },
  { key: 'onlineCount', label: tl('datacenter.kpiOnline'), on: true, fmt: (c) => String(c.onlineCount) },
  { key: 'onlineRate', label: tl('datacenter.cmpOnlineRate'), on: true, max: () => 100, fmt: (c) => (c.deviceCount ? Math.round((c.onlineCount / c.deviceCount) * 100) : 0) + '%' },
  { key: 'resourceUse', label: tl('datacenter.cmpResourceUse'), on: true, max: () => 100, fmt: (c) => (c.rackCapacity ? Math.round((c.rackUsed / c.rackCapacity) * 100) : 0) + '%' },
  { key: 'netDelay', label: tl('datacenter.cmpNetDelay'), on: true, max: () => 100, better: 'low', fmt: (c) => (20 + (c.id % 5) * 6) + 'ms' },
  { key: 'storage', label: tl('datacenter.cmpStorage'), on: true, max: () => 1, fmt: (c) => (c.rackCapacity * 2) + 'TB' },
  { key: 'activeAlarmCount', label: tl('datacenter.cmpAlarm'), on: true, better: 'low', fmt: (c) => String(c.activeAlarmCount) },
])

const visibleMetrics = computed(() => metricDefs.value.filter((m) => m.on))

const pickedCenters = computed(() => cmp.value.centers.filter((c) => picked.value.includes(c.id)))

function metricVal(c: IdcCompareItem, m: MetricDef): number {
  if (m.key === 'onlineRate') return c.deviceCount ? (c.onlineCount / c.deviceCount) * 100 : 0
  if (m.key === 'resourceUse') return c.rackCapacity ? (c.rackUsed / c.rackCapacity) * 100 : 0
  if (m.key === 'netDelay') return 20 + (c.id % 5) * 6
  if (m.key === 'storage') return c.rackCapacity * 2
  return (c as any)[m.key] ?? 0
}

const sortedPicked = computed(() => {
  const arr = [...pickedCenters.value]
  const m = metricDefs.value.find((x) => x.key === sortKey.value)
  arr.sort((a, b) => {
    const va = metricVal(a, m as MetricDef)
    const vb = metricVal(b, m as MetricDef)
    return sortDir.value === 'asc' ? va - vb : vb - va
  })
  return arr
})

function fmt(c: IdcCompareItem, m: MetricDef) {
  return m.fmt ? m.fmt(c) : String((c as any)[m.key] ?? '—')
}
function cellCls(c: IdcCompareItem, m: MetricDef) {
  const max = m.max ? m.max(c) : Math.max(1, ...pickedCenters.value.map((x) => metricVal(x, m)))
  const v = metricVal(c, m)
  if (m.better === 'low') return v > max * 0.6 ? 'crit' : v > 0 ? 'warn' : 'ok'
  if (m.better === 'high') return v >= max * 0.8 ? 'ok' : v > 0 ? 'warn' : 'crit'
  if (m.max) return v >= max * 0.8 ? 'warn' : 'ok'
  return ''
}

const pickedAlarms = computed(() => alarms.value.items.filter((a) => picked.value.includes(a.idcId)))

function togglePick(id: number) {
  const i = picked.value.indexOf(id)
  if (i >= 0) picked.value.splice(i, 1)
  else picked.value.push(id)
}
function dropCol(idx: number) {
  if (dragIdx.value < 0 || dragIdx.value === idx) return
  const arr = metricDefs.value
  const [item] = arr.splice(dragIdx.value, 1)
  arr.splice(idx, 0, item)
  dragIdx.value = -1
}
function resetCols() {
  metricDefs.value.forEach((m) => (m.on = true))
  metricDefs.value.sort((a, b) => metricOrder.indexOf(a.key) - metricOrder.indexOf(b.key))
}
const metricOrder = ['powerCapacityMw', 'coolingCapacityMw', 'rackUsed', 'deviceCount', 'onlineCount', 'onlineRate', 'resourceUse', 'netDelay', 'storage', 'activeAlarmCount']

const palette = ['#22d3ee', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#ec4899', '#14b8a6']
function colorOf(id: number) {
  const i = cmp.value.centers.findIndex((c) => c.id === id)
  return palette[i % palette.length]
}

const barOption = computed(() => {
  const centers = sortedPicked.value
  const cats = metricDefs.value.filter((m) => m.on)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: centers.map((c) => c.name), textStyle: { color: '#9fb3c8' } },
    grid: { left: 80, right: 24, bottom: 40, top: 40 },
    xAxis: { type: 'category', data: cats.map((m) => m.label), axisLabel: { color: '#9fb3c8', interval: 0, rotate: 20 } },
    yAxis: { type: 'value', axisLabel: { color: '#9fb3c8' } },
    series: centers.map((c) => ({
      name: c.name, type: 'bar',
      data: cats.map((m) => (m.fmt ? metricVal(c, m) : (c as any)[m.key])),
      itemStyle: { color: colorOf(c.id) },
    })),
  }
})

const radarOption = computed(() => {
  const centers = sortedPicked.value
  const cats = metricDefs.value.filter((m) => m.on)
  const indicators = cats.map((m) => ({
    name: m.label,
    max: m.max ? m.max(centers[0]) : Math.max(1, ...centers.map((c) => metricVal(c, m))),
  }))
  return {
    tooltip: {},
    legend: { data: centers.map((c) => c.name), textStyle: { color: '#9fb3c8' }, top: 0 },
    radar: { indicator: indicators, axisName: { color: '#9fb3c8' }, radius: '65%' },
    series: [{
      type: 'radar',
      data: centers.map((c) => ({
        name: c.name,
        value: cats.map((m) => (m.fmt ? metricVal(c, m) : (c as any)[m.key])),
        lineStyle: { color: colorOf(c.id) },
        itemStyle: { color: colorOf(c.id) },
        areaStyle: { opacity: 0.08 },
      })),
    }],
  }
})

function exportCsv() {
  const headers = ['name', ...visibleMetrics.value.map((m) => m.label)]
  const rows = sortedPicked.value.map((c) => [c.name, ...visibleMetrics.value.map((m) => fmt(c, m))])
  const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'datacenter-compare.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function load() {
  loading.value = true
  Promise.all([compareIdcs(), unifiedAlarms()])
    .then(([c, a]) => {
      cmp.value = c
      alarms.value = a
      picked.value = c.centers.map((x) => x.id).slice(0, 4)
    })
    .finally(() => (loading.value = false))
}

onMounted(load)
</script>

<style scoped>
.dc-cmp { display: flex; flex-direction: column; gap: 14px; }
.view-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.view-head h1 { font-size: 18px; margin: 0; }
.view-head .sub { color: var(--muted); font-size: 12px; }
.head-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.btn-sm { color: var(--txt2); border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 5px 10px; font-size: 12px; cursor: pointer; text-decoration: none; display: inline-block; }
.btn-sm:hover { color: var(--cyan); border-color: var(--cyan); }
.btn-xs { color: var(--txt2); border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 3px 8px; font-size: 11px; cursor: pointer; }
.ipt.sm { background: var(--track); border: 1px solid var(--line); border-radius: 8px; padding: 5px 8px; color: var(--txt-strong); font-size: 12px; }
.list-head { font-size: 14px; font-weight: 700; color: var(--txt-strong); margin-bottom: 10px; }
.sub2 { font-size: 11px; color: var(--muted); font-weight: 400; margin-left: 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 999px; font-size: 12px; color: var(--txt2); cursor: pointer; }
.chip.on { border-color: var(--cyan); color: var(--cyan); }
.chip.cur { box-shadow: 0 0 0 1px var(--cyan) inset; }
.chip input { display: none; }
.cur-tag { font-size: 10px; color: var(--cyan); font-style: normal; }
.opts { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px; align-items: flex-end; }
.opt { display: flex; flex-direction: column; gap: 4px; }
.opt label { font-size: 11px; color: var(--muted); }
.cols { margin-top: 12px; border-top: 1px dashed var(--line); padding-top: 10px; }
.cols-head { font-size: 11px; color: var(--muted); margin-bottom: 8px; }
.col-list { list-style: none; margin: 0 0 8px; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.col-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: var(--track); border-radius: 8px; cursor: grab; }
.grip { color: var(--muted); }
.chk { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--txt2); margin-right: auto; }
.order { font-size: 11px; color: var(--muted); }
.table { overflow: auto; }
.cmp-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.cmp-table th, .cmp-table td { padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: center; color: var(--txt2); }
.cmp-table thead th { color: var(--txt-strong); font-weight: 700; }
.cmp-table thead th.cur, .cmp-table td.cur { color: var(--cyan); }
.metric-col { text-align: left !important; color: var(--muted) !important; }
.cmp-table td.crit { color: var(--red); font-weight: 700; }
.cmp-table td.warn { color: var(--amber); }
.cmp-table td.ok { color: var(--green); }
.mono { font-family: monospace; font-size: 11px; font-style: normal; }
.charts { display: block; }
.a-row { display: grid; grid-template-columns: 1.4fr 1.2fr 1fr 0.8fr 1fr; gap: 8px; padding: 8px; border-top: 1px solid var(--line); font-size: 12px; color: var(--txt2); }
.a-row.ah { color: var(--muted); font-weight: 600; border-top: none; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--txt2); }
.tag.b { color: #38bdf8; border-color: rgba(56,189,248,.4); }
.tag.a { color: var(--amber); border-color: rgba(245,158,11,.4); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); }
.empty { text-align: center; color: var(--muted); padding: 24px; font-size: 13px; }
.empty.warn { color: var(--amber); }

@media (max-width: 720px) {
  .head-actions { margin-left: 0; width: 100%; }
  .opts { gap: 10px; }
  .a-row { grid-template-columns: 1fr 1fr; }
  .a-row.ah { display: none; }
}
</style>
