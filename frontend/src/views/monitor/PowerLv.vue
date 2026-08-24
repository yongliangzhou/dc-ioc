<template>
  <div class="net-lv">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('0.4KV 低压配电') }}</h1>
      <span class="sub">{{ tl('变压器 → 低压柜/抽屉 → 母排 → 列头柜/PDU · 备自投 · 柴发进线 · 全电参量') }}</span>
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
      <!-- ======== 3.2.1 低压一次系统图 SVG + 备自投/柴发开关监视 ======== -->
      <Panel>
        <template #ct>{{ tl('低压一次系统图') }}</template>
        <template #extra>
          <div class="legend">
            <span class="lg"><i class="dot g"></i>{{ tl('合闸') }}</span>
            <span class="lg"><i class="dot r"></i>{{ tl('分闸') }}</span>
            <span class="lg"><i class="dot b"></i>{{ tl('备用/柴发') }}</span>
            <span class="lg muted">{{ tl('点击开关查看详情') }}</span>
          </div>
        </template>
        <div class="schematic-wrap">
          <svg :viewBox="`0 0 ${SVG_W} ${SVG_H}`" class="lv-svg" preserveAspectRatio="xMidYMid meet">
            <!-- I 段母排 -->
            <rect :x="BUS_I.x" :y="BUS_I.y" :width="BUS_I.w" :height="BUS_H" rx="4" class="bus" />
            <text :x="BUS_I.x + BUS_I.w/2" :y="BUS_I.y - 8" class="bus-label">{{ tl('低压 Ⅰ段母排') }}</text>
            <!-- II 段母排 -->
            <rect :x="BUS_II.x" :y="BUS_II.y" :width="BUS_II.w" :height="BUS_H" rx="4" class="bus" />
            <text :x="BUS_II.x + BUS_II.w/2" :y="BUS_II.y - 8" class="bus-label">{{ tl('低压 Ⅱ段母排') }}</text>

            <!-- 变压器进线 T1 / T2 -->
            <g v-for="(t, ti) in txNodes" :key="'t'+ti" class="feeder-line">
              <line :x1="t.x" :y1="t.y" :x2="t.x" :y2="t.busY" />
              <rect :x="t.x - 40" :y="t.y - 16" width="80" height="24" rx="5" class="tx-box" />
              <text :x="t.x" :y="t.y + 1" class="tx-text">{{ t.label }}</text>
            </g>

            <!-- 柴发进线 DG (应急电源, mock) -->
            <g class="feeder-line">
              <line :x1="DG.x" :y1="DG.y" :x2="DG.x" :y2="BUS_I.y" />
              <rect :x="DG.x - 40" :y="DG.y - 16" width="80" height="24" rx="5" class="dg-box" />
              <text :x="DG.x" :y="DG.y + 1" class="dg-text">{{ tl('柴油发电机') }}</text>
            </g>

            <!-- 变压器进线断路器 QT1 / QT2 -->
            <g v-for="(qt, qi) in txBreakers" :key="'qt'+qi" class="breaker-node" @click="selectNode(qt)">
              <rect :x="qt.x - BR_W/2" :y="qt.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(qt.breaker)]" />
              <text :x="qt.x" :y="qt.y + 4" class="breaker-text">{{ qt.code }}</text>
            </g>

            <!-- 母联 QB -->
            <g class="breaker-node" @click="selectNode(busTieNode)">
              <rect :x="busTieNode.x - BR_W/2" :y="busTieNode.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(busTieNode.breaker)]" />
              <text :x="busTieNode.x" :y="busTieNode.y + 4" class="breaker-text">{{ busTieNode.code }}</text>
              <text :x="busTieNode.x" :y="busTieNode.y - BR_H/2 - 6" class="bus-tie-label">{{ busTieNode.autoSwitch }}</text>
            </g>

            <!-- 柴发进线开关 QDG (mock) -->
            <g class="breaker-node" @click="selectNode(dgNode)">
              <rect :x="dgNode.x - BR_W/2" :y="dgNode.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(dgNode.breaker)]" />
              <text :x="dgNode.x" :y="dgNode.y + 4" class="breaker-text">{{ dgNode.code }}</text>
            </g>

            <!-- 馈线抽屉 -->
            <g v-for="(f, fi) in feederNodes" :key="'f'+fi" class="breaker-node" @click="selectNode(f)">
              <line :x1="f.x" :y1="f.busY" :x2="f.x" :y2="f.y" class="feeder-line" />
              <rect :x="f.x - BR_W/2" :y="f.y - BR_H/2" :width="BR_W" :height="BR_H" rx="5"
                    :class="['breaker-rect', breakerCls(f.breaker)]" />
              <text :x="f.x" :y="f.y + 4" class="breaker-text">{{ f.code }}</text>
              <text :x="f.x" :y="f.y + BR_H/2 + 13" class="feeder-load">{{ f.load }}</text>
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
      </Panel>

      <!-- ======== 顶部 KPI (KpiCard × 6) ======== -->
      <div class="grid cols-6">
        <KpiCard :title="tl('设备总数')" :value="s.total" unit="台" :decimals="0" dot="var(--cyan)" size="sm" />
        <KpiCard :title="tl('在线率')" :value="onlinePercent" unit="%" :decimals="1" :bar-value="onlinePercent" bar-color="var(--green)" size="sm"
                 :status="onlinePercent < 95 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('低压总有功')" :value="totalPower" unit="kW" :decimals="0" :bar-value="Math.min(100, totalPower/ratedP*100)" bar-color="var(--violet)" size="sm"
                 :status="totalPower > ratedP*0.85 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('平均负载率')" :value="avgBranchLoad" unit="%" :decimals="1" :bar-value="avgBranchLoad" bar-color="var(--blue)" size="sm"
                 :status="avgBranchLoad > 85 ? 'danger' : avgBranchLoad > 70 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('谐波 THD-U 均值')" :value="avgThdu" unit="%" :decimals="2" size="sm"
                 :status="avgThdu > 5 ? 'warning' : 'normal'" />
        <KpiCard :title="tl('防雷报警')" :value="spdAlarmCount" unit="路" :decimals="0" size="sm"
                 :status="spdAlarmCount > 0 ? 'warning' : 'normal'" />
      </div>

      <!-- ======== 3.2.3 备自投切换状态可视化面板 ======== -->
      <div class="grid cols-3">
        <Panel v-for="a in atsPanels" :key="a.id">
          <template #ct>{{ a.id }} {{ tl('备自投 / ATS') }}</template>
          <template #extra>
            <span class="pill" :class="isClosed(a.state) ? 'g' : 'b'">{{ a.state }}</span>
          </template>
          <div class="ats-body">
            <div class="ats-row"><span class="k">{{ tl('模式') }}</span><span class="v">{{ a.mode }}</span></div>
            <div class="ats-row"><span class="k">{{ tl('常用侧电压') }}</span><span class="v mono">{{ fmt(a.uIn) }} V</span></div>
            <div class="ats-row"><span class="k">{{ tl('负载侧电压') }}</span><span class="v mono">{{ fmt(a.uOut) }} V</span></div>
            <div class="ats-row"><span class="k">{{ tl('负载功率') }}</span><span class="v mono">{{ fmt(a.p, 0) }} kW</span></div>
            <div class="ats-row"><span class="k">{{ tl('末次切换') }}</span><span class="v mono muted">{{ a.lastSw }}</span></div>
          </div>
          <!-- 电源流向条 -->
          <div class="flow-bar">
            <span class="flow-src" :class="isClosed(a.state) ? 'on' : ''">{{ tl('市电') }}</span>
            <span class="flow-arrow">→</span>
            <span class="flow-bus">ATS</span>
            <span class="flow-arrow">→</span>
            <span class="flow-load" :class="isClosed(a.state) ? 'on' : ''">{{ tl('负载') }}</span>
          </div>
        </Panel>

        <!-- 母联 + 柴发 备自投总览 -->
        <Panel>
          <template #ct>{{ tl('母联 / 柴发 备自投') }}</template>
          <template #extra>
            <span class="pill" :class="busTieNode.breaker.includes('合') ? 'g' : 'a'">{{ busTieNode.breaker }}</span>
          </template>
          <div class="ats-body">
            <div class="ats-row"><span class="k">{{ tl('母联开关') }}</span><span class="v mono">{{ busTieNode.code }} · {{ busTieNode.breaker }}</span></div>
            <div class="ats-row"><span class="k">{{ tl('备自投逻辑') }}</span><span class="v mono">{{ busTieNode.autoSwitch }}</span></div>
            <div class="ats-row"><span class="k">{{ tl('柴发进线') }}</span><span class="v mono">{{ dgNode.code }} · {{ dgNode.breaker }}</span></div>
            <div class="ats-row"><span class="k">{{ tl('柴发状态') }}</span><span class="v" :class="dgStateCls">{{ dgStateText }}</span></div>
          </div>
          <div class="flow-bar">
            <span class="flow-src" :class="dgNode.breaker.includes('合') ? 'on' : ''">{{ tl('柴发') }}</span>
            <span class="flow-arrow">→</span>
            <span class="flow-bus">QDG/QB</span>
            <span class="flow-arrow">→</span>
            <span class="flow-load on">{{ tl('母排') }}</span>
          </div>
        </Panel>
      </div>

      <!-- ======== 3.2.4 24h 相电流趋势曲线 (TrendChart) ======== -->
      <Panel>
        <template #ct>{{ tl('24h 相电流趋势') }} ({{ tl('代表馈线') }} {{ repBranchId }})</template>
        <template #extra>
          <span class="pill g">{{ tl('三相 Ia / Ib / Ic') }}</span>
        </template>
        <TrendChart
          :title="''"
          :x-axis-data="phaseTrend.labels"
          :series="phaseTrend.series"
          :height="240"
        />
      </Panel>

      <!-- ======== 3.2.2 回路电参量表 (DeviceTable: 全电参量) ======== -->
      <Panel class="scroll-x moni-card">
        <template #ct>{{ tl('低压馈线回路监测') }} ({{ tl('全电参量') }})</template>
        <template #extra>
          <span class="pill" :class="branchAllClosed ? 'g' : 'a'">{{ s.branches.length }} {{ tl('路') }} · {{ tl('合闸') }} {{ branchClosedCount }}/{{ s.branches.length }}</span>
        </template>
        <table>
          <thead>
            <tr>
              <th>{{ tl('回路') }}</th><th>{{ tl('负荷名称') }}</th><th>{{ tl('断路器') }}</th><th>{{ tl('额定') }}(A)</th>
              <th>Ua(V)</th><th>Ub(V)</th><th>Uc(V)</th>
              <th>Ia(A)</th><th>Ib(A)</th><th>Ic(A)</th>
              <th>{{ tl('频率') }}(Hz)</th><th>P(kW)</th><th>Q(kVar)</th><th>PF</th><th>{{ tl('电度') }}(kWh)</th>
              <th>THD-U(%)</th><th>THD-I(%)</th><th>{{ tl('负载率') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in s.branches" :key="d.id">
              <td class="d-name">{{ d.id }}</td>
              <td class="muted">{{ d.name }}</td>
              <td><span class="tag" :class="breakerCls(d.breaker)">{{ d.breaker }}</span></td>
              <td class="mono">{{ d.rated }}</td>
              <td class="mono">{{ fmt(d.ua, 0) }}</td><td class="mono">{{ fmt(d.ub, 0) }}</td><td class="mono">{{ fmt(d.uc, 0) }}</td>
              <td class="mono">{{ fmt(d.ia, 0) }}</td><td class="mono">{{ fmt(d.ib, 0) }}</td><td class="mono">{{ fmt(d.ic, 0) }}</td>
              <td class="mono">{{ fmt(d.freq) }}</td>
              <td class="mono">{{ fmt(d.p, 0) }}</td><td class="mono">{{ fmt(d.q, 0) }}</td>
              <td class="mono" :class="pfCls(d.pf)">{{ fmt(d.pf) }}</td>
              <td class="mono">{{ fmtEnergy(d.energy) }}</td>
              <td class="mono" :class="thduCls(d.thdu)">{{ fmt(d.thdu) }}</td>
              <td class="mono" :class="thdiCls(d.thdi)">{{ fmt(d.thdi) }}</td>
              <td class="mono" :class="loadCls(d.loadPct)">{{ d.loadPct }}%</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ======== 3.2.5 电能统计报表 ======== -->
      <div class="grid cols-2">
        <Panel>
          <template #ct>{{ tl('电能统计报表') }}</template>
          <template #extra>
            <span class="pill g">{{ tl('本月累计') }} {{ fmtEnergy(totalEnergy) }} kWh</span>
          </template>
          <table class="report-tbl">
            <thead><tr><th>{{ tl('分段') }}</th><th>{{ tl('电度') }}(kWh)</th><th>{{ tl('占比') }}</th><th>{{ tl('平均负载率') }}</th></tr></thead>
            <tbody>
              <tr v-for="r in energyReport" :key="r.seg">
                <td class="d-name">{{ r.seg }}</td>
                <td class="mono">{{ fmtEnergy(r.kwh) }}</td>
                <td class="mono">{{ r.pct }}%</td>
                <td class="mono" :class="loadCls(r.load)">{{ r.load }}%</td>
              </tr>
              <tr class="total-row">
                <td class="d-name">{{ tl('合计') }}</td>
                <td class="mono">{{ fmtEnergy(totalEnergy) }}</td>
                <td class="mono">100%</td>
                <td class="mono">{{ avgBranchLoad }}%</td>
              </tr>
            </tbody>
          </table>
        </Panel>

        <!-- 三相不平衡度 / 负载率柱状图 -->
        <Panel>
          <template #ct>{{ tl('三相不平衡度 / 负载率') }}</template>
          <template #extra>
            <span class="pill" :class="imbalance > 2 ? 'a' : 'g'">{{ tl('最大不平衡') }} {{ imbalance }}%</span>
          </template>
          <TrendChart
            :title="''"
            :x-axis-data="loadLabels"
            :series="loadSeries"
            :height="220"
          />
        </Panel>
      </div>

      <!-- ======== UPS / HVDC / 母排 概要 ======== -->
      <div class="grid cols-3" v-if="s.upsGroups?.length || s.hvdc?.length || s.busbars?.length">
        <Panel class="scroll-x moni-card" v-if="s.upsGroups?.length">
          <template #ct>{{ tl('UPS 不间断电源') }}</template>
          <template #extra>
            <span class="pill" :class="upsAllNormal ? 'g' : 'a'">{{ s.upsGroups.length }} {{ tl('组') }} · {{ upsNormalCount }} {{ tl('正常') }}</span>
          </template>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('组') }}</th><th>{{ tl('模式') }}</th><th>{{ tl('旁路') }}</th><th>{{ tl('状态') }}</th><th>{{ tl('负载') }}</th><th>U出(V)</th><th>I出(A)</th><th>P(kW)</th></tr></thead>
            <tbody>
              <tr v-for="u in s.upsGroups" :key="u.id">
                <td class="d-name">{{ u.id }}</td>
                <td class="muted">{{ u.mode }}</td>
                <td><span class="tag" :class="u.bypass === '正常' ? 'g' : 'a'">{{ u.bypass }}</span></td>
                <td><span class="tag" :class="u.state === '正常' ? 'g' : 'a'">{{ u.state }}</span></td>
                <td class="mono" :class="loadCls(u.load)">{{ u.load }}%</td>
                <td class="mono">{{ fmt(u.uOut, 0) }}</td>
                <td class="mono">{{ fmt(u.iOut, 0) }}</td>
                <td class="mono">{{ fmt(u.p, 0) }}</td>
              </tr>
            </tbody>
          </table>
        </Panel>

        <Panel class="scroll-x moni-card" v-if="s.hvdc?.length">
          <template #ct>{{ tl('HVDC 直流电源') }}</template>
          <template #extra>
            <span class="pill g">{{ s.hvdc.length }} {{ tl('路') }}</span>
          </template>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('编号') }}</th><th>U(V)</th><th>{{ tl('负载') }}</th><th>{{ tl('模块') }}</th><th>P(kW)</th><th>THD-I(%)</th><th>{{ tl('状态') }}</th></tr></thead>
            <tbody>
              <tr v-for="h in s.hvdc" :key="h.id">
                <td class="d-name">{{ h.id }}</td>
                <td class="mono">{{ fmt(h.u, 1) }}</td>
                <td class="mono" :class="loadCls(h.load)">{{ h.load }}%</td>
                <td class="mono">{{ h.modRun }}/{{ h.modN }}</td>
                <td class="mono">{{ fmt(h.p, 0) }}</td>
                <td class="mono" :class="thdiCls(h.thdi)">{{ fmt(h.thdi) }}</td>
                <td><span class="tag" :class="h.state === '正常' ? 'g' : 'a'">{{ h.state }}</span></td>
              </tr>
            </tbody>
          </table>
        </Panel>

        <Panel class="scroll-x moni-card" v-if="s.busbars?.length">
          <template #ct>{{ tl('低压母排') }}</template>
          <template #extra>
            <span class="pill g">{{ s.busbars.length }} {{ tl('段') }}</span>
          </template>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('母排') }}</th><th>{{ tl('负载') }}</th><th>I(A)</th><th>U(V)</th><th>PF</th><th>THD-U(%)</th><th>{{ tl('状态') }}</th></tr></thead>
            <tbody>
              <tr v-for="b in s.busbars" :key="b.id">
                <td class="d-name">{{ b.id }}</td>
                <td class="mono" :class="loadCls(b.load)">{{ b.load }}%</td>
                <td class="mono">{{ fmt(b.i, 0) }}</td>
                <td class="mono">{{ fmt(b.u * 1000, 0) }}</td>
                <td class="mono">{{ fmt(b.pf) }}</td>
                <td class="mono" :class="thduCls(b.thdu)">{{ fmt(b.thdu) }}</td>
                <td><span class="tag" :class="b.state === '正常' ? 'g' : 'a'">{{ b.state }}</span></td>
              </tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <!-- ======== SPD 防雷状态 ======== -->
      <Panel class="scroll-x moni-card" v-if="s.spds?.length">
        <template #ct>{{ tl('防雷 / 浪涌保护器') }} (SPD)</template>
        <template #extra>
          <span class="pill" :class="spdAlarmCount === 0 ? 'g' : 'a'">{{ s.spds.length }} {{ tl('路') }} · {{ tl('正常') }} {{ spdNormalCount }}/{{ s.spds.length }}</span>
        </template>
        <table class="mini-tbl">
          <thead><tr><th>{{ tl('安装位置') }}</th><th>{{ tl('运行状态') }}</th><th>{{ tl('泄漏电流') }}(mA)</th><th>{{ tl('动作次数') }}</th><th>{{ tl('报警状态') }}</th></tr></thead>
          <tbody>
            <tr v-for="sp in s.spds" :key="sp.id">
              <td class="d-name">{{ sp.id }}</td>
              <td><span class="tag" :class="sigLevelTagCls(sp.level)">{{ sp.state }}</span></td>
              <td class="mono" :class="sp.leakI > 0.5 ? 'r-text' : 'g-text'">{{ fmt(sp.leakI, 2) }}</td>
              <td class="mono" :class="sp.count > 5 ? 'a-text' : ''">{{ sp.count }}</td>
              <td><span class="tag" :class="sp.status === '正常' ? 'g' : 'r'">{{ sp.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ======== 实时告警 (AlarmBadge) ======== -->
      <Panel>
        <template #ct>{{ tl('实时告警') }}</template>
        <template #extra>
          <span v-if="!alarms.length" class="pill g">{{ tl('无活动告警') }}</span>
          <span v-else class="pill a">{{ alarms.length }} {{ tl('条') }}</span>
        </template>
        <div v-if="!alarms.length" class="empty-tip muted">{{ tl('当前无越限/过载/谐波超标等告警') }}</div>
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
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmt, fmtInt, breakerCls, pfCls, loadCls, tempCls, thduCls, genHours } from '@/utils/format'
import { KpiCard } from '@dc-ioc/ui'
import SkeletonCard from '@/components/monitor/SkeletonCard.vue'
import { AlarmBadge } from '@dc-ioc/ui'
import TrendChart from '@/components/monitor/TrendChart.vue'
import { getPowerLvDetailed, type LvSummary, type LvBranchView } from '@/api/power'
import Panel from '@/components/common/Panel.vue'
const { t: tl } = useI18n()

/** 电量格式化：原始值以 Wh 计，折算为 kWh 并以千分位整数展示 */
const fmtEnergy = (v: number | null | undefined): string =>
  fmtInt(v == null ? null : v / 1000)

// ──────────────────────────────────────────
// SVG 几何
// ──────────────────────────────────────────
const SVG_W = 1000
const SVG_H = 440
const BUS_H = 14
const BUS_I = { x: 230, y: 150, w: 300 }
const BUS_II = { x: 470, y: 150, w: 300 }
const BR_W = 52
const BR_H = 24
const ratedP = 5000

interface BreakerNode {
  id: string
  code: string
  label: string
  breaker: string
  x: number
  y: number
  busY?: number
  load?: string
  autoSwitch?: string
  kvs: { k: string; v: string; cls?: string }[]
}

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = ref<LvSummary | null>(null)
const selectedNode = ref<BreakerNode | null>(null)

// 变压器 (进线源)
const txNodes = computed(() => {
  const list = s.value?.transformers ?? []
  return list.slice(0, 2).map((t, i) => {
    const x = i === 0 ? 320 : 680
    return { x, y: 40, busY: BUS_I.y, label: t.id }
  })
})
const txBreakers = computed<BreakerNode[]>(() => {
  const list = s.value?.transformers ?? []
  return list.slice(0, 2).map((t, i) => ({
    id: t.id, code: 'QT' + (i + 1), label: t.id + ' ' + tl('进线断路器'), breaker: '合闸',
    x: i === 0 ? 320 : 680, y: 86,
    kvs: [
      { k: tl('开关状态'), v: tl('合闸'), cls: 'g-text' },
      { k: tl('变压器') + ' U/I', v: `${fmt(t.u, 3)}kV / ${fmt(t.i, 0)}A` },
      { k: 'P / Q', v: `${fmt(t.p, 0)} / ${fmt(t.q, 0)} kW` },
      { k: 'PF', v: fmt(t.pf), cls: pfCls(t.pf) },
      { k: tl('负载率'), v: t.load + '%', cls: loadCls(t.load) },
      { k: tl('绕组温度'), v: fmt(t.t) + '°C', cls: tempCls(t.t, 85, 95) },
      { k: 'THD-U/I', v: `${fmt(t.thdu)}% / ${fmt(t.thdi)}%` },
    ],
  }))
})

const DG = { x: 80, y: 40 }
const dgNode = computed<BreakerNode>(() => ({
  id: 'DG', code: 'QDG', label: tl('柴发进线开关'), breaker: dgBreaker.value,
  x: DG.x, y: 86,
  kvs: [
    { k: tl('开关状态'), v: dgBreaker.value, cls: breakerCls(dgBreaker.value) },
    { k: tl('柴发状态'), v: dgStateText.value, cls: dgStateCls.value },
    { k: tl('额定功率'), v: '1600 kW' },
    { k: tl('启动方式'), v: tl('自启动 (市电失电)') },
  ],
}))

// 母联 QB (mock, 基于 busbars 是否存在推断)
const busTieNode = computed<BreakerNode>(() => {
  const bars = s.value?.busbars ?? []
  const closed = bars.length >= 2 // 两段母排均存在 → 母联通常分闸分段运行
  const state = closed ? tl('分段运行') : tl('合闸')
  const breaker = closed ? '分闸' : '合闸'
  return {
    id: 'QB', code: 'QB', label: tl('低压母联断路器'), breaker,
    x: (BUS_I.x + BUS_I.w + BUS_II.x) / 2, y: BUS_I.y + BUS_H / 2,
    autoSwitch: tl('投入'),
    kvs: [
      { k: tl('开关状态'), v: breaker, cls: breakerCls(breaker) },
      { k: tl('备自投'), v: tl('投入') },
      { k: tl('运行方式'), v: state },
    ],
  }
})

// 柴发状态 (mock)
const dgBreaker = computed(() => '分闸') // 市电正常时柴发热备，开关分闸
const dgStateText = computed(() => (dgBreaker.value.includes('分') ? tl('热备用') : tl('运行')))
const dgStateCls = computed(() => (dgBreaker.value.includes('分') ? 'a-text' : 'g-text'))

// 馈线抽屉节点
const feederNodes = computed<BreakerNode[]>(() => {
  const list = s.value?.branches ?? []
  const half = Math.ceil(list.length / 2)
  return list.map((d, i) => {
    const onI = i < half
    const bus = onI ? BUS_I : BUS_II
    const count = onI ? half : list.length - half
    const idx = onI ? i : i - half
    const step = bus.w / Math.max(1, count)
    const x = Math.round(bus.x + step * (idx + 0.5))
    const busY = bus.y + BUS_H
    return {
      id: d.id, code: 'LP' + (i + 1), label: d.id + ' ' + tl('低压抽屉'), breaker: d.breaker,
      x, y: busY + 56, busY, load: d.name,
      kvs: [
        { k: tl('负荷名称'), v: d.name },
        { k: tl('断路器'), v: d.breaker, cls: breakerCls(d.breaker) },
        { k: 'Ua/Ub/Uc', v: `${fmt(d.ua, 0)}/${fmt(d.ub, 0)}/${fmt(d.uc, 0)} V` },
        { k: 'Ia/Ib/Ic', v: `${fmt(d.ia, 0)}/${fmt(d.ib, 0)}/${fmt(d.ic, 0)} A` },
        { k: 'P / Q', v: `${fmt(d.p, 0)} / ${fmt(d.q, 0)} kW` },
        { k: 'PF', v: fmt(d.pf), cls: pfCls(d.pf) },
        { k: tl('频率'), v: fmt(d.freq) + ' Hz' },
        { k: tl('电度'), v: fmtEnergy(d.energy) + ' kWh' },
        { k: 'THD-U/I', v: `${fmt(d.thdu)}% / ${fmt(d.thdi)}%`, cls: thduCls(d.thdu) },
        { k: tl('负载率'), v: d.loadPct + '%', cls: loadCls(d.loadPct) },
      ],
    }
  })
})

function selectNode(n: BreakerNode) {
  selectedNode.value = n
}

// ──────────────────────────────────────────
// KPI 派生
// ──────────────────────────────────────────
const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})
const branches = computed(() => s.value?.branches ?? [])
const totalPower = computed(() => Number(branches.value.reduce((sum, d) => sum + (d.p || 0), 0).toFixed(0)))
const avgBranchLoad = computed(() => avgNum(branches.value.map((d) => d.loadPct)))
const avgThdu = computed(() => avgNum(branches.value.map((d) => d.thdu)))
const totalEnergy = computed(() => branches.value.reduce((sum, d) => sum + (d.energy || 0), 0))

const branchClosedCount = computed(() => branches.value.filter((d) => isClosed(d.breaker)).length)
const branchAllClosed = computed(() => branches.value.length > 0 && branchClosedCount.value === branches.value.length)

const spdAlarmCount = computed(() => (s.value?.spds ?? []).filter((sp) => sp.status !== '正常').length)
const spdNormalCount = computed(() => (s.value?.spds ?? []).filter((sp) => sp.status === '正常').length)
const upsNormalCount = computed(() => (s.value?.upsGroups ?? []).filter((u) => u.state === '正常').length)
const upsAllNormal = computed(() => {
  const list = s.value?.upsGroups ?? []
  return list.length > 0 && upsNormalCount.value === list.length
})

// ──────────────────────────────────────────
// 3.2.3 备自投面板
// ──────────────────────────────────────────
const atsPanels = computed(() => {
  const list = s.value?.ats ?? []
  if (list.length) return list
  // mock fallback
  return [
    { id: tl('ATS-1'), state: '常用侧', mode: tl('自投自复'), uIn: 400, uOut: 399, p: 1800, lastSw: '-' },
    { id: tl('ATS-2'), state: '常用侧', mode: tl('自投不自复'), uIn: 400, uOut: 398, p: 1500, lastSw: '-' },
  ]
})

// ──────────────────────────────────────────
// 3.2.4 24h 相电流趋势
// ──────────────────────────────────────────
const repBranchId = computed(() => {
  const b = branches.value
  if (!b.length) return '-'
  // 选负载率最高的回路作代表
  return b.slice().sort((a, b2) => b2.loadPct - a.loadPct)[0].id
})
function genCurrent(n: number, base: number, peak: number): number[] {
  return Array.from({ length: n }, (_, i) => {
    const hour = i
    // 白天负载高, 夜间低
    const daily = 0.5 + 0.5 * Math.sin(((hour - 6) / 24) * Math.PI * 2)
    return Number((base + daily * (peak - base) + (Math.random() - 0.5) * peak * 0.08).toFixed(1))
  })
}
const phaseTrend = reactive({
  labels: genHours(24),
  series: [
    { name: 'Ia', type: 'line' as const, data: genCurrent(24, 120, 420), color: '#22d3ee' },
    { name: 'Ib', type: 'line' as const, data: genCurrent(24, 115, 405), color: '#22c55e' },
    { name: 'Ic', type: 'line' as const, data: genCurrent(24, 118, 412), color: '#f59e0b' },
  ],
})

// ──────────────────────────────────────────
// 3.2.5 电能报表 + 负载率/不平衡柱状图
// ──────────────────────────────────────────
const energyReport = computed(() => {
  const b = branches.value
  if (!b.length) return []
  const half = Math.ceil(b.length / 2)
  const segA = b.slice(0, half)
  const segB = b.slice(half)
  const sumKwh = (arr: LvBranchView[]) => arr.reduce((s2, d) => s2 + (d.energy || 0), 0)
  const avgLoad = (arr: LvBranchView[]) => avgNum(arr.map((d) => d.loadPct))
  const total = totalEnergy.value || 1
  const mk = (seg: string, arr: LvBranchView[]) => ({
    seg, kwh: sumKwh(arr), pct: Number(((sumKwh(arr) / total) * 100).toFixed(1)),
    load: Number(avgLoad(arr).toFixed(1)),
  })
  return [mk(tl('Ⅰ段母排'), segA), mk(tl('Ⅱ段母排'), segB)]
})

const loadLabels = computed(() => branches.value.slice(0, 12).map((d) => d.id))
const loadSeries = computed(() => [
  { name: tl('负载率 (%)'), type: 'bar' as const, data: branches.value.slice(0, 12).map((d) => d.loadPct), color: '#3b82f6', barWidth: '55%' },
])
// 三相不平衡度 = 各回路三相电流最大偏差的均代表 (演示: 取电流标准差占比近似)
const imbalance = computed(() => {
  const b = branches.value
  if (!b.length) return 0
  const vals = b.map((d) => {
    const arr = [d.ia, d.ib, d.ic].filter((v) => v != null) as number[]
    if (arr.length < 3) return 1
    const max = Math.max(...arr), min = Math.min(...arr)
    const avg = arr.reduce((s2, v) => s2 + v, 0) / arr.length
    return avg ? ((max - min) / avg) * 100 : 0
  })
  return Number((vals.reduce((s2, v) => s2 + v, 0) / vals.length).toFixed(1))
})

// ──────────────────────────────────────────
// 实时告警 (越限派生)
// ──────────────────────────────────────────
const alarms = computed(() => {
  const out: { level: string; time: string; source: string; message: string; value: string }[] = []
  const now = new Date()
  const ts = (m: number) => new Date(now.getTime() - m * 60000).toTimeString().slice(0, 8)
  branches.value.forEach((d, i) => {
    const uph = (d.ua + d.ub + d.uc) / 3
    if (uph > 418 || uph < 361) out.push({ level: 'major', time: ts(2 + i), source: d.id, message: tl('相电压越限'), value: uph.toFixed(0) + 'V' })
    if (d.loadPct >= 90) out.push({ level: 'warning', time: ts(4 + i), source: d.id, message: tl('回路负载率过高'), value: d.loadPct + '%' })
    else if (d.loadPct >= 80) out.push({ level: 'warning', time: ts(6 + i), source: d.id, message: tl('回路负载率偏高'), value: d.loadPct + '%' })
    if (d.pf < 0.85) out.push({ level: 'warning', time: ts(8 + i), source: d.id, message: tl('功率因数偏低'), value: fmt(d.pf) })
    if (d.thdu >= 5) out.push({ level: 'warning', time: ts(10 + i), source: d.id, message: tl('谐波 THD-U 超标'), value: fmt(d.thdu) + '%' })
    if (d.thdi >= 8) out.push({ level: 'warning', time: ts(12 + i), source: d.id, message: tl('谐波 THD-I 超标'), value: fmt(d.thdi) + '%' })
  })
  ;(s.value?.spds ?? []).forEach((sp) => {
    if (sp.status !== '正常') out.push({ level: 'critical', time: ts(3), source: sp.id, message: tl('防雷器 SPD 报警'), value: sp.status })
    else if (sp.leakI > 0.5) out.push({ level: 'warning', time: ts(5), source: sp.id, message: tl('SPD 泄漏电流增大'), value: sp.leakI.toFixed(2) + 'mA' })
  })
  ;(s.value?.transformers ?? []).forEach((t) => {
    if (t.t >= 95) out.push({ level: 'critical', time: ts(3), source: t.id, message: tl('变压器温度高报警'), value: t.t + '°C' })
    else if (t.t >= 85) out.push({ level: 'warning', time: ts(5), source: t.id, message: tl('变压器温度偏高'), value: t.t + '°C' })
  })
  return out.slice(0, 14)
})

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function isClosed(v?: string): boolean {
  const t = String(v ?? '').trim()
  return t.includes('合闸') || (t.includes('合') && !t.includes('分'))
}
function avgNum(list: number[]): number {
  const vals = list.filter((v) => v != null && Number.isFinite(v))
  if (!vals.length) return 0
  return Number((vals.reduce((s2, v) => s2 + v, 0) / vals.length).toFixed(1))
}

function thdiCls(v: number): string {
  if (v >= 8) return 'r-text'
  if (v >= 5) return 'a-text'
  return 'g-text'
}
function sigLevelTagCls(level: string): string {
  if (level === 'g') return 'g'
  if (level === 'a') return 'a'
  if (level === 'r') return 'r'
  return 'b'
}

// ──────────────────────────────────────────
// Mock fallback (当 API 无数据)
// ──────────────────────────────────────────
function mockSummary(): LvSummary {
  const transformers = [
    { id: 'T1', load: 62, t: 68, state: '运行', u: 0.398, i: 10320, p: 2900, q: 820, pf: 0.965, freq: 50.01, energy: 9200000, thdu: 2.1, thdi: 3.4 },
    { id: 'T2', load: 58, t: 64, state: '运行', u: 0.399, i: 9680, p: 2700, q: 760, pf: 0.971, freq: 49.99, energy: 8700000, thdu: 2.3, thdi: 3.6 },
  ]
  const branchDefs: [string, string, number][] = [
    ['LP1', 'IT 机柜 A 列', 320], ['LP2', 'IT 机柜 B 列', 360], ['LP3', '空调机组 1', 410],
    ['LP4', '空调机组 2', 300], ['LP5', 'UPS 输入', 280], ['LP6', '照明动力', 220],
    ['LP7', '冷水机组', 450], ['LP8', '消防设备', 90], ['LP9', '电梯', 130], ['LP10', '备用回路', 0],
  ]
  const branches: LvBranchView[] = branchDefs.map(([id, name, rated], i) => {
    const pClosed = i < 9
    const p = pClosed ? Math.round(rated * (0.6 + (i % 3) * 0.12) * 4) / 4 : 0
    const ia = pClosed ? Math.round(rated * 0.7 + i * 5) : 0
    const ib = pClosed ? Math.round(ia * (0.95 + (i % 2) * 0.04)) : 0
    const ic = pClosed ? Math.round(ia * (0.97 + (i % 3) * 0.03)) : 0
    const ua = pClosed ? 230 + (i % 4) - 1 : 231
    const ub = pClosed ? 229 + (i % 3) : 230
    const uc = pClosed ? 231 + (i % 5) - 2 : 230
    const loadPct = rated ? Math.round((p / (rated * 1.5)) * 100) : 0
    return {
      id, name, breaker: pClosed ? '合闸' : '分闸', rated,
      ua, ub, uc, u: (ua + ub + uc) / 3, ia, ib, ic, i: ia,
      freq: 50.0, p, q: Math.round(p * 0.28), pf: pClosed ? 0.94 + (i % 3) * 0.01 : 1,
      energy: Math.round(100000 + i * 450000), thdu: 2 + (i % 3), thdi: 3 + (i % 4), loadPct,
    }
  })
  return {
    transformers,
    upsGroups: [
      { id: 'UPS-A', n: '200kVA', load: 45, uIn: 400, uOut: 230, mode: '正常', bypass: '正常', state: '正常', iIn: 320, iOut: 560, p: 130, pf: 0.99, freq: 50.0, energyIn: 2100000, thdu: 1.8, thdi: 2.5 },
      { id: 'UPS-B', n: '200kVA', load: 48, uIn: 400, uOut: 230, mode: '正常', bypass: '正常', state: '正常', iIn: 340, iOut: 590, p: 140, pf: 0.98, freq: 50.0, energyIn: 2200000, thdu: 1.9, thdi: 2.6 },
    ],
    hvdc: [
      { id: 'HVDC-1', u: 240, load: 52, modN: 8, modRun: 8, state: '正常', i: 200, p: 48, pf: 0.99, energy: 800000, thdi: 3.1 },
    ],
    ats: [
      { id: 'ATS-1', state: '常用侧', mode: '自投自复', lastSw: '2026-07-20 02:11', uIn: 400, uOut: 399, pf: 0.97, p: 1800 },
      { id: 'ATS-2', state: '常用侧', mode: '自投不自复', lastSw: '2026-07-18 11:42', uIn: 400, uOut: 398, pf: 0.96, p: 1500 },
    ],
    busbars: [
      { id: 'Ⅰ段', load: 60, i: 2100, state: '正常', u: 0.398, pf: 0.96, energy: 9200000, thdu: 2.1 },
      { id: 'Ⅱ段', load: 57, i: 1980, state: '正常', u: 0.399, pf: 0.97, energy: 8700000, thdu: 2.3 },
    ],
    branches,
    spds: [
      { id: 'SPD-进线柜', state: '正常', level: 'g', leakI: 0.12, count: 2, status: '正常' },
      { id: 'SPD-配电柜1', state: '正常', level: 'g', leakI: 0.18, count: 1, status: '正常' },
      { id: 'SPD-配电柜2', state: '正常', level: 'g', leakI: 0.15, count: 3, status: '正常' },
      { id: 'SPD-UPS间', state: '预警', level: 'a', leakI: 0.62, count: 7, status: '异常' },
    ],
    knowledge: { thresholds: [] },
    total: 24, online: 23, avgLoadPercent: 58, avgVoltage: 398, avgCurrent: 2050, devices: [],
  }
}

// ──────────────────────────────────────────
// Load data
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getPowerLvDetailed()
    if (data && (data.branches?.length || data.transformers?.length)) {
      s.value = data
    } else {
      s.value = mockSummary()
    }
  } catch (e: unknown) {
    error.value = (e as ErrorLike)?.message || String(e)
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
.grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid.cols-2 { grid-template-columns: repeat(2, 1fr); }

/* ── SVG 一次图 ── */
.schematic-wrap { background: rgba(15, 23, 42, 0.5); border-radius: 8px; padding: 8px; }
.lv-svg { width: 100%; height: auto; display: block; }
.bus { fill: #22d3ee; opacity: 0.85; }
.bus-label { fill: var(--text-muted, #94a3b8); font-size: 11px; text-anchor: middle; }
.feeder-line line { stroke: #475569; stroke-width: 2; }
.tx-box { fill: #1e3a5f; stroke: #22d3ee; stroke-width: 1; }
.tx-text { fill: #cbd5e1; font-size: 11px; text-anchor: middle; }
.dg-box { fill: #3b2f1e; stroke: #f59e0b; stroke-width: 1; }
.dg-text { fill: #fcd34d; font-size: 11px; text-anchor: middle; }
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

/* ── 备自投面板 ── */
.ats-body { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.ats-row { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 3px 0; border-bottom: 1px dashed rgba(51,65,85,0.5); }
.ats-row .k { color: var(--text-muted, #94a3b8); }
.ats-row .v { color: var(--text-secondary, #94a3b8); font-weight: 500; }
.flow-bar { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 8px; background: rgba(30,41,59,0.5); border-radius: 6px; font-size: 11px; }
.flow-src, .flow-load { padding: 3px 10px; border-radius: 5px; border: 1px solid var(--border, #334155); color: var(--text-muted, #94a3b8); }
.flow-src.on, .flow-load.on { color: #22c55e; border-color: rgba(34,197,94,0.4); background: rgba(34,197,94,0.08); }
.flow-bus { padding: 3px 10px; border-radius: 5px; background: rgba(34,211,255,0.1); color: #22d3ee; }
.flow-arrow { color: var(--text-muted, #6b7280); }

/* ── table ── */
table { width: 100%; border-collapse: collapse; font-size: 0.75rem; }
th { text-align: left; color: var(--text-muted, #6b7280); font-weight: 600; font-size: 10px; letter-spacing: .4px; padding: 7px 8px; border-bottom: 1px solid var(--border, #334155); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid rgba(51, 65, 85, 0.5); color: var(--text-secondary, #94a3b8); white-space: nowrap; }
tbody tr:hover { background: rgba(255, 255, 255, 0.03); }
.d-name { font-weight: 500; color: var(--text-primary, #e5e7eb); }
.mono { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }

.mini-tbl th, .mini-tbl td { font-size: 11px; padding: 5px 6px; }
.report-tbl .total-row td { font-weight: 700; color: var(--text-primary, #e5e7eb); border-top: 1px solid var(--border, #334155); }

/* tag */

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
  .grid.cols-3 { grid-template-columns: 1fr; }
  .grid.cols-2 { grid-template-columns: 1fr; }
}
@media (max-width: 860px) {
  .grid.cols-6 { grid-template-columns: repeat(2, 1fr); }
}
</style>
