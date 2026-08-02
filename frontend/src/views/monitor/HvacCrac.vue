<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.hvacMonitor') }} {{ tl('·') }} {{ tl('nav.crac') }} (CRAC)</h1>
      <span class="sub">{{ tl('空调末端诊断') }} {{ tl('·') }} {{ tl('包间设备归集') }} {{ tl('·') }} {{ tl('7类趋势分析') }}</span>
    </div>

    <!-- ======== KPI Row 1 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="crac-total" :label="tl('末端设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="crac-online" :label="tl('运行/待机/故障')" :value="s.online" :unit="`/ ${s.standby} / ${s.fault}`" quality="good" :online="true" />
      <MetricCard metric-name="crac-leak" :label="tl('漏水告警')" :value="s.leakAlarm" :unit="`/ ${s.leakTotal}`" :quality="s.leakAlarm ? 'bad' : 'good'" :severity="s.leakAlarm ? 'crit' : 'normal'" :online="true" />
      <MetricCard metric-name="crac-outdoor" :label="tl('室外参照温度')" :value="s.outdoorRef" unit="°C" quality="good" :online="true" icon-hint="temp" />
    </div>

    <!-- KPI Row 2 -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="crac-supply-t" :label="tl('平均送风温度')" :value="s.avgSupplyT" unit="°C" quality="good" :online="true" icon-hint="temp" />
      <MetricCard metric-name="crac-return-t" :label="tl('平均回风温度')" :value="s.avgReturnT" unit="°C" :quality="s.avgReturnT > 30 ? 'uncertain' : 'good'" :severity="s.avgReturnT > 32 ? 'warn' : 'normal'" :online="true" icon-hint="temp" />
      <MetricCard metric-name="crac-supply-wt" :label="tl('平均供水温度')" :value="s.avgSupplyWaterT" unit="°C" quality="good" :online="true" icon-hint="temp" />
      <MetricCard metric-name="crac-inout-diff" :label="tl('平均室内外压差')" :value="s.avgInOutDiff" unit="Pa" :quality="s.avgInOutDiff > 0 ? 'good' : 'uncertain'" :online="true" />
    </div>

    <!-- 加载 / 错误态 -->
    <template v-if="!s">
      <div class="card" v-if="!error"><div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div></div>
      <div class="card" v-if="error"><div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div></div>
    </template>

    <template v-else>
      <!-- ======== 包间设备归集卡片 ======== -->
      <div class="section-title">
        <span>{{ tl('包间设备归集') }}</span>
        <span class="section-sub">{{ tl('每个包间一框：新风机组 + 房间级精密空调 + 列间空调 + 恒湿一体机 + 温湿度压差传感器') }}</span>
      </div>
      <div class="room-groups-grid">
        <div class="room-card" v-for="g in roomGroups" :key="g.roomId">
          <!-- 包间头部 -->
          <div class="room-card-head">
            <span class="rch-status" :class="g.status === '正常' ? 'g' : 'r'">●</span>
            <span class="rch-name">{{ g.roomName }}</span>
            <span class="rch-badges">
              <span class="badge badge-info">{{ g.cracRun }}/{{ g.cracN }} {{ tl('运行') }}</span>
              <span class="badge" :class="g.leak.status === '报警' ? 'badge-bad' : 'badge-ok'">{{ g.leak.status === '报警' ? '⚠ ' : '' }}{{ tl('漏水') }}: {{ g.leak.status }}</span>
            </span>
          </div>

          <!-- 温湿度压差传感器 -->
          <div class="sensor-row">
            <div class="sensor-block" v-for="item in sensorItems(g)" :key="item.label">
              <span class="sensor-label">{{ item.label }}</span>
              <span class="sensor-val" :class="item.cls">{{ item.val }}</span>
            </div>
          </div>

          <!-- 精密空调区域 -->
          <div class="equip-section" v-if="g.roomCracs.length">
            <span class="equip-tag tag-crac">{{ tl('房间级精密空调') }}</span>
            <div class="equip-row" v-for="u in g.roomCracs" :key="u.code">
              <span class="e-status" :class="pinCls(u.status)">●</span>
              <span class="e-name">{{ u.code }}</span>
              <span class="e-val">{{ u.supplyT === '-' ? '—' : u.supplyT + '°C' }}</span>
              <span class="e-sep">/</span>
              <span class="e-val">{{ u.returnT === '-' ? '—' : u.returnT + '°C' }}</span>
              <span class="e-meta">{{ tl('风机') }} {{ u.fanSpeed }}% {{ tl('阀') }} {{ u.waterValve }}%</span>
            </div>
          </div>
          <div class="equip-section" v-if="g.inRowCracs.length">
            <span class="equip-tag tag-inrow">{{ tl('列间空调') }}</span>
            <div class="equip-row" v-for="u in g.inRowCracs" :key="u.code">
              <span class="e-status" :class="pinCls(u.status)">●</span>
              <span class="e-name">{{ u.code }}</span>
              <span class="e-val">{{ u.supplyT === '-' ? '—' : u.supplyT + '°C' }}</span>
              <span class="e-sep">/</span>
              <span class="e-val">{{ u.returnT === '-' ? '—' : u.returnT + '°C' }}</span>
              <span class="e-meta">{{ tl('风机') }} {{ u.fanSpeed }}% {{ tl('阀') }} {{ u.waterValve }}%</span>
            </div>
          </div>

          <!-- 新风机组 + 恒湿机 -->
          <div class="aux-row">
            <div class="aux-item" v-if="g.fau">
              <span class="aux-tag tag-fau">FAU</span>
              <span class="aux-status" :class="g.fau.state === '运行' ? 'g' : 'm'">●</span>
              <span class="aux-name">{{ g.fau.id }}</span>
              <span class="aux-val">{{ g.fau.state === '运行' ? g.fau.supplyT + '°C ' + g.fau.rh + '% CO₂' + g.fau.co2 + 'ppm ΔP' + g.fau.filterDp + 'Pa' : '待机' }}</span>
            </div>
            <div class="aux-item" v-if="g.humidifier">
              <span class="aux-tag tag-hum">HUM</span>
              <span class="aux-status" :class="g.humidifier.state === '运行' ? 'g' : 'm'">●</span>
              <span class="aux-name">{{ g.humidifier.id }}</span>
              <span class="aux-val">{{ g.humidifier.state === '运行' ? g.humidifier.mode + ' ' + g.humidifier.rh + '%RH' : '待机' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 7类趋势诊断图表 ======== -->
      <div class="section-title">{{ tl('趋势诊断分析') }}</div>

      <!-- 1. 回风温度偏差累积 48h -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('1. 回风温度与设定值偏差累积 (温差积分)') }}</span>
          <span class="chart-period">48h</span>
        </div>
        <div ref="elDeltaT" class="chart-body" style="height:320px"></div>
      </div>

      <!-- 2. 滤网压差爬升斜率 90d -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('2. 滤网压差(ΔP)月度爬升斜率') }}</span>
          <span class="chart-period">90d</span>
        </div>
        <div ref="elFilterDp" class="chart-body" style="height:340px"></div>
      </div>

      <!-- 3. SHR 长期趋势 周 -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('3. 显热比(SHR)长期趋势') }}</span>
          <span class="chart-period">{{ tl('以周为单位') }}</span>
        </div>
        <div ref="elShr" class="chart-body" style="height:300px"></div>
      </div>

      <!-- 4. 送风 vs 机柜进风温差 -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('4. 送风温度与机柜进风区域温度温差对比') }}</span>
          <span class="chart-period">
            <button class="btn-tiny" :class="{ active: stPeriod === '24h' }" @click="setSupplyPeriod('24h')">24h</button>
            <button class="btn-tiny" :class="{ active: stPeriod === '7d' }" @click="setSupplyPeriod('7d')">7d</button>
            <button class="btn-tiny" :class="{ active: stPeriod === '30d' }" @click="setSupplyPeriod('30d')">30d</button>
          </span>
        </div>
        <div ref="elSupplyCab" class="chart-body" style="height:320px"></div>
      </div>

      <!-- 5. 风机转速 vs 送风静压 关联滞后 -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('5. 风机转速(%)与送风静压(Pa)关联滞后分析') }}</span>
          <span class="chart-period">{{ tl('7天 (逐日相关系数)') }}</span>
        </div>
        <div ref="elFanStatic" class="chart-body" style="height:360px"></div>
      </div>

      <!-- 6. 水阀开度 vs ΔT 叠加 -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('6. 冷冻水电动二通阀开度(%V)与进出水水温差(ΔT)趋势叠加') }}</span>
          <span class="chart-period">24h</span>
        </div>
        <div ref="elValveDt" class="chart-body" style="height:320px"></div>
      </div>

      <!-- 7. 吸气/排气过热度 -->
      <div class="chart-card">
        <div class="chart-head">
          <span class="chart-title">{{ tl('7. 吸气过热度与排气过热度趋势') }}</span>
          <span class="chart-period">24h</span>
        </div>
        <div ref="elSuperheat" class="chart-body" style="height:320px"></div>
      </div>

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('空调末端') }} · {{ s.total }} {{ tl('台设备') }} · {{ s.devices.length }} {{ tl('台精密空调') }} · {{ s.leakTotal }} {{ tl('路漏水检测') }}
        · {{ roomGroups.length }} {{ tl('包间设备归集') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import MetricCard from '@/components/common/MetricCard.vue'
import { getCrac, getCracTrends, mapCracRoomGroups, type CracSummary, type CracRoomGroupView, type CracTrends } from '@/api/hvac'

const { t: tl } = useI18n()

// --- 基础数据 ---
const s = ref<CracSummary | null>(null)
const roomGroups = ref<CracRoomGroupView[]>([])
const trends = ref<CracTrends | null>(null)
const error = ref('')

const stPeriod = ref('24h')

function pinCls(st: string) {
  if (st === 'online') return 'g'
  if (st === 'fault') return 'r'
  return 'm'
}

function tempCls(v: number): string {
  if (v >= 32) return 'r'
  if (v >= 28) return 'a'
  return ''
}

function sensorItems(g: CracRoomGroupView) {
  const e = g.envSensors
  return [
    { label: '平均温度', val: e.avgTemp.toFixed(1) + '°C', cls: tempCls(e.avgTemp) },
    { label: '湿度', val: e.avgRh.toFixed(0) + '%', cls: '' },
    { label: '热通道', val: e.hotAisleTemp.toFixed(1) + '°C ' + e.hotAisleRh.toFixed(0) + '%', cls: tempCls(e.hotAisleTemp) },
    { label: '冷通道', val: e.coldAisleTemp.toFixed(1) + '°C ' + e.coldAisleRh.toFixed(0) + '%', cls: '' },
    { label: '露点', val: e.dewPoint.toFixed(1) + '°C', cls: '' },
    { label: '压差', val: e.inOutDiff.toFixed(1) + 'Pa', cls: e.inOutDiff < 3 ? 'a' : '' },
    { label: '静压', val: e.supplyStaticPressure.toFixed(0) + 'Pa', cls: '' },
  ]
}

// --- ECharts 容器 refs ---
const elDeltaT = ref<HTMLElement | null>(null)
const elFilterDp = ref<HTMLElement | null>(null)
const elShr = ref<HTMLElement | null>(null)
const elSupplyCab = ref<HTMLElement | null>(null)
const elFanStatic = ref<HTMLElement | null>(null)
const elValveDt = ref<HTMLElement | null>(null)
const elSuperheat = ref<HTMLElement | null>(null)

const charts: Record<string, echarts.ECharts | null> = {}

const COLORS = [
  '#4fc3f7', '#81c784', '#ffb74d', '#e57373', '#ba68c8', '#4db6ac',
  '#ff8a65', '#7986cb', '#a1887f', '#90a4ae'
]

function initChart(key: string, el: HTMLElement | null, option: any) {
  if (!el) return
  if (charts[key]) {
    try { charts[key]!.dispose() } catch {}
    charts[key] = null
  }
  try {
    const inst = echarts.init(el)
    inst.setOption(option)
    charts[key] = inst
  } catch { /* DOM未就绪 */ }
}

function disposeAll() {
  Object.values(charts).forEach((c) => { try { c?.dispose() } catch {} })
  Object.keys(charts).forEach((k) => { charts[k] = null })
}

// --- 渲染所有图表 ---
function renderCharts() {
  if (!trends.value) return
  const td = trends.value

  // 1. ΔT Integral 48h
  if (td.deltaTIntegral?.rooms?.length) {
    const series: any[] = []
    td.deltaTIntegral.rooms.forEach((rm, ri) => {
      (rm.series || []).forEach((s: any) => {
        series.push({
          name: `${rm.roomName} ${s.label}`,
          type: 'line',
          data: s.data,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.5 },
        })
      })
    })
    initChart('deltaT', elDeltaT.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 10, color: '#999' }, itemWidth: 12, itemHeight: 8, type: 'scroll' },
      grid: { left: 60, right: 20, top: 35, bottom: 30 },
      xAxis: { type: 'category', data: Array.from({ length: series[0]?.data?.length || 0 }, (_, i) => i * 5 + 'm'), axisLabel: { fontSize: 9, interval: 47 } },
      yAxis: { type: 'value', name: '°C·h', axisLabel: { fontSize: 10 } },
      dataZoom: [{ type: 'inside' }],
      series,
    })
  }

  // 2. Filter ΔP Slope 90d
  if (td.filterDpSlope?.units?.length) {
    const rawSeries: any[] = []
    const slopeSeries: any[] = []
    const days = (td.filterDpSlope.units[0]?.raw || []).map((p: any) => p.date)
    td.filterDpSlope.units.forEach((u: any) => {
      rawSeries.push({ name: `${u.roomName} ${u.label} ΔP`, type: 'line', data: (u.raw || []).map((p: any) => p.value), smooth: true, symbol: 'none', lineStyle: { width: 1.5 } })
      slopeSeries.push({ name: `${u.roomName} ${u.label} 斜率`, type: 'line', data: (u.slope || []).map((p: any) => p.value), smooth: true, symbol: 'none', lineStyle: { width: 2, type: 'dashed' } })
    })
    initChart('filterDp', elFilterDp.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 9, color: '#999' }, type: 'scroll' },
      grid: { left: 60, right: 20, top: 35, bottom: 50 },
      xAxis: { type: 'category', data: days, axisLabel: { fontSize: 9, interval: 9 } },
      yAxis: [
        { type: 'value', name: 'ΔP (Pa)', axisLabel: { fontSize: 10 } },
        { type: 'value', name: '斜率 (Pa/d)', axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: 'inside' }],
      series: [...rawSeries, ...slopeSeries.map((s: any, i: number) => ({ ...s, yAxisIndex: 1 }))],
    })
  }

  // 3. SHR Trend Weekly
  if (td.shrTrend?.units?.length) {
    const weeks = (td.shrTrend.units[0]?.data || []).map((p: any) => p.week)
    const shrSeries = td.shrTrend.units.map((u: any) => ({
      name: `${u.roomName} ${u.label}`,
      type: 'line',
      data: (u.data || []).map((p: any) => p.value),
      smooth: true,
      symbol: 'circle', symbolSize: 6,
      lineStyle: { width: 2 },
      markLine: { silent: true, data: [{ yAxis: 0.80, label: { formatter: '下限' }, lineStyle: { color: '#e57373', type: 'dashed' } }] },
    }))
    initChart('shr', elShr.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 9, color: '#999' }, type: 'scroll' },
      grid: { left: 55, right: 20, top: 35, bottom: 30 },
      xAxis: { type: 'category', data: weeks, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: 'SHR', min: 0.70, max: 1.0, axisLabel: { fontSize: 10 } },
      series: shrSeries,
    })
  }

  // 4. Supply vs Cabinet Temp
  if (td.supplyVsCabinet?.rooms?.length) {
    const pd = td.supplyVsCabinet.rooms[0]?.periods?.[stPeriod.value]
    if (pd) {
      initChart('supplyCab', elSupplyCab.value, {
        tooltip: { trigger: 'axis' },
        legend: { top: 0, textStyle: { fontSize: 10, color: '#999' } },
        grid: { left: 55, right: 55, top: 35, bottom: 30 },
        xAxis: { type: 'category', data: (pd.timestamps || []).map((_t, i) => i % Math.ceil(pd.timestamps.length / 20) === 0 ? _t.slice(11, 16) : ''), axisLabel: { fontSize: 9 } },
        yAxis: [
          { type: 'value', name: '温度 °C', axisLabel: { fontSize: 10 } },
          { type: 'value', name: 'ΔT °C', axisLabel: { fontSize: 10 } },
        ],
        dataZoom: [{ type: 'inside' }],
        series: [
          { name: '送风温度', type: 'line', data: pd.supplyTemp, smooth: true, symbol: 'none', lineStyle: { color: '#4fc3f7', width: 1.5 } },
          { name: '机柜进风温度', type: 'line', data: pd.cabinetInletTemp, smooth: true, symbol: 'none', lineStyle: { color: '#ffb74d', width: 1.5 } },
          { name: '温差 ΔT', type: 'line', data: pd.deltaT, smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#e57373', width: 2, type: 'dashed' }, areaStyle: { color: 'rgba(229,115,115,0.08)' } },
        ],
      })
    }
  }

  // 5. Fan Speed vs Static Pressure
  if (td.fanVsStaticPressure?.units?.length) {
    const u0 = td.fanVsStaticPressure.units[0]
    const fanSeries: any[] = []
    td.fanVsStaticPressure.units.forEach((u: any) => {
      fanSeries.push({ name: `${u.roomName} ${u.label} 风机`, type: 'line', data: u.fanSpeed, smooth: true, symbol: 'none', lineStyle: { width: 1.5 }, yAxisIndex: 0 })
      fanSeries.push({ name: `${u.roomName} ${u.label} 静压`, type: 'line', data: u.staticPressure, smooth: true, symbol: 'none', lineStyle: { width: 1.5 }, yAxisIndex: 1 })
    })
    initChart('fanStatic', elFanStatic.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 9, color: '#999' }, type: 'scroll' },
      grid: { left: 55, right: 55, top: 35, bottom: 55 },
      xAxis: { type: 'category', data: (u0?.timestamps || []).map((t, i) => i % 48 === 0 ? t.slice(5, 16) : ''), axisLabel: { fontSize: 9 } },
      yAxis: [
        { type: 'value', name: '风机转速 %', axisLabel: { fontSize: 10 } },
        { type: 'value', name: '静压 Pa', axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: 'inside' }],
      series: fanSeries,
    })
  }

  // 6. Valve vs ΔT
  if (td.valveDeltaT?.units?.length) {
    const u0 = td.valveDeltaT.units[0]
    const vSeries: any[] = []
    td.valveDeltaT.units.forEach((u: any) => {
      vSeries.push({ name: `${u.roomName} ${u.label} 阀开度`, type: 'line', data: u.valveOpening, smooth: true, symbol: 'none', lineStyle: { width: 1.5 }, yAxisIndex: 0 })
      vSeries.push({ name: `${u.roomName} ${u.label} ΔT`, type: 'line', data: u.waterDeltaT, smooth: true, symbol: 'none', lineStyle: { width: 2, type: 'dashed' }, yAxisIndex: 1 })
    })
    initChart('valveDt', elValveDt.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 9, color: '#999' }, type: 'scroll' },
      grid: { left: 55, right: 55, top: 35, bottom: 30 },
      xAxis: { type: 'category', data: (u0?.timestamps || []).map((t, i) => i % 60 === 0 ? t.slice(11, 16) : ''), axisLabel: { fontSize: 9 } },
      yAxis: [
        { type: 'value', name: '阀开度 %', max: 100, axisLabel: { fontSize: 10 } },
        { type: 'value', name: 'ΔT °C', axisLabel: { fontSize: 10 } },
      ],
      dataZoom: [{ type: 'inside' }],
      series: vSeries,
    })
  }

  // 7. Superheat Trend
  if (td.superheatTrend?.units?.length) {
    const u0 = td.superheatTrend.units[0]
    const shSeries: any[] = []
    td.superheatTrend.units.forEach((u: any) => {
      shSeries.push({ name: `${u.roomName} ${u.label} 吸气`, type: 'line', data: u.suctionSuperheat, smooth: true, symbol: 'none', lineStyle: { width: 2 } })
      shSeries.push({ name: `${u.roomName} ${u.label} 排气`, type: 'line', data: u.dischargeSuperheat, smooth: true, symbol: 'none', lineStyle: { width: 2, type: 'dashed' } })
    })
    initChart('superheat', elSuperheat.value, {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 9, color: '#999' }, type: 'scroll' },
      grid: { left: 55, right: 20, top: 35, bottom: 30 },
      xAxis: { type: 'category', data: (u0?.timestamps || []).map((t, i) => i % 24 === 0 ? t.slice(11, 16) : ''), axisLabel: { fontSize: 9 } },
      yAxis: { type: 'value', name: '°C', axisLabel: { fontSize: 10 } },
      dataZoom: [{ type: 'inside' }],
      series: shSeries,
    })
  }
}

function setSupplyPeriod(p: string) {
  stPeriod.value = p
}

// --- 数据加载 ---
async function load() {
  error.value = ''
  try {
    const [cracRaw, trendsRaw] = await Promise.all([
      getCrac().then(() => getCracRaw()),
      getCracTrends(),
    ]) as [any, CracTrends]
    s.value = mapCrac(cracRaw)
    roomGroups.value = mapCracRoomGroups(cracRaw)
    trends.value = trendsRaw
    await nextTick()
    renderCharts()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}

// helper: get raw data for mapCracRoomGroups
async function getCracRaw() {
  const { default: request } = await import('@/api/request')
  return request.get('/api/hvac/crac')
}

function mapCrac(raw: any): CracSummary {
  const list: any[] = raw?.units ?? []
  const devices = list.map((d: any, i: number) => ({
    id: i + 1,
    code: d.id ?? `CRAC-${i + 1}`,
    name: d.id ?? `CRAC-${i + 1}`,
    roomName: d.room ?? '包间',
    type: d.type ?? '精密空调',
    status: d.state === '运行' ? 'online' : d.state === '故障' ? 'fault' : 'standby',
    supplyT: d.supplyT === '-' ? '-' as const : Number(d.supplyT) || 0,
    returnT: d.returnT === '-' ? '-' as const : Number(d.returnT) || 0,
    supplyRh: d.supplyRh === '-' ? '-' as const : Number(d.supplyRh) || 0,
    returnRh: d.returnRh === '-' ? '-' as const : Number(d.returnRh) || 0,
    chilledWaterT: d.chilledWaterT === '-' ? '-' as const : Number(d.chilledWaterT) || 0,
    returnWaterT: d.returnWaterT === '-' ? '-' as const : Number(d.returnWaterT) || 0,
    fanSpeed: Number(d.fan) || 0,
    valve: Number(d.valve) || 0,
    waterValve: Number(d.waterValve) || 0,
    power: Number(d.power) || 0,
    dp: d.dp === '-' ? '-' as const : Number(d.dp) || 0,
    filter: d.filter ?? '正常',
    fanEnable: d.control?.fanEnable ?? true,
    fanSpeedSet: Number(d.control?.fanSpeedSet) || 0,
    waterValveSet: Number(d.control?.waterValveSet) || 0,
    coolingMode: d.control?.coolingMode ?? '制冷',
    humidOn: d.control?.humidOn ?? false,
    supplyTSet: Number(d.setpoints?.supplyTSet) || 0,
    rhSet: Number(d.setpoints?.rhSet) || 0,
    roomTSet: Number(d.setpoints?.roomTSet) || 0,
    highTempAlarm: Number(d.setpoints?.highTempAlarm) || 0,
    lowTempAlarm: Number(d.setpoints?.lowTempAlarm) || 0,
    highRhAlarm: Number(d.setpoints?.highRhAlarm) || 0,
    commissionedOn: null,
    healthScore: null,
  } as any))
  const onlineCount = devices.filter((d: any) => d.status === 'online').length
  const ss = raw?.summary ?? {}
  return {
    total: Number(ss.total) || devices.length,
    online: onlineCount,
    standby: Number(ss.standby) || 0,
    fault: Number(ss.fault) || 0,
    outdoorRef: Number(ss.outdoorRef) || 0,
    avgSupplyT: Number(ss.avgSupply) || 0,
    avgReturnT: Number(ss.avgReturn) || 0,
    avgSupplyWaterT: Number(ss.avgSupplyWater) || 0,
    avgReturnWaterT: Number(ss.avgReturnWater) || 0,
    avgInOutDiff: Number(ss.avgInOutDiff) || 0,
    leakAlarm: Number(ss.leakAlarm) || 0,
    leakTotal: Number(ss.leakTotal) || 0,
    devices,
    rooms: [],
    leakDevices: [],
    freshAir: [],
    humidifiers: [],
    funcRooms: [],
    ctrl: {} as any,
    avgTemperatureIn: 0,
    avgTemperatureOut: 0,
    avgHumidityIn: 0,
    avgFanSpeed: 0,
  }
}

// --- 生命周期 ---
onMounted(load)

watch(stPeriod, () => {
  nextTick(() => renderCharts())
})

import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => { disposeAll() })
</script>

<style scoped>
/* ---- 通用 ---- */
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.ct { font-weight: 600; font-size: 14px; }
.muted { color: var(--txt3); }
.flex { display: flex; }
.center { justify-content: center; align-items: center; }

/* ---- Section ---- */
.section-title {
  display: flex; justify-content: space-between; align-items: baseline;
  margin: 20px 0 12px; font-weight: 600; font-size: 15px; color: var(--cyan);
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
}
.section-sub { font-weight: 400; font-size: 11px; color: var(--muted); }

/* ---- Room Groups Grid ---- */
.room-groups-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.room-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 11px;
}

.room-card-head {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px; padding-bottom: 6px;
  border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.05));
}
.rch-status { font-size: 7px; }
.rch-status.g { color: var(--green); }
.rch-status.r { color: var(--red); }
.rch-name { font-weight: 600; font-size: 13px; flex: 1; }
.rch-badges { display: flex; gap: 4px; }
.badge { font-size: 9px; padding: 1px 6px; border-radius: 8px; background: var(--bg3); }
.badge-info { color: var(--blue); background: rgba(79,195,247,0.12); }
.badge-ok { color: var(--green); background: rgba(82,196,26,0.12); }
.badge-bad { color: var(--red); background: rgba(255,77,94,0.12); }

/* ---- Sensor Row ---- */
.sensor-row {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 4px 8px; margin-bottom: 8px;
  padding: 4px 6px; background: var(--bg1); border-radius: 4px;
}
.sensor-block { display: flex; flex-direction: column; }
.sensor-label { font-size: 9px; color: var(--txt3); }
.sensor-val { font-size: 11px; font-weight: 500; }
.sensor-val.r { color: var(--red); }
.sensor-val.a { color: var(--amber); }

/* ---- Equipment Sections ---- */
.equip-section { margin-bottom: 5px; }
.equip-tag { font-size: 9px; padding: 1px 5px; border-radius: 3px; margin-bottom: 3px; display: inline-block; }
.tag-crac { background: rgba(79,195,247,0.15); color: var(--cyan); }
.tag-inrow { background: rgba(129,199,132,0.15); color: #81c784; }

.equip-row {
  display: flex; align-items: center; gap: 3px;
  padding: 2px 6px; font-size: 10px;
}
.e-status { font-size: 7px; }
.e-status.g { color: var(--green); }
.e-status.r { color: var(--red); }
.e-status.m { color: var(--muted); }
.e-name { font-weight: 500; min-width: 50px; }
.e-val { color: var(--txt1); min-width: 30px; }
.e-sep { opacity: 0.3; font-size: 8px; }
.e-meta { color: var(--txt3); font-size: 9px; margin-left: auto; }

/* ---- Aux row (FAU + HUM) ---- */
.aux-row { display: flex; gap: 6px; margin-top: 5px; }
.aux-item { display: flex; align-items: center; gap: 3px; flex: 1; font-size: 10px; padding: 2px 4px; background: var(--bg1); border-radius: 3px; overflow: hidden; }
.aux-tag { font-size: 8px; padding: 0 3px; border-radius: 2px; font-weight: 600; }
.tag-fau { background: rgba(255,183,77,0.15); color: #ffb74d; }
.tag-hum { background: rgba(186,104,200,0.15); color: #ba68c8; }
.aux-status { font-size: 6px; flex-shrink: 0; }
.aux-status.g { color: var(--green); }
.aux-status.m { color: var(--muted); }
.aux-name { font-weight: 500; white-space: nowrap; font-size: 9px; }
.aux-val { color: var(--txt2); font-size: 9px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---- Chart Cards ---- */
.chart-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
}
.chart-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 6px;
}
.chart-title { font-size: 13px; font-weight: 600; color: var(--txt1); }
.chart-period { display: flex; gap: 4px; align-items: center; font-size: 10px; color: var(--muted); }
.btn-tiny {
  padding: 2px 8px; font-size: 10px; border-radius: 4px; border: 1px solid var(--border);
  background: transparent; color: var(--txt2); cursor: pointer;
}
.btn-tiny.active { background: var(--cyan); color: #000; border-color: var(--cyan); }
.btn-tiny:hover { border-color: var(--cyan); }
.chart-body { width: 100%; }

/* ---- Footer ---- */
.footer-note { text-align: center; margin-top: 20px; font-size: 11px; }
</style>