<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.lv') }}</h1>
      <span class="sub">{{ tl('0.4KV 低压配电') }} {{ tl('·') }} {{ tl('智能电量仪表') }} {{ tl('·') }} {{ tl('全电参量 / 断路器 / 防雷状态 / 谐波含量') }}</span>
    </div>

    <!-- ======== 顶部 KPI: 系统总体 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="lv-total" :label="tl('设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="lv-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="lv-load" :label="tl('馈线平均负载率')" :value="avgBranchLoad" unit="%" :quality="avgBranchLoad > 85 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="lv-voltage" :label="tl('平均相电压')" :value="avgBranchVoltage" unit="V" quality="good" :online="true" />
    </div>
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="lv-power" :label="tl('低压总有功')" :value="totalPower" unit="kW" quality="good" :online="true" />
      <MetricCard metric-name="lv-ats" :label="tl('ATS 回路')" :value="s.ats?.length ?? 0" unit="路" quality="good" :online="true" />
      <MetricCard metric-name="lv-thd" :label="tl('谐波 THD-U 均值')" :value="avgThdu" unit="%" :quality="avgThdu > 5 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="lv-spd" :label="tl('防雷报警')" :value="spdAlarmCount" unit="路" :quality="spdAlarmCount > 0 ? 'uncertain' : 'good'" :online="true" />
    </div>

    <!-- 加载 / 错误态 -->
    <template v-if="!s">
      <div class="card" v-if="!error">
        <div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div>
      </div>
      <div class="card" v-if="error">
        <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div>
      </div>
    </template>

    <template v-else>
      <!-- ======== 智能电量仪表架构 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('智能电量仪表采集系统') }}</span>
          <span class="pill g">{{ tl('接入运维监控平台') }}</span>
        </div>
        <p class="arch-desc muted">{{ tl('0.4KV 低压系统通过集成智能电量仪表，对各馈线回路检测全部电力参数——三相电压、三相电流、频率、有功功率、无功功率、功率因数、电度及谐波含量（THD-U/THD-I）；同步采集断路器合分状态与防雷器（SPD）运行状态，经统一协议接入运维监控平台，保障末端 IT 设备零中断与动力负荷安全可靠供电。') }}</p>
        <div class="chips">
          <span class="chip" v-for="c in collectTargets" :key="c">{{ c }}</span>
        </div>
      </div>

      <!-- ======== 低压馈线回路监测 (智能电量仪表·全电参量) ======== -->
      <div class="card scroll-x" v-if="s.branches?.length">
        <div class="card-head">
          <span class="ct">{{ tl('低压馈线回路') }} ({{ tl('智能电量仪表·全电参量') }})</span>
          <span class="pill" :class="branchAllClosed ? 'g' : 'a'">{{ s.branches.length }} {{ tl('路') }} · {{ tl('断路器合闸') }} {{ branchClosedCount }}/{{ s.branches.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('回路') }}</th><th>{{ tl('负荷名称') }}</th><th>{{ tl('断路器') }}</th><th>{{ tl('额定') }}(A)</th>
              <th>Ua (V)</th><th>Ub (V)</th><th>Uc (V)</th>
              <th>Ia (A)</th><th>Ib (A)</th><th>Ic (A)</th>
              <th>{{ tl('频率') }}(Hz)</th><th>P (kW)</th><th>Q (kVar)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('电度') }}(kWh)</th>
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
      </div>

      <!-- ======== 防雷 / 浪涌保护器 (SPD) ======== -->
      <div class="card scroll-x" v-if="s.spds?.length">
        <div class="card-head">
          <span class="ct">{{ tl('防雷 / 浪涌保护器') }} (SPD)</span>
          <span class="pill" :class="spdAlarmCount === 0 ? 'g' : 'a'">{{ s.spds.length }} {{ tl('路') }} · {{ tl('正常') }} {{ spdNormalCount }}/{{ s.spds.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('安装位置') }}</th><th>{{ tl('运行状态') }}</th><th>{{ tl('泄漏电流') }}(mA)</th><th>{{ tl('动作次数') }}</th><th>{{ tl('报警状态') }}</th>
            </tr>
          </thead>
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
        <p class="arch-desc muted" style="margin-top:8px">{{ tl('泄漏电流持续增大或动作次数异常增多提示 SPD 劣化，需及时更换，保障防雷保护有效性。') }}</p>
      </div>

      <!-- ======== 配电变压器 (低压侧) ======== -->
      <div class="card scroll-x" v-if="s.transformers?.length">
        <div class="card-head">
          <span class="ct">{{ tl('低压侧配电变压器') }}</span>
          <span class="pill" :class="txAllRunning ? 'g' : 'a'">{{ s.transformers.length }} {{ tl('台') }} · {{ txRunningCount }} {{ tl('运行') }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('变压器') }}</th><th>{{ tl('状态') }}</th><th>{{ tl('负载率') }}</th><th>{{ tl('绕组温度') }}(°C)</th>
              <th>U (kV)</th><th>I (A)</th><th>P (kW)</th><th>Q (kVar)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('频率') }}(Hz)</th><th>{{ tl('电度') }}(kWh)</th><th>THD-U(%)</th><th>THD-I(%)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in s.transformers" :key="t.id">
              <td class="d-name">{{ t.id }}</td>
              <td><span class="tag" :class="t.state === '运行' ? 'g' : 'a'">{{ t.state }}</span></td>
              <td class="mono" :class="loadCls(t.load)">{{ t.load }}%</td>
              <td class="mono" :class="tempCls(t.t, 85, 95)">{{ t.t }}</td>
              <td class="mono">{{ fmt(t.u, 3) }}</td>
              <td class="mono">{{ fmt(t.i, 0) }}</td>
              <td class="mono">{{ fmt(t.p, 0) }}</td>
              <td class="mono">{{ fmt(t.q, 0) }}</td>
              <td class="mono" :class="pfCls(t.pf)">{{ fmt(t.pf) }}</td>
              <td class="mono">{{ fmt(t.freq) }}</td>
              <td class="mono">{{ fmtEnergy(t.energy) }}</td>
              <td class="mono" :class="thduCls(t.thdu)">{{ fmt(t.thdu) }}</td>
              <td class="mono" :class="thdiCls(t.thdi)">{{ fmt(t.thdi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== UPS 不间断电源 ======== -->
      <div class="card scroll-x" v-if="s.upsGroups?.length">
        <div class="card-head">
          <span class="ct">{{ tl('UPS 不间断电源') }} (2N)</span>
          <span class="pill" :class="upsAllNormal ? 'g' : 'a'">{{ s.upsGroups.length }} {{ tl('组') }} · {{ upsNormalCount }} {{ tl('正常') }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('UPS 组') }}</th><th>{{ tl('配置') }}</th><th>{{ tl('模式') }}</th><th>{{ tl('旁路') }}</th><th>{{ tl('状态') }}</th>
              <th>{{ tl('负载率') }}</th><th>U入(V)</th><th>U出(V)</th><th>I入(A)</th><th>I出(A)</th>
              <th>P (kW)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('频率') }}(Hz)</th><th>{{ tl('电度') }}(kWh)</th><th>THD-U(%)</th><th>THD-I(%)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in s.upsGroups" :key="u.id">
              <td class="d-name">{{ u.id }}</td>
              <td class="muted">{{ u.n }}</td>
              <td>{{ u.mode }}</td>
              <td><span class="tag" :class="u.bypass === '正常' ? 'g' : 'a'">{{ u.bypass }}</span></td>
              <td><span class="tag" :class="u.state === '正常' ? 'g' : 'a'">{{ u.state }}</span></td>
              <td class="mono" :class="loadCls(u.load)">{{ u.load }}%</td>
              <td class="mono">{{ fmt(u.uIn, 0) }}</td><td class="mono">{{ fmt(u.uOut, 0) }}</td>
              <td class="mono">{{ fmt(u.iIn, 0) }}</td><td class="mono">{{ fmt(u.iOut, 0) }}</td>
              <td class="mono">{{ fmt(u.p, 0) }}</td>
              <td class="mono" :class="pfCls(u.pf)">{{ fmt(u.pf) }}</td>
              <td class="mono">{{ fmt(u.freq) }}</td>
              <td class="mono">{{ fmtEnergy(u.energyIn) }}</td>
              <td class="mono" :class="thduCls(u.thdu)">{{ fmt(u.thdu) }}</td>
              <td class="mono" :class="thdiCls(u.thdi)">{{ fmt(u.thdi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== HVDC / ATS / 母排 ======== -->
      <div class="grid cols-3">
        <!-- HVDC 直流电源 -->
        <div class="card" v-if="s.hvdc?.length">
          <div class="card-head">
            <span class="ct">{{ tl('HVDC 直流电源') }}</span>
            <span class="pill g">{{ s.hvdc.length }} {{ tl('路') }}</span>
          </div>
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
        </div>

        <!-- ATS 自动转换开关 -->
        <div class="card" v-if="s.ats?.length">
          <div class="card-head">
            <span class="ct">{{ tl('ATS 自动转换开关') }}</span>
            <span class="pill g">{{ s.ats.length }} {{ tl('路') }}</span>
          </div>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('回路') }}</th><th>{{ tl('状态') }}</th><th>{{ tl('模式') }}</th><th>U入(V)</th><th>U出(V)</th><th>P(kW)</th></tr></thead>
            <tbody>
              <tr v-for="a in s.ats" :key="a.id">
                <td class="d-name">{{ a.id }}</td>
                <td><span class="tag" :class="a.state === '常用侧' ? 'g' : 'b'">{{ a.state }}</span></td>
                <td class="muted">{{ a.mode }}</td>
                <td class="mono">{{ fmt(a.uIn, 0) }}</td>
                <td class="mono">{{ fmt(a.uOut, 0) }}</td>
                <td class="mono">{{ fmt(a.p, 0) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="arch-desc muted" style="margin-top:6px">{{ s.ats[0]?.lastSw }}</p>
        </div>

        <!-- 母排 -->
        <div class="card" v-if="s.busbars?.length">
          <div class="card-head">
            <span class="ct">{{ tl('低压母排') }}</span>
            <span class="pill g">{{ s.busbars.length }} {{ tl('段') }}</span>
          </div>
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
        </div>
      </div>

      <!-- ======== 知识库: 阈值 ======== -->
      <div class="card" v-if="s.knowledge?.thresholds?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('设计 / 告警阈值') }}</div>
        <div class="kv-grid">
          <div class="kv" v-for="t in s.knowledge.thresholds" :key="t.k">
            <span class="k">{{ t.k }}</span>
            <span class="v">{{ t.v }}</span>
            <span v-if="t.note" class="note muted">{{ t.note }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 架构 ======== -->
      <div class="card" v-if="s.knowledge?.arch">
        <div class="section-title"><span class="bar"></span>{{ tl('系统架构与组成') }}</div>
        <p class="arch-desc muted">{{ s.knowledge.arch.design }}</p>
        <div class="chips">
          <span class="chip" v-for="c in s.knowledge.arch.components" :key="c">{{ c }}</span>
        </div>
        <p class="redundancy muted" v-if="s.knowledge.arch.redundancy">{{ tl('冗余配置') }}：{{ s.knowledge.arch.redundancy }}</p>
      </div>

      <!-- ======== 知识库: 控制逻辑 ======== -->
      <div class="card" v-for="g in (s.knowledge?.logic || [])" :key="g.title">
        <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
        <div class="logic-list">
          <div class="logic-step" v-for="st in g.steps" :key="st.step">
            <span class="step-no">{{ st.step }}</span>
            <span class="step-text">{{ st.text }}</span>
            <span v-if="st.ok !== undefined" class="ok" :class="st.ok ? 'ok-y' : 'ok-n'">{{ st.ok ? tl('满足') : tl('未满足') }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 故障锁定 ======== -->
      <div class="card scroll-x" v-if="s.knowledge?.faults?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('故障锁定知识库') }}</div>
        <table>
          <thead><tr><th style="width:50px">{{ tl('序号') }}</th><th>{{ tl('故障') }}</th><th>{{ tl('锁定 / 影响') }}</th><th>{{ tl('处置动作') }}</th><th style="width:80px">{{ tl('复位') }}</th></tr></thead>
          <tbody>
            <tr v-for="f in s.knowledge.faults" :key="f.no">
              <td class="mono">{{ f.no }}</td>
              <td class="d-name">{{ f.fault }}</td>
              <td class="muted">{{ f.lock }}</td>
              <td class="muted">{{ f.action }}</td>
              <td><span class="tag" :class="f.manualReset ? 'a' : 'g'">{{ f.manualReset ? tl('人工复位') : tl('自动') }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="knote muted" v-if="s.knowledge?.note">{{ s.knowledge.note }}</p>

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('0.4KV 低压配电') }} · {{ tl('智能电量仪表') }} | {{ tl('设备总数') }} {{ s.total }} {{ tl('台') }} · {{ s.online }} {{ tl('台在线') }} · {{ tl('总有功') }} {{ totalPower }} kW · {{ tl('防雷报警') }} {{ spdAlarmCount }} {{ tl('路') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerLvDetailed, type LvSummary } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<LvSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})

// 馈线平均负载率 / 平均相电压 / 总有功 / 谐波均值
const branches = computed(() => s.value?.branches ?? [])
const avgBranchLoad = computed(() => avgNum(branches.value.map((d) => d.loadPct)))
const avgBranchVoltage = computed(() => avgNum(branches.value.map((d) => d.u)))
const totalPower = computed(() =>
  Number(branches.value.reduce((sum, d) => sum + (d.p || 0), 0).toFixed(0)),
)
const avgThdu = computed(() => avgNum(branches.value.map((d) => d.thdu)))

// 断路器合闸统计
const branchClosedCount = computed(() => branches.value.filter((d) => isClosed(d.breaker)).length)
const branchAllClosed = computed(() => branches.value.length > 0 && branchClosedCount.value === branches.value.length)

// 防雷 SPD
const spdAlarmCount = computed(() => (s.value?.spds ?? []).filter((sp) => sp.status !== '正常').length)
const spdNormalCount = computed(() => (s.value?.spds ?? []).filter((sp) => sp.status === '正常').length)

// 变压器
const txRunningCount = computed(() => (s.value?.transformers ?? []).filter((t) => t.state === '运行').length)
const txAllRunning = computed(() => {
  const list = s.value?.transformers ?? []
  return list.length > 0 && txRunningCount.value === list.length
})

// UPS
const upsNormalCount = computed(() => (s.value?.upsGroups ?? []).filter((u) => u.state === '正常').length)
const upsAllNormal = computed(() => {
  const list = s.value?.upsGroups ?? []
  return list.length > 0 && upsNormalCount.value === list.length
})

// 智能电量仪表采集对象
const collectTargets = computed(() => [
  '三相电压 Ua/Ub/Uc', '三相电流 Ia/Ib/Ic', '频率', '有功功率', '无功功率',
  '功率因数', '电度', '谐波 THD-U/THD-I', '断路器合分状态', '防雷器 SPD 状态',
  'UPS 旁路/模式', 'ATS 切换',
])

// ---- 工具函数 ----
function avgNum(list: number[]): number {
  const vals = list.filter((v) => v != null && Number.isFinite(v))
  if (!vals.length) return 0
  return Number((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1))
}

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
  if (isClosed(v)) return 'g'
  if (v.includes('分闸') || v.includes('分')) return 'b'
  return 'a'
}

function pfCls(pf: number): string {
  if (pf >= 0.95) return 'g-text'
  if (pf >= 0.9) return 'a-text'
  return 'r-text'
}

function loadCls(load: number): string {
  if (load >= 90) return 'r-text'
  if (load >= 80) return 'a-text'
  return 'g-text'
}

function tempCls(t: number, warn: number, alarm: number): string {
  if (t >= alarm) return 'r-text'
  if (t >= warn) return 'a-text'
  return 'g-text'
}

function thduCls(v: number): string {
  if (v >= 5) return 'r-text'
  if (v >= 3) return 'a-text'
  return 'g-text'
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

async function load() {
  error.value = ''
  try {
    s.value = await getPowerLvDetailed()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
/* ----------  card / head / pill ---------- */
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }

.arch-desc { font-size: 12px; line-height: 1.7; margin: 0 0 10px; }

/* ----------  chips ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 11px; padding: 2px 9px; border-radius: 12px; background: rgba(34,227,255,0.08); color: var(--cyan); border: 1px solid rgba(34,227,255,0.25); }

/* ----------  table ---------- */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10.5px; letter-spacing: .5px; padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid var(--td-line); color: var(--txt); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }
.mini-tbl th, .mini-tbl td { font-size: 11px; padding: 5px 6px; }

.d-name { font-weight: 500; color: var(--txt); }
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }

/* 文本色 (用于 td 数值着色) */
.g-text { color: var(--green); }
.a-text { color: var(--amber); }
.r-text { color: var(--red); }

/* ----------  tag ---------- */
.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: var(--blue); border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* ----------  kv-grid ---------- */
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); }
.v { font-size: 13px; color: var(--txt); font-weight: 600; }
.note { font-size: 10px; }

/* ----------  知识库 ---------- */
.section-title { font-size: 13px; font-weight: 700; color: var(--cyan); margin: 0 0 10px; display: flex; align-items: center; gap: 8px; }
.section-title::before { content: ""; width: 4px; height: 14px; border-radius: 2px; background: var(--cyan); }
.section-title .bar { display: none; }
.logic-list { display: flex; flex-direction: column; gap: 8px; }
.logic-step { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--txt); line-height: 1.5; }
.step-no { flex: 0 0 auto; width: 20px; height: 20px; border-radius: 50%; background: var(--cyan); color: #061021; font-size: 11px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.step-text { flex: 1; }
.ok { flex: 0 0 auto; font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.ok-y { background: rgba(43,212,122,.15); color: var(--green); }
.ok-n { background: rgba(255,77,94,.15); color: var(--red); }
.redundancy { font-size: 12px; margin: 10px 0 0; }
.knote { font-size: 12px; font-style: italic; text-align: center; margin-top: 12px; }

/* ----------  layout ---------- */
.grid { display: grid; gap: 12px; }
.cols-3 { grid-template-columns: repeat(3, 1fr); }
@media (max-width: 1180px) { .cols-3 { grid-template-columns: 1fr; } }

/* ----------  misc ---------- */
.flex { display: flex; }
.center { align-items: center; }
.muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; }
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
