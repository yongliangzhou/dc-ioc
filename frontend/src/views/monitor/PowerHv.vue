<template>
  <div class="net-hv">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('10KV 中压配电') }}</h1>
      <span class="sub">{{ tl('两路市电进线 · 母线 · 馈线回路 · 开关状态 · 电能质量 · 保护事件') }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid cols-4">
      <SkeletonCard v-for="i in 6" :key="i" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card err-card">
      <div class="err-title">{{ tl('加载失败') }}</div>
      <div class="err-detail">{{ error }}</div>
      <button class="btn" @click="loadData()">{{ tl('重试') }}</button>
    </div>

    <template v-else-if="s">
      <!-- ======== 3.1.1 / 3.1.2 电气一次系统图 (SVG, 可交互节点) ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('电气一次系统图') }}</span>
          <div class="legend">
            <span class="lg"><i class="dot g"></i>{{ tl('合闸') }}</span>
            <span class="lg"><i class="dot r"></i>{{ tl('分闸') }}</span>
            <span class="lg"><i class="dot b"></i>{{ tl('检修/备用') }}</span>
            <span class="lg muted">{{ tl('点击断路器查看详情') }}</span>
          </div>
        </div>
        <div class="schematic-wrap">
          <svg :viewBox="`0 0 ${SVG_W} ${SVG_H}`" class="hv-svg" preserveAspectRatio="xMidYMid meet">
            <!-- 母线 A / B -->
            <rect :x="BUS_A.x" :y="BUS_A.y" :width="BUS_A.w" :height="BUS_H" rx="4" class="bus" />
            <text :x="BUS_A.x + BUS_A.w/2" :y="BUS_A.y - 8" class="bus-label">{{ tl('10KV Ⅰ段母线') }}</text>
            <rect :x="BUS_B.x" :y="BUS_B.y" :width="BUS_B.w" :height="BUS_H" rx="4" class="bus" />
            <text :x="BUS_B.x + BUS_B.w/2" :y="BUS_B.y - 8" class="bus-label">{{ tl('10KV Ⅱ段母线') }}</text>

            <!-- 进线 1 -->
            <g class="feeder-line">
              <line :x1="IN1.x" :y1="IN1.y" :x2="IN1.x" :y2="BUS_A.y" />
              <rect :x="IN1.x - 34" :y="IN1.y - 14" width="68" height="22" rx="4" class="source-box" />
              <text :x="IN1.x" :y="IN1.y + 2" class="src-text">{{ tl('市电进线') }} 1</text>
            </g>
            <!-- 进线 2 -->
            <g class="feeder-line">
              <line :x1="IN2.x" :y1="IN2.y" :x2="IN2.x" :y2="BUS_B.y" />
              <rect :x="IN2.x - 34" :y="IN2.y - 14" width="68" height="22" rx="4" class="source-box" />
              <text :x="IN2.x" :y="IN2.y + 2" class="src-text">{{ tl('市电进线') }} 2</text>
            </g>

            <!-- 进线断路器 Q1 / Q2 -->
            <g v-for="(q, qi) in incomerBreakers" :key="'q'+qi" class="breaker-node"
               @click="selectNode(q)">
              <rect :x="q.x - BR_W/2" :y="q.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(q.breaker)]" />
              <text :x="q.x" :y="q.y + 4" class="breaker-text">{{ q.code }}</text>
            </g>

            <!-- 母联 QB -->
            <g class="breaker-node" @click="selectNode(busTieNode)">
              <rect :x="busTieNode.x - BR_W/2" :y="busTieNode.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(busTieNode.breaker)]" />
              <text :x="busTieNode.x" :y="busTieNode.y + 4" class="breaker-text">{{ busTieNode.code }}</text>
              <text :x="busTieNode.x" :y="busTieNode.y - BR_H/2 - 6" class="bus-tie-label">{{ s.busTie?.autoSwitch }}</text>
            </g>

            <!-- 馈线断路器 + 标签 -->
            <g v-for="(f, fi) in feederNodes" :key="'f'+fi" class="breaker-node" @click="selectNode(f)">
              <line :x1="f.x" :y1="f.busY" :x2="f.x" :y2="f.y" class="feeder-line" />
              <rect :x="f.x - BR_W/2" :y="f.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(f.breaker)]" />
              <text :x="f.x" :y="f.y + 4" class="breaker-text">{{ f.code }}</text>
              <text :x="f.x" :y="f.y + BR_H/2 + 14" class="feeder-load">{{ f.load }}</text>
            </g>
          </svg>
        </div>

        <!-- 节点详情面板 -->
        <transition name="fade">
          <div v-if="selectedNode" class="node-detail">
            <div class="nd-head">
              <span class="nd-code" :class="breakerCls(selectedNode.breaker)">{{ selectedNode.code }}</span>
              <span class="nd-title">{{ selectedNode.label }}</span>
              <span class="tag" :class="breakerCls(selectedNode.breaker)">{{ selectedNode.breaker }}</span>
              <button class="nd-close" @click="selectedNode = null">×</button>
            </div>
            <div class="nd-grid">
              <div class="nd-kv" v-for="kv in selectedNode.kvs" :key="kv.k">
                <span class="nd-k">{{ kv.k }}</span>
                <span class="nd-v mono" :class="kv.cls || ''">{{ kv.v }}</span>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- ======== 3.1.3 进线监测 KPI (KpiCard × 6) ======== -->
      <div class="grid cols-6" v-if="primaryIncomer">
        <KpiCard :title="tl('线电压')" :value="lineVoltage" unit="kV" :decimals="2" dot="var(--cyan)" size="sm" />
        <KpiCard :title="tl('电流')" :value="primaryIncomer.i" unit="A" :decimals="0" :bar-value="Math.min(100, primaryIncomer.i/ratedI*100)" bar-color="var(--blue)" size="sm"
                 :status="primaryIncomer.i > ratedI ? 'danger' : primaryIncomer.i > ratedI*0.85 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('有功功率')" :value="primaryIncomer.p" unit="MW" :decimals="2" :bar-value="Math.min(100, primaryIncomer.p/ratedP*100)" bar-color="var(--violet)" size="sm"
                 :status="primaryIncomer.p > ratedP*0.85 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('功率因数')" :value="primaryIncomer.pf" :decimals="3" :status="primaryIncomer.pf < 0.9 ? 'warning' : 'normal'" size="sm"
                 :value-class="pfCls(primaryIncomer.pf)" />
        <KpiCard :title="tl('频率')" :value="primaryIncomer.freq" unit="Hz" :decimals="2" :status="freqStatus(primaryIncomer.freq)" size="sm" />
        <KpiCard :title="tl('电度')" :value="primaryIncomer.energy" unit="kWh" :decimals="0" size="sm" :prefix="''" />
      </div>

      <!-- ======== 进线 / 馈线 三相电参量表 ======== -->
      <div class="grid cols-2">
        <div class="card scroll-x">
          <div class="card-head">
            <span class="ct">{{ tl('10KV 进线监测') }} ({{ tl('三相电参量') }})</span>
            <span class="pill" :class="incomerAllClosed ? 'g' : 'a'">{{ s.incomers.length }} {{ tl('路') }} · {{ tl('合闸') }} {{ incomerClosedCount }}/{{ s.incomers.length }}</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>{{ tl('进线') }}</th><th>{{ tl('电源') }}</th><th>{{ tl('开关') }}</th>
                <th>Ua</th><th>Ub</th><th>Uc</th><th>Ia</th><th>Ib</th><th>Ic</th>
                <th>P(MW)</th><th>Q(MVar)</th><th>PF</th><th>f(Hz)</th><th>E(kWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in s.incomers" :key="d.id">
                <td class="d-name">{{ d.id }}</td>
                <td class="muted">{{ d.src }}</td>
                <td><span class="tag" :class="breakerCls(d.breaker)">{{ d.breaker }}</span></td>
                <td class="mono">{{ fmt(d.ua) }}</td><td class="mono">{{ fmt(d.ub) }}</td><td class="mono">{{ fmt(d.uc) }}</td>
                <td class="mono">{{ fmt(d.ia,0) }}</td><td class="mono">{{ fmt(d.ib,0) }}</td><td class="mono">{{ fmt(d.ic,0) }}</td>
                <td class="mono">{{ fmt(d.p) }}</td><td class="mono">{{ fmt(d.q) }}</td>
                <td class="mono" :class="pfCls(d.pf)">{{ fmt(d.pf,3) }}</td>
                <td class="mono">{{ fmt(d.freq) }}</td>
                <td class="mono">{{ fmtEnergy(d.energy) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card scroll-x">
          <div class="card-head">
            <span class="ct">{{ tl('10KV 出线/馈线监测') }}</span>
            <span class="pill" :class="feederAllClosed ? 'g' : 'a'">{{ s.feeders.length }} {{ tl('路') }} · {{ tl('合闸') }} {{ feederClosedCount }}/{{ s.feeders.length }}</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>{{ tl('馈线') }}</th><th>{{ tl('负荷') }}</th><th>{{ tl('开关') }}</th>
                <th>Ua</th><th>Ub</th><th>Uc</th><th>I(A)</th><th>P(MW)</th><th>PF</th><th>E(kWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in s.feeders" :key="d.id">
                <td class="d-name">{{ d.id }}</td>
                <td class="muted">{{ d.load }}</td>
                <td><span class="tag" :class="breakerCls(d.breaker)">{{ d.breaker }}</span></td>
                <td class="mono">{{ fmt(d.ua) }}</td><td class="mono">{{ fmt(d.ub) }}</td><td class="mono">{{ fmt(d.uc) }}</td>
                <td class="mono">{{ fmt(d.i,0) }}</td>
                <td class="mono">{{ fmt(d.p) }}</td>
                <td class="mono" :class="pfCls(d.pf)">{{ fmt(d.pf,3) }}</td>
                <td class="mono">{{ fmtEnergy(d.energy) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ======== 3.1.4 电能质量: 谐波柱状图 + 功率因数趋势 ======== -->
      <div class="grid cols-2">
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('谐波电压含有率') }} (THD / 各次)</span>
            <span class="pill" :class="(s.quality?.thdU ?? 0) > 3 ? 'a' : 'g'">THD-U {{ fmt(s.quality?.thdU) }}%</span>
          </div>
          <TrendChart
            :title="''"
            :x-axis-data="harmonicLabels"
            :series="[{ name: tl('谐波含有率'), type: 'bar' as const, data: harmonicData, color: '#22d3ee', barWidth: '55%' }]"
            :height="220"
          />
        </div>
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('功率因数趋势') }} (24h)</span>
          </div>
          <TrendChart
            :title="''"
            :x-axis-data="pfTrend.labels"
            :series="pfTrend.series"
            :height="220"
          />
        </div>
      </div>

      <!-- ======== 3.1.5 实时告警列表 (AlarmBadge) ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('实时告警') }}</span>
          <span v-if="!alarms.length" class="pill g">{{ tl('无活动告警') }}</span>
          <span v-else class="pill a">{{ alarms.length }} {{ tl('条') }}</span>
        </div>
        <div v-if="!alarms.length" class="empty-tip muted">{{ tl('当前无过压/欠压/过流/温度等越限告警') }}</div>
        <div v-else class="alarm-list">
          <div v-for="(a, ai) in alarms" :key="ai" class="alarm-row" :class="a.level">
            <AlarmBadge :level="a.level" />
            <span class="a-ts mono">{{ a.time }}</span>
            <span class="a-src">{{ a.source }}</span>
            <span class="a-msg">{{ a.message }}</span>
            <span class="a-val mono">{{ a.value }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 3.1.6 历史事件查询表 (保护动作/跳闸) ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('历史事件') }} · {{ tl('保护动作 / 跳闸记录') }}</span>
          <span class="pill">{{ events.length }} {{ tl('条') }}</span>
        </div>
        <div class="port-table scroll-x">
          <table>
            <thead>
              <tr>
                <th style="width:140px">{{ tl('时间') }}</th>
                <th>{{ tl('设备') }}</th>
                <th>{{ tl('事件类型') }}</th>
                <th>{{ tl('保护元件') }}</th>
                <th>{{ tl('描述') }}</th>
                <th style="width:70px">{{ tl('动作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, ei) in events" :key="ei">
                <td class="mono">{{ e.time }}</td>
                <td class="d-name">{{ e.device }}</td>
                <td><span class="tag" :class="e.type === 'trip' ? 'r' : e.type === 'action' ? 'a' : 'b'">{{ e.typeText }}</span></td>
                <td class="muted">{{ e.element }}</td>
                <td class="muted">{{ e.desc }}</td>
                <td><span class="tag" :class="e.acted ? 'r' : 'g'">{{ e.acted ? tl('动作') : tl('告警') }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ======== 配电变压器 / 母线 / 直流屏 概要 ======== -->
      <div class="grid cols-3" v-if="s.transformers?.length">
        <div class="card col-span-2">
          <div class="card-head">
            <span class="ct">{{ tl('10KV/0.4KV 配电变压器') }}</span>
            <span class="pill" :class="txAllRunning ? 'g' : 'a'">{{ s.transformers.length }} {{ tl('台') }} · {{ txRunningCount }} {{ tl('运行') }}</span>
          </div>
          <div class="tx-grid">
            <div class="tx-block" v-for="t in s.transformers" :key="t.id">
              <div class="tx-head">
                <span class="d-status" :class="txStateCls(t.state)">●</span>
                <span class="d-name">{{ t.id }}</span>
                <span class="d-code muted">{{ t.feeder }}</span>
                <span class="tag" :class="txStateTagCls(t.state)">{{ t.state }}</span>
              </div>
              <div class="tx-mini-grid">
                <div class="tx-mini"><span class="k">{{ tl('负载率') }}</span><span class="v mono" :class="loadCls(t.load)">{{ t.load }}%</span></div>
                <div class="tx-mini"><span class="k">{{ tl('绕组温度') }}</span><span class="v mono" :class="tempCls(t.windingT, 85, 95)">{{ t.windingT }}°C</span></div>
                <div class="tx-mini"><span class="k">{{ tl('油温') }}</span><span class="v mono" :class="tempCls(t.oilT, 75, 85)">{{ t.oilT }}°C</span></div>
                <div class="tx-mini"><span class="k">{{ tl('环境温度') }}</span><span class="v mono">{{ t.ambT }}°C</span></div>
                <div class="tx-mini"><span class="k">{{ tl('湿度') }}</span><span class="v mono" :class="humCls(t.humidity)">{{ t.humidity }}%RH</span></div>
                <div class="tx-mini"><span class="k">{{ tl('高压侧') }}</span><span class="v mono">{{ fmt(t.uHigh) }}kV / {{ fmt(t.iHigh,0) }}A</span></div>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('母线段电压') }}</span>
            <span class="pill g">{{ s.busSections?.length || 0 }} {{ tl('段带电') }}</span>
          </div>
          <div class="bus-grid">
            <div class="bus-item" v-for="b in s.busSections" :key="b.id">
              <span class="bus-label">{{ b.id }}</span>
              <span class="bus-val" :class="busStateCls(b.state)">{{ fmt(b.u) }} <small>kV</small></span>
              <span class="bus-sub mono">{{ fmt(b.freq) }} Hz · {{ b.state }}</span>
            </div>
          </div>
          <div class="mt10" v-if="s.dcPanel">
            <div class="kv"><span class="k">{{ tl('直流屏') }} {{ s.dcPanel.id }}</span><span class="v">{{ s.dcPanel.state }}</span></div>
            <div class="kv"><span class="k">DC {{ tl('母线') }}</span><span class="v mono">{{ s.dcPanel.dcBus }}V / {{ tl('目标') }} {{ s.dcPanel.dcBusTarget }}V</span></div>
          </div>
        </div>
      </div>

      <!-- ======== 微机保护装置 ======== -->
      <div class="card scroll-x" v-if="s.protectionRelays?.length">
        <div class="card-head">
          <span class="ct">{{ tl('微机保护装置') }} (REF615/611)</span>
          <span class="pill" :class="relayAllComm ? 'g' : 'a'">{{ s.protectionRelays.length }} {{ tl('套') }} · {{ tl('通讯正常') }} {{ relayCommCount }}/{{ s.protectionRelays.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('装置') }}</th><th>{{ tl('被保护设备') }}</th><th>{{ tl('状态') }}</th>
              <th>{{ tl('过流') }}</th><th>{{ tl('接地') }}</th><th>{{ tl('差动') }}</th>
              <th>{{ tl('欠压') }}</th><th>{{ tl('过压') }}</th><th>{{ tl('频率') }}</th>
              <th>{{ tl('通讯') }}</th><th>{{ tl('最近动作') }}</th><th>{{ tl('动作次数') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in s.protectionRelays" :key="r.id">
              <td class="d-name">{{ r.id }}</td>
              <td class="muted">{{ r.device }}</td>
              <td><span class="tag" :class="r.state === '运行' ? 'g' : 'b'">{{ r.state }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.overcurrent)">{{ r.overcurrent }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.earthFault)">{{ r.earthFault }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.diff)">{{ r.diff }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.underVoltage)">{{ r.underVoltage }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.overVoltage)">{{ r.overVoltage }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.freq)">{{ r.freq }}</span></td>
              <td><span class="tag" :class="r.comm === '正常' ? 'g' : 'r'">{{ r.comm }}</span></td>
              <td class="muted mono" :class="r.tripCount > 0 ? 'a' : ''" style="font-size:11px">{{ r.lastTrip }}</td>
              <td class="mono" :class="r.tripCount > 0 ? 'a' : ''">{{ r.tripCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import KpiCard from '@/components/monitor/KpiCard.vue'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import AlarmBadge from '@/components/monitor/AlarmBadge.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'
import { getPowerHvDetailed, type HvSummary, type HvIncomerView, type HvFeederView } from '@/api/power'
const { t: tl } = useI18n()

// ──────────────────────────────────────────
// SVG 一次图几何
// ──────────────────────────────────────────
const SVG_W = 1000
const SVG_H = 440
const BUS_H = 14
const BUS_A = { x: 250, y: 120, w: 230 }
const BUS_B = { x: 520, y: 120, w: 230 }
const IN1 = { x: 330, y: 40 }
const IN2 = { x: 670, y: 40 }
const BR_W = 56
const BR_H = 26
const ratedI = 1250
const ratedP = 18

interface BreakerNode {
  id: string
  code: string
  label: string
  breaker: string
  x: number
  y: number
  busY?: number
  load?: string
  kvs: { k: string; v: string; cls?: string }[]
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = ref<HvSummary | null>(null)
const selectedNode = ref<BreakerNode | null>(null)

// ──────────────────────────────────────────
// Derived: 一次图节点
// ──────────────────────────────────────────
const incomerBreakers = computed<BreakerNode[]>(() => {
  const list = s.value?.incomers ?? []
  return list.map((d, i) => ({
    id: d.id, code: 'Q' + (i + 1), label: d.id + ' ' + tl('进线断路器'), breaker: d.breaker,
    x: i === 0 ? IN1.x : IN2.x, y: (i === 0 ? IN1.y : IN2.y) + 36,
    kvs: [
      { k: tl('电源'), v: d.src },
      { k: tl('开关状态'), v: d.breaker, cls: breakerCls(d.breaker) },
      { k: 'Ua/Ub/Uc', v: `${fmt(d.ua)}/${fmt(d.ub)}/${fmt(d.uc)} kV` },
      { k: 'Ia/Ib/Ic', v: `${fmt(d.ia,0)}/${fmt(d.ib,0)}/${fmt(d.ic,0)} A` },
      { k: 'P / Q', v: `${fmt(d.p)} MW / ${fmt(d.q)} MVar` },
      { k: 'PF', v: fmt(d.pf, 3), cls: pfCls(d.pf) },
      { k: 'f', v: fmt(d.freq) + ' Hz' },
      { k: 'E', v: fmtEnergy(d.energy) + ' kWh' },
    ],
  }))
})

const busTieNode = computed<BreakerNode>(() => {
  const bt = s.value?.busTie
  return {
    id: bt?.id ?? 'QB', code: 'QB', label: tl('母联断路器'), breaker: bt?.state ?? '',
    x: (BUS_A.x + BUS_A.w + BUS_B.x) / 2, y: BUS_A.y + BUS_H / 2,
    kvs: [
      { k: tl('开关状态'), v: bt?.state ?? '-', cls: breakerCls(bt?.state ?? '') },
      { k: tl('备自投'), v: bt?.autoSwitch ?? '-' },
      { k: tl('模式'), v: bt?.mode ?? '-' },
      { k: tl('额定电流'), v: (bt?.iRated ?? 0) + ' A' },
      { k: tl('当前电流'), v: (bt?.i ?? 0) + ' A' },
    ],
  }
})

const feederNodes = computed<BreakerNode[]>(() => {
  const list = s.value?.feeders ?? []
  const span = BUS_A.w + (BUS_B.x - BUS_A.x)
  const startX = BUS_A.x
  const step = span / Math.max(1, list.length)
  return list.map((d, i) => {
    const x = Math.round(startX + step * (i + 0.5))
    const onA = x < (BUS_A.x + BUS_A.w + BUS_B.x) / 2
    const busY = onA ? BUS_A.y + BUS_H : BUS_B.y + BUS_H
    return {
      id: d.id, code: 'F' + (i + 1), label: d.id + ' ' + tl('馈线断路器'), breaker: d.breaker,
      x, y: busY + 60, busY, load: d.load,
      kvs: [
        { k: tl('负荷'), v: d.load ?? '-' },
        { k: tl('开关状态'), v: d.breaker, cls: breakerCls(d.breaker) },
        { k: 'Ua/Ub/Uc', v: `${fmt(d.ua)}/${fmt(d.ub)}/${fmt(d.uc)} kV` },
        { k: 'I', v: fmt(d.i, 0) + ' A' },
        { k: 'P', v: fmt(d.p) + ' MW' },
        { k: 'PF', v: fmt(d.pf, 3), cls: pfCls(d.pf) },
        { k: 'E', v: fmtEnergy(d.energy) + ' kWh' },
      ],
    }
  })
})

function selectNode(n: BreakerNode) {
  selectedNode.value = n
}

// ──────────────────────────────────────────
// 3.1.3 主导进线 (取 #1 进线)
// ──────────────────────────────────────────
const primaryIncomer = computed<HvIncomerView | null>(() => s.value?.incomers?.[0] ?? null)
const lineVoltage = computed(() => {
  const d = primaryIncomer.value
  if (!d) return 0
  // 线电压近似 = 相电压均值 × √3
  const uph = (d.ua + d.ub + d.uc) / 3
  return Number((uph * Math.sqrt(3)).toFixed(2))
})

// ──────────────────────────────────────────
// 3.1.4 电能质量
// ──────────────────────────────────────────
const harmonicLabels = ['3', '5', '7', '9', '11', '13', '15', '17', '19', '21', '23', '25']
// 基于 THD-U 派生各次含有率 (演示, 真实应从 API 取)
const harmonicData = computed<number[]>(() => {
  const thd = s.value?.quality?.thdU ?? 2.5
  const base = [1.6, 1.2, 0.9, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.12, 0.1]
  return base.map((v) => Number((v * Math.min(2, thd / 2.5)).toFixed(2)))
})

function genHours(n: number): string[] {
  const now = new Date()
  const hrs: string[] = []
  for (let i = n - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 3600 * 1000)
    hrs.push(t.getHours().toString().padStart(2, '0') + ':' + t.getMinutes().toString().padStart(2, '0'))
  }
  return hrs
}
function genPf(n: number, base: number, noise: number): number[] {
  return Array.from({ length: n }, (_, i) =>
    Number((base + Math.sin((i / n) * Math.PI * 2) * 0.02 + (Math.random() - 0.5) * noise).toFixed(3)),
  )
}
const pfTrend = reactive({
  labels: genHours(24),
  series: [{ name: tl('功率因数'), type: 'line' as const, data: genPf(24, 0.97, 0.02), color: '#22c55e' }],
})

// ──────────────────────────────────────────
// 3.1.5 实时告警 (从越限逻辑派生)
// ──────────────────────────────────────────
const alarms = computed(() => {
  const out: { level: string; time: string; source: string; message: string; value: string }[] = []
  const now = new Date()
  const ts = (m: number) => {
    const d = new Date(now.getTime() - m * 60000)
    return d.toTimeString().slice(0, 8)
  }
  const inc = s.value?.incomers ?? []
  inc.forEach((d, i) => {
    const uph = (d.ua + d.ub + d.uc) / 3
    if (uph > 10.7 || uph < 9.3) {
      out.push({ level: 'major', time: ts(2 + i), source: d.id, message: tl('母线电压越限'), value: uph.toFixed(2) + 'kV' })
    }
    if (d.pf < 0.9) {
      out.push({ level: 'warning', time: ts(5 + i), source: d.id, message: tl('功率因数偏低'), value: d.pf.toFixed(3) })
    }
    if (d.freq < 49.5 || d.freq > 50.5) {
      out.push({ level: 'major', time: ts(1 + i), source: d.id, message: tl('系统频率异常'), value: d.freq.toFixed(2) + 'Hz' })
    }
  })
  ;(s.value?.feeders ?? []).forEach((f, i) => {
    if (f.pf < 0.85) {
      out.push({ level: 'warning', time: ts(8 + i), source: f.id, message: tl('馈线功率因数低'), value: f.pf.toFixed(3) })
    }
  })
  ;(s.value?.transformers ?? []).forEach((t, i) => {
    if (t.windingT >= 95) out.push({ level: 'critical', time: ts(3 + i), source: t.id, message: tl('绕组温度高报警'), value: t.windingT + '°C' })
    else if (t.windingT >= 85) out.push({ level: 'warning', time: ts(4 + i), source: t.id, message: tl('绕组温度偏高'), value: t.windingT + '°C' })
    if (t.load >= 90) out.push({ level: 'warning', time: ts(6 + i), source: t.id, message: tl('变压器负载率过高'), value: t.load + '%' })
  })
  const thd = s.value?.quality?.thdU ?? 0
  if (thd > 3) out.push({ level: 'warning', time: ts(7), source: tl('10KV 母线'), message: tl('电压谐波 THD-U 超标'), value: thd.toFixed(2) + '%' })
  ;(s.value?.protectionRelays ?? []).forEach((r) => {
    if (r.tripCount > 0) out.push({ level: 'critical', time: r.lastTrip, source: r.id, message: tl('保护动作跳闸'), value: tl('动作') + ' ' + r.tripCount + tl('次') })
  })
  return out.slice(0, 12)
})

// ──────────────────────────────────────────
// 3.1.6 历史事件 (保护动作/跳闸)
// ──────────────────────────────────────────
const events = computed(() => {
  const out: { time: string; device: string; type: string; typeText: string; element: string; desc: string; acted: boolean }[] = []
  ;(s.value?.protectionRelays ?? []).forEach((r) => {
    if (r.lastTrip && r.lastTrip !== '-' && r.tripCount > 0) {
      out.push({ time: r.lastTrip, device: r.device, type: 'trip', typeText: tl('跳闸'), element: r.id, desc: tl('过流保护动作，断路器跳闸'), acted: true })
    } else {
      out.push({ time: r.lastTrip || '-', device: r.device, type: 'action', typeText: tl('保护动作'), element: r.id, desc: tl('保护功能投入，未发生跳闸'), acted: false })
    }
  })
  // 补充典型历史事件 (演示)
  if (s.value) {
    out.push({ time: '08-02 03:14:22', device: s.value.incomers[0]?.id ?? 'IN1', type: 'action', typeText: tl('备自投'), element: s.value.busTie?.id ?? 'QB', desc: tl('Ⅰ段失电，母联自投成功，Ⅱ段带全站负荷'), acted: false })
    out.push({ time: '07-31 22:48:05', device: s.value.feeders[0]?.id ?? 'F1', type: 'trip', typeText: tl('跳闸'), element: '50/51', desc: tl('馈线速断保护动作，排查电缆接地'), acted: true })
  }
  return out.sort((a, b) => (a.time < b.time ? 1 : -1))
})

// ──────────────────────────────────────────
// 统计
// ──────────────────────────────────────────
const incomerClosedCount = computed(() => (s.value?.incomers ?? []).filter((d) => isClosed(d.breaker)).length)
const incomerAllClosed = computed(() => {
  const l = s.value?.incomers ?? []
  return l.length > 0 && incomerClosedCount.value === l.length
})
const feederClosedCount = computed(() => (s.value?.feeders ?? []).filter((d) => isClosed(d.breaker)).length)
const feederAllClosed = computed(() => {
  const l = s.value?.feeders ?? []
  return l.length > 0 && feederClosedCount.value === l.length
})
const txRunningCount = computed(() => (s.value?.transformers ?? []).filter((t) => t.state === '运行').length)
const txAllRunning = computed(() => {
  const l = s.value?.transformers ?? []
  return l.length > 0 && txRunningCount.value === l.length
})
const relayCommCount = computed(() => (s.value?.protectionRelays ?? []).filter((r) => r.comm === '正常').length)
const relayAllComm = computed(() => {
  const l = s.value?.protectionRelays ?? []
  return l.length > 0 && relayCommCount.value === l.length
})

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function isClosed(v?: string): boolean {
  const t = String(v ?? '').trim()
  return t.includes('合闸') || (t.includes('合') && !t.includes('分'))
}
function fmt(v: number | undefined | null, dp = 2): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Number(v).toFixed(dp)
}
function fmtEnergy(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Math.round(v).toLocaleString()
}
function breakerCls(v: string): string {
  const t = String(v ?? '').trim()
  if (isClosed(t)) return 'g'
  if (t.includes('分')) return 'r'
  if (t.includes('检修') || t.includes('备用') || t.includes('热备')) return 'b'
  return 'a'
}
function pfCls(pf: number): string {
  if (pf >= 0.95) return 'g-text'
  if (pf >= 0.9) return 'a-text'
  return 'r-text'
}
function freqStatus(f: number): 'normal' | 'warning' | 'danger' {
  if (f < 49.5 || f > 50.5) return 'danger'
  if (f < 49.8 || f > 50.2) return 'warning'
  return 'normal'
}
function txStateCls(st: string): string {
  if (st === '运行') return 'g'
  if (st.includes('故障') || st.includes('停机')) return 'r'
  if (st.includes('预警') || st.includes('异常')) return 'a'
  return 'm'
}
function txStateTagCls(st: string): string {
  if (st === '运行') return 'g'
  if (st.includes('故障') || st.includes('停机')) return 'r'
  if (st.includes('预警') || st.includes('异常')) return 'a'
  return 'b'
}
function tempCls(t: number, warn: number, alarm: number): string {
  if (t >= alarm) return 'r-text'
  if (t >= warn) return 'a-text'
  return 'g-text'
}
function loadCls(load: number): string {
  if (load >= 90) return 'r-text'
  if (load >= 80) return 'a-text'
  return 'g-text'
}
function humCls(h: number): string {
  if (h > 70 || h < 20) return 'a-text'
  return 'g-text'
}
function busStateCls(state: string): string {
  if (state === '带电' || state === '运行') return 'g-text'
  if (state.includes('失电')) return 'r-text'
  return 'a-text'
}
function relayFuncCls(v: string): string {
  return v === '投入' ? 'g' : 'b'
}

// ──────────────────────────────────────────
// Mock fallback (当 API 无数据)
// ──────────────────────────────────────────
function mockSummary(): HvSummary {
  const incomers: HvIncomerView[] = [
    { id: 'IN1', src: '市政电源 1#', state: '运行', breaker: '合闸', ua: 5.78, ub: 5.81, uc: 5.79, u: 10.03, ia: 642, ib: 638, ic: 645, i: 642, p: 11.2, q: 3.1, pf: 0.965, freq: 50.02, energy: 18452300 },
    { id: 'IN2', src: '市政电源 2#', state: '运行', breaker: '合闸', ua: 5.80, ub: 5.77, uc: 5.82, u: 10.05, ia: 530, ib: 533, ic: 528, i: 530, p: 9.1, q: 2.4, pf: 0.971, freq: 49.99, energy: 15098200 },
  ]
  const feeders: HvFeederView[] = [
    { id: 'F1', load: '1# 主变', state: '运行', breaker: '合闸', ua: 5.79, ub: 5.80, uc: 5.78, ia: 410, ib: 408, ic: 412, i: 410, p: 7.1, pf: 0.958, energy: 9200000 },
    { id: 'F2', load: '2# 主变', state: '运行', breaker: '合闸', ua: 5.81, ub: 5.79, uc: 5.80, ia: 388, ib: 390, ic: 386, i: 388, p: 6.7, pf: 0.962, energy: 8700000 },
    { id: 'F3', load: '冷水机组', state: '运行', breaker: '合闸', ua: 5.77, ub: 5.78, uc: 5.79, ia: 220, ib: 218, ic: 221, i: 220, p: 3.8, pf: 0.901, energy: 4300000 },
    { id: 'F4', load: 'UPS 进线', state: '运行', breaker: '合闸', ua: 5.80, ub: 5.81, uc: 5.79, ia: 175, ib: 176, ic: 174, i: 175, p: 3.0, pf: 0.948, energy: 3100000 },
    { id: 'F5', load: '照明动力', state: '运行', breaker: '分闸', ua: 5.80, ub: 5.80, uc: 5.80, ia: 0, ib: 0, ic: 0, i: 0, p: 0, pf: 1.0, energy: 1200000 },
    { id: 'F6', load: '备用回路', state: '备用', breaker: '分闸', ua: 5.80, ub: 5.80, uc: 5.80, ia: 0, ib: 0, ic: 0, i: 0, p: 0, pf: 1.0, energy: 0 },
  ]
  const transformers = [
    { id: 'T1', feeder: 'F1', state: '运行', load: 62, uHigh: 10.02, iHigh: 408, uLow: 0.398, iLow: 10320, windingT: 68, oilT: 59, ambT: 28, humidity: 45, tap: 3, fan: '运行', signals: [] },
    { id: 'T2', feeder: 'F2', state: '运行', load: 58, uHigh: 10.04, iHigh: 386, uLow: 0.399, iLow: 9680, windingT: 64, oilT: 56, ambT: 28, humidity: 44, tap: 3, fan: '运行', signals: [] },
  ]
  return {
    scheme: tl('两路市电 + 母联备自投'),
    incomers,
    busTie: { id: 'QB', state: '分闸', autoSwitch: tl('投入'), mode: tl('自投自复'), iRated: 2500, i: 0 },
    busSections: [
      { id: 'Ⅰ段', u: 10.03, freq: 50.02, state: '带电' },
      { id: 'Ⅱ段', u: 10.05, freq: 49.99, state: '带电' },
    ],
    ats: { logic: tl('Ⅰ段失电经延时跳 Q1、合 QB 由Ⅱ段带全站负荷'), lastTest: '2026-07-20', switchTime: '<2s' },
    feeders,
    transformers,
    dcPanel: { id: 'DC1', dcBus: 220, dcBusTarget: 220, batteryBank: 234, chargeI: 12, dischargeI: 0, insulationR: 42, ripple: 0.8, state: tl('浮充'), alarms: [] },
    switchgearEnv: { rows: [], note: '' },
    protectionRelays: [
      { id: 'P1', device: 'IN1', state: '运行', overcurrent: '投入', earthFault: '投入', diff: '投入', underVoltage: '投入', overVoltage: '投入', freq: '投入', lastTrip: '2026-07-31 22:48', tripCount: 0, comm: '正常' },
      { id: 'P2', device: 'IN2', state: '运行', overcurrent: '投入', earthFault: '投入', diff: '投入', underVoltage: '投入', overVoltage: '投入', freq: '投入', lastTrip: '-', tripCount: 0, comm: '正常' },
      { id: 'P3', device: 'T1', state: '运行', overcurrent: '投入', earthFault: '投入', diff: '投入', underVoltage: '投入', overVoltage: '投入', freq: '投入', lastTrip: '-', tripCount: 0, comm: '正常' },
    ],
    arcSuppression: { mode: tl('过补偿'), coilCurrent: 28, coilPosition: 7, neutralV: 320, earthCapacitance: 35, residualCurrent: 4, state: tl('运行'), groundingTx: { id: 'ZT1', state: '运行', t: 52, i: 12 } },
    metering: {
      incomer1: { energyTotal: 18452300, energyPeak: 7200000, energyValley: 3100000, energyFlat: 8152300, demand: 12.4, demandMax: 14.8 },
      incomer2: { energyTotal: 15098200, energyPeak: 6000000, energyValley: 2500000, energyFlat: 6598200, demand: 10.1, demandMax: 12.0 },
    },
    quality: { thdU: 2.4, thdI: 4.1, unbalance: 1.3, incomer1: { thdU: 2.3, thdI: 4.0, unbalance: 1.2, flicker: 0.7 }, incomer2: { thdU: 2.5, thdI: 4.2, unbalance: 1.4, flicker: 0.8 } },
    knowledge: { thresholds: [] },
    total: 10, online: 9, avgLoadPercent: 60, avgVoltage: 10040, avgCurrent: 572, devices: [],
  }
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getPowerHvDetailed()
    if (data && (data.incomers?.length || data.feeders?.length)) {
      s.value = data
    } else {
      s.value = mockSummary()
    }
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
/* ── view-head ── */
.view-head { margin-bottom: 16px; }
.view-head h1 { font-size: 1.25rem; font-weight: 700; color: var(--text-primary, #e5e7eb); margin: 0; }
.view-head .sub { font-size: 0.75rem; color: var(--text-muted, #6b7280); margin-top: 2px; display: block; }

/* ── grid ── */
.grid { display: grid; gap: 14px; margin-bottom: 14px; }
.grid.cols-6 { grid-template-columns: repeat(6, 1fr); }
.grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
.col-span-2 { grid-column: span 2; }

/* ── card ── */
.card { background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 10px; padding: 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.ct { font-size: 0.875rem; font-weight: 600; color: var(--text-primary, #e5e7eb); }

/* pill */
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 99px; font-size: 0.6875rem; font-weight: 600; line-height: 1.5; }
.pill.g { background: rgba(34, 197, 94, 0.12); color: #22c55e; }
.pill.a { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }

/* ── SVG 一次图 ── */
.schematic-wrap { background: rgba(15, 23, 42, 0.5); border-radius: 8px; padding: 8px; }
.hv-svg { width: 100%; height: auto; display: block; }
.bus { fill: #22d3ee; opacity: 0.85; }
.bus-label { fill: var(--text-muted, #94a3b8); font-size: 11px; text-anchor: middle; }
.feeder-line line { stroke: #475569; stroke-width: 2; }
.source-box { fill: #1e3a5f; stroke: #22d3ee; stroke-width: 1; }
.src-text { fill: #cbd5e1; font-size: 11px; text-anchor: middle; }
.breaker-node { cursor: pointer; }
.breaker-rect { stroke-width: 1.5; transition: filter 0.2s; }
.breaker-node:hover .breaker-rect { filter: drop-shadow(0 0 6px rgba(34,211,255,0.7)); }
.breaker-rect.g { fill: rgba(34, 197, 94, 0.25); stroke: #22c55e; }
.breaker-rect.r { fill: rgba(239, 68, 68, 0.25); stroke: #ef4444; }
.breaker-rect.b { fill: rgba(59, 130, 246, 0.2); stroke: #3b82f6; }
.breaker-rect.a { fill: rgba(245, 158, 11, 0.2); stroke: #f59e0b; }
.breaker-text { fill: #e5e7eb; font-size: 11px; text-anchor: middle; font-weight: 600; pointer-events: none; }
.bus-tie-label { fill: #f59e0b; font-size: 9px; text-anchor: middle; }
.feeder-load { fill: var(--text-muted, #94a3b8); font-size: 9px; text-anchor: middle; }
.legend { display: flex; align-items: center; gap: 12px; font-size: 11px; }
.lg { display: inline-flex; align-items: center; gap: 4px; color: var(--text-muted, #94a3b8); }
.lg .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.g { background: #22c55e; } .dot.r { background: #ef4444; } .dot.b { background: #3b82f6; }

/* 节点详情 */
.node-detail { margin-top: 12px; border: 1px solid var(--border, #334155); border-radius: 8px; padding: 12px 14px; background: rgba(30, 41, 59, 0.5); }
.nd-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.nd-code { font-family: monospace; font-weight: 700; font-size: 13px; padding: 1px 8px; border-radius: 5px; }
.nd-code.g { color: #22c55e; background: rgba(34,197,94,0.12); }
.nd-code.r { color: #ef4444; background: rgba(239,68,68,0.12); }
.nd-code.b { color: #3b82f6; background: rgba(59,130,246,0.12); }
.nd-code.a { color: #f59e0b; background: rgba(245,158,11,0.12); }
.nd-title { font-size: 13px; font-weight: 600; color: var(--text-primary, #e5e7eb); }
.nd-close { margin-left: auto; background: none; border: none; color: var(--text-muted, #94a3b8); font-size: 18px; cursor: pointer; line-height: 1; }
.nd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px 18px; }
.nd-kv { display: flex; justify-content: space-between; gap: 8px; padding: 4px 0; border-bottom: 1px dotted rgba(51,65,85,0.5); }
.nd-k { font-size: 11px; color: var(--text-muted, #94a3b8); }
.nd-v { font-size: 12px; color: var(--text-secondary, #94a3b8); font-weight: 500; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── table ── */
table { width: 100%; border-collapse: collapse; font-size: 0.75rem; }
th { text-align: left; color: var(--text-muted, #6b7280); font-weight: 600; font-size: 10px; letter-spacing: .4px; padding: 7px 8px; border-bottom: 1px solid var(--border, #334155); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid rgba(51, 65, 85, 0.5); color: var(--text-secondary, #94a3b8); white-space: nowrap; }
tbody tr:hover { background: rgba(255, 255, 255, 0.03); }
.d-name { font-weight: 500; color: var(--text-primary, #e5e7eb); }
.mono { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }
.muted { color: var(--text-muted, #6b7280); }

/* tag */
.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--border, #334155); white-space: nowrap; }
.tag.g { color: #22c55e; border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: #f59e0b; border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: #ef4444; border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: #3b82f6; border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* text color */
.g-text { color: #22c55e; } .a-text { color: #f59e0b; } .r-text { color: #ef4444; }

/* ── 告警列表 ── */
.alarm-list { display: flex; flex-direction: column; gap: 6px; }
.alarm-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 6px; background: rgba(30,41,59,0.5); border-left: 3px solid transparent; }
.alarm-row.major { border-left-color: #f59e0b; }
.alarm-row.critical { border-left-color: #ef4444; }
.alarm-row.warning { border-left-color: #eab308; }
.a-ts { font-size: 11px; color: var(--text-muted, #94a3b8); }
.a-src { font-size: 12px; font-weight: 600; color: var(--text-primary, #e5e7eb); min-width: 80px; }
.a-msg { font-size: 12px; color: var(--text-secondary, #94a3b8); flex: 1; }
.a-val { font-size: 11px; color: #f59e0b; }

/* ── 变压器 ── */
.tx-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.tx-block { border: 1px solid rgba(51,65,85,0.6); border-radius: 8px; padding: 10px 12px; background: rgba(30,41,59,0.4); }
.tx-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.d-status { font-size: 8px; } .d-status.g { color: #22c55e; } .d-status.r { color: #ef4444; } .d-status.a { color: #f59e0b; } .d-status.m { color: var(--text-muted, #94a3b8); }
.d-code { font-size: 11px; }
.tx-head .tag { margin-left: auto; }
.tx-mini-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 12px; }
.tx-mini { display: flex; flex-direction: column; gap: 1px; padding: 4px 0; }
.tx-mini .k { font-size: 10px; color: var(--text-muted, #94a3b8); }
.tx-mini .v { font-size: 12px; font-weight: 600; }

/* ── 母线段 ── */
.bus-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.bus-item { text-align: center; padding: 10px 6px; border-radius: 6px; background: rgba(30,41,59,0.6); }
.bus-label { display: block; font-size: 11px; color: var(--text-muted, #94a3b8); margin-bottom: 4px; }
.bus-val { display: block; font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.bus-val small { font-size: 11px; color: var(--text-muted, #94a3b8); font-weight: 500; }
.bus-sub { display: block; font-size: 10px; color: var(--text-muted, #94a3b8); margin-top: 3px; }
.mt10 { margin-top: 10px; }
.kv { display: flex; justify-content: space-between; gap: 8px; padding: 4px 0; border-bottom: 1px dashed rgba(51,65,85,0.5); }
.k { font-size: 11px; color: var(--text-muted, #94a3b8); }
.v { font-size: 12px; color: var(--text-secondary, #94a3b8); font-weight: 600; }

/* ── port table ── */
.port-table { max-height: 320px; overflow-y: auto; }
.port-table.scroll-x { overflow-x: auto; }

/* ── error/empty ── */
.err-card { text-align: center; padding: 32px 16px; }
.err-title { font-size: 1rem; font-weight: 700; color: #ef4444; margin-bottom: 8px; }
.err-detail { font-size: 0.75rem; color: var(--text-muted, #6b7280); margin-bottom: 14px; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 18px; border-radius: 6px; border: 1px solid var(--border, #334155); background: transparent; color: var(--text-primary, #e5e7eb); font-size: 0.75rem; cursor: pointer; }
.btn:hover { background: rgba(255,255,255,0.05); }
.empty-tip { text-align: center; padding: 20px; font-size: 12px; }

/* ── responsive ── */
@media (max-width: 1280px) {
  .grid.cols-6 { grid-template-columns: repeat(3, 1fr); }
  .grid.cols-4 { grid-template-columns: repeat(2, 1fr); }
  .grid.cols-3 { grid-template-columns: 1fr; }
  .col-span-2 { grid-column: span 1; }
  .tx-grid { grid-template-columns: 1fr; }
}
@media (max-width: 860px) {
  .grid.cols-6, .grid.cols-2 { grid-template-columns: 1fr; }
}
</style>
