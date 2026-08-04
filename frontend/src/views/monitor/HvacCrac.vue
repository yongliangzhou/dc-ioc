<template>
  <div class="hvac-crac">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div class="ph-left">
        <h2 class="ph-title">空调末端系统</h2>
        <span class="ph-sub">精密空调 CRAC · 列间空调 · 包间环境 · 漏水检测</span>
      </div>
      <div class="ph-right">
        <span class="ph-badge" :class="cracData ? 'ok' : 'loading'">
          {{ cracData ? '在线' : '加载中…' }}
        </span>
        <span class="ph-time" v-if="lastUpdate">{{ lastUpdate }}</span>
        <button class="ph-btn" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </div>

    <!-- ========== KPI Row 1 ========== -->
    <div class="kpi-row" v-if="cracData">
      <KpiCard
        title="设备总数"
        :value="cracData.total"
        unit="台"
        :detail="`在线 ${cracData.online} · 待机 ${cracData.standby}`"
        dot="#06b6d4"
      />
      <KpiCard
        title="运行/待机/故障"
        :value="`${cracData.online}/${cracData.standby}/${cracData.fault}`"
        valueClass="gk-cv-cyan"
        detail="在线/待机/故障"
        dot="#22c55e"
      />
      <KpiCard
        title="漏水告警"
        :value="cracData.leakAlarm"
        unit="处"
        :subtitle="`共 ${cracData.leakTotal} 个监测点`"
        :status="cracData.leakAlarm > 0 ? 'danger' : 'normal'"
        dot="#ef4444"
      />
      <KpiCard title="室外参照温度" :value="cracData.outdoorRef" unit="℃" dot="#f97316" />
    </div>

    <!-- ========== KPI Row 2 ========== -->
    <div class="kpi-row" v-if="cracData">
      <KpiCard
        title="平均送风温度"
        :value="cracData.avgSupplyT"
        unit="℃"
        :decimals="1"
        dot="#06b6d4"
      />
      <KpiCard
        title="平均回风温度"
        :value="cracData.avgReturnT"
        unit="℃"
        :decimals="1"
        dot="#f97316"
      />
      <KpiCard
        title="平均供水温度"
        :value="cracData.avgSupplyWaterT"
        unit="℃"
        :decimals="1"
        dot="#3b82f6"
      />
      <KpiCard
        title="平均室内外压差"
        :value="cracData.avgInOutDiff"
        unit="Pa"
        :decimals="1"
        dot="#8b5cf6"
      />
    </div>

    <!-- Loading -->
    <div class="skel-row" v-if="loading && !cracData">
      <SkeletonCard v-for="i in 4" :key="i" size="sm" />
    </div>

    <!-- ========== 设备全景列表 ========== -->
    <div class="section" v-if="cracData">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--cyan)"></span>
        设备全景列表
        <span class="section-sum">{{ cracData.devices.length }} 台</span>
      </h3>
      <DeviceTable :columns="deviceColumns" :rows="deviceRows" :count="cracData.devices.length" />
    </div>

    <!-- ========== 包间温度热力图 ========== -->
    <div class="section" v-if="roomHeatData.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--amber)"></span>
        包间温度热力图
      </h3>
      <HeatmapView
        :xAxisData="heatXLabels"
        :yAxisData="heatYLabels"
        :heatData="roomHeatData"
        :valueRange="[10, 40]"
        :colors="heatColors"
        unit="℃"
        :loading="trendsLoading"
        title=""
      />
    </div>

    <!-- ========== 包间设备归集 ========== -->
    <div class="section" v-if="roomGroups.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--green)"></span>
        包间设备归集
        <span class="section-sum">{{ roomGroups.length }} 个包间</span>
      </h3>
      <GroupCard
        v-for="rg in roomGroups"
        :key="rg.roomId"
        :title="rg.roomName"
        :subtitle="`运行 ${rg.cracRun}/${rg.cracN} · 状态 ${rg.status}`"
        :dot-color="
          rg.status === '正常'
            ? 'var(--green)'
            : rg.status === '告警'
              ? 'var(--red)'
              : 'var(--amber)'
        "
      >
        <!-- 环境传感器 -->
        <div class="rg-env">
          <h4 class="rg-subtitle">环境传感器</h4>
          <div class="rg-kpi-grid">
            <KpiCard
              title="平均温度"
              :value="rg.envSensors.avgTemp"
              unit="℃"
              size="sm"
              dot="var(--cyan)"
            />
            <KpiCard
              title="平均湿度"
              :value="rg.envSensors.avgRh"
              unit="%"
              size="sm"
              dot="var(--blue)"
            />
            <KpiCard
              title="热通道温度"
              :value="rg.envSensors.hotAisleTemp"
              unit="℃"
              size="sm"
              dot="var(--red)"
            />
            <KpiCard
              title="冷通道温度"
              :value="rg.envSensors.coldAisleTemp"
              unit="℃"
              size="sm"
              dot="var(--cyan)"
            />
            <KpiCard
              title="热通道湿度"
              :value="rg.envSensors.hotAisleRh"
              unit="%"
              size="sm"
              dot="var(--orange)"
            />
            <KpiCard
              title="冷通道湿度"
              :value="rg.envSensors.coldAisleRh"
              unit="%"
              size="sm"
              dot="var(--teal)"
            />
            <KpiCard
              title="露点温度"
              :value="rg.envSensors.dewPoint"
              unit="℃"
              size="sm"
              dot="var(--purple)"
            />
            <KpiCard
              title="室内外压差"
              :value="rg.envSensors.inOutDiff"
              unit="Pa"
              size="sm"
              dot="var(--amber)"
            />
          </div>
        </div>

        <!-- 精密空调 -->
        <div v-if="rg.roomCracs.length" class="rg-devices">
          <h4 class="rg-subtitle">精密空调 ({{ rg.roomCracs.length }} 台)</h4>
          <DeviceTable :columns="cracUnitColumns" :rows="mapCracRows(rg.roomCracs)" />
        </div>

        <!-- 列间空调 -->
        <div v-if="rg.inRowCracs.length" class="rg-devices">
          <h4 class="rg-subtitle">列间空调 ({{ rg.inRowCracs.length }} 台)</h4>
          <DeviceTable :columns="cracUnitColumns" :rows="mapCracRows(rg.inRowCracs)" />
        </div>

        <!-- 新风 + 恒湿 -->
        <div class="rg-aux" v-if="rg.fau || rg.humidifier">
          <h4 class="rg-subtitle">辅助设备</h4>
          <div class="rg-aux-grid">
            <div v-if="rg.fau" class="rg-aux-card">
              <span class="rg-aux-label">新风机组</span>
              <StatusBadge :status="rg.fau.state" />
              <span class="rg-aux-v"
                >送风 {{ formatVal(rg.fau.supplyT) }}℃ / CO₂ {{ formatVal(rg.fau.co2) }}ppm</span
              >
            </div>
            <div v-if="rg.humidifier" class="rg-aux-card">
              <span class="rg-aux-label">恒湿机</span>
              <StatusBadge :status="rg.humidifier.state" />
              <span class="rg-aux-v"
                >RH {{ formatVal(rg.humidifier.rh) }}% / {{ rg.humidifier.mode }}</span
              >
            </div>
          </div>
        </div>

        <!-- 漏水状态 -->
        <div class="rg-leak" v-if="rg.leak">
          <span class="rg-leak-label">漏水检测 (Zone {{ rg.leak.zone }})</span>
          <StatusBadge :status="rg.leak.status" />
          <span v-if="rg.leak.level !== '正常'" class="rg-leak-level"
            >级别: {{ rg.leak.level }}</span
          >
        </div>

        <!-- 远程控制 -->
        <QuickControl
          :showTemp="true"
          tempLabel="回风温度设定"
          :tempValue="rg.roomCracs[0]?.roomTSet ?? 24"
          :tempMin="16"
          :tempMax="32"
          :tempStep="0.5"
          tempUnit="℃"
          :showStartStop="false"
          @tempChange="(v) => onRoomTempChange(rg.roomId, v)"
        />
      </GroupCard>
    </div>

    <!-- ========== 群控策略 ========== -->
    <div class="section" v-if="cracData?.ctrl">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--purple)"></span>
        群控策略
      </h3>
      <div class="ctrl-grid">
        <div class="ctrl-card">
          <span class="ctrl-name">恒湿机联控</span>
          <span class="ctrl-desc"
            >加湿启动 RH ≤ {{ cracData.ctrl.humId.rhLowOn }}% · 关闭 RH ≥
            {{ cracData.ctrl.humId.rhHighOff }}%</span
          >
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">正压送风</span>
          <span class="ctrl-desc"
            >{{ cracData.ctrl.positivePressure.min }}~{{ cracData.ctrl.positivePressure.max }}
            {{ cracData.ctrl.positivePressure.unit }} ·
            {{ cracData.ctrl.positivePressure.desc }}</span
          >
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">二次泵策略</span>
          <span class="ctrl-desc"
            >压差目标 {{ cracData.ctrl.secPump.diffTarget }}{{ cracData.ctrl.secPump.diffUnit }} ·
            加泵 {{ cracData.ctrl.secPump.addHz }}Hz · 减泵 {{ cracData.ctrl.secPump.reduceHz }}Hz ·
            {{ cracData.ctrl.secPump.desc }}</span
          >
        </div>
      </div>
    </div>

    <!-- ========== 趋势诊断 ========== -->
    <div class="section" v-if="trends">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--yellow)"></span>
        趋势诊断分析
        <span class="section-sum">7 项指标</span>
      </h3>

      <!-- Chart 1: ΔT Integral -->
      <div class="trend-item" v-if="trends.deltaTIntegral?.rooms?.length">
        <TrendChart
          :title="trends.deltaTIntegral.title"
          :xAxisData="dtiXData"
          :series="dtiSeries"
          :loading="trendsLoading"
          :height="260"
        />
      </div>

      <!-- Chart 2: Filter ΔP Slope (dual Y) -->
      <div class="trend-item" v-if="trends.filterDpSlope?.units?.length">
        <TrendChart
          :title="trends.filterDpSlope.title"
          :xAxisData="fdpXData"
          :series="fdpSeries"
          :loading="trendsLoading"
          :height="270"
        />
      </div>

      <!-- Chart 3: SHR Trend -->
      <div class="trend-item" v-if="trends.shrTrend?.units?.length">
        <TrendChart
          :title="trends.shrTrend.title"
          :xAxisData="shrXData"
          :series="shrSeries"
          :loading="trendsLoading"
          :height="240"
        />
      </div>

      <!-- Chart 4: Supply vs Cabinet -->
      <div class="trend-item" v-if="activeSVC">
        <div class="trend-header">
          <span class="trend-name">{{ trends.supplyVsCabinet.title }}</span>
          <select
            v-model="svcPeriod"
            class="trend-period"
            v-if="trends.supplyVsCabinet.periods?.length > 1"
          >
            <option v-for="p in trends.supplyVsCabinet.periods" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <TrendChart
          :xAxisData="svcXData"
          :series="svcSeries"
          :loading="trendsLoading"
          :height="270"
        />
      </div>

      <!-- Chart 5: Fan vs Static Pressure (dual Y) -->
      <div class="trend-item" v-if="trends.fanVsStaticPressure?.units?.length">
        <TrendChart
          :title="trends.fanVsStaticPressure.title"
          :xAxisData="fspXData"
          :series="fspSeries"
          :loading="trendsLoading"
          :height="260"
        />
      </div>

      <!-- Chart 6: Valve vs ΔT (dual Y) -->
      <div class="trend-item" v-if="trends.valveDeltaT?.units?.length">
        <TrendChart
          :title="trends.valveDeltaT.title"
          :xAxisData="vdtXData"
          :series="vdtSeries"
          :loading="trendsLoading"
          :height="260"
        />
      </div>

      <!-- Chart 7: Superheat Trend -->
      <div class="trend-item" v-if="trends.superheatTrend?.units?.length">
        <TrendChart
          :title="trends.superheatTrend.title"
          :xAxisData="shXData"
          :series="shSeries"
          :loading="trendsLoading"
          :height="260"
        />
      </div>
    </div>

    <!-- ========== 活跃告警 ========== -->
    <div class="section" v-if="cracAlarms.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--red)"></span>
        活跃告警
        <span class="section-sum danger">{{ cracAlarms.length }} 条</span>
      </h3>
      <div class="alarm-list">
        <div v-for="a in cracAlarms" :key="a.id" class="alarm-item">
          <AlarmBadge :level="a.level || 'warning'" />
          <span class="alarm-msg"
            >{{ a.message || a.title || a.description || '-' }}
            <em class="alarm-tag">[{{ a.source || a.domain || '-' }}]</em></span
          >
          <span class="alarm-time">{{ formatTime(a.time || a.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- ========== Footer Stats ========== -->
    <div class="page-footer" v-if="cracData">
      <span>总设备 {{ cracData.total }} 台</span>
      <span
        >在线 {{ cracData.online }} · 待机 {{ cracData.standby }} · 故障 {{ cracData.fault }}</span
      >
      <span>新风机组 {{ cracData.freshAir?.length ?? 0 }} 台</span>
      <span>恒湿机 {{ cracData.humidifiers?.length ?? 0 }} 台</span>
      <span>功能房间 {{ cracData.funcRooms?.length ?? 0 }} 间</span>
      <span v-if="lastUpdate">数据更新: {{ lastUpdate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getCrac, getCracTrends, mapCracRoomGroups } from '@/api/hvac'
import { getActiveAlarms } from '@/api'
import type { CracSummary, CracView, CracRoomGroupView, CracTrends } from '@/api/hvac'
import { CHART_COLORS } from '@/assets/echarts-theme'
import KpiCard from '@/components/monitor/KpiCard.vue'
import StatusBadge from '@/components/monitor/StatusBadge.vue'
import AlarmBadge from '@/components/monitor/AlarmBadge.vue'
import GroupCard from '@/components/monitor/GroupCard.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import DeviceTable from '@/components/monitor/DeviceTable.vue'
import HeatmapView from '@/components/monitor/HeatmapView.vue'
import QuickControl from '@/components/monitor/QuickControl.vue'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import { numVal, formatVal, formatTime } from '@/utils/format'

// ===== State =====
const cracData = ref<CracSummary | null>(null)
const trends = ref<CracTrends | null>(null)
const rawCrac = ref<any>(null)
const loading = ref(false)
const trendsLoading = ref(false)
const lastUpdate = ref('')
let timer: ReturnType<typeof setInterval> | null = null

// ===== Alarm State =====
const alarms = ref<any[]>([])

// ===== Supply vs Cabinet period =====
const svcPeriod = ref('1h')

// ===== Data Loading =====
async function loadCrac() {
  try {
    const [summary, alarmResult] = await Promise.all([
      getCrac(),
      getActiveAlarms().catch(() => ({ total: 0, items: [] })),
    ])
    cracData.value = summary
    // Room groups come from mapCracRoomGroups — pass the summary directly
    rawCrac.value = summary as any
    alarms.value = alarmResult.items || []
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    console.error('Failed to load CRAC data:', e)
  }
}

async function loadTrends() {
  trendsLoading.value = true
  try {
    trends.value = await getCracTrends()
    if (
      Object.keys(trends.value || {}).length > 0 &&
      trends.value?.supplyVsCabinet?.periods?.length
    ) {
      svcPeriod.value = trends.value.supplyVsCabinet.periods[0]
    }
  } catch {
    /* trends optional */
  } finally {
    trendsLoading.value = false
  }
}

async function refresh() {
  loading.value = true
  await Promise.all([loadCrac(), loadTrends()])
  loading.value = false
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

// ===== Room Groups =====
const roomGroups = computed<CracRoomGroupView[]>(() => {
  if (!rawCrac.value) return []
  return mapCracRoomGroups(rawCrac.value)
})

// ===== Device Table =====
const deviceColumns = [
  { key: 'code', label: '设备编号', width: '130px' },
  { key: 'roomName', label: '包间', width: '80px' },
  { key: 'type', label: '类型', width: '80px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'supplyT', label: '送风(℃)', width: '75px' },
  { key: 'returnT', label: '回风(℃)', width: '75px' },
  { key: 'fanSpeed', label: '风机(%)', width: '75px' },
  { key: 'valve', label: '风阀(%)', width: '75px' },
  { key: 'waterValve', label: '水阀(%)', width: '75px' },
  { key: 'power', label: '功率(kW)', width: '80px' },
  { key: 'filter', label: '滤网', width: '70px' },
  { key: 'coolingMode', label: '模式', width: '70px' },
]

const cracUnitColumns = [
  { key: 'code', label: '编号', width: '100px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'supplyT', label: '送风(℃)', width: '70px' },
  { key: 'returnT', label: '回风(℃)', width: '70px' },
  { key: 'fanSpeed', label: '风机(%)', width: '70px' },
  { key: 'valve', label: '风阀(%)', width: '70px' },
  { key: 'waterValve', label: '水阀(%)', width: '70px' },
  { key: 'power', label: '功率(kW)', width: '75px' },
  { key: 'filter', label: '滤网', width: '60px' },
]

const deviceRows = computed(() => {
  if (!cracData.value) return []
  return cracData.value.devices.map((d: CracView) => ({
    code: d.code,
    roomName: d.roomName,
    type: d.type,
    status: d.status,
    supplyT: numVal(d.supplyT),
    returnT: numVal(d.returnT),
    fanSpeed: d.fanSpeed,
    valve: d.valve,
    waterValve: d.waterValve,
    power: d.power,
    filter: d.filter,
    coolingMode: d.coolingMode,
    _rowClass: d.status === 'fault' ? 'row-danger' : d.status === 'standby' ? 'row-warning' : '',
  }))
})

function mapCracRows(devices: CracView[]) {
  return devices.map((d: CracView) => ({
    code: d.code,
    status: d.status,
    supplyT: numVal(d.supplyT),
    returnT: numVal(d.returnT),
    fanSpeed: d.fanSpeed,
    valve: d.valve,
    waterValve: d.waterValve,
    power: d.power,
    filter: d.filter,
    _rowClass: d.status === 'fault' ? 'row-danger' : d.status === 'standby' ? 'row-warning' : '',
  }))
}

// ===== Heatmap =====
const heatColors = ['#06b6d4', '#22c55e', '#eab308', '#f97316', '#ef4444']
const heatXLabels = ['平均温度', '热通道', '冷通道', '露点']
const heatYLabels = computed(() => roomGroups.value.map((r) => r.roomName))

const roomHeatData = computed<[number, number, number][]>(() => {
  const data: [number, number, number][] = []
  roomGroups.value.forEach((rg, yi) => {
    data.push([0, yi, rg.envSensors.avgTemp])
    data.push([1, yi, rg.envSensors.hotAisleTemp])
    data.push([2, yi, rg.envSensors.coldAisleTemp])
    data.push([3, yi, rg.envSensors.dewPoint])
  })
  return data
})

// ===== Trend Charts =====

// Chart 1: ΔT Integral
const dtiXData = computed<string[]>(() => {
  const r = trends.value?.deltaTIntegral
  if (!r?.rooms?.length) return ['--']
  const room = r.rooms[0]
  const s0 = room.series[0]
  const len = s0?.data?.length || 0
  return Array.from({ length: len }, (_, i) => `t${i + 1}`)
})

const dtiSeries = computed(() => {
  const r = trends.value?.deltaTIntegral
  if (!r?.rooms?.length) return []
  const series: any[] = []
  for (const room of r.rooms) {
    for (const s of room.series) {
      series.push({
        name: `${room.roomName}·${s.label}`,
        data: s.data as number[],
        type: 'line',
        areaStyle: { opacity: 0.06 },
      })
    }
  }
  return series
})

// Chart 2: Filter ΔP Slope
const fdpXData = computed(() => {
  const u = trends.value?.filterDpSlope?.units
  if (!u?.length) return ['--']
  const u0 = u[0]
  return u0.raw?.map((p: any) => p.date) ?? ['--']
})

const fdpSeries = computed(() => {
  const units = trends.value?.filterDpSlope?.units ?? []
  const series: any[] = []
  const palette = CHART_COLORS.palette as readonly string[]
  units.forEach((u, i) => {
    series.push({
      name: `${u.label} 原始值`,
      data: (u.raw ?? []).map((p: any) => p.value),
      type: 'line',
      lineStyle: { color: palette[i % palette.length], width: 1.5 },
    })
    series.push({
      name: `${u.label} 斜率(右轴)`,
      data: (u.slope ?? []).map((p: any) => p.value),
      type: 'line',
      yAxisIndex: 1,
      lineStyle: { color: palette[i % palette.length], width: 2, type: 'dashed' as const },
    })
  })
  return series
})

// Chart 3: SHR Trend
const shrXData = computed<string[]>(() => {
  const units = trends.value?.shrTrend?.units ?? []
  if (!units.length) return ['--']
  return units[0].data?.map((p: any) => p.week) ?? ['--']
})

const shrSeries = computed(() => {
  const units = trends.value?.shrTrend?.units ?? []
  const palette = CHART_COLORS.palette as readonly string[]
  return units.map((u, i) => ({
    name: `${u.label} (${u.roomName})`,
    data: u.data.map((p: any) => p.value) as number[],
    type: 'line' as const,
    lineStyle: { color: palette[i % palette.length] },
    areaStyle: { opacity: 0.05 },
  }))
})

// Chart 4: Supply vs Cabinet
const activeSVC = computed(() => {
  const svc = trends.value?.supplyVsCabinet
  if (!svc?.rooms?.length) return null
  return svc.rooms[0]
})

watch(svcPeriod, () => {
  /* reactive — recompute below */
})

const svcXData = computed(() => {
  const room = activeSVC.value
  if (!room) return ['--']
  const period = room.periods[svcPeriod.value]
  return period?.timestamps ?? ['--']
})

const svcSeries = computed(() => {
  const room = activeSVC.value
  if (!room) return []
  const period = room.periods[svcPeriod.value]
  if (!period) return []
  return [
    {
      name: '送风温度',
      data: period.supplyTemp as number[],
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.cyan },
    },
    {
      name: '机柜进风温度',
      data: period.cabinetInletTemp as number[],
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.orange },
    },
    {
      name: '温差 ΔT',
      data: period.deltaT as number[],
      type: 'bar' as const,
      yAxisIndex: 1,
      itemStyle: { color: CHART_COLORS.purple },
    },
  ]
})

// Chart 5: Fan vs Static Pressure
const fspXData = computed(() => {
  const u = trends.value?.fanVsStaticPressure?.units
  if (!u?.length) return ['--']
  return u[0].timestamps ?? ['--']
})

const fspSeries = computed(() => {
  const units = trends.value?.fanVsStaticPressure?.units ?? []
  const palette = CHART_COLORS.palette as readonly string[]
  const series: any[] = []
  units.forEach((u, i) => {
    series.push({
      name: `${u.label} 风机转速`,
      data: u.fanSpeed as number[],
      type: 'line',
      lineStyle: { color: palette[i % palette.length] },
    })
    series.push({
      name: `${u.label} 静压(右轴)`,
      data: u.staticPressure as number[],
      type: 'line',
      yAxisIndex: 1,
      lineStyle: { color: palette[i % palette.length], type: 'dashed' as const },
    })
  })
  return series
})

// Chart 6: Valve vs ΔT
const vdtXData = computed(() => {
  const u = trends.value?.valveDeltaT?.units
  if (!u?.length) return ['--']
  return u[0].timestamps ?? ['--']
})

const vdtSeries = computed(() => {
  const units = trends.value?.valveDeltaT?.units ?? []
  const palette = CHART_COLORS.palette as readonly string[]
  const series: any[] = []
  units.forEach((u, i) => {
    series.push({
      name: `${u.label} 水阀`,
      data: u.valveOpening as number[],
      type: 'line',
      lineStyle: { color: palette[i % palette.length] },
    })
    series.push({
      name: `${u.label} ΔT(右轴)`,
      data: u.waterDeltaT as number[],
      type: 'line',
      yAxisIndex: 1,
      lineStyle: { color: palette[i % palette.length], type: 'dashed' as const },
    })
  })
  return series
})

// Chart 7: Superheat
const shXData = computed(() => {
  const u = trends.value?.superheatTrend?.units
  if (!u?.length) return ['--']
  return u[0].timestamps ?? ['--']
})

const shSeries = computed(() => {
  const units = trends.value?.superheatTrend?.units ?? []
  const palette = CHART_COLORS.palette as readonly string[]
  const series: any[] = []
  units.forEach((u, i) => {
    series.push({
      name: `${u.label} 吸气过热度`,
      data: u.suctionSuperheat as number[],
      type: 'line',
      lineStyle: { color: palette[i % palette.length] },
    })
    series.push({
      name: `${u.label} 排气过热度`,
      data: u.dischargeSuperheat as number[],
      type: 'line',
      lineStyle: { color: palette[i % palette.length], type: 'dashed' as const },
    })
  })
  return series
})

// ===== Alarms =====
const cracAlarms = computed(() => {
  return alarms.value.filter((a) => {
    const t = `${a.source || ''}${a.domain || ''}${a.message || ''}${a.title || ''}`.toLowerCase()
    return (
      t.includes('crac') ||
      t.includes('空调') ||
      t.includes('精密') ||
      t.includes('列间') ||
      t.includes('hvac')
    )
  })
})

// ===== QuickControl Handler =====
function onRoomTempChange(roomId: string, value: number) {
  console.log('Room temp change:', roomId, value)
  // Future: POST to /api/hvac/crac/setpoint
}
</script>

<style scoped>
.hvac-crac {
  padding: 12px;
  min-height: 100%;
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 8px;
}
.ph-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.ph-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--txt);
  margin: 0;
}
.ph-sub {
  font-size: 12px;
  color: var(--txt3);
}
.ph-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ph-badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.ph-badge.ok {
  background: rgba(34, 197, 94, 0.12);
  color: var(--green);
}
.ph-badge.loading {
  background: rgba(148, 163, 184, 0.1);
  color: var(--txt3);
}
.ph-time {
  font-size: 11px;
  color: var(--txt3);
}
.ph-btn {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--txt);
  font-size: 11px;
  padding: 4px 14px;
  border-radius: 5px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.ph-btn:hover {
  border-color: var(--cyan);
}

/* KPI rows */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}
@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 640px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
}

.gk-cv-cyan {
  color: var(--cyan);
  font-weight: 700;
}

/* Skeleton */
.skel-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}

/* Sections */
.section {
  margin-top: 14px;
}

.section-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.section-sum {
  font-size: 11px;
  font-weight: 400;
  color: var(--txt3);
  margin-left: auto;
}
.section-sum.danger {
  color: var(--red);
}

/* Room Groups */
.rg-subtitle {
  font-size: 12px;
  font-weight: 600;
  color: var(--txt2);
  margin: 10px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--line);
}
.rg-env {
  margin-bottom: 10px;
}
.rg-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
@media (max-width: 900px) {
  .rg-kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.rg-devices {
  margin-bottom: 10px;
}
.rg-aux {
  margin-bottom: 10px;
}
.rg-aux-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.rg-aux-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
}
.rg-aux-label {
  font-size: 11px;
  color: var(--txt3);
  min-width: 55px;
}
.rg-aux-v {
  font-size: 11px;
  color: var(--txt);
}
.rg-leak {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
  font-size: 11px;
}
.rg-leak-label {
  color: var(--txt3);
}
.rg-leak-level {
  color: var(--red);
  font-weight: 600;
}

/* Control strategy */
.ctrl-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .ctrl-grid {
    grid-template-columns: 1fr;
  }
}
.ctrl-card {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ctrl-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt);
}
.ctrl-desc {
  font-size: 11px;
  color: var(--txt2);
  line-height: 1.5;
}

/* Trend items */
.trend-item {
  margin-bottom: 10px;
}
.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.trend-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt);
}
.trend-period {
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--txt);
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
}

/* Alarms */
.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
}
.alarm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 5px;
  font-size: 11px;
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.1);
}
.alarm-msg {
  color: var(--txt);
  flex: 1;
}
.alarm-tag {
  color: var(--txt3);
  font-style: normal;
}
.alarm-time {
  color: var(--txt3);
  white-space: nowrap;
  font-size: 10px;
}

/* Footer */
.page-footer {
  margin-top: 16px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--txt3);
}
</style>
