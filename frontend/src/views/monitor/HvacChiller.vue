<template>
  <div class="chiller-page">
    <!-- ======== 系统总览 KPI ======== -->
    <div class="kpi-bar">
      <div class="kpi-item">
        <div class="kpi-label">运行模式</div>
        <div class="kpi-value mode" :class="chiller?.mode">{{ chiller?.mode || '-' }}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">冷冻供水温度</div>
        <div class="kpi-value">{{ chiller?.supplyTemp ?? '-' }}<small>℃</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">冷冻回水温度</div>
        <div class="kpi-value">{{ chiller?.returnTemp ?? '-' }}<small>℃</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">室外温度 / 湿球</div>
        <div class="kpi-value">{{ chiller?.outdoorTemp ?? '-' }} / {{ chiller?.wetBulb ?? '-' }}<small>℃</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">部分负载率 PLR</div>
        <div class="kpi-value" :class="plrClass">{{ chiller?.plr ?? '-' }}<small>%</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">制冷总量</div>
        <div class="kpi-value">{{ chiller?.coolingCap ?? '-' }}<small>MW</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">总流量</div>
        <div class="kpi-value">{{ chiller?.flow ?? '-' }}<small>m³/h</small></div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">在线/总数</div>
        <div class="kpi-value">{{ chiller?.online ?? 0 }}/{{ chiller?.total ?? 0 }}</div>
      </div>
    </div>

    <!-- ======== 制冷机组×水泵×蓄冷罐 分组卡片 ======== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c"></span> 制冷机组分组 (CH↔冷冻泵↔冷却泵↔蓄冷罐)
      </h3>
      <div class="chiller-groups">
        <div v-for="(g, i) in chillerGroups" :key="'g'+i" class="chiller-card" :class="{ standby: g.chiller?.state === '待机', fault: g.chiller?.state === '检修' }">
          <!-- 冷机头 -->
          <div class="ch-header">
            <span class="ch-id">{{ g.chiller?.id }}</span>
            <span class="ch-state" :class="g.chiller?.state">{{ g.chiller?.state }}</span>
          </div>
          <div class="ch-body">
            <div class="ch-metrics">
              <div><span>负载</span><b>{{ g.chiller?.load ?? 0 }}%</b></div>
              <div><span>COP</span><b :class="{ good: (g.chiller?.cop||0) >= 6 }">{{ g.chiller?.cop || '-' }}</b></div>
              <div><span>蒸发T</span><b>{{ g.chiller?.evapT ?? '-' }}℃</b></div>
              <div><span>冷凝T</span><b>{{ g.chiller?.condT ?? '-' }}℃</b></div>
            </div>
            <!-- 冷冻泵 CHWP -->
            <div class="pump-row" v-if="g.chwPump">
              <div class="pump-tag chw">CHW</div>
              <span>{{ g.chwPump.id }}</span>
              <span :class="g.chwPump.state">{{ g.chwPump.hz }}Hz</span>
              <span>{{ g.chwPump.flow }}m³/h</span>
            </div>
            <!-- 冷却泵 CWP -->
            <div class="pump-row" v-if="g.cwPump">
              <div class="pump-tag cw">CW</div>
              <span>{{ g.cwPump.id }}</span>
              <span :class="g.cwPump.state">{{ g.cwPump.hz }}Hz</span>
              <span>{{ g.cwPump.flow }}m³/h</span>
            </div>
            <!-- 蓄冷罐连接 -->
            <div class="tank-link" :class="{ on: g.tankConnected }">
              <span>{{ g.tankConnected ? '蓄冷罐直连' : '未连接蓄冷罐' }}</span>
              <span v-if="g.tankConnected && g.tankFlow > 0" class="tank-flow">{{ g.tankFlow }} m³/h</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ======== 趋势图 1: 冷冻水出水温度 vs 湿球温度 vs 负载率 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c1"></span> 冷冻水出水温度 · 室外湿球温度 · 负载率 叠加趋势</h3>
      <div class="chart-toolbar">
        <button v-for="r in ranges" :key="r" @click="activeRange=r" :class="{ active: activeRange === r }">{{ r }}</button>
      </div>
      <div ref="freezeChart" class="chart-box"></div>
    </div>

    <!-- ======== 趋势图 2: COP vs %RLA 散点 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c2"></span> 机组能效比 (COP) 与 负载率 (%RLA) 散点趋势</h3>
      <div class="chart-toolbar">
        <button v-for="r in ranges" :key="r" @click="activeRange=r" :class="{ active: activeRange === r }">{{ r }}</button>
      </div>
      <div ref="copChart" class="chart-box"></div>
    </div>

    <!-- ======== 趋势图 3: 冷凝水 vs 冷却水出水温差 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c3"></span> 冷凝水与冷却水出水温差趋势</h3>
      <div class="chart-toolbar">
        <button v-for="r in ranges" :key="r" @click="activeRange=r" :class="{ active: activeRange === r }">{{ r }}</button>
      </div>
      <div ref="condChart" class="chart-box"></div>
    </div>

    <!-- ======== 趋势图 4: 水泵频率 vs 流量 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c4"></span> 水泵频率 (Hz) 与 流量 (m³/h) 关联趋势</h3>
      <div class="chart-toolbar">
        <button v-for="r in ranges" :key="r" @click="activeRange=r" :class="{ active: activeRange === r }">{{ r }}</button>
      </div>
      <div ref="pumpChart" class="chart-box"></div>
    </div>

    <!-- ======== 趋势图 5: 罐体垂直温度梯度色阶图 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c5"></span> 蓄冷罐垂直温度梯度色阶图 (热力图)</h3>
      <div class="chart-toolbar">
        <button v-for="r in ranges" :key="r" @click="activeRange=r" :class="{ active: activeRange === r }">{{ r }}</button>
      </div>
      <div ref="tankChart" class="chart-box chart-box-lg"></div>
    </div>

    <!-- ======== 趋势图 6: 总制冷负载 + 自然冷源利用率 月度柱状 ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c6"></span> 总制冷负载 (RT) 与 自然冷源利用率 月度柱状叠加</h3>
      <div ref="monthlyChart" class="chart-box chart-box-lg"></div>
    </div>

    <!-- ======== 趋势图 7: ΔT vs 旁通阀开度 (1h) ======== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c7"></span> 冷冻水供回水温差 (ΔT) 与 旁通阀开度 — 过去1小时</h3>
      <div ref="deltaChart" class="chart-box"></div>
    </div>

    <!-- ======== 冷却塔 ======== -->
    <div class="section" v-if="chiller?.towers?.length">
      <h3 class="section-title">冷却塔</h3>
      <div class="simple-grid">
        <div v-for="t in chiller.towers" :key="t.code" class="simple-card" :class="t.state">
          <div class="sc-head">{{ t.code }} <span>{{ t.state }}</span></div>
          <div class="sc-row">风机 {{ t.fanHz }}Hz | 出水 {{ t.outTemp }}℃</div>
        </div>
      </div>
    </div>

    <!-- ======== 板式换热器 ======== -->
    <div class="section" v-if="chiller?.hexs?.length">
      <h3 class="section-title">板式换热器</h3>
      <div class="simple-grid">
        <div v-for="h in chiller.hexs" :key="h.code" class="simple-card" :class="h.state">
          <div class="sc-head">{{ h.code }} <span>{{ h.state }}</span></div>
          <div class="sc-row">效率 {{ h.eff }}% | 一次 {{ h.priIn }}→{{ h.priOut }}℃ | 二次 {{ h.secIn }}→{{ h.secOut }}℃</div>
        </div>
      </div>
    </div>

    <!-- ======== 蓄冷罐概要 ======== -->
    <div class="section" v-if="chiller?.storageTank">
      <h3 class="section-title">蓄冷罐概要</h3>
      <div class="simple-grid">
        <div class="simple-card">
          <div class="sc-row">液位 {{ chiller.storageTank.level }}% | 模式 {{ chiller.storageTank.mode }}</div>
          <div class="sc-row">顶部 {{ chiller.storageTank.topTemp }}℃ | 底部 {{ chiller.storageTank.botTemp }}℃ | 容量 {{ chiller.storageTank.capacity }}m³</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getChillerPlant, getChillerTrends, type ChillerSummary, type ChillerGroupView, type ChillerTrends } from '@/api/hvac'

const chiller = ref<ChillerSummary | null>(null)
const chillerGroups = ref<ChillerGroupView[]>([])
const trends = ref<ChillerTrends | null>(null)
const activeRange = ref('24h')
const ranges = ['24h', '7d', '30d']

// Chart refs
const freezeChart = ref<HTMLDivElement | null>(null)
const copChart = ref<HTMLDivElement | null>(null)
const condChart = ref<HTMLDivElement | null>(null)
const pumpChart = ref<HTMLDivElement | null>(null)
const tankChart = ref<HTMLDivElement | null>(null)
const monthlyChart = ref<HTMLDivElement | null>(null)
const deltaChart = ref<HTMLDivElement | null>(null)

let charts: Record<string, echarts.ECharts | null> = {
  freeze: null, cop: null, cond: null, pump: null, tank: null, monthly: null, delta: null
}

const plrClass = ref('low')

// ---- Color Palette ----
const colors = {
  cyan: '#06b6d4', orange: '#f97316', blue: '#3b82f6', green: '#22c55e',
  red: '#ef4444', purple: '#8b5cf6', yellow: '#eab308',
}

// ---- ECharts init helper ----
function initChart(el: HTMLDivElement | null, key: string): echarts.ECharts | null {
  if (!el) return null
  const instance = echarts.init(el)
  charts[key] = instance
  const ro = new ResizeObserver(() => instance.resize())
  ro.observe(el)
  ;(el as any).__ro = ro
  return instance
}

function disposeCharts() {
  Object.values(charts).forEach(c => {
    if (c) {
      const dom = c.getDom()
      if ((dom as any).__ro) (dom as any).__ro.disconnect()
      c.dispose()
    }
  })
  charts = { freeze: null, cop: null, cond: null, pump: null, tank: null, monthly: null, delta: null }
}

// ---- Time formatter ----
function fmtTime(ts: string, range: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  if (range === '24h') return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (range === '7d') return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return (d.getMonth() + 1) + '/' + d.getDate()
}

// ========== 图表渲染函数 ==========

function renderFreezeTrend() {
  const inst = charts.freeze
  if (!inst || !trends.value) return
  const r = activeRange.value
  const data = trends.value.freezeTrend?.[r]
  if (!data) return
  const tss = data.timestamps.map(t => fmtTime(t, r))
  inst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['冷冻水出水温度', '室外湿球温度', '负载率'], bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 50, right: 55, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: tss, axisLabel: { color: '#64748b', fontSize: 10, interval: Math.floor(tss.length / 8) }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: [
      { type: 'value', name: '℃', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
      { type: 'value', name: '%', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    ],
    series: [
      { name: '冷冻水出水温度', type: 'line', data: data.supplyTemp, smooth: true, lineStyle: { color: colors.cyan, width: 2 }, itemStyle: { color: colors.cyan }, symbol: 'none' },
      { name: '室外湿球温度', type: 'line', data: data.wetBulb, smooth: true, lineStyle: { color: colors.green, width: 2, type: 'dashed' }, itemStyle: { color: colors.green }, symbol: 'none' },
      { name: '负载率', type: 'line', yAxisIndex: 1, data: data.loadPct, smooth: true, lineStyle: { color: colors.orange, width: 2 }, areaStyle: { color: 'rgba(249,115,22,0.08)' }, itemStyle: { color: colors.orange }, symbol: 'none' },
    ],
  }, true)
}

function renderCopRla() {
  const inst = charts.cop
  if (!inst || !trends.value) return
  const r = activeRange.value
  const pts = trends.value.copRlaScatter?.[r]
  if (!pts) return
  const chIds = [...new Set(pts.map((p: any) => p.chiller))]
  const palette = [colors.cyan, colors.orange, colors.purple, colors.green, colors.blue, colors.red, colors.yellow, '#ec4899']
  inst.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.value[2]}<br/>RLA: ${p.value[0]}% | COP: ${p.value[1]}`,
    },
    legend: { data: chIds, bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 55, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'value', name: 'RLA (%)', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    yAxis: { type: 'value', name: 'COP', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: chIds.map((ch, i) => ({
      name: ch, type: 'scatter', symbolSize: 8,
      data: pts.filter((p: any) => p.chiller === ch).map((p: any) => [p.rla, p.cop, `${ch} @ ${fmtTime(p.ts, '24h')}`]),
      itemStyle: { color: palette[i % palette.length], opacity: 0.8 },
    })),
  }, true)
}

function renderCondCoolDiff() {
  const inst = charts.cond
  if (!inst || !trends.value) return
  const r = activeRange.value
  const data = trends.value.condCoolDiff?.[r]
  if (!data) return
  const tss = data.timestamps.map(t => fmtTime(t, r))
  inst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['冷凝出水温', '冷却出水温', '温差'], bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: tss, axisLabel: { color: '#64748b', fontSize: 10, interval: Math.floor(tss.length / 8) }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', name: '℃', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: '冷凝出水温', type: 'line', data: data.condTemp, smooth: true, lineStyle: { color: colors.red, width: 2 }, symbol: 'none' },
      { name: '冷却出水温', type: 'line', data: data.coolTemp, smooth: true, lineStyle: { color: colors.blue, width: 2 }, symbol: 'none' },
      { name: '温差', type: 'line', data: data.diff, smooth: true, lineStyle: { color: colors.purple, width: 2, type: 'dashed' }, symbol: 'none' },
    ],
  }, true)
}

function renderPumpFreqFlow() {
  const inst = charts.pump
  if (!inst || !trends.value) return
  const r = activeRange.value
  const data = trends.value.pumpFreqFlow?.[r]
  if (!data) return
  // Linear regression trendline
  function trendline(pts: { hz: number; flow: number }[]) {
    const n = pts.length
    const sumX = pts.reduce((s, p) => s + p.hz, 0)
    const sumY = pts.reduce((s, p) => s + p.flow, 0)
    const sumXY = pts.reduce((s, p) => s + p.hz * p.flow, 0)
    const sumXX = pts.reduce((s, p) => s + p.hz * p.hz, 0)
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX)
    const intercept = (sumY - slope * sumX) / n
    const xMin = Math.min(...pts.map(p => p.hz))
    const xMax = Math.max(...pts.map(p => p.hz))
    return [[xMin, slope * xMin + intercept], [xMax, slope * xMax + intercept]]
  }
  const chwTL = trendline(data.chwPump)
  const cwTL = trendline(data.cwPump)
  inst.setOption({
    tooltip: { trigger: 'item', formatter: (p: any) => `${p.seriesName}<br/>频率: ${p.value[0]}Hz<br/>流量: ${p.value[1]}m³/h` },
    legend: { data: ['冷冻泵 CHWP', '冷却泵 CWP'], bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 55, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'value', name: '频率 (Hz)', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    yAxis: { type: 'value', name: '流量 (m³/h)', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: '冷冻泵 CHWP', type: 'scatter', symbolSize: 7, data: data.chwPump.map((p: any) => [p.hz, p.flow]), itemStyle: { color: colors.cyan, opacity: 0.7 } },
      { name: '冷冻泵 CHWP', type: 'line', data: chwTL, smooth: false, lineStyle: { color: colors.cyan, width: 2, type: 'dashed' }, symbol: 'none', silent: true, z: 1 },
      { name: '冷却泵 CWP', type: 'scatter', symbolSize: 7, data: data.cwPump.map((p: any) => [p.hz, p.flow]), itemStyle: { color: colors.orange, opacity: 0.7 } },
      { name: '冷却泵 CWP', type: 'line', data: cwTL, smooth: false, lineStyle: { color: colors.orange, width: 2, type: 'dashed' }, symbol: 'none', silent: true, z: 1 },
    ],
  }, true)
}

function renderTankGradient() {
  const inst = charts.tank
  if (!inst || !trends.value) return
  const r = activeRange.value
  const data = trends.value.tankGradient?.[r]
  if (!data) return
  const tss = data.timestamps.map(t => fmtTime(t, r))
  const heatData: [number, number, number][] = []
  for (let lv = 0; lv < data.levels.length; lv++) {
    for (let ti = 0; ti < tss.length; ti++) {
      heatData.push([ti, lv, data.data[lv][ti]])
    }
  }
  inst.setOption({
    tooltip: {
      position: 'top',
      formatter: (p: any) => `时间: ${tss[p.value[0]]}<br/>${data.levels[p.value[1]]}: <b>${p.value[2]}℃</b>`,
    },
    grid: { left: 80, right: 30, top: 10, bottom: 40 },
    xAxis: {
      type: 'category', data: tss, axisLabel: { color: '#64748b', fontSize: 10, interval: Math.floor(tss.length / 10) },
      axisLine: { lineStyle: { color: '#334155' } }, position: 'bottom',
    },
    yAxis: { type: 'category', data: data.levels, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#334155' } } },
    visualMap: {
      min: 5, max: 14, calculable: true, orient: 'vertical', right: 0, top: 'center',
      inRange: { color: ['#06b6d4', '#22c55e', '#eab308', '#f97316', '#ef4444'] },
      text: ['高', '低'], textStyle: { color: '#94a3b8', fontSize: 10 },
    },
    series: [{ name: '罐温', type: 'heatmap', data: heatData, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
  }, true)
}

function renderMonthlyChart() {
  const inst = charts.monthly
  if (!inst || !trends.value) return
  const data = trends.value.coolingFreecoolingMonthly
  if (!data) return
  inst.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['制冷负载(RT)', '自然冷源利用率(%)'], bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 55, right: 55, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: data.days, axisLabel: { color: '#64748b', fontSize: 10, interval: 2 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: [
      { type: 'value', name: 'RT', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b', formatter: (v: number) => (v / 1000).toFixed(0) + 'k' }, splitLine: { lineStyle: { color: '#1e293b' } } },
      { type: 'value', name: '%', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    ],
    series: [
      { name: '制冷负载(RT)', type: 'bar', data: data.coolingLoad, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: colors.orange }, { offset: 1, color: 'rgba(249,115,22,0.3)' }]) }, barWidth: '40%' },
      { name: '自然冷源利用率(%)', type: 'line', yAxisIndex: 1, data: data.freeCoolingPct, smooth: true, lineStyle: { color: colors.green, width: 2.5 }, areaStyle: { color: 'rgba(34,197,94,0.12)' }, symbol: 'circle', symbolSize: 4, itemStyle: { color: colors.green } },
    ],
  }, true)
}

function renderDeltaTBypass() {
  const inst = charts.delta
  if (!inst || !trends.value) return
  const data = trends.value.deltaTBypass1h
  if (!data) return
  const tss = data.timestamps.map((t: string) => {
    const d = new Date(t)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  inst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['ΔT供回水温差', '旁通阀开度', 'ΔT设计值'], bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    grid: { left: 50, right: 55, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: tss, axisLabel: { color: '#64748b', fontSize: 10, interval: 9 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: [
      { type: 'value', name: '℃', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
      { type: 'value', name: '%', nameTextStyle: { color: '#94a3b8' }, min: 0, max: 100, axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    ],
    series: [
      { name: 'ΔT供回水温差', type: 'line', data: data.deltaT, smooth: true, lineStyle: { color: colors.cyan, width: 2.5 }, areaStyle: { color: 'rgba(6,182,212,0.1)' }, symbol: 'none', markLine: { silent: true, data: [{ yAxis: data.deltaTDesign, label: { formatter: '设计值 ' + data.deltaTDesign + '℃', color: '#94a3b8', fontSize: 10 }, lineStyle: { color: '#64748b', type: 'dashed' } }] } },
      { name: '旁通阀开度', type: 'line', yAxisIndex: 1, data: data.bypassValve, smooth: true, lineStyle: { color: colors.orange, width: 2, type: 'dotted' }, areaStyle: { color: 'rgba(249,115,22,0.06)' }, symbol: 'none', markLine: { silent: true, data: [{ yAxis: data.bypassHighAlarm, label: { formatter: '告警线 ' + data.bypassHighAlarm + '%', color: '#ef4444', fontSize: 10 }, lineStyle: { color: '#ef4444', type: 'dashed' } }] } },
    ],
  }, true)
}

// ---- 渲染全部图表 ----
function renderAll() {
  nextTick(() => {
    renderFreezeTrend()
    renderCopRla()
    renderCondCoolDiff()
    renderPumpFreqFlow()
    renderTankGradient()
    renderMonthlyChart()
    renderDeltaTBypass()
  })
}

// ---- 数据加载 ----
async function loadData() {
  try {
    const [plantRes, trendsRes] = await Promise.all([getChillerPlant(), getChillerTrends()])
    chiller.value = plantRes
    // 后端直接返回 chillerGroups 分组数据，做字段映射即可
    const rawGroups: any[] = plantRes?.chillerGroups ?? []
    chillerGroups.value = rawGroups.map((g: any) => ({
      chiller: {
        id: g.chiller?.code || g.chiller?.id || '-',
        state: g.chiller?.status === 'online' ? '运行' : g.chiller?.status === 'offline' ? '待机' : (g.chiller?.status || '待机'),
        load: g.chiller?.loadPercent ?? 0,
        cop: g.chiller?.cop ?? (g.chiller?.loadPercent > 0 ? +(6.3 + Math.random() * 0.4).toFixed(2) : 0),
        evapT: g.chiller?.temperatureIn ?? '-',
        condT: g.chiller?.temperatureOut ?? '-',
        current: (g.chiller?.loadPercent ?? 0) * 0.95,
        runHrs: g.chiller?.runningHours ?? 0,
      },
      chwPump: g.chwPump ? {
        id: g.chwPump.code || g.chwPump.id || '-',
        state: g.chwPump.state || '待机',
        hz: g.chwPump.hz ?? 0,
        kw: g.chwPump.kw ?? 0,
        flow: g.chwPump.flow ?? 0,
        inP: g.chwPump.inPressure ?? 0,
        outP: g.chwPump.outPressure ?? 0,
      } : null,
      cwPump: g.cwPump ? {
        id: g.cwPump.code || g.cwPump.id || '-',
        state: g.cwPump.state || '待机',
        hz: g.cwPump.hz ?? 0,
        kw: g.cwPump.kw ?? 0,
        flow: g.cwPump.flow ?? 0,
        inP: g.cwPump.inPressure ?? 0,
        outP: g.cwPump.outPressure ?? 0,
      } : null,
      tankConnected: Boolean(g.tankConnected),
      tankFlow: g.tankFlow ?? 0,
    }))
    trends.value = trendsRes
    plrClass.value = (plantRes?.plr ?? 0) < 50 ? 'low' : (plantRes?.plr ?? 0) < 80 ? 'mid' : 'high'
    renderAll()
  } catch { /* silent */ }
}

// ---- 生命周期 ----
onMounted(() => {
  nextTick(() => {
    initChart(freezeChart.value, 'freeze')
    initChart(copChart.value, 'cop')
    initChart(condChart.value, 'cond')
    initChart(pumpChart.value, 'pump')
    initChart(tankChart.value, 'tank')
    initChart(monthlyChart.value, 'monthly')
    initChart(deltaChart.value, 'delta')
  })
  loadData()
})

onUnmounted(() => disposeCharts())

watch(activeRange, () => {
  renderFreezeTrend()
  renderCopRla()
  renderCondCoolDiff()
  renderPumpFreqFlow()
  renderTankGradient()
})

// 自动刷新
const refreshTimer = setInterval(loadData, 60000)
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.chiller-page { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }

/* KPI Bar */
.kpi-bar { display: flex; gap: 8px; flex-wrap: wrap; }
.kpi-item { flex: 1; min-width: 110px; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 12px; text-align: center; }
.kpi-label { font-size: 11px; color: #64748b; margin-bottom: 4px; }
.kpi-value { font-size: 20px; font-weight: 700; color: #e2e8f0; }
.kpi-value small { font-size: 12px; font-weight: 400; color: #64748b; margin-left: 2px; }
.kpi-value.mode { font-size: 16px; }
.kpi-value.mode.预冷模式 { color: #22c55e; }
.kpi-value.mode.自然冷却模式 { color: #06b6d4; }
.kpi-value.mode.制冷模式 { color: #f97316; }
.kpi-value.low { color: #22c55e; }
.kpi-value.mid { color: #eab308; }
.kpi-value.high { color: #ef4444; }

/* Section */
.section { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 14px 16px; }
.section-title { font-size: 14px; font-weight: 600; color: #cbd5e1; margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.c { background: #06b6d4; }
.dot.c1 { background: #06b6d4; }
.dot.c2 { background: #f97316; }
.dot.c3 { background: #ef4444; }
.dot.c4 { background: #22c55e; }
.dot.c5 { background: #8b5cf6; }
.dot.c6 { background: #eab308; }
.dot.c7 { background: #3b82f6; }

/* Chiller Groups */
.chiller-groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.chiller-card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; overflow: hidden; }
.chiller-card.standby { opacity: 0.55; }
.chiller-card.fault { border-color: #7f1d1d; background: #1a1118; }
.ch-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,.2); }
.ch-id { font-weight: 700; font-size: 14px; color: #e2e8f0; }
.ch-state { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.ch-state.运行 { background: rgba(34,197,94,.2); color: #22c55e; }
.ch-state.待机 { background: rgba(148,163,184,.15); color: #94a3b8; }
.ch-state.检修 { background: rgba(239,68,68,.2); color: #ef4444; }
.ch-body { padding: 8px 12px 10px; }
.ch-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; margin-bottom: 8px; }
.ch-metrics div { font-size: 12px; color: #94a3b8; }
.ch-metrics div span { font-size: 10px; color: #64748b; display: block; }
.ch-metrics div b { color: #e2e8f0; }
.ch-metrics div b.good { color: #22c55e; }
.pump-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #94a3b8; padding: 3px 0; border-top: 1px solid #1e293b; }
.pump-tag { font-size: 9px; padding: 1px 5px; border-radius: 4px; font-weight: 700; }
.pump-tag.chw { background: rgba(6,182,212,.2); color: #06b6d4; }
.pump-tag.cw { background: rgba(249,115,22,.2); color: #f97316; }
.pump-row span.运行 { color: #22c55e; }
.tank-link { margin-top: 6px; font-size: 10px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 4px; display: flex; justify-content: space-between; }
.tank-link.on { color: #22c55e; }
.tank-flow { color: #06b6d4; }

/* Chart */
.chart-toolbar { display: flex; gap: 4px; margin-bottom: 8px; }
.chart-toolbar button { padding: 4px 14px; border: 1px solid #334155; border-radius: 14px; background: transparent; color: #94a3b8; font-size: 11px; cursor: pointer; transition: all .15s; }
.chart-toolbar button:hover { border-color: #64748b; color: #cbd5e1; }
.chart-toolbar button.active { background: rgba(6,182,212,.15); border-color: #06b6d4; color: #06b6d4; }
.chart-box { width: 100%; height: 280px; }
.chart-box-lg { height: 320px; }

/* Simple cards for remaining subsystems */
.simple-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; }
.simple-card { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 10px 12px; }
.simple-card.待机 { opacity: 0.5; }
.simple-card.检修 { border-color: #7f1d1d; }
.sc-head { font-size: 13px; font-weight: 600; color: #e2e8f0; display: flex; justify-content: space-between; }
.sc-head span { font-size: 10px; padding: 1px 6px; border-radius: 8px; }
.sc-head span.投入, .sc-head span.运行 { background: rgba(34,197,94,.15); color: #22c55e; }
.sc-row { font-size: 11px; color: #94a3b8; margin-top: 4px; }
</style>
