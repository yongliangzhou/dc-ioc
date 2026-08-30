<template>
  <div class="hvac-liquid">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div class="ph-left">
        <h2 class="ph-title">液冷系统</h2>
        <span class="ph-sub">一次侧 CDU · 二次侧 CDU · 冷板 GPU · 分集水器 · 漏水监测</span>
      </div>
      <div class="ph-right">
        <span class="ph-badge" :class="dataOk ? 'ok' : 'loading'">
          {{ dataOk ? '在线' : '加载中…' }}
        </span>
        <span class="ph-mode" v-if="data?.systemMode">{{ data!.systemMode }}</span>
        <span class="ph-time" v-if="lastUpdate">{{ lastUpdate }}</span>
        <button class="ph-btn" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </div>

    <!-- ========== KPI Row 1: Global ========== -->
    <AsyncSection
      :loading="loading"
      :error="error"
      :empty="!data"
      @retry="refresh"
      :min-height="'360px'"
    >
      <KpiCard title="系统模式" :value="data.systemMode" dot="#8b5cf6" />
      <KpiCard
        title="室外温度"
        :value="data.outdoorT"
        unit="℃"
        :decimals="1"
        dot="#f97316"
        :subtitle="`RH ${data.outdoorRH}%`"
      />
      <KpiCard
        title="总制冷能力"
        :value="data.totalCoolingCap"
        unit="kW"
        dot="#06b6d4"
        :detail="`使用 ${data.coolingCapUsed} kW · 率 ${data.capRate}%`"
        :barValue="data.capRate"
        barColor="linear-gradient(90deg, var(--cyan), var(--blue))"
      />
      <KpiCard
        title="PUE 贡献"
        :value="data.pueContribution"
        :decimals="3"
        dot="#22c55e"
        :subtitle="`自然冷却 ${data.freeCoolingHours}h`"
        :detail="`余热回收 ${data.heatRecoveryMW} MW`"
      />
    </AsyncSection>

    <!-- ========== KPI Row 2: 一次侧 ========== -->
    <div class="kpi-row" v-if="data">
      <KpiCard
        title="一次侧供水温度"
        :value="data.primarySupplyTemp"
        unit="℃"
        :decimals="1"
        dot="#3b82f6"
      />
      <KpiCard
        title="一次侧回水温度"
        :value="data.primaryReturnTemp"
        unit="℃"
        :decimals="1"
        dot="#f97316"
      />
      <KpiCard
        title="一次侧流量"
        :value="data.primaryFlow"
        unit="m³/h"
        :decimals="1"
        dot="#06b6d4"
      />
      <KpiCard
        title="一次侧压力"
        :value="data.primaryPressure"
        unit="bar"
        :decimals="1"
        dot="#8b5cf6"
      />
    </div>

    <!-- ========== KPI Row 3: 二次侧 ========== -->
    <div class="kpi-row" v-if="data">
      <KpiCard
        title="二次侧供水温度"
        :value="data.secSupplyTemp"
        unit="℃"
        :decimals="1"
        dot="#3b82f6"
      />
      <KpiCard
        title="二次侧回水温度"
        :value="data.secReturnTemp"
        unit="℃"
        :decimals="1"
        dot="#f97316"
      />
      <KpiCard title="二次侧流量" :value="data.secFlow" unit="m³/h" :decimals="1" dot="#06b6d4" />
      <KpiCard
        title="温差 ΔT"
        :value="data.deltaT"
        unit="℃"
        :decimals="1"
        dot="#eab308"
        :status="Math.abs(data.deltaT) > 8 ? 'warning' : 'normal'"
      />
    </div>

    <!-- ========== 一次侧 CDU ========== -->
    <div class="section" v-if="data?.primaryCDUs?.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--blue)"></span>
        一次侧 CDU
        <span class="section-sum">{{ data.primaryCDUs.length }} 台</span>
      </h3>
      <DeviceTable :columns="primCduCols" :rows="primCduRows" />
    </div>

    <!-- ========== 二次侧 CDU ========== -->
    <div class="section" v-if="data?.secondaryCDUs?.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--cyan)"></span>
        二次侧 CDU
        <span class="section-sum">{{ data.secondaryCDUs.length }} 台</span>
      </h3>
      <DeviceTable :columns="secCduCols" :rows="secCduRows" />
    </div>

    <!-- ========== 冷板 GPU 节点 ========== -->
    <div class="section" v-if="data?.coldPlates?.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--red)"></span>
        冷板 GPU 节点
        <span class="section-sum">{{ data.coldPlates.length }} 个</span>
      </h3>
      <DeviceTable :columns="coldPlateCols" :rows="coldPlateRows" />
    </div>

    <!-- ========== 分集水器 ========== -->
    <div
      class="manifold-grid"
      v-if="data?.manifoldsSupply?.length || data?.manifoldsReturn?.length"
    >
      <div class="manifold-half" v-if="data?.manifoldsSupply?.length">
        <h3 class="section-title">
          <span class="section-dot" style="background: var(--blue)"></span>
          供水集管
          <span class="section-sum">{{ data.manifoldsSupply.length }} 节点</span>
        </h3>
        <DeviceTable :columns="manifoldCols" :rows="supplyManRows" />
      </div>
      <div class="manifold-half" v-if="data?.manifoldsReturn?.length">
        <h3 class="section-title">
          <span class="section-dot" style="background: var(--orange)"></span>
          回水集管
          <span class="section-sum">{{ data.manifoldsReturn.length }} 节点</span>
        </h3>
        <DeviceTable :columns="manifoldCols" :rows="returnManRows" />
      </div>
    </div>

    <!-- ========== 漏水检测 ========== -->
    <div class="section" v-if="data?.leakTotalSensors">
      <h3 class="section-title">
        <span
          class="section-dot"
          :style="`background:${data.leakAlarmCount > 0 ? 'var(--red)' : 'var(--green)'}`"
        ></span>
        漏水检测
        <span class="section-sum" :class="{ danger: data.leakAlarmCount > 0 }">
          {{ data.leakTotalSensors }} 个传感器 · 告警 {{ data.leakAlarmCount }}
        </span>
      </h3>
      <div class="leak-grid">
        <!-- 漏水绳 -->
        <div class="leak-block" v-if="data.leakRope?.length">
          <h4 class="rg-subtitle">漏水绳 ({{ data.leakRope.length }})</h4>
          <DeviceTable :columns="leakRopeCols" :rows="leakRopeRows" />
        </div>
        <!-- 漏水点 -->
        <div class="leak-block" v-if="data.leakPoint?.length">
          <h4 class="rg-subtitle">漏水监测点 ({{ data.leakPoint.length }})</h4>
          <DeviceTable :columns="leakPointCols" :rows="leakPointRows" />
        </div>
      </div>
    </div>

    <!-- ========== 冷却液水质 ========== -->
    <div class="section" v-if="data?.coolantQuality">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--teal)"></span>
        冷却液水质
        <StatusBadge :status="data.coolantQuality.status" />
        <span class="section-sum-s" v-if="data.coolantQuality.lastTested"
          >上次检测: {{ data.coolantQuality.lastTested }}</span
        >
      </h3>
      <div class="quality-grid">
        <KpiCard
          title="电导率"
          :value="data.coolantQuality.conductivity"
          unit="μS/cm"
          size="sm"
          dot="var(--blue)"
        />
        <KpiCard
          title="pH 值"
          :value="data.coolantQuality.ph"
          unit="pH"
          size="sm"
          :decimals="1"
          dot="var(--green)"
        />
        <KpiCard
          title="缓蚀剂"
          :value="data.coolantQuality.corrosionInhibitor"
          unit="ppm"
          size="sm"
          dot="var(--cyan)"
        />
        <KpiCard
          title="乙二醇浓度"
          :value="data.coolantQuality.glycolConcentration"
          unit="%"
          size="sm"
          dot="var(--purple)"
        />
        <KpiCard
          title="颗粒计数"
          :value="data.coolantQuality.particleCount"
          unit="个/mL"
          size="sm"
          dot="var(--amber)"
        />
      </div>
    </div>

    <!-- ========== 排热系统 ========== -->
    <div class="section" v-if="hasRejection">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--orange)"></span>
        排热系统
        <span class="section-sum"
          >排热量 {{ data!.totalHeatRejected }} kW · 逼近温度 {{ data!.approachTemp }}℃</span
        >
      </h3>

      <!-- 冷却塔风机 -->
      <GroupCard
        v-if="data?.towerFans?.length"
        :title="`冷却塔风机 · ${data.towerFans.length} 台`"
        :subtitle="`自然冷却${data.freeCoolingAvailable ? '可用' : '不可用'}`"
        dotColor="var(--orange)"
      >
        <DeviceTable :columns="towerFanCols" :rows="towerFanRows" />
      </GroupCard>

      <!-- 干冷器 -->
      <GroupCard
        v-if="data?.dryCoolers?.length"
        :title="`干冷器 · ${data.dryCoolers.length} 台`"
        dotColor="var(--blue)"
      >
        <DeviceTable :columns="dryCoolerCols" :rows="dryCoolerRows" />
      </GroupCard>

      <!-- 排热水泵 -->
      <GroupCard
        v-if="data?.rejectionPumps?.length"
        :title="`排热水泵 · ${data.rejectionPumps.length} 台`"
        dotColor="var(--cyan)"
      >
        <DeviceTable :columns="rejPumpCols" :rows="rejPumpRows" />
      </GroupCard>

      <!-- 余热回收 -->
      <GroupCard
        v-if="data?.heatRecovery"
        :title="`余热回收 · ${data.heatRecovery.enabled ? '已启用' : '已停用'}`"
        :subtitle="`用途: ${data.heatRecovery.usageType}`"
        :dot-color="data.heatRecovery.enabled ? 'var(--green)' : 'var(--txt3)'"
      >
        <div class="hr-grid">
          <KpiCard
            title="回收率"
            :value="data.heatRecovery.recoveryRate"
            unit="%"
            size="sm"
            dot="var(--green)"
          />
          <KpiCard
            title="回收温度"
            :value="data.heatRecovery.recoveryTemp"
            unit="℃"
            size="sm"
            :decimals="1"
            dot="var(--orange)"
          />
          <KpiCard
            title="回流温度"
            :value="data.heatRecovery.returnTemp"
            unit="℃"
            size="sm"
            :decimals="1"
            dot="var(--blue)"
          />
          <KpiCard
            title="流量"
            :value="data.heatRecovery.flow"
            unit="m³/h"
            size="sm"
            :decimals="1"
            dot="var(--cyan)"
          />
          <KpiCard
            title="年减排 CO₂"
            :value="data.heatRecovery.co2Reduction"
            unit="吨"
            size="sm"
            dot="var(--green)"
          />
          <KpiCard
            title="年节能"
            :value="data.heatRecovery.annualSaving"
            unit="万元"
            size="sm"
            dot="var(--amber)"
          />
        </div>
      </GroupCard>
    </div>

    <!-- ========== 群控策略 ========== -->
    <div class="section" v-if="data?.control">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--purple)"></span>
        群控策略
      </h3>
      <div class="ctrl-grid">
        <div class="ctrl-card">
          <span class="ctrl-name">一次侧供水设定</span>
          <span class="ctrl-val">{{ data.control.primarySupplySetpoint }} ℃</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">二次侧供水设定</span>
          <span class="ctrl-val">{{ data.control.secondarySupplySetpoint }} ℃</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">逼近温度目标</span>
          <span class="ctrl-val">{{ data.control.approachTarget }} ℃</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">乙二醇最低浓度</span>
          <span class="ctrl-val">{{ data.control.glycolMin }}%</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">电导率上限</span>
          <span class="ctrl-val">{{ data.control.conductivityMax }} μS/cm</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">漏水响应时间</span>
          <span class="ctrl-val">{{ data.control.leakResponseTime }}s</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">泵冗余</span>
          <span class="ctrl-val">{{ data.control.pumpRedundancy }}</span>
        </div>
        <div class="ctrl-card">
          <span class="ctrl-name">CDU 冗余</span>
          <span class="ctrl-val">{{ data.control.cdurRedundancy }}</span>
        </div>
      </div>
      <div class="ctrl-desc" v-if="data.control.description">{{ data.control.description }}</div>
    </div>

    <!-- ========== 趋势图 ========== -->
    <div class="section" v-if="hasTrends">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--yellow)"></span>
        运行趋势 (48h)
      </h3>
      <div class="trend-grid">
        <TrendChart
          title="一次/二次侧温度趋势"
          :xAxisData="trendTimestamps"
          :series="tempTrendSeries"
          :loading="loading"
          :height="250"
        />
        <TrendChart
          title="一次/二次侧流量趋势"
          :xAxisData="trendTimestamps"
          :series="flowTrendSeries"
          :loading="loading"
          :height="250"
        />
        <TrendChart
          title="二次侧温差 ΔT 趋势"
          :xAxisData="trendTimestamps"
          :series="dtTrendSeries"
          :loading="loading"
          :height="250"
        />
        <TrendChart
          title="制冷能力与 PUE 贡献"
          :xAxisData="trendTimestamps"
          :series="capTrendSeries"
          :loading="loading"
          :height="250"
        />
      </div>
    </div>

    <!-- ========== 活跃告警 ========== -->
    <div class="section" v-if="liquidAlarms.length">
      <h3 class="section-title">
        <span class="section-dot" style="background: var(--red)"></span>
        活跃告警
        <span class="section-sum danger">{{ liquidAlarms.length }} 条</span>
      </h3>
      <div class="alarm-list">
        <div v-for="a in liquidAlarms" :key="a.id" class="alarm-item">
          <AlarmBadge :level="a.level || 'warning'" />
          <span class="alarm-msg"
            >{{ a.message || a.title || '-' }}
            <em class="alarm-tag">[{{ a.source || a.domain || '-' }}]</em>
          </span>
          <span class="alarm-time">{{ formatTime(a.time || a.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- ========== Footer ========== -->
    <div class="page-footer" v-if="data">
      <span>总设备 {{ data.total }} 台</span>
      <span>在线 {{ data.online }} · 故障 {{ data.total - data.online }}</span>
      <span>平均流量 {{ data.avgFlowRate }} m³/h</span>
      <span>CDI 温度 {{ data.avgCdiTemperature }}℃ · CDO {{ data.avgCdoTemperature }}℃</span>
      <span v-if="lastUpdate">更新: {{ lastUpdate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getLiquidCooling } from '@/api/hvac'
import { getActiveAlarms } from '@/api'
import type { LiquidCoolingSummary, ManifoldNodeView } from '@/api/hvac'
import type { Alarm } from '@/types'
import { CHART_COLORS } from '@/assets/echarts-theme'
import { KpiCard } from '@dc-ioc/ui'
import { StatusBadge } from '@dc-ioc/ui'
import { AlarmBadge } from '@dc-ioc/ui'
import GroupCard from '@/components/monitor/GroupCard.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import DeviceTable from '@/components/monitor/DeviceTable.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
import { formatVal, statusRow, formatTime } from '@/utils/format'

// ===== State =====
const data = ref<LiquidCoolingSummary | null>(null)
const loading = ref(false)
const error = ref('')
const lastUpdate = ref('')
const alarms = ref<Alarm[]>([])
let timer: ReturnType<typeof setInterval> | null = null

const dataOk = computed(() => !!data.value)
const hasTrends = computed(() => {
  if (!data.value) return false
  const s = data.value.supplyTrend?.length ?? 0
  const r = data.value.returnTrend?.length ?? 0
  return s > 0 || r > 0
})

const hasRejection = computed(() => {
  if (!data.value) return false
  return (
    (data.value.towerFans?.length ?? 0) > 0 ||
    (data.value.dryCoolers?.length ?? 0) > 0 ||
    (data.value.rejectionPumps?.length ?? 0) > 0 ||
    !!data.value.heatRecovery
  )
})

// ===== Data Loading =====
async function loadAll(reportError = false) {
  // 首屏或显式刷新才置 loading（避免 30s 轮询闪烁骨架）；
  // 轮询失败静默保留上一次成功数据，仅显式刷新暴露错误态
  if (reportError) {
    loading.value = true
    error.value = ''
  } else if (!data.value) {
    loading.value = true
  }
  try {
    const [summary, alarmResult] = await Promise.all([
      getLiquidCooling(),
      getActiveAlarms().catch(() => ({ total: 0, items: [] as Alarm[] })),
    ])
    data.value = summary
    alarms.value = alarmResult.items || []
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    if (reportError) error.value = toErrorMessage(e) || '液冷系统加载失败'
  } finally {
    loading.value = false
  }
}

function refresh() {
  loadAll(true)
}

onMounted(() => {
  refresh()
  timer = setInterval(() => loadAll(false), 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

// ===== Helpers =====

// ===== 一次侧 CDU =====
const primCduCols = [
  { key: 'name', label: '名称', width: '110px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'priInTemp', label: '一次进水(℃)', width: '90px' },
  { key: 'priOutTemp', label: '一次出水(℃)', width: '90px' },
  { key: 'secInTemp', label: '二次进水(℃)', width: '90px' },
  { key: 'secOutTemp', label: '二次出水(℃)', width: '90px' },
  { key: 'heatExEff', label: '换热效率(%)', width: '90px' },
  { key: 'flowPri', label: '一次流量(m³/h)', width: '95px' },
  { key: 'dpPri', label: '一次压差(bar)', width: '90px' },
  { key: 'pumpSpeed', label: '泵速(Hz)', width: '80px' },
  { key: 'pumpKw', label: '泵功(kW)', width: '80px' },
  { key: 'valve', label: '阀门(%)', width: '75px' },
  { key: 'leakStatus', label: '漏检', width: '60px', render: 'status' as const },
  { key: 'runHrs', label: '运行(h)', width: '75px' },
]

const primCduRows = computed(() => {
  if (!data.value?.primaryCDUs) return []
  return data.value.primaryCDUs.map((d) => ({
    name: d.name,
    state: d.state,
    priInTemp: formatVal(d.priInTemp),
    priOutTemp: formatVal(d.priOutTemp),
    secInTemp: formatVal(d.secInTemp),
    secOutTemp: formatVal(d.secOutTemp),
    heatExEff: formatVal(d.heatExEff),
    flowPri: formatVal(d.flowPri),
    dpPri: formatVal(d.dpPri),
    pumpSpeed: formatVal(d.pumpSpeed),
    pumpKw: formatVal(d.pumpKw),
    valve: formatVal(d.valve),
    leakStatus: d.leakStatus,
    runHrs: formatVal(d.runHrs),
    _rowClass: statusRow(d.state),
  }))
})

// ===== 二次侧 CDU =====
const secCduCols = [
  { key: 'name', label: '名称', width: '110px' },
  { key: 'rackGroup', label: '机柜组', width: '85px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'supplyTemp', label: '供水(℃)', width: '75px' },
  { key: 'returnTemp', label: '回水(℃)', width: '75px' },
  { key: 'flow', label: '流量(m³/h)', width: '85px' },
  { key: 'dp', label: '压差(bar)', width: '80px' },
  { key: 'pumpSpeed', label: '泵速(%)', width: '75px' },
  { key: 'pumpKw', label: '泵功(kW)', width: '75px' },
  { key: 'leakStatus', label: '漏检', width: '60px', render: 'status' as const },
  { key: 'coldPlateInfo', label: '冷板(在线/总数)', width: '110px' },
]

const secCduRows = computed(() => {
  if (!data.value?.secondaryCDUs) return []
  return data.value.secondaryCDUs.map((d) => ({
    name: d.name,
    rackGroup: d.rackGroup,
    state: d.state,
    supplyTemp: formatVal(d.supplyTemp),
    returnTemp: formatVal(d.returnTemp),
    flow: formatVal(d.flow),
    dp: formatVal(d.dp),
    pumpSpeed: formatVal(d.pumpSpeed),
    pumpKw: formatVal(d.pumpKw),
    leakStatus: d.leakStatus,
    coldPlateInfo: `${d.coldPlateOnline}/${d.coldPlateCount}`,
    _rowClass: statusRow(d.state),
  }))
})

// ===== 冷板 GPU =====
const coldPlateCols = [
  { key: 'rackId', label: '机柜', width: '90px' },
  { key: 'nodeType', label: '节点类型', width: '80px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'inletTemp', label: '入口(℃)', width: '75px' },
  { key: 'outletTemp', label: '出口(℃)', width: '75px' },
  { key: 'deltaT', label: 'ΔT(℃)', width: '65px' },
  { key: 'flow', label: '流量(L/min)', width: '85px' },
  { key: 'dp', label: '压差(Pa)', width: '75px' },
  { key: 'gpuTemp', label: 'GPU 温度', width: '140px' },
]

const coldPlateRows = computed(() => {
  if (!data.value?.coldPlates) return []
  return data.value.coldPlates.map((d) => ({
    rackId: d.rackId,
    nodeType: d.nodeType,
    state: d.state,
    inletTemp: formatVal(d.inletTemp),
    outletTemp: formatVal(d.outletTemp),
    deltaT: formatVal((d.outletTemp as number) - (d.inletTemp as number)),
    flow: formatVal(d.flow),
    dp: formatVal(d.dp),
    gpuTemp: d.gpuTemp?.length ? d.gpuTemp.map((t) => `${t}℃`).join(' · ') : '-',
    _rowClass: statusRow(d.state),
  }))
})

// ===== 分集水器 =====
const manifoldCols = [
  { key: 'id', label: 'ID', width: '90px' },
  { key: 'zone', label: '区域', width: '80px' },
  { key: 'temp', label: '温度(℃)', width: '80px' },
  { key: 'pressure', label: '压力(bar)', width: '80px' },
  { key: 'flow', label: '流量(m³/h)', width: '85px' },
  { key: 'branches', label: '阀门/支路', width: '90px' },
]

function mapManRows(items: ManifoldNodeView[]) {
  return items.map((d) => ({
    id: d.id,
    zone: d.zone,
    temp: formatVal(d.temp),
    pressure: formatVal(d.pressure),
    flow: formatVal(d.flow),
    branches:
      d.valvesOpen != null
        ? `开 ${d.valvesOpen}/${d.branchCount ?? '-'}`
        : `${d.branchCount ?? '-'} 路`,
  }))
}

const supplyManRows = computed(() =>
  data.value?.manifoldsSupply ? mapManRows(data.value.manifoldsSupply) : [],
)
const returnManRows = computed(() =>
  data.value?.manifoldsReturn ? mapManRows(data.value.manifoldsReturn) : [],
)

// ===== 漏水检测 =====
const leakRopeCols = [
  { key: 'id', label: 'ID', width: '100px' },
  { key: 'location', label: '位置', width: '160px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'length', label: '长度(m)', width: '80px' },
  { key: 'coverage', label: '覆盖率(%)', width: '85px' },
]

const leakRopeRows = computed(() => {
  if (!data.value?.leakRope) return []
  return data.value.leakRope.map((d) => ({
    id: d.id,
    location: d.location,
    status: d.status,
    length: formatVal(d.length),
    coverage: formatVal(d.coverage),
    _rowClass: d.status !== '正常' ? 'row-danger' : '',
  }))
})

const leakPointCols = [
  { key: 'id', label: 'ID', width: '100px' },
  { key: 'zone', label: '区域', width: '120px' },
  { key: 'count', label: '监测点', width: '80px' },
  { key: 'alarmCount', label: '告警数', width: '80px' },
]

const leakPointRows = computed(() => {
  if (!data.value?.leakPoint) return []
  return data.value.leakPoint.map((d) => ({
    id: d.id,
    zone: d.zone,
    count: d.count,
    alarmCount: d.alarmCount,
    _rowClass: d.alarmCount > 0 ? 'row-danger' : '',
  }))
})

// ===== 排热系统 =====
const towerFanCols = [
  { key: 'id', label: 'ID', width: '90px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'fanHz', label: '风机(Hz)', width: '85px' },
  { key: 'outletTemp', label: '出口(℃)', width: '85px' },
  { key: 'approach', label: '逼近(℃)', width: '85px' },
]

const towerFanRows = computed(() => {
  if (!data.value?.towerFans) return []
  return data.value.towerFans.map((d) => ({
    id: d.id,
    state: d.state,
    fanHz: formatVal(d.fanHz),
    outletTemp: formatVal(d.outletTemp),
    approach: formatVal(d.approach),
    _rowClass: statusRow(d.state),
  }))
})

const dryCoolerCols = [
  { key: 'id', label: 'ID', width: '90px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'fanHz', label: '风机(Hz)', width: '85px' },
  { key: 'ambientT', label: '环境(℃)', width: '85px' },
]

const dryCoolerRows = computed(() => {
  if (!data.value?.dryCoolers) return []
  return data.value.dryCoolers.map((d) => ({
    id: d.id,
    state: d.state,
    fanHz: formatVal(d.fanHz),
    ambientT: formatVal(d.ambientT),
    _rowClass: statusRow(d.state),
  }))
})

const rejPumpCols = [
  { key: 'id', label: 'ID', width: '90px' },
  { key: 'state', label: '状态', width: '70px', render: 'status' as const },
  { key: 'hz', label: '频率(Hz)', width: '85px' },
  { key: 'kw', label: '功率(kW)', width: '85px' },
]

const rejPumpRows = computed(() => {
  if (!data.value?.rejectionPumps) return []
  return data.value.rejectionPumps.map((d) => ({
    id: d.id,
    state: d.state,
    hz: formatVal(d.hz),
    kw: formatVal(d.kw),
    _rowClass: statusRow(d.state),
  }))
})

// ===== 趋势图 =====
const TREND_LEN = 96 // 48h × 2 (30min intervals)
const trendTimestamps = computed<string[]>(() => {
  const now = new Date()
  const stamps: string[] = []
  for (let i = TREND_LEN - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 30 * 60_000)
    stamps.push(
      `${t.getMonth() + 1}/${t.getDate()} ${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}`,
    )
  }
  return stamps
})

function padArray(arr: number[] | undefined, len: number): number[] {
  if (!arr || arr.length === 0) return new Array(len).fill(0)
  if (arr.length >= len) return arr.slice(-len)
  const pad = new Array(len - arr.length).fill(0)
  return [...pad, ...arr]
}

const tempTrendSeries = computed(() => {
  if (!data.value) return []
  return [
    {
      name: '一次供水',
      data: padArray(data.value.supplyTrend, TREND_LEN),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.blue },
    },
    {
      name: '二次供水',
      data: padArray(
        data.value.secSupplyTemp != null ? [data.value.secSupplyTemp] : [],
        TREND_LEN,
      ).map((_, i) => {
        const s = data.value!.supplyTrend ?? []
        return s.length > i ? s[i] - 2 : 0
      }),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.cyan },
    },
    {
      name: '一次回水',
      data: padArray(data.value.returnTrend, TREND_LEN),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.orange },
    },
    {
      name: '二次回水',
      data: padArray(
        data.value.secReturnTemp != null ? [data.value.secReturnTemp] : [],
        TREND_LEN,
      ).map((_, i) => {
        const r = data.value!.returnTrend ?? []
        return r.length > i ? r[i] + 1 : 0
      }),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.amber },
    },
  ]
})

const flowTrendSeries = computed(() => {
  if (!data.value) return []
  return [
    {
      name: '一次侧流量',
      data: padArray(data.value.flowTrend, TREND_LEN),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.blue },
    },
    {
      name: '二次侧流量',
      data: padArray(data.value.flowTrend, TREND_LEN).map((v) => v * 0.85),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.cyan },
    },
  ]
})

const dtTrendSeries = computed(() => {
  if (!data.value) return []
  return [
    {
      name: '温差 ΔT',
      data: padArray(data.value.deltaTTrend, TREND_LEN),
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.yellow },
      areaStyle: { opacity: 0.1, color: CHART_COLORS.yellow },
    },
  ]
})

const capTrendSeries = computed(() => {
  if (!data.value) return []
  const base = Array(TREND_LEN).fill(data.value.totalCoolingCap)
  const used = Array(TREND_LEN).fill(data.value.coolingCapUsed)
  return [
    {
      name: '制冷能力(kW)',
      data: base,
      type: 'line' as const,
      lineStyle: { color: CHART_COLORS.cyan, width: 2 },
      areaStyle: { opacity: 0.05, color: CHART_COLORS.cyan },
    },
    {
      name: '实际使用(kW)',
      data: used,
      type: 'bar' as const,
      yAxisIndex: 1,
      itemStyle: { color: CHART_COLORS.purple },
      barWidth: '60%',
    },
  ]
})

// ===== 告警过滤 =====
const liquidAlarms = computed(() => {
  return alarms.value.filter((a) => {
    const t = `${a.source || ''}${a.domain || ''}${a.message || ''}${a.title || ''}`.toLowerCase()
    return (
      t.includes('liquid') ||
      t.includes('液冷') ||
      t.includes('cdu') ||
      t.includes('冷板') ||
      t.includes('leak') ||
      t.includes('漏水') ||
      t.includes('分集水')
    )
  })
})
</script>

<style scoped>
.hvac-liquid {
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
.ph-mode {
  font-size: 11px;
  color: var(--purple);
  background: rgba(139, 92, 246, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
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
.section-sum-s {
  font-size: 11px;
  color: var(--txt3);
  margin-left: auto;
}

/* Manifolds */
.manifold-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}
@media (max-width: 1000px) {
  .manifold-grid {
    grid-template-columns: 1fr;
  }
}

/* Quality */
.quality-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .quality-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 600px) {
  .quality-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Leak */
.leak-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
@media (max-width: 1000px) {
  .leak-grid {
    grid-template-columns: 1fr;
  }
}
.leak-block {
  margin-top: 4px;
}

/* Subtitle */
.rg-subtitle {
  font-size: 12px;
  font-weight: 600;
  color: var(--txt2);
  margin: 8px 0 6px;
}

/* Control strategy */
.ctrl-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .ctrl-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 500px) {
  .ctrl-grid {
    grid-template-columns: 1fr;
  }
}
.ctrl-card {
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ctrl-name {
  font-size: 11px;
  color: var(--txt3);
}
.ctrl-val {
  font-size: 15px;
  font-weight: 700;
  color: var(--txt);
}
.ctrl-desc {
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 6px;
  font-size: 11px;
  color: var(--txt2);
  line-height: 1.6;
}

/* Heat recovery */
.hr-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
@media (max-width: 700px) {
  .hr-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Trends */
.trend-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 1000px) {
  .trend-grid {
    grid-template-columns: 1fr;
  }
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
