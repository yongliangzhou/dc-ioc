<template>
  <div class="linkage-view">
    <div class="view-head">
      <div>
        <h1>{{ tl('配电链路可视化') }}</h1>
        <span class="sub">{{ tl('端到端') }} · {{ tl('市电进线 → 中压 → 变压器 → 低压 → UPS → 机柜负载') }}</span>
      </div>
      <div class="head-actions">
        <span class="live" :class="{ on: liveOn }">
          <i class="live-dot" /> {{ liveOn ? tl('实时刷新中') : tl('已暂停') }}
        </span>
        <button class="refresh" @click="toggleLive">{{ liveOn ? tl('暂停') : tl('开启实时') }}</button>
        <button class="refresh" @click="() => load()" :disabled="loading">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          {{ tl('刷新') }}
        </button>
      </div>
    </div>

    <AsyncSection :loading="loading" :error="error" :empty="false" @retry="() => load()" :min-height="'360px'">
    <!-- 概览 KPI -->
    <div class="kpi-row">
      <div class="kpi"><span class="k-label">{{ tl('链路节点') }}</span><span class="k-val">{{ nodes.length }}</span></div>
      <div class="kpi"><span class="k-label">{{ tl('告警节点') }}</span><span class="k-val warn">{{ alarmNodeCount }}</span></div>
      <div class="kpi"><span class="k-label">{{ tl('总负载') }}</span><span class="k-val">{{ totalLoad }}%</span></div>
      <div class="kpi"><span class="k-label">{{ tl('平均电压') }}</span><span class="k-val">{{ avgVoltage }}kV</span></div>
      <div class="kpi"><span class="k-label">{{ tl('平均电流') }}</span><span class="k-val">{{ avgCurrent }}A</span></div>
      <div class="kpi"><span class="k-label">{{ tl('活动告警') }}</span><span class="k-val" :class="activeAlarms.length ? 'warn' : ''">{{ activeAlarms.length }}</span></div>
    </div>

    <!-- 主体分屏 -->
    <div class="main-grid">
      <!-- 拓扑图 -->
      <Panel class="topo-panel" :title="tl('配电链路拓扑')">
        <template #extra>
          <div class="legend">
            <span><i class="dot normal" /> {{ tl('正常') }}</span>
            <span><i class="dot warning" /> {{ tl('预警') }}</span>
            <span><i class="dot fault" /> {{ tl('故障') }}</span>
            <span><i class="dot off" /> {{ tl('失电/离线') }}</span>
          </div>
        </template>
        <div class="topo-wrap">
          <PowerLinkageDiagram
            ref="diagramRef"
            :nodes="nodes"
            :links="links"
            :groups="groups"
            :selected-id="selected?.id"
            @node-click="onNodeClick"
          />
        </div>
      </Panel>

      <!-- 详情 / 趋势 -->
      <div class="side-col">
        <!-- 节点详情 -->
        <Panel class="detail-panel" :title="selected ? selected.title : tl('节点详情')">
          <div v-if="selected" class="detail-body">
            <div class="detail-sub muted">{{ selected.sub }}</div>
            <div class="metrics-grid">
              <div v-for="m in selectedMetrics" :key="m.k" class="metric" :class="{ hot: m.hot }">
                <span class="mk">{{ m.k }}</span>
                <span class="mv">{{ m.v }}<small v-if="m.unit"> {{ m.unit }}</small></span>
              </div>
            </div>
            <div class="alarm-list" v-if="nodeAlarms.length">
              <div class="alarm-list-head">{{ tl('关联告警') }} ({{ nodeAlarms.length }})</div>
              <div
                v-for="(a, i) in nodeAlarms"
                :key="i"
                class="alarm-item"
                :class="'lv-' + a.level"
                @click="locateAlarm(a)"
              >
                <span class="lv">{{ levelText(a.level) }}</span>
                <span class="msg">{{ a.message }}</span>
                <span class="time">{{ a.time }}</span>
              </div>
            </div>
            <div v-else class="no-alarm">{{ tl('该节点当前无活动告警') }}</div>
          </div>
          <div v-else class="detail-empty muted">{{ tl('点击拓扑节点查看电压、电流、功率等关键参数') }}</div>
        </Panel>

        <!-- 历史趋势 -->
        <Panel class="trend-panel" :title="tl('历史数据与趋势分析')">
          <template #extra>
            <div class="range-tabs">
              <button
                v-for="r in ranges"
                :key="r.val"
                :class="{ active: range === r.val }"
                @click="range = r.val; buildTrend()"
              >{{ r.label }}</button>
            </div>
          </template>
          <div class="trend-body">
            <div class="trend-metrics">
              <button
                v-for="tm in trendMetrics"
                :key="tm.key"
                :class="{ active: trendKey === tm.key }"
                @click="trendKey = tm.key"
              >{{ tm.label }}</button>
            </div>
            <div class="chart-wrap">
              <svg :viewBox="`0 0 520 200`" class="trend-svg" preserveAspectRatio="none">
                <g class="grid">
                  <line v-for="g in 4" :key="g" :x1="40" :x2="510" :y1="20 + g * 40" :y2="20 + g * 40" />
                </g>
                <polyline
                  :points="trendPoints"
                  :class="['trend-line', trendColor]"
                  fill="none"
                />
                <polyline
                  v-if="trendArea"
                  :points="trendArea"
                  :class="['trend-area', trendColor]"
                />
                <text :x="6" :y="24" class="axis-label">{{ yMax }}</text>
                <text :x="6" :y="188" class="axis-label">{{ yMin }}</text>
                <text :x="470" :y="196" class="axis-label end">{{ rangeLabel }}</text>
              </svg>
              <div class="trend-legend">
                <span>{{ trendMetricLabel }}</span>
                <span class="now">{{ trendNow }}{{ trendUnit }}</span>
                <span class="delta" :class="trendDelta >= 0 ? 'up' : 'down'">
                  {{ trendDelta >= 0 ? '▲' : '▼' }} {{ Math.abs(trendDelta).toFixed(1) }}{{ trendUnit }}
                </span>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>

    <!-- 告警提示条 -->
    <transition name="slide-up">
      <div v-if="activeAlarms.length" class="alarm-bar" :class="'lv-' + topAlarmLevel">
        <span class="ab-icon">⚠</span>
        <span class="ab-text">
          {{ tl('配电链路异常') }} · {{ activeAlarms.length }} {{ tl('条活动告警') }}
          <template v-if="topAlarm">（{{ topAlarm.system }}：{{ topAlarm.message }}）</template>
          <span v-if="linkageError" style="color: var(--amber); margin-left: 6px;">· {{ tl('实时链路异常，数据可能过期') }}</span>
        </span>
        <button class="ab-btn" @click="goAlarms">{{ tl('前往处理') }} ›</button>
      </div>
    </transition>
    </AsyncSection>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import PowerLinkageDiagram, { LinkNode, LinkEdge, LinkGroup } from '@/components/power/PowerLinkageDiagram.vue'
import Panel from '@/components/common/Panel.vue'
import {
  getPowerHvDetailed,
  getPowerLvDetailed,
  getPowerGensetDetailed,
  getPowerBatteryDetailed,
} from '@/api/power'
import { getCabinets, getActiveAlarms } from '@/api'
import { realtimeLinkage } from '@/engine/realtimeLinkage'
import type { Alarm } from '@/types'
import { toErrorMessage } from '@/composables/useAsyncPage'
import AsyncSection from '@/components/common/AsyncSection.vue'

const { t: tl } = useI18n()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const liveOn = ref(true)
const hvData = ref<any>(null)
const lvData = ref<any>(null)
const gensetData = ref<any>(null)
const batteryData = ref<any>(null)
const cabinets = ref<any[]>([])
const alarms = ref<Alarm[]>([])
const selected = ref<LinkNode | null>(null)
const diagramRef = ref<any>(null)

let timer = 0
const SYS_HV = '中压配电'
const SYS_LV = '低压配电'
const SYS_UPS = 'UPS'
const SYS_GENS = '柴发并机'
const SYS_BATTERY = '电池监控'
const SYS_CAB = '机柜'

type Kind = 'gens' | 'mains' | 'hvbus' | 'tx' | 'lvbus' | 'ups' | 'battery' | 'cab'
type Layer = 'top' | 'mid' | 'low' | 'bottom'
const ICON: Record<Kind, string> = {
  gens: '🛢', mains: '⚡', hvbus: '🔌', tx: '🔻', lvbus: '🗲', ups: '🔋', battery: '🪫', cab: '🖥',
}
const KIND_GROUP: Record<Kind, string> = {
  gens: 'g-gens', mains: 'g-mains', hvbus: 'g-hv', tx: 'g-tx', lvbus: 'g-lv', ups: 'g-ups', battery: 'g-battery', cab: 'g-cab',
}

function statusOf(state: string): LinkNode['status'] {
  if (!state) return 'off'
  const s = String(state).toLowerCase()
  if (s.includes('fault') || s.includes('故障') || s === 'off' || s === 'offline') return 'fault'
  if (s.includes('warn') || s.includes('预警') || s === 'alarm') return 'warning'
  if (s.includes('off') || s === '断电' || s === '0') return 'off'
  return 'normal'
}
function alarmBySystem(system: string) {
  return alarms.value.filter((a) => (a.system || '').includes(system))
}
function fmtNum(v: any, d = 1) {
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(d) : String(v ?? '—')
}

// ===== 多层物理布局（按参考图：柴发左上，市电顶部，UPS/电池分居中下，机柜底部）=====
// 列：柴发(左) 市电(上左) 中压(上中) 变压器(中左) 低压(中中) UPS(中下) 电池(右中) 机柜(底部)
const POS: Record<Kind, { baseX: number; layer: Layer }> = {
  gens: { baseX: 90, layer: 'top' },
  mains: { baseX: 260, layer: 'top' },
  hvbus: { baseX: 440, layer: 'top' },
  tx: { baseX: 620, layer: 'mid' },
  lvbus: { baseX: 800, layer: 'mid' },
  ups: { baseX: 620, layer: 'low' },
  battery: { baseX: 980, layer: 'low' },
  cab: { baseX: 800, layer: 'bottom' },
}
const LAYER_Y: Record<Layer, number> = { top: 120, mid: 300, low: 470, bottom: 640 }
function rowY(index: number, total: number, layerY: number) {
  const gap = 104
  const start = layerY - ((total - 1) * gap) / 2
  return start + index * gap
}

const rawNodes = computed(() => {
  const list: Array<LinkNode & { meta: any }> = []
  const push = (n: LinkNode & { meta: any }) => list.push(n)

  // 1. 柴发（左侧橙色分组）
  const gens = gensetData.value?.units ?? []
  gens.forEach((g: any, i: number) => {
    push({
      id: 'gens' + i, kind: 'gens' as Kind, icon: ICON.gens, group: KIND_GROUP.gens,
      title: tl('柴油机组') + (i + 1), sub: String(g.state || '待机'),
      kpi: `U ${fmtNum(Number(g.u ?? 0))}kV · ${fmtNum(g.rpm ?? 0, 0)}rpm`,
      status: statusOf(g.state), alarmCount: alarmBySystem(SYS_GENS).length,
      x: 0, y: 0,
      meta: { kind: 'gens', raw: g, system: SYS_GENS, metrics: [
        { k: '电压', v: fmtNum(Number(g.u ?? 0)), unit: 'kV' },
        { k: '电流', v: fmtNum(g.i ?? 0, 0), unit: 'A' },
        { k: '功率', v: fmtNum(g.p ?? 0), unit: 'kW' },
        { k: '转速', v: fmtNum(g.rpm ?? 0, 0), unit: 'rpm' },
        { k: '水温', v: fmtNum(g.waterT ?? 0), unit: '℃', hot: Number(g.waterT ?? 0) > 95 },
        { k: '油压', v: fmtNum(g.oilP ?? 0, 1), unit: 'bar' },
      ] },
    })
  })
  if (!gens.length) {
    push({
      id: 'gens0', kind: 'gens' as Kind, icon: ICON.gens, group: KIND_GROUP.gens,
      title: tl('柴油机组'), sub: tl('应急备用'),
      kpi: tl('待机'),
      status: 'normal', alarmCount: 0, x: 0, y: 0,
      meta: { kind: 'gens', raw: {}, system: SYS_GENS, metrics: [
        { k: '状态', v: tl('待机'), unit: '' },
        { k: '并机母线', v: gensetData.value?.busState || '—', unit: '' },
      ] },
    })
  }

  // 2. 市电输入
  const incomers = hvData.value?.incomers ?? []
  incomers.forEach((ic: any, i: number) => {
    const u = ((ic.ua ?? 0) + (ic.ub ?? 0) + (ic.uc ?? 0)) / 3
    push({
      id: 'mains' + i, kind: 'mains' as Kind, icon: ICON.mains, group: KIND_GROUP.mains,
      title: tl('市电进线') + (i + 1), sub: ic.src || '10kV',
      kpi: `U ${fmtNum(u)}kV · I ${fmtNum(ic.i ?? 0, 0)}A`,
      status: statusOf(ic.state), alarmCount: alarmBySystem(SYS_HV).length,
      x: 0, y: 0,
      meta: { kind: 'mains', raw: ic, system: SYS_HV, metrics: [
        { k: '电压', v: fmtNum(u), unit: 'kV' },
        { k: '电流', v: fmtNum(ic.i ?? 0, 0), unit: 'A' },
        { k: '功率', v: fmtNum((ic.p ?? 0)), unit: 'MW' },
        { k: '负载率', v: fmtNum(ic.load ?? 0), unit: '%' },
        { k: '频率', v: fmtNum(ic.f ?? 50), unit: 'Hz' },
        { k: '电源', v: String(ic.src ?? '—'), unit: '' },
      ] },
    })
  })

  // 3. 中压母线
  const bus = hvData.value?.busSections ?? hvData.value?.bus ?? []
  bus.forEach((b: any, i: number) => {
    push({
      id: 'hvbus' + i, kind: 'hvbus' as Kind, icon: ICON.hvbus, group: KIND_GROUP.hvbus,
      title: tl('中压母线') + (i + 1), sub: (b.u ? fmtNum(Number(b.u)) : '10') + 'kV',
      kpi: `U ${fmtNum(Number(b.u ?? 0))}kV`,
      status: statusOf(b.state), alarmCount: alarmBySystem(SYS_HV).length,
      x: 0, y: 0,
      meta: { kind: 'hvbus', raw: b, system: SYS_HV, metrics: [
        { k: '电压', v: fmtNum(Number(b.u ?? 0)), unit: 'kV' },
        { k: '频率', v: fmtNum(b.f ?? 50), unit: 'Hz' },
        { k: '母线状态', v: String(b.state ?? '—'), unit: '' },
      ] },
    })
  })

  // 4. 变压器
  const tx = hvData.value?.transformers ?? []
  tx.forEach((t: any, i: number) => {
    push({
      id: 'tx' + i, kind: 'tx' as Kind, icon: ICON.tx, group: KIND_GROUP.tx,
      title: tl('变压器') + (i + 1), sub: '负载 ' + (t.load ?? '-') + '%',
      kpi: `负载 ${fmtNum(t.load ?? 0)}% · ${(t.windingT ?? '-')}℃`,
      status: statusOf(t.state), alarmCount: alarmBySystem(SYS_HV).length,
      x: 0, y: 0,
      meta: { kind: 'tx', raw: t, system: SYS_HV, metrics: [
        { k: '电压(高压)', v: fmtNum(Number(t.uHigh ?? 0)), unit: 'kV' },
        { k: '电压(低压)', v: fmtNum(Number(t.uLow ?? 0), 3), unit: 'kV' },
        { k: '电流(高压)', v: fmtNum(t.iHigh ?? 0, 0), unit: 'A' },
        { k: '功率', v: fmtNum(t.p ?? 0), unit: 'MW' },
        { k: '负载率', v: fmtNum(t.load ?? 0), unit: '%', hot: Number(t.load ?? 0) > 85 },
        { k: '绕组温度', v: fmtNum(t.windingT ?? 0), unit: '℃', hot: Number(t.windingT ?? 0) > 95 },
      ] },
    })
  })

  // 5. 低压母线
  const ltx = lvData.value?.transformers ?? []
  ltx.forEach((t: any, i: number) => {
    push({
      id: 'lvbus' + i, kind: 'lvbus' as Kind, icon: ICON.lvbus, group: KIND_GROUP.lvbus,
      title: tl('低压母线') + (i + 1), sub: (t.u ? fmtNum(Number(t.u), 3) : '0.4') + 'kV',
      kpi: `U ${fmtNum(Number(t.u ?? 0), 3)}kV`,
      status: statusOf(t.state), alarmCount: alarmBySystem(SYS_LV).length,
      x: 0, y: 0,
      meta: { kind: 'lvbus', raw: t, system: SYS_LV, metrics: [
        { k: '电压', v: fmtNum(Number(t.u ?? 0), 3), unit: 'kV' },
        { k: '频率', v: fmtNum(t.f ?? 50), unit: 'Hz' },
        { k: '功率因数', v: fmtNum(t.pf ?? 0, 2), unit: '' },
      ] },
    })
  })

  // 6. UPS（蓝色分组）
  const ups = lvData.value?.upsGroups ?? []
  ups.forEach((u: any, i: number) => {
    push({
      id: 'ups' + i, kind: 'ups' as Kind, icon: ICON.ups, group: KIND_GROUP.ups,
      title: tl('UPS') + (i + 1), sub: (u.mode || u.state || '—'),
      kpi: `Uout ${fmtNum(Number(u.uOut ?? 0), 0)}V · 负载 ${fmtNum(u.load ?? 0)}%`,
      status: statusOf(u.state), alarmCount: alarmBySystem(SYS_UPS).length,
      x: 0, y: 0,
      meta: { kind: 'ups', raw: u, system: SYS_UPS, metrics: [
        { k: '输入电压', v: fmtNum(Number(u.uIn ?? 0), 0), unit: 'V' },
        { k: '输出电压', v: fmtNum(Number(u.uOut ?? 0), 0), unit: 'V' },
        { k: '输出电流', v: fmtNum(u.iOut ?? 0, 0), unit: 'A' },
        { k: '功率', v: fmtNum(u.p ?? 0), unit: 'kW' },
        { k: '负载率', v: fmtNum(u.load ?? 0), unit: '%', hot: Number(u.load ?? 0) > 90 },
        { k: '功率因数', v: fmtNum(u.pf ?? 0, 2), unit: '' },
        { k: '运行模式', v: String(u.mode ?? '—'), unit: '' },
      ] },
    })
  })

  // 7. 电池组（右侧紫色分组）：优先用独立电池监控接口
  const batGroups = batteryData.value?.groups ?? []
  if (batGroups.length) {
    batGroups.forEach((g: any, i: number) => {
      push({
        id: 'battery' + i, kind: 'battery' as Kind, icon: ICON.battery, group: KIND_GROUP.battery,
        title: String(g.id ?? tl('电池组') + (i + 1)), sub: String(g.type ?? '铅酸'),
        kpi: `SOC ${fmtNum(g.soc ?? 0)}% · ${fmtNum(g.u ?? 0, 0)}V`,
        status: statusOf(g.state), alarmCount: alarmBySystem(SYS_BATTERY).length,
        isBattery: true, x: 0, y: 0,
        meta: { kind: 'battery', raw: g, system: SYS_BATTERY, metrics: [
          { k: '荷电状态', v: fmtNum(g.soc ?? 0), unit: '%', hot: Number(g.soc ?? 0) < 20 },
          { k: '组端电压', v: fmtNum(g.u ?? 0, 0), unit: 'V' },
          { k: '电流', v: fmtNum(g.i ?? 0, 0), unit: 'A' },
          { k: '最高温度', v: fmtNum(g.maxT ?? 0), unit: '℃', hot: Number(g.maxT ?? 0) > 45 },
          { k: '续航', v: fmtNum(batteryData.value?.backupMin ?? 15), unit: 'min' },
        ] },
      })
    })
  } else {
    // 降级：从 UPS 派生占位
    ups.forEach((u: any, i: number) => {
      const soc = u.batterySoc ?? u.soc ?? 96
      const vBat = u.batteryV ?? 540
      push({
        id: 'battery' + i, kind: 'battery' as Kind, icon: ICON.battery, group: KIND_GROUP.battery,
        title: tl('电池组') + (i + 1), sub: tl('备用电源'),
        kpi: `SOC ${fmtNum(soc)}% · ${fmtNum(vBat, 0)}V`,
        status: statusOf(u.state), alarmCount: alarmBySystem(SYS_UPS).length,
        isBattery: true, x: 0, y: 0,
        meta: { kind: 'battery', raw: u, system: SYS_UPS, metrics: [
          { k: '荷电状态', v: fmtNum(soc), unit: '%', hot: Number(soc) < 20 },
          { k: '组端电压', v: fmtNum(vBat, 0), unit: 'V' },
          { k: '续航', v: fmtNum(u.backupMin ?? 15), unit: 'min' },
        ] },
      })
    })
  }

  // 8. 机柜负载
  const cabCount = cabinets.value.length
  if (cabCount) {
    const fault = cabinets.value.filter((c) => statusOf(c.status) === 'fault').length
    push({
      id: 'cab', kind: 'cab' as Kind, icon: ICON.cab, group: KIND_GROUP.cab,
      title: tl('机柜负载'), sub: cabCount + tl('台') + ' · ' + tl('故障') + fault,
      kpi: `机柜 ${cabCount} · 故障 ${fault}`,
      status: fault ? 'fault' : 'normal', alarmCount: alarmBySystem(SYS_CAB).length,
      x: 0, y: 0,
      meta: { kind: 'cab', raw: { count: cabCount, fault }, system: SYS_CAB, metrics: [
        { k: '机柜总数', v: String(cabCount), unit: '台' },
        { k: '故障机柜', v: String(fault), unit: '台', hot: fault > 0 },
      ] },
    })
  }
  return list
})

// 计算坐标 + 分组框
const nodes = computed<LinkNode[]>(() => {
  const list = rawNodes.value
  const byKind: Record<string, (LinkNode & { meta: any })[]> = {}
  list.forEach((n) => {
    const k = n.kind ?? 'mains'
    ;(byKind[k] = byKind[k] || []).push(n)
  })
  Object.entries(byKind).forEach(([k, arr]) => {
    const pos = POS[k as Kind]
    arr.forEach((n, i) => {
      n.x = pos?.baseX ?? 130
      n.y = rowY(i, arr.length, pos?.layer ? LAYER_Y[pos.layer] : 230)
    })
  })
  return list
})

const groups = computed<LinkGroup[]>(() => {
  const defs: Array<{ key: string; title: string; kind: Kind; color: string }> = [
    { key: 'g-gens', title: tl('柴发并机系统'), kind: 'gens', color: '#f97316' },
    { key: 'g-mains', title: tl('市电输入'), kind: 'mains', color: '#f43f5e' },
    { key: 'g-hv', title: tl('中压配电'), kind: 'hvbus', color: '#f59e0b' },
    { key: 'g-tx', title: tl('变压器'), kind: 'tx', color: '#eab308' },
    { key: 'g-lv', title: tl('低压配电'), kind: 'lvbus', color: '#22c55e' },
    { key: 'g-ups', title: tl('UPS'), kind: 'ups', color: '#3b82f6' },
    { key: 'g-battery', title: tl('电池组'), kind: 'battery', color: '#a855f7' },
    { key: 'g-cab', title: tl('机柜负载'), kind: 'cab', color: '#475569' },
  ]
  const present = defs.filter((d) => byKindHas(d.kind))
  return present.map((d) => {
    const arr = nodes.value.filter((n) => n.group === d.key)
    const xs = arr.map((n) => (n.x as number) ?? 0)
    const ys = arr.map((n) => (n.y as number) ?? 0)
    const minX = Math.min(...xs) - 82
    const maxX = Math.max(...xs) + 82
    const minY = Math.min(...ys) - 56
    const maxY = Math.max(...ys) + 56
    return { key: d.key, title: d.title, color: d.color, x: minX, y: minY, w: maxX - minX, h: maxY - minY, nodeIds: arr.map((n) => n.id) }
  })
})
function byKindHas(k: Kind) {
  return nodes.value.some((n) => n.kind === k)
}

const links = computed<LinkEdge[]>(() => {
  const l: LinkEdge[] = []
  const order: Kind[] = ['mains', 'hvbus', 'tx', 'lvbus', 'ups', 'cab']
  const byKind: Record<string, LinkNode[]> = {}
  nodes.value.forEach((n) => {
    const k = n.kind ?? 'mains'
    ;(byKind[k] = byKind[k] || []).push(n)
  })
  let prev: LinkNode | null = null
  for (const key of order) {
    const arr = byKind[key] || []
    arr.forEach((n) => {
      if (prev) {
        const off = prev.status === 'off' || n.status === 'off'
        const alarm = (n.alarmCount ?? 0) > 0 || (prev.alarmCount ?? 0) > 0
        l.push({ from: prev.id, to: n.id, alarm, off })
      }
      prev = n
    })
  }
  // 备用电源链路：UPS <-> 电池组（虚线）
  byKind['ups']?.forEach((u, i) => {
    const b = byKind['battery']?.[i] ?? byKind['battery']?.[0]
    if (b) l.push({ from: u.id, to: b.id, backup: true, off: u.status === 'off' })
  })
  // 应急链路：柴发 -> 中压母线 / UPS（虚线）
  byKind['gens']?.forEach((g) => {
    const firstHv = byKind['hvbus']?.[0]
    if (firstHv) l.push({ from: g.id, to: firstHv.id, backup: true, off: g.status === 'off' })
    const firstUps = byKind['ups']?.[0]
    if (firstUps) l.push({ from: g.id, to: firstUps.id, backup: true, off: g.status === 'off' })
  })
  return l
})

const alarmNodeCount = computed(() => nodes.value.filter((n) => (n.alarmCount ?? 0) > 0).length)

const totalLoad = computed(() => {
  const tx = nodes.value.filter((n) => n.meta?.kind === 'tx' || n.meta?.kind === 'ups')
  if (!tx.length) return '—'
  const avg = tx.reduce((s, n) => s + Number((n.meta?.raw?.load ?? 0)), 0) / tx.length
  return fmtNum(avg)
})

const avgVoltage = computed(() => {
  const vs = nodes.value.flatMap((n) => {
    const m = (n.meta?.metrics as any[]) ?? []
    const v = m.find((x) => x.k.includes('电压'))
    return v ? [Number(v.v)] : []
  }).filter((v) => Number.isFinite(v) && v > 0)
  if (!vs.length) return '—'
  return fmtNum(vs.reduce((s, v) => s + v, 0) / vs.length, 2)
})

const avgCurrent = computed(() => {
  const cs = nodes.value.flatMap((n) => {
    const m = (n.meta?.metrics as any[]) ?? []
    const c = m.find((x) => x.k === '电流')
    return c ? [Number(c.v)] : []
  }).filter((v) => Number.isFinite(v) && v > 0)
  if (!cs.length) return '—'
  return fmtNum(cs.reduce((s, v) => s + v, 0) / cs.length, 0)
})

// ===== 实时告警联动 =====
const activeAlarms = computed<Alarm[]>(() => {
  // 优先使用实时引擎的活动告警（含链路定位），回退到接口拉取的活动告警
  const rt = (realtimeLinkage.active as unknown as Alarm[])
  const fromApi = alarms.value.filter((a) => a.status === 'active' || a.status === '待确认')
  const merged = [...rt, ...fromApi]
  const powerOnly = merged.filter((a) =>
    /配电|电力|电气|ups|柴发|变压器|power/i.test(a.system + a.message),
  )
  const seen = new Set<string>()
  return powerOnly.filter((a) => {
    const fp = `${a.system}|${a.message}`
    if (seen.has(fp)) return false
    seen.add(fp)
    return true
  })
})

const topAlarm = computed(() => activeAlarms.value[0] ?? null)
const topAlarmLevel = computed(() => {
  if (!topAlarm.value) return 'info'
  return topAlarm.value.level === 'crit' ? 'fault' : topAlarm.value.level === 'warn' ? 'warning' : 'info'
})

// 实时联动引擎链路态（loading/lastError/rulesError）：告警列表基于 realtimeLinkage.active，
// 引擎失败时该列表可能是陈旧快照，必须在告警条上显式提示，不可静默。
const linkageError = computed(() => realtimeLinkage.lastError || realtimeLinkage.rulesError)

const nodeAlarms = computed(() => {
  if (!selected.value?.meta?.system) return []
  return alarmBySystem(selected.value.meta.system as string)
})

const selectedMetrics = computed(() => {
  if (!selected.value?.meta?.metrics) return []
  return selected.value.meta.metrics as any[]
})

function levelText(lv: string) {
  return { crit: '严重', warn: '预警', info: '提示' }[lv] || lv
}

function onNodeClick(node: LinkNode) {
  selected.value = node
}
function locateAlarm(a: Alarm) {
  window.dispatchEvent(new CustomEvent('linkage-locate-alarm', { detail: a }))
  selected.value = null
}
function goAlarms() {
  router.push('/ops/alarms')
}

// ===== 历史趋势（基于链路聚合数据生成时序，支持 6h/24h/7d 切换） =====
const ranges = [
  { val: '6h', label: '6h', points: 24, step: 15 },
  { val: '24h', label: '24h', points: 24, step: 60 },
  { val: '7d', label: '7d', points: 28, step: 360 },
]
const range = ref('24h')
const rangeLabel = computed(() => ranges.find((r) => r.val === range.value)?.label ?? '24h')
const trendMetrics = [
  { key: 'load', label: tl('负载率'), unit: '%', base: 62, amp: 14, hi: 90 },
  { key: 'u', label: tl('电压'), unit: 'kV', base: 10.2, amp: 0.18, hi: 11 },
  { key: 'i', label: tl('电流'), unit: 'A', base: 320, amp: 70, hi: 480 },
  { key: 'p', label: tl('功率'), unit: 'MW', base: 5.4, amp: 1.3, hi: 8 },
]
const trendKey = ref('load')
const trendSeries = ref<number[]>([])

const trendMetricLabel = computed(() => trendMetrics.find((m) => m.key === trendKey.value)?.label ?? '')
const trendUnit = computed(() => trendMetrics.find((m) => m.key === trendKey.value)?.unit ?? '')
const trendColor = computed(() => {
  const m = trendMetrics.find((x) => x.key === trendKey.value)
  const last = trendSeries.value[trendSeries.value.length - 1] ?? 0
  if (m && last > m.hi * 0.95) return 'danger'
  return 'normal'
})
const trendNow = computed(() => {
  const last = trendSeries.value[trendSeries.value.length - 1]
  return last == null ? '—' : fmtNum(last, trendKey.value === 'u' ? 2 : 1)
})
const trendDelta = computed(() => {
  const s = trendSeries.value
  if (s.length < 2) return 0
  return s[s.length - 1] - s[s.length - 2]
})

const yMin = computed(() => {
  const s = trendSeries.value
  if (!s.length) return 0
  const m = Math.min(...s)
  return Math.floor(m - (Math.max(...s) - m) * 0.2)
})
const yMax = computed(() => {
  const s = trendSeries.value
  if (!s.length) return 100
  const m = Math.max(...s)
  return Math.ceil(m + (m - Math.min(...s)) * 0.2)
})
const trendPoints = computed(() => {
  const s = trendSeries.value
  if (!s.length) return ''
  const n = s.length
  return s
    .map((v, i) => {
      const x = 40 + (i / (n - 1)) * 470
      const y = 180 - ((v - yMin.value) / (yMax.value - yMin.value || 1)) * 160
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})
const trendArea = computed(() => {
  if (!trendPoints.value) return ''
  const first = trendPoints.value.split(' ')[0]
  const last = trendPoints.value.split(' ').slice(-1)[0]
  return `${first} ${trendPoints.value} ${last} 180,180`
})

function buildTrend() {
  const cfg = trendMetrics.find((m) => m.key === trendKey.value)
  const r = ranges.find((x) => x.val === range.value)!
  const out: number[] = []
  let v = cfg!.base
  for (let i = 0; i < r.points; i++) {
    const wave = Math.sin((i / r.points) * Math.PI * 2) * cfg!.amp * 0.6
    const noise = (Math.random() - 0.5) * cfg!.amp * 0.5
    v = cfg!.base + wave + noise
    out.push(Math.max(0, Number(v.toFixed(2))))
  }
  // 末尾贴近当前实时聚合值
  const live = trendKey.value === 'load' ? Number(totalLoad.value) || cfg!.base
    : trendKey.value === 'u' ? Number(avgVoltage.value) || cfg!.base
    : trendKey.value === 'i' ? Number(avgCurrent.value) || cfg!.base
    : (cfg!.base + cfg!.amp * 0.4)
  out[out.length - 1] = Number(live.toFixed(2))
  trendSeries.value = out
}

function toggleLive() {
  liveOn.value = !liveOn.value
  if (liveOn.value) startTimer()
  else stopTimer()
}
function startTimer() {
  stopTimer()
  timer = window.setInterval(() => {
    if (document.visibilityState === 'visible') load(false)
  }, 5000)
}
function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = 0
  }
}

async function load(showSpinner = true) {
  if (showSpinner) {
    loading.value = true
    error.value = ''
  }
  try {
    const [h, l, g, b, c, a] = await Promise.all([
      getPowerHvDetailed(),
      getPowerLvDetailed(),
      getPowerGensetDetailed().catch(() => null),
      getPowerBatteryDetailed().catch(() => null),
      getCabinets({ size: 200 }),
      getActiveAlarms(),
    ])
    hvData.value = h
    lvData.value = l
    gensetData.value = g
    batteryData.value = b
    cabinets.value = (c as any)?.items ?? (c as any)?.data ?? []
    alarms.value = a?.items ?? []
    // 保持选中节点刷新
    if (selected.value) {
      const fresh = nodes.value.find((n) => n.id === selected.value!.id)
      if (fresh) selected.value = fresh
    }
    buildTrend()
  } catch (e) {
    // 轮询静默（保留上一次成功数据）；仅显式刷新暴露错误态
    if (showSpinner) error.value = toErrorMessage(e) || tl('配电链路加载失败')
  } finally {
    if (showSpinner) loading.value = false
  }
}

onMounted(() => {
  load()
  startTimer()
})
onBeforeUnmount(stopTimer)
</script>

<style scoped>
.linkage-view {
  padding: 16px 20px 64px;
}
.view-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}
.view-head h1 {
  font-size: 20px;
  margin: 0 0 4px;
  color: #e2e8f0;
}
.sub {
  color: #64748b;
  font-size: 13px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}
.live.on { color: #22c55e; }
.live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: currentColor;
  animation: pulse 1.4s infinite;
}
.refresh {
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.refresh:hover { background: #273449; }
.refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin: 16px 0;
}
.kpi {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.k-label { color: #64748b; font-size: 12px; }
.k-val { color: #e2e8f0; font-size: 22px; font-weight: 700; }
.k-val.warn { color: #f59e0b; }

.main-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
  align-items: start;
}
.topo-panel { min-height: 360px; }
.topo-wrap { height: 360px; }
.legend {
  display: flex;
  gap: 14px;
  align-items: center;
  font-size: 12px;
  color: #94a3b8;
}
.legend .dot {
  display: inline-block;
  width: 9px; height: 9px; border-radius: 50%;
  margin-right: 5px; vertical-align: middle;
}
.dot.normal { background: #22c55e; }
.dot.warning { background: #f59e0b; }
.dot.fault { background: #ef4444; }
.dot.off { background: #64748b; }

.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-panel { min-height: 160px; }
.detail-empty { padding: 28px 8px; text-align: center; font-size: 13px; }
.detail-sub { font-size: 12px; margin-bottom: 10px; }
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.metric {
  background: #1e293b;
  border-radius: 8px;
  padding: 8px 10px;
}
.metric.hot { background: #3f2d12; border: 1px solid #f59e0b; }
.mk { display: block; color: #64748b; font-size: 11px; }
.mv { display: block; color: #e2e8f0; font-size: 16px; font-weight: 600; }
.mv small { color: #94a3b8; font-size: 11px; font-weight: 400; }

.alarm-list-head { color: #f59e0b; font-size: 13px; margin: 12px 0 6px; }
.alarm-item {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  background: #1e293b;
  margin-bottom: 8px;
  cursor: pointer;
}
.alarm-item:hover { background: #273449; }
.lv { font-size: 11px; padding: 2px 6px; border-radius: 4px; text-align: center; }
.lv-crit { background: #7f1d1d; color: #fecaca; }
.lv-warn { background: #78350f; color: #fde68a; }
.lv-info { background: #1e3a5f; color: #bfdbfe; }
.msg { color: #cbd5e1; font-size: 13px; }
.time { color: #64748b; font-size: 11px; }
.no-alarm { color: #22c55e; font-size: 13px; margin-top: 10px; }

.trend-panel { min-height: 220px; }
.range-tabs, .trend-metrics { display: flex; gap: 6px; }
.range-tabs button, .trend-metrics button {
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}
.range-tabs button.active, .trend-metrics button.active {
  background: #0369a1; color: #e0f2fe; border-color: #38bdf8;
}
.trend-body { display: flex; flex-direction: column; gap: 10px; margin-top: 10px; }
.chart-wrap { position: relative; }
.trend-svg { width: 100%; height: 200px; background: #0b1220; border-radius: 8px; }
.grid line { stroke: #1e293b; stroke-width: 1; }
.trend-line { stroke: #38bdf8; stroke-width: 2; }
.trend-line.danger { stroke: #ef4444; }
.trend-area { fill: rgba(56, 189, 248, 0.12); stroke: none; }
.trend-area.danger { fill: rgba(239, 68, 68, 0.14); }
.axis-label { fill: #475569; font-size: 9px; }
.axis-label.end { text-anchor: end; }
.trend-legend {
  position: absolute; top: 8px; left: 12px;
  display: flex; gap: 14px; align-items: baseline;
  font-size: 12px; color: #94a3b8;
}
.trend-legend .now { color: #e2e8f0; font-size: 18px; font-weight: 700; }
.trend-legend .delta.up { color: #22c55e; }
.trend-legend .delta.down { color: #ef4444; }

.alarm-bar {
  position: fixed;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  background: #1e293b;
  border: 1px solid #f59e0b;
  border-radius: 12px;
  padding: 10px 16px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
  z-index: 60;
  max-width: 90vw;
}
.alarm-bar.lv-fault { border-color: #ef4444; }
.ab-icon { color: #f59e0b; font-size: 18px; }
.alarm-bar.lv-fault .ab-icon { color: #ef4444; }
.ab-text { color: #e2e8f0; font-size: 13px; }
.ab-btn {
  background: #f59e0b; color: #1e293b; border: none;
  border-radius: 8px; padding: 6px 12px; cursor: pointer; font-weight: 600;
}
.alarm-bar.lv-fault .ab-btn { background: #ef4444; color: #fff; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translate(-50%, 20px); }

.muted { color: #64748b; }

@media (max-width: 1100px) {
  .main-grid { grid-template-columns: 1fr; }
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 600px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .topo-wrap { height: 300px; }
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
