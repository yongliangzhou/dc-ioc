<template>
  <div class="net-genset">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('柴发并机系统') }}</h1>
      <span class="sub">{{
        tl('N+1 并机机组 · 同期并车 · 负载母排 · 自动/手动控制 · 保护告警')
      }}</span>
      <MockDataBanner :level="mockLevel" :reason="mockReason" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid cols-4">
      <SkeletonCard v-for="i in 6" :key="i" />
    </div>

    <!-- Error -->
    <Panel v-else-if="error" class="err-card">
      <div class="err-title">{{ tl('加载失败') }}</div>
      <div class="err-detail">{{ error }}</div>
      <button class="btn" @click="loadData()">{{ tl('重试') }}</button>
    </Panel>

    <template v-else-if="s">
      <!-- ======== 3.3.1 机组运行总览 ======== -->
      <div class="grid cols-6">
        <KpiCard
          :title="tl('机组数量')"
          :value="s.units.length"
          unit="台"
          :decimals="0"
          dot="var(--cyan)"
          size="sm"
        />
        <KpiCard
          :title="tl('在线机组')"
          :value="onlineCount"
          unit="台"
          :decimals="0"
          :bar-value="onlinePercent"
          bar-color="var(--green)"
          size="sm"
        />
        <KpiCard
          :title="tl('总输出功率')"
          :value="totalPower"
          unit="kW"
          :decimals="0"
          :bar-value="Math.min(100, (totalPower / ratedP) * 100)"
          bar-color="var(--violet)"
          size="sm"
        />
        <KpiCard
          :title="tl('平均负载率')"
          :value="avgLoad"
          unit="%"
          :decimals="1"
          :status="avgLoad >= 80 ? 'warning' : 'normal'"
          size="sm"
          :bar-value="avgLoad"
          bar-color="var(--blue)"
        />
        <KpiCard
          :title="tl('并机母线')"
          :value="busStateText"
          :decimals="0"
          size="sm"
          :status="busState === '并联运行' ? 'normal' : 'warning'"
        />
        <KpiCard
          :title="tl('控制模式')"
          :value="s.autoMode"
          :decimals="0"
          size="sm"
          :status="s.autoMode.includes('自动') ? 'normal' : 'warning'"
        />
      </div>

      <!-- ======== 3.3.2 并机系统一次图 ======== -->
      <Panel title="并机系统一次图">
        <template #extra>
          <div class="legend">
            <span class="lg"><i class="dot g"></i>{{ tl('运行/合闸') }}</span>
            <span class="lg"><i class="dot r"></i>{{ tl('停机/分闸') }}</span>
            <span class="lg"><i class="dot b"></i>{{ tl('热备/备用') }}</span>
            <span class="lg muted">{{ tl('点击机组/开关查看详情') }}</span>
            <button class="gs-edit" @click="editOpen = true">
              {{ tl('编辑') }}{{ hasGraphicEdits ? ' ●' : '' }}
            </button>
          </div>
        </template>
        <div class="schematic-wrap">
          <svg
            :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
            class="genset-svg"
            preserveAspectRatio="xMidYMid meet"
          >
            <!-- 市电汇流 (左) -->
            <g>
              <rect
                :x="M_LINK.x - 40"
                :y="M_LINK.y - 16"
                width="80"
                height="24"
                rx="5"
                class="mains-box"
              />
              <text :x="M_LINK.x" :y="M_LINK.y + 1" class="mains-text">{{ tl('市电') }}</text>
              <line
                :x1="M_LINK.x"
                :y1="M_LINK.y + 8"
                :x2="BUS_P.x"
                :y2="BUS_P.y - BUS_H / 2"
                class="feeder-line"
              />
            </g>

            <!-- 并机母线 (竖) -->
            <rect
              :x="BUS_P.x - BUS_W / 2"
              :y="BUS_P.y"
              :width="BUS_W"
              :height="BUS_P.h"
              rx="4"
              class="bus"
            />
            <text :x="BUS_P.x + BUS_W / 2 + 6" :y="BUS_P.y + 12" class="bus-label">
              {{ tl('并机母线') }}
            </text>

            <!-- 机组进线 + 出口断路器 G1..GN (机组节点来自 s.units, 渲染用覆盖层合并后的 unitsView) -->
            <g v-for="u in unitsView" :key="'u' + u.id" class="feeder-line">
              <!-- 机组框 -->
              <rect
                :x="u.gx - 46"
                :y="u.gy - 16"
                width="92"
                height="24"
                rx="5"
                :class="['unit-box', stateCls(u.state)]"
              />
              <text :x="u.gx" :y="u.gy + 1" :class="['unit-text', stateTextCls(u.state)]">
                {{ u.dl }}
              </text>
              <!-- 进线连线 -->
              <line :x1="u.gx" :y1="u.gy + 8" :x2="u.gx" :y2="u.gy + UNIT_BR_DY - BR_H / 2" />
              <!-- 出口断路器 -->
              <g class="breaker-node" @click="selectNode(unitBreakerNode(u))">
                <rect
                  :x="u.gx - BR_W / 2"
                  :y="u.gy + UNIT_BR_DY - BR_H / 2"
                  :width="BR_W"
                  :height="BR_H"
                  rx="5"
                  :class="['breaker-rect', breakerCls(u.breaker)]"
                />
                <text :x="u.gx" :y="u.gy + UNIT_BR_DY + 4" class="breaker-text">
                  {{ u.id.replace(/[^0-9]/g, '') }}-CB
                </text>
              </g>
              <!-- 至并机母线连线 -->
              <line :x1="u.gx" :y1="u.gy + UNIT_BR_DY + BR_H / 2" :x2="u.gx" :y2="BUS_P.y" />
            </g>

            <!-- 并机母线 → 负载母排 联络断路器 QB (用户删除时隐藏) -->
            <g
              v-if="!busTieNodeView.hidden"
              class="breaker-node"
              @click="selectNode(busTieNodeView)"
            >
              <line
                :x1="BUS_P.x"
                :y1="BUS_P.y + BUS_P.h"
                :x2="BUS_P.x"
                :y2="BUS_L.y - BR_H / 2"
                class="feeder-line"
              />
              <rect
                :x="busTieNodeView.x - BR_W / 2"
                :y="busTieNodeView.y - BR_H / 2"
                :width="BR_W"
                :height="BR_H"
                rx="5"
                :class="['breaker-rect', breakerCls(busTieNodeView.breaker)]"
              />
              <text :x="busTieNodeView.x" :y="busTieNodeView.y + 4" class="breaker-text">
                {{ busTieNodeView.code }}
              </text>
            </g>

            <!-- 负载母排 -->
            <rect
              :x="BUS_L.x"
              :y="BUS_L.y + BR_H / 2"
              :width="BUS_L.w"
              :height="BUS_H"
              rx="4"
              class="bus"
            />
            <text :x="BUS_L.x + BUS_L.w / 2" :y="BUS_L.y + BR_H / 2 - 8" class="bus-label">
              {{ tl('负载母排') }}
            </text>
            <!-- 负载引出 -->
            <line
              :x1="BUS_L.x + BUS_L.w / 2"
              :y1="BUS_L.y + BR_H / 2 + BUS_H"
              :x2="BUS_L.x + BUS_L.w / 2"
              :y2="BUS_L.y + BR_H / 2 + BUS_H + 26"
              class="feeder-line"
            />
            <text :x="BUS_L.x + BUS_L.w / 2" :y="BUS_L.y + BR_H / 2 + BUS_H + 40" class="bus-label">
              {{ tl('数据中心负载') }}
            </text>
          </svg>
        </div>

        <!-- 节点详情面板 -->
        <transition name="fade">
          <div v-if="selectedNode" class="node-detail">
            <div class="nd-head">
              <span class="nd-code" :class="breakerCls(selectedNode.breaker)">{{
                selectedNode.code
              }}</span>
              <span class="nd-title">{{ selectedNode.label }}</span>
              <button class="nd-close" @click="selectedNode = null">×</button>
            </div>
            <div class="nd-grid">
              <div v-for="(kv, ki) in selectedNode.kvs" :key="ki" class="nd-kv">
                <span class="nd-k">{{ kv.k }}</span>
                <span class="nd-v" :class="kv.cls">{{ kv.v }}</span>
              </div>
            </div>
          </div>
        </transition>
      </Panel>

      <!-- 统一图形编辑入口: 对并机一次图的机组/母联节点做增删改 (覆盖层, 不影响接口数据) -->
      <GraphicEditDrawer
        v-model="editOpen"
        :editor="graphicEditor"
        :title="tl('柴发并机系统一次图')"
        :defaults="graphicDefaults"
      />

      <!-- ======== 3.3.3 单机组电参量 + 趋势 ======== -->
      <div class="grid cols-2">
        <!-- 机组卡片 -->
        <Panel class="scroll-x" title="机组电参量">
          <template #extra>
            <span class="pill" :class="runningCount > 0 ? 'g' : 'a'"
              >{{ runningCount }} {{ tl('台运行') }}</span
            >
          </template>
          <table class="mini-tbl">
            <thead>
              <tr>
                <th>{{ tl('机组') }}</th>
                <th>{{ tl('状态') }}</th>
                <th>U(V)</th>
                <th>I(A)</th>
                <th>P(kW)</th>
                <th>PF</th>
                <th>Hz</th>
                <th>{{ tl('转速') }}</th>
                <th>{{ tl('水温') }}</th>
                <th>{{ tl('油压') }}</th>
                <th>{{ tl('电池') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in s.units"
                :key="u.id"
                class="unit-row"
                :class="{ active: selectedUnitId === u.id }"
                @click="selectUnit(u.id)"
              >
                <td class="d-name">{{ u.id }}</td>
                <td>
                  <span class="tag" :class="stateTagCls(u.state)">{{ u.state }}</span>
                </td>
                <td class="mono">{{ fmt(u.u, 0) }}</td>
                <td class="mono">{{ fmt(u.i, 0) }}</td>
                <td class="mono" :class="loadCls(loadPct(u))">{{ fmt(u.p, 0) }}</td>
                <td class="mono" :class="pfCls(u.pf)">{{ fmt(u.pf) }}</td>
                <td class="mono">{{ fmt(u.freq) }}</td>
                <td class="mono">{{ fmt(u.rpm, 0) }}</td>
                <td class="mono" :class="tempCls(u.waterT, 90, 98)">{{ fmt(u.waterT, 0) }}°</td>
                <td class="mono" :class="u.oilP < 3 ? 'r-text' : 'g-text'">{{ fmt(u.oilP, 1) }}</td>
                <td class="mono" :class="u.battU < 24 ? 'r-text' : 'g-text'">{{ fmt(u.battU) }}</td>
              </tr>
            </tbody>
          </table>
        </Panel>

        <!-- 选中机组趋势 -->
        <Panel :title="selUnit ? selUnit.id + ' · ' + tl('运行趋势') : tl('机组运行趋势')">
          <template #extra>
            <span class="pill" :class="selUnit && selUnit.state === '运行' ? 'g' : 'a'">{{
              selUnit ? selUnit.state : '-'
            }}</span>
          </template>
          <TrendChart :labels="trend.labels" :series="trend.series" :height="210" />
        </Panel>
      </div>

      <!-- ======== 3.3.4 并机同步状态 ======== -->
      <Panel class="scroll-x" title="并机同步状态">
        <template #extra>
          <span class="pill" :class="syncOk ? 'g' : 'a'">{{
            syncOk ? tl('同步允许') : tl('待同期')
          }}</span>
        </template>
        <table class="mini-tbl">
          <thead>
            <tr>
              <th>{{ tl('机组') }}</th>
              <th>{{ tl('电压') }}(V)</th>
              <th>{{ tl('频率') }}(Hz)</th>
              <th>ΔU(V)</th>
              <th>Δf(Hz)</th>
              <th>{{ tl('相位差') }}(°)</th>
              <th>{{ tl('并机状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(u, ui) in s.units" :key="'sy' + u.id">
              <td class="d-name">{{ u.id }}</td>
              <td class="mono">{{ fmt(u.u, 0) }}</td>
              <td class="mono" :class="Math.abs(u.freq - refFreq) > 0.2 ? 'a-text' : 'g-text'">
                {{ fmt(u.freq) }}
              </td>
              <td class="mono" :class="Math.abs(u.u - refU) > 5 ? 'a-text' : 'g-text'">
                {{ fmt(Math.abs(u.u - refU), 0) }}
              </td>
              <td class="mono" :class="Math.abs(u.freq - refFreq) > 0.2 ? 'a-text' : 'g-text'">
                {{ fmt(Math.abs(u.freq - refFreq)) }}
              </td>
              <td class="mono" :class="phaseDiff(ui) > 10 ? 'a-text' : 'g-text'">
                {{ fmt(phaseDiff(ui), 1) }}
              </td>
              <td>
                <span class="tag" :class="u.breaker.includes('合闸') ? 'g' : 'b'">
                  {{ u.breaker.includes('合闸') ? tl('已并机') : tl('待同期') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ======== 3.3.5 同期 / 并机控制 ======== -->
      <div class="grid cols-2">
        <!-- 控制状态 -->
        <Panel title="同期 / 并机控制">
          <template #extra>
            <span class="pill" :class="s.autoMode.includes('自动') ? 'g' : 'a'">{{
              s.autoMode
            }}</span>
          </template>
          <div class="ctrl-body">
            <div class="ctrl-row">
              <span class="k">{{ tl('并机方案') }}</span
              ><span class="v mono">{{ s.scheme }}</span>
            </div>
            <div class="ctrl-row">
              <span class="k">{{ tl('母联状态') }}</span>
              <span class="v"
                ><span class="tag" :class="busTieNode.breaker.includes('合闸') ? 'g' : 'b'">{{
                  busTieNode.breaker
                }}</span></span
              >
            </div>
            <div class="ctrl-row">
              <span class="k">{{ tl('控制模式') }}</span>
              <span class="v"
                ><span class="tag" :class="s.autoMode.includes('自动') ? 'g' : 'a'">{{
                  s.autoMode
                }}</span></span
              >
            </div>
            <div class="ctrl-actions">
              <button class="btn" :class="{ on: s.autoMode.includes('自动') }" @click="toggleAuto">
                {{ tl('自动/手动') }}
              </button>
              <button class="btn" @click="toggleBusTie">{{ tl('母联投/退') }}</button>
              <button class="btn" @click="startParallel">{{ tl('发起并机') }}</button>
            </div>
          </div>
        </Panel>

        <!-- 并机步进流程 -->
        <Panel title="并机步进流程">
          <template #extra>
            <span class="pill" :class="s.stepActive >= s.parallelSteps.length ? 'g' : 'a'">
              {{ tl('第') }} {{ s.stepActive }}/{{ s.parallelSteps.length }} {{ tl('步') }}
            </span>
          </template>
          <div class="steps">
            <div
              v-for="(st, si) in s.parallelSteps"
              :key="si"
              class="step"
              :class="si + 1 < s.stepActive ? 'done' : si + 1 === s.stepActive ? 'active' : 'todo'"
            >
              <span class="step-idx">{{ si + 1 }}</span>
              <span class="step-txt">{{ st }}</span>
            </div>
          </div>
        </Panel>
      </div>

      <!-- ======== 3.3.6 告警与保护 ======== -->
      <div class="grid cols-2">
        <!-- 实时告警 -->
        <Panel title="实时告警">
          <template #extra>
            <span v-if="!alarms.length" class="pill g">{{ tl('无活动告警') }}</span>
            <span v-else class="pill a">{{ alarms.length }} {{ tl('条') }}</span>
          </template>
          <div v-if="!alarms.length" class="empty-tip muted">
            {{ tl('当前无越限/过载/保护动作等告警') }}
          </div>
          <div v-else class="alarm-list">
            <div v-for="(a, ai) in alarms" :key="ai" class="alarm-row" :class="a.level">
              <AlarmBadge :level="a.level" />
              <span class="a-ts mono">{{ a.time }}</span>
              <span class="a-src">{{ a.source }}</span>
              <span class="a-msg">{{ a.message }}</span>
              <span class="a-val mono">{{ a.value }}</span>
            </div>
          </div>
        </Panel>

        <!-- 保护与最近试机 -->
        <Panel title="保护动作 / 最近试机">
          <div v-if="selUnit" class="protect-list">
            <div v-for="(p, pi) in selUnit.protections" :key="'p' + pi" class="protect-row">
              <span class="pt-name">{{ p.name }}</span>
              <span class="pt-st" :class="p.state === '正常' ? 'g-text' : 'r-text'">{{
                p.state
              }}</span>
              <span class="pt-lv tag" :class="levelTagCls(p.level)">{{ p.level }}</span>
            </div>
            <div v-if="!selUnit.protections.length" class="empty-tip muted">
              {{ tl('该机组无保护记录') }}
            </div>
          </div>
          <div v-if="s.lastTest" class="test-box">
            <div class="test-title">{{ tl('最近试机记录') }}</div>
            <div class="ctrl-row">
              <span class="k">{{ tl('日期') }}</span
              ><span class="v mono">{{ s.lastTest.date }}</span>
            </div>
            <div class="ctrl-row">
              <span class="k">{{ tl('类型') }}</span
              ><span class="v">{{ s.lastTest.type }}</span>
            </div>
            <div class="ctrl-row">
              <span class="k">{{ tl('结果') }}</span
              ><span class="v" :class="s.lastTest.result.includes('合格') ? 'g-text' : 'r-text'">{{
                s.lastTest.result
              }}</span>
            </div>
            <div class="ctrl-row">
              <span class="k">{{ tl('时长') }}</span
              ><span class="v mono">{{ s.lastTest.duration }}</span>
            </div>
          </div>
        </Panel>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { toErrorMessage, useMockFlag } from '@/composables/useAsyncPage'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { pfCls, loadCls, tempCls, fmt, breakerCls, genHours } from '@/utils/format'
import { KpiCard } from '@dc-ioc/ui'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import { AlarmBadge } from '@dc-ioc/ui'
import TrendChart from '@/components/monitor/TrendChart.vue'
import { getPowerGensetDetailed, type GensetSummary, type GensetUnitView } from '@/api/power'
import Panel from '@/components/common/Panel.vue'
import GraphicEditDrawer from '@/components/common/GraphicEditDrawer.vue'
import { useGraphicEditor, type NodeAdapter } from '@/composables/useGraphicEditor'
import type { GraphicNode } from '@/types/graphic'
const { t: tl } = useI18n()

/** 后端无有效返回时页面会回退到本地 mockSummary()，必须让用户看见这是假的 */
const { level: mockLevel, reason: mockReason, markMock, markPartial } = useMockFlag()

// ──────────────────────────────────────────
// SVG 几何
// ──────────────────────────────────────────
const SVG_W = 1000
const SVG_H = 360
const BUS_H = 14
const BUS_W = 14
const BR_W = 52
const BR_H = 24
const M_LINK = { x: 90, y: 60 }
const BUS_P = { x: 500, y: 40, h: 200 }
const BUS_L = { x: 360, y: 300, w: 280 }
const ratedP = 3200
const UNIT_RATED = 1000 // 单台机组额定功率 kW

function loadPct(u: GensetUnitView): number {
  if (!u || !u.p) return 0
  return Number(Math.min(100, (u.p / UNIT_RATED) * 100).toFixed(1))
}

function unitX(i: number): number {
  const n = s.value?.units.length || 1
  const left = 200,
    right = 820,
    span = right - left
  return n <= 1 ? (left + right) / 2 : Math.round(left + (span * i) / Math.max(1, n - 1))
}
const UNIT_Y = 60 // 机组框默认 y (可被图形编辑覆盖)
const UNIT_BR_DY = 50 // 机组框 → 出口断路器 的垂直距离

interface BreakerNode {
  id: string
  code: string
  label: string
  breaker: string
  x: number
  y: number
  kvs: { k: string; v: string; cls?: string }[]
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = ref<GensetSummary | null>(null)
const selectedNode = ref<BreakerNode | null>(null)
const selectedUnitId = ref<string>('')
const autoModeLocal = ref('')
const busTieClosed = ref<boolean | null>(null)

const selUnit = computed<GensetUnitView | null>(() => {
  const list = s.value?.units ?? []
  if (selectedUnitId.value) return list.find((u) => u.id === selectedUnitId.value) ?? null
  return list[0] ?? null
})

// 并机母线参考 (以首台运行机组为基准)
const refUnit = computed(
  () => (s.value?.units ?? []).find((u) => u.state === '运行') ?? (s.value?.units ?? [])[0] ?? null,
)
const refU = computed(() => refUnit.value?.u ?? 400)
const refFreq = computed(() => refUnit.value?.freq ?? 50)

// ──────────────────────────────────────────
// KPI 派生
// ──────────────────────────────────────────
const onlineCount = computed(
  () => (s.value?.units ?? []).filter((u) => u.state !== '停机' && u.state !== '检修').length,
)
const onlinePercent = computed(() => {
  const list = s.value?.units ?? []
  if (!list.length) return 0
  return Number(((onlineCount.value / list.length) * 100).toFixed(1))
})
const runningCount = computed(() => (s.value?.units ?? []).filter((u) => u.state === '运行').length)
const totalPower = computed(() =>
  Number((s.value?.units ?? []).reduce((sum, u) => sum + (u.p || 0), 0).toFixed(0)),
)
const avgLoad = computed(() => {
  const list = (s.value?.units ?? []).filter((u) => (u.p || 0) > 0)
  if (!list.length) return 0
  return Number((list.reduce((sum, u) => sum + loadPct(u), 0) / list.length).toFixed(1))
})
const busState = computed(() => s.value?.busState ?? '-')
const busStateText = computed(() => {
  const st = s.value?.busState ?? '-'
  return st === '并联运行'
    ? tl('并联运行')
    : runningCount.value > 1
      ? tl('并联运行')
      : tl('单机/待机')
})
// 同步判据
const syncOk = computed(() => {
  const list = s.value?.units ?? []
  if (list.length < 2) return false
  const running = list.filter((u) => u.breaker.includes('合闸'))
  if (running.length < 2) return false
  return running.every(
    (u) => Math.abs(u.u - refU.value) <= 5 && Math.abs(u.freq - refFreq.value) <= 0.2,
  )
})

// ──────────────────────────────────────────
// 交互
// ──────────────────────────────────────────
function selectUnit(id: string) {
  selectedUnitId.value = id
  rebuildTrend()
}
function selectNode(n: BreakerNode) {
  selectedNode.value = n
}
function unitBreakerNode(u: UnitGraphic): BreakerNode {
  return {
    id: u.id,
    code: u.id.replace(/[^0-9]/g, '') + '-CB',
    label: u.id + ' ' + tl('出口断路器'),
    breaker: u.breaker,
    x: u.gx,
    y: u.gy + UNIT_BR_DY,
    kvs: [
      { k: tl('开关状态'), v: u.breaker, cls: breakerCls(u.breaker) },
      { k: tl('机组状态'), v: u.state, cls: stateTextCls(u.state) },
      { k: 'U', v: fmt(u.u, 0) + ' V' },
      { k: 'I', v: fmt(u.i, 0) + ' A' },
      { k: 'P / Q', v: `${fmt(u.p, 0)} / ${fmt(u.q, 0)} kW` },
      { k: 'PF', v: fmt(u.pf), cls: pfCls(u.pf) },
      { k: tl('转速'), v: fmt(u.rpm, 0) + ' rpm' },
      { k: tl('启动次数'), v: String(u.startCnt) },
      { k: tl('运行小时'), v: fmt(u.runHrs, 0) + ' h' },
    ],
  }
}
const busTieNode = computed<BreakerNode>(() => {
  const closed = busTieClosed.value == null ? true : busTieClosed.value
  const breaker = closed ? tl('合闸') : tl('分闸')
  return {
    id: 'QB',
    code: 'QB',
    label: tl('并机母联断路器'),
    breaker,
    x: BUS_P.x,
    y: BUS_L.y,
    kvs: [
      { k: tl('开关状态'), v: breaker, cls: breakerCls(breaker) },
      { k: tl('连接'), v: tl('并机母线') + ' ↔ ' + tl('负载母排') },
    ],
  }
})

/* ───────── 统一图形编辑入口 (柴发并机系统一次图) ─────────
 * 场景覆盖层: 机组节点来自 s.units, 改名/改状态/改坐标/改参数 = 覆盖;
 * 删除 = removed (单节点 QB 用 hidden 隐藏); 新增 = 用户自建机组。 */
const graphicEditor = useGraphicEditor('power-genset-parallel', {
  title: '柴发并机系统一次图',
})
const editOpen = ref(false)
const hasGraphicEdits = computed(() => graphicEditor.hasOverrides.value)

/** 机组渲染节点: 接口数据 + 计算坐标 + 可覆盖显示名 */
interface UnitGraphic extends GensetUnitView {
  gx: number
  gy: number
  dl: string
}

/** BreakerNode ↔ GraphicNode 双向映射 (母联 QB 等) */
const breakerAdapter: NodeAdapter<BreakerNode> = {
  toNode: (n) => ({
    id: n.id,
    label: n.label,
    type: n.code,
    x: n.x,
    y: n.y,
    status: n.breaker,
    params: Object.fromEntries((n.kvs ?? []).map((kv) => [kv.k, String(kv.v)])),
  }),
  fromNode: (g, base) => {
    const src: BreakerNode = base ?? {
      id: g.id,
      code: g.type || g.id,
      label: g.label || g.id,
      breaker: g.status || tl('分闸'),
      x: g.x ?? 0,
      y: g.y ?? 0,
      kvs: [],
    }
    const params = g.params ?? {}
    const kvs = Object.keys(params).length
      ? Object.entries(params).map(([k, v]) => ({ k, v }))
      : src.kvs
    return {
      ...src,
      id: g.id,
      label: g.label || src.label,
      code: g.type || src.code,
      x: g.x ?? src.x,
      y: g.y ?? src.y,
      breaker: g.status || src.breaker,
      kvs,
    }
  },
}

/** 机组节点双向映射: 名称/状态/坐标可覆盖, 电气参数进 params 供编辑 */
const unitAdapter: NodeAdapter<UnitGraphic> = {
  toNode: (u) => ({
    id: u.id,
    label: u.dl || u.id,
    type: tl('柴发机组'),
    x: u.gx,
    y: u.gy,
    status: u.state,
    params: {
      [tl('状态')]: u.state,
      [tl('开关')]: u.breaker,
      U: `${fmt(u.u, 0)} V`,
      I: `${fmt(u.i, 0)} A`,
      P: `${fmt(u.p, 0)} kW`,
      PF: fmt(u.pf),
      [tl('转速')]: `${fmt(u.rpm, 0)} rpm`,
      [tl('水温')]: `${fmt(u.waterT, 0)} °C`,
      [tl('油压')]: fmt(u.oilP, 1),
      [tl('电池')]: `${fmt(u.battU)} V`,
    },
  }),
  fromNode: (g, base) => {
    if (!base) {
      // 用户自建机组节点: 电气量给中性默认值, 仍可参与渲染与详情
      return {
        id: g.id,
        state: g.status || tl('备用'),
        breaker: tl('分闸'),
        incomer: '',
        ua: 0,
        ub: 0,
        uc: 0,
        u: 0,
        ia: 0,
        ib: 0,
        ic: 0,
        i: 0,
        p: 0,
        q: 0,
        pf: 1,
        freq: 50,
        energy: 0,
        rpm: 1500,
        waterT: 0,
        oilP: 0,
        battU: 0,
        heater: '关',
        startCnt: 0,
        runHrs: 0,
        faults: [],
        protections: [],
        gx: g.x ?? 0,
        gy: g.y ?? UNIT_Y,
        dl: g.label || g.id,
      }
    }
    return {
      ...base,
      gx: g.x ?? base.gx,
      gy: g.y ?? base.gy,
      dl: g.label || base.dl || base.id,
      state: g.status || base.state,
    }
  },
}

const unitsBase = computed<UnitGraphic[]>(() =>
  (s.value?.units ?? []).map((u, i) => ({ ...u, gx: unitX(i), gy: UNIT_Y, dl: u.id })),
)
const unitsView = computed(() => graphicEditor.apply(unitsBase.value, unitAdapter))
/** 单节点: 被用户删除时带 hidden 标记, 模板据此隐藏 */
const busTieNodeView = computed(() => {
  const arr = graphicEditor.apply([busTieNode.value], breakerAdapter)
  return { ...(arr[0] ?? busTieNode.value), hidden: arr.length === 0 }
})
const graphicDefaults = (): GraphicNode[] => [
  ...unitsBase.value.map(unitAdapter.toNode),
  breakerAdapter.toNode(busTieNode.value),
]

// 控制动作 (本地演示, 不改变真实后端)
function toggleAuto() {
  const cur = autoModeLocal.value || s.value?.autoMode || ''
  autoModeLocal.value = cur.includes('自动') ? tl('手动') : tl('自动')
  if (s.value) s.value.autoMode = autoModeLocal.value
}
function toggleBusTie() {
  const cur = busTieNode.value.breaker
  busTieClosed.value = !cur.includes('合闸')
}
function startParallel() {
  // 演示: 将首台机组置为运行 + 出口合闸
  if (!s.value) return
  const u = s.value.units[0]
  if (u) {
    u.state = tl('运行')
    u.breaker = tl('合闸')
  }
  busTieClosed.value = true
}

// 相位差 (演示: 运行机组间取确定性偏差)
function phaseDiff(i: number): number {
  const list = s.value?.units ?? []
  if (i >= list.length) return 0
  if (!list[i].breaker.includes('合闸')) return 0
  // 以首台为参考, 其余按索引给出小相位差
  if (i === 0) return 0
  return Number((((i * 7) % 13) - 6).toFixed(1))
}

// ──────────────────────────────────────────
// 3.3.3 选中机组趋势
// ──────────────────────────────────────────
function genPower(n: number, base: number, peak: number): number[] {
  return Array.from({ length: n }, (_, i) => {
    const daily = 0.5 + 0.5 * Math.sin(((i - 6) / 24) * Math.PI * 2)
    return Number((base + daily * (peak - base) + (Math.random() - 0.5) * peak * 0.06).toFixed(0))
  })
}
const trend = reactive<{
  labels: string[]
  series: { name: string; type: 'line' | 'bar'; data: number[]; color: string }[]
}>({
  labels: genHours(24),
  series: [
    { name: tl('功率 kW'), type: 'line' as const, data: genPower(24, 200, 900), color: '#22d3ee' },
    {
      name: tl('转速 rpm'),
      type: 'line' as const,
      data: genPower(24, 1480, 1510),
      color: '#22c55e',
    },
    { name: tl('水温 °C'), type: 'line' as const, data: genPower(24, 70, 95), color: '#f59e0b' },
  ],
})
function rebuildTrend() {
  const u = selUnit.value
  const base = u ? (u.p || 300) * 0.6 : 300
  const peak = u ? u.p || 900 : 900
  trend.series[0].data = genPower(24, base * 0.5, peak)
  trend.series[1].data = genPower(24, u ? u.rpm - 20 : 1480, u ? u.rpm + 10 : 1510)
  trend.series[2].data = genPower(24, u ? u.waterT - 15 : 70, u ? u.waterT : 95)
}

// ──────────────────────────────────────────
// 3.3.6 告警派生
// ──────────────────────────────────────────
const alarms = computed(() => {
  const out: { level: string; time: string; source: string; message: string; value: string }[] = []
  const now = new Date()
  const ts = (m: number) => new Date(now.getTime() - m * 60000).toTimeString().slice(0, 8)
  ;(s.value?.units ?? []).forEach((u, i) => {
    if (loadPct(u) >= 90)
      out.push({
        level: 'warning',
        time: ts(2 + i),
        source: u.id,
        message: tl('机组负载率过高'),
        value: loadPct(u) + '%',
      })
    else if (loadPct(u) >= 80)
      out.push({
        level: 'warning',
        time: ts(4 + i),
        source: u.id,
        message: tl('机组负载率偏高'),
        value: loadPct(u) + '%',
      })
    if (u.waterT >= 98)
      out.push({
        level: 'critical',
        time: ts(3),
        source: u.id,
        message: tl('冷却水温度过高'),
        value: u.waterT + '°C',
      })
    else if (u.waterT >= 90)
      out.push({
        level: 'warning',
        time: ts(5),
        source: u.id,
        message: tl('冷却水温度偏高'),
        value: u.waterT + '°C',
      })
    if (u.oilP < 3)
      out.push({
        level: 'critical',
        time: ts(6),
        source: u.id,
        message: tl('润滑油压力低'),
        value: fmt(u.oilP, 1),
      })
    if (u.battU < 24)
      out.push({
        level: 'warning',
        time: ts(7),
        source: u.id,
        message: tl('启动电池电压低'),
        value: fmt(u.battU),
      })
    if (u.pf < 0.8)
      out.push({
        level: 'warning',
        time: ts(8),
        source: u.id,
        message: tl('功率因数偏低'),
        value: fmt(u.pf),
      })
    if (u.freq < 49.5 || u.freq > 50.5)
      out.push({
        level: 'major',
        time: ts(9),
        source: u.id,
        message: tl('频率越限'),
        value: fmt(u.freq) + 'Hz',
      })
    // 保护动作
    ;(u.protections ?? []).forEach((p) => {
      if (p.state !== '正常')
        out.push({
          level: 'critical',
          time: ts(10),
          source: `${u.id}·${p.name}`,
          message: tl('保护动作'),
          value: p.level,
        })
    })
  })
  return out.slice(0, 14)
})

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function stateCls(state: string): string {
  if (state === '运行') return 'run'
  if (state === '停机' || state === '检修') return 'stop'
  return 'standby'
}
function stateTextCls(state: string): string {
  if (state === '运行') return 'g-text'
  if (state === '停机' || state === '检修') return 'r-text'
  return 'a-text'
}
function stateTagCls(state: string): string {
  if (state === '运行') return 'g'
  if (state === '停机' || state === '检修') return 'r'
  return 'b'
}

function levelTagCls(level: string): string {
  if (level === 'critical' || level === '紧急') return 'r'
  if (level === 'major' || level === '严重') return 'a'
  if (level === 'warning' || level === '预警') return 'b'
  return 'g'
}

// ──────────────────────────────────────────
// Mock fallback
// ──────────────────────────────────────────
function mockSummary(): GensetSummary {
  const mk = (
    id: string,
    state: string,
    breaker: string,
    p: number,
    i: number,
  ): GensetUnitView => ({
    id,
    state,
    breaker,
    incomer: '市电失电',
    ua: 230,
    ub: 231,
    uc: 229,
    u: 400,
    ia: i,
    ib: Math.round(i * 0.98),
    ic: Math.round(i * 0.99),
    i,
    p,
    q: Math.round(p * 0.3),
    pf: 0.96,
    freq: 50.0,
    energy: Math.round(200000 + i * 1000),
    rpm: 1500,
    waterT: 82,
    oilP: 4.2,
    battU: 27.5,
    heater: '关',
    startCnt: 12,
    runHrs: 1840,
    faults: state === '运行' ? [] : [{ name: '低燃油液位', value: '12%', level: 'warning' }],
    protections: [
      { name: '过流保护', state: '正常', level: 'critical' },
      { name: '过温保护', state: state === '运行' ? '正常' : '动作', level: 'critical' },
      { name: '低油压保护', state: '正常', level: 'major' },
    ],
  })
  const units = [
    mk('G1', '运行', '合闸', 760, 1380),
    mk('G2', '运行', '合闸', 720, 1310),
    mk('G3', '热备用', '分闸', 0, 0),
  ]
  return {
    scheme: 'N+1 自动并机',
    busState: '并联运行',
    autoMode: '自动',
    units,
    lastTest: { date: '2026-07-25', type: '带载试机', result: '合格', duration: '30min' },
    parallelSteps: [
      tl('市电失电检测'),
      tl('机组自启动'),
      tl('转速/电压建立'),
      tl('同期检测'),
      tl('自动并车'),
      tl('均分负载'),
      tl('母联合闸'),
    ],
    stepActive: 7,
    knowledge: {
      thresholds: [],
      arch: { components: [], design: '', redundancy: '' },
      logic: [],
      faults: [],
    },
    total: 3,
    online: 3,
    avgLoadPercent: 62,
    avgVoltage: 400,
    avgCurrent: 2690,
    devices: [],
  }
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getPowerGensetDetailed()
    if (data && data.units?.length) {
      s.value = data
      markPartial('机组运行趋势为本地随机生成，其余读数来自实时接口')
    } else {
      s.value = mockSummary()
      markMock()
    }
    if (s.value.units.length) selectedUnitId.value = s.value.units[0].id
    rebuildTrend()
  } catch (e: unknown) {
    error.value = toErrorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
/* ── view-head ── */
.view-head {
  margin-bottom: 16px;
}
.view-head h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary, #e5e7eb);
  margin: 0;
}
.view-head .sub {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-top: 2px;
  display: block;
}

/* ── grid ── */
.grid {
  display: grid;
  gap: 14px;
  margin-bottom: 14px;
}
.grid.cols-6 {
  grid-template-columns: repeat(6, 1fr);
}
.grid.cols-3 {
  grid-template-columns: repeat(3, 1fr);
}
.grid.cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

/* ── SVG 一次图 ── */
.schematic-wrap {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  padding: 8px;
}
.genset-svg {
  width: 100%;
  height: auto;
  display: block;
}
.bus {
  fill: #22d3ee;
  opacity: 0.85;
}
.bus-label {
  fill: var(--text-muted, #94a3b8);
  font-size: 11px;
  text-anchor: middle;
}
.feeder-line {
  stroke: #475569;
  stroke-width: 2;
}
.feeder-line line {
  stroke: #475569;
  stroke-width: 2;
}
.mains-box {
  fill: #1e3a5f;
  stroke: #22d3ee;
  stroke-width: 1;
}
.mains-text {
  fill: #cbd5e1;
  font-size: 11px;
  text-anchor: middle;
}
.unit-box {
  stroke-width: 1;
}
.unit-box.run {
  fill: rgba(34, 197, 94, 0.18);
  stroke: #22c55e;
}
.unit-box.stop {
  fill: rgba(239, 68, 68, 0.16);
  stroke: #ef4444;
}
.unit-box.standby {
  fill: rgba(245, 158, 11, 0.14);
  stroke: #f59e0b;
}
.unit-text {
  font-size: 11px;
  text-anchor: middle;
  font-weight: 600;
}
.breaker-node {
  cursor: pointer;
}
.breaker-rect {
  stroke-width: 1.5;
  transition: filter 0.2s;
}
.breaker-node:hover .breaker-rect {
  filter: drop-shadow(0 0 6px rgba(34, 211, 255, 0.7));
}
.breaker-rect.g {
  fill: rgba(34, 197, 94, 0.25);
  stroke: #22c55e;
}
.breaker-rect.r {
  fill: rgba(239, 68, 68, 0.25);
  stroke: #ef4444;
}
.breaker-rect.b {
  fill: rgba(59, 130, 246, 0.2);
  stroke: #3b82f6;
}
.breaker-rect.a {
  fill: rgba(245, 158, 11, 0.2);
  stroke: #f59e0b;
}
.breaker-text {
  fill: #e5e7eb;
  font-size: 11px;
  text-anchor: middle;
  font-weight: 600;
  pointer-events: none;
}
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
}
.lg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted, #94a3b8);
}
.lg .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.g {
  background: #22c55e;
}
.dot.r {
  background: #ef4444;
}
.dot.b {
  background: #3b82f6;
}

/* 统一图形编辑入口按钮 */
.gs-edit {
  background: var(--bg2, #0f172a);
  border: 1px solid var(--cyan, #22d3ee);
  color: var(--cyan, #22d3ee);
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
.gs-edit:hover {
  background: rgba(34, 211, 238, 0.14);
}

/* 节点详情 */
.node-detail {
  margin-top: 12px;
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(30, 41, 59, 0.5);
}
.nd-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.nd-code {
  font-family: monospace;
  font-weight: 700;
  font-size: 13px;
  padding: 1px 8px;
  border-radius: 5px;
}
.nd-code.g {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
}
.nd-code.r {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}
.nd-code.b {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.12);
}
.nd-code.a {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
}
.nd-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
}
.nd-close {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}
.nd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 6px 18px;
}
.nd-kv {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dotted rgba(51, 65, 85, 0.5);
}
.nd-k {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.nd-v {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 机组表格行高亮 */
.unit-row {
  cursor: pointer;
}
.unit-row.active {
  background: rgba(34, 211, 255, 0.08);
}
.unit-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

/* ── 控制 / 同期 ── */
.ctrl-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ctrl-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(51, 65, 85, 0.5);
}
.ctrl-row .k {
  color: var(--text-muted, #94a3b8);
}
.ctrl-row .v {
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}
.ctrl-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--border, #334155);
  background: transparent;
  color: var(--text-primary, #e5e7eb);
  font-size: 0.75rem;
  cursor: pointer;
}
.btn:hover {
  background: rgba(255, 255, 255, 0.05);
}
.btn.on {
  border-color: rgba(34, 197, 94, 0.4);
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}

/* 步进 */
.steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid transparent;
}
.step.done {
  border-left-color: #22c55e;
  opacity: 0.7;
}
.step.active {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}
.step.todo {
  border-left-color: #334155;
  opacity: 0.5;
}
.step-idx {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: rgba(51, 65, 85, 0.6);
  color: #cbd5e1;
}
.step.done .step-idx {
  background: #22c55e;
  color: #0f172a;
}
.step.active .step-idx {
  background: #f59e0b;
  color: #0f172a;
}
.step-txt {
  color: var(--text-secondary, #94a3b8);
}

/* 保护 / 试机 */
.protect-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.protect-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(51, 65, 85, 0.5);
}
.pt-name {
  flex: 1;
  color: var(--text-secondary, #94a3b8);
}
.pt-st {
  font-weight: 600;
}
.pt-lv {
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 20px;
  border: 1px solid var(--border, #334155);
}
.test-box {
  border-top: 1px solid var(--border, #334155);
  padding-top: 10px;
}
.test-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
  margin-bottom: 6px;
}

/* ── table ── */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
th {
  text-align: left;
  color: var(--text-muted, #6b7280);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 0.4px;
  padding: 7px 8px;
  border-bottom: 1px solid var(--border, #334155);
  white-space: nowrap;
}
td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
}
tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}
.d-name {
  font-weight: 500;
  color: var(--text-primary, #e5e7eb);
}
.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

.mini-tbl th,
.mini-tbl td {
  font-size: 11px;
  padding: 5px 6px;
}

/* text color */
.g-text {
  color: #22c55e;
}
.a-text {
  color: #f59e0b;
}
.r-text {
  color: #ef4444;
}

/* ── 告警列表 ── */
.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.alarm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid transparent;
}
.alarm-row.major {
  border-left-color: #f59e0b;
}
.alarm-row.critical {
  border-left-color: #ef4444;
}
.alarm-row.warning {
  border-left-color: #eab308;
}
.a-ts {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.a-src {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
  min-width: 80px;
}
.a-msg {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  flex: 1;
}
.a-val {
  font-size: 11px;
  color: #f59e0b;
}

/* ── error/empty ── */
.err-card {
  text-align: center;
  padding: 32px 16px;
}
.err-title {
  font-size: 1rem;
  font-weight: 700;
  color: #ef4444;
  margin-bottom: 8px;
}
.err-detail {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-bottom: 14px;
}
.empty-tip {
  text-align: center;
  padding: 20px;
  font-size: 12px;
}

/* ── responsive ── */
@media (max-width: 1280px) {
  .grid.cols-6 {
    grid-template-columns: repeat(3, 1fr);
  }
  .grid.cols-3 {
    grid-template-columns: 1fr;
  }
  .grid.cols-2 {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 860px) {
  .grid.cols-6 {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
