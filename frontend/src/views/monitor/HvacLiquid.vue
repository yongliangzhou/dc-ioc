<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.hvacMonitor') }} {{ tl('·') }} {{ tl('nav.liquidCooling') }}</h1>
      <span class="sub">{{ tl('液冷系统') }} · CDU / {{ tl('冷板GPU') }} / {{ tl('管路') }} / {{ tl('漏液检测') }} / {{ tl('冷却液品质') }} / {{ tl('热排放及余热回收') }} {{ tl('·') }} {{ tl('分布式DCS实时监控 (ODCC标准)') }}</span>
    </div>

    <!-- ======== 总览 KPI Row 1 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="liquid-mode" :label="tl('运行模式')" :value="0" :unit="s.systemMode" quality="good" :online="true" icon-hint="mode" />
      <MetricCard metric-name="liquid-cap" :label="tl('制冷总容量/已用')" :value="s.coolingCapUsed" :unit="`/ ${s.totalCoolingCap} MW`" quality="good" :online="true" icon-hint="power" />
      <MetricCard metric-name="liquid-cr" :label="tl('制冷利用率')" :value="s.capRate" unit="%" :quality="s.capRate > 85 ? 'uncertain' : 'good'" :severity="s.capRate > 90 ? 'warn' : 'normal'" :online="true" />
      <MetricCard metric-name="liquid-outdoor" :label="tl('室外温/湿')" :value="s.outdoorT" :unit="`°C / ${s.outdoorRH}%`" quality="good" :online="true" icon-hint="temp" />
    </div>

    <!-- ======== KPI Row 2 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="liquid-pri" :label="tl('一次侧供/回水温')" :value="s.primarySupplyTemp" :unit="`/ ${s.primaryReturnTemp}°C`" quality="good" :online="true" icon-hint="temp" />
      <MetricCard metric-name="liquid-pri-flow" :label="tl('一次侧流量/压力')" :value="s.primaryFlow" :unit="`m³/h · ${s.primaryPressure} bar`" quality="good" :online="true" icon-hint="flow" />
      <MetricCard metric-name="liquid-sec" :label="tl('二次侧供/回液温')" :value="s.secSupplyTemp" :unit="`/ ${s.secReturnTemp}°C · ΔT=${s.deltaT}°C`" quality="good" :online="true" icon-hint="temp" />
      <MetricCard metric-name="liquid-sec-flow" :label="tl('二次侧流量/压力')" :value="s.secFlow" :unit="`m³/h · ${s.secPressure} bar`" quality="good" :online="true" icon-hint="flow" />
    </div>

    <!-- ======== KPI Row 3 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="liquid-pue" :label="tl('PUE 贡献值')" :value="s.pueContribution" unit="" :quality="s.pueContribution < 0.08 ? 'good' : 'uncertain'" :online="true" icon-hint="power" />
      <MetricCard metric-name="liquid-free" :label="tl('年自然冷可用')" :value="s.freeCoolingHours" unit="h" quality="good" :online="true" />
      <MetricCard metric-name="liquid-hr" :label="tl('余热回收量')" :value="s.heatRecoveryMW" unit="MW" quality="good" :online="true" />
      <MetricCard metric-name="liquid-leak-kpi" :label="tl('漏液告警/总数')" :value="s.leakAlarmCount" :unit="`/ ${s.leakTotalSensors} {{ tl('传感器') }}`" :quality="s.leakAlarmCount ? 'bad' : 'good'" :severity="s.leakAlarmCount ? 'crit' : 'normal'" :online="true" />
    </div>

    <!-- 加载/错误态 -->
    <template v-if="!s">
      <div class="card" v-if="!error"><div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div></div>
      <div class="card" v-if="error"><div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div></div>
    </template>

    <template v-else>
      <!-- ======== 一次侧 CDU ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('一次侧 CDU') }} ({{ tl('冷却液分配单元') }}) · N+1 {{ tl('冗余') }}</span>
          <span class="pill" :class="s.primaryCDUs.filter(d=>d.state==='运行').length >= 3 ? 'g' : 'a'">{{ s.primaryCDUs.filter(d=>d.state==='运行').length }}/{{ s.primaryCDUs.length }} {{ tl('运行') }}</span>
        </div>
        <div class="device-list">
          <div class="device-row cdu-row" v-for="d in s.primaryCDUs" :key="d.id">
            <div class="d-info">
              <span class="d-status" :class="d.state==='运行'?'g':'m'">●</span>
              <span class="d-name">{{ d.name }}</span>
              <span class="d-code">{{ d.id }}</span>
            </div>
            <div class="cdu-metrics-block">
              <div class="cdu-metrics">
                <span class="ml">{{ tl('一次侧') }}</span> {{ d.priInTemp }}→{{ d.priOutTemp }}°C · {{ d.flowPri }}m³/h · ΔP={{ d.dpPri }}bar
                <span class="sep">|</span>
                <span class="ml">{{ tl('二次侧') }}</span> {{ d.secInTemp }}→{{ d.secOutTemp }}°C · {{ d.flowSec }}m³/h · ΔP={{ d.dpSec }}bar
              </div>
              <div class="cdu-metrics">
                <span class="ml">{{ tl('换热效率') }}</span> {{ d.heatExEff }}%
                <span class="sep">|</span>
                <span class="ml">{{ tl('泵速/功率') }}</span> {{ d.pumpSpeed }}% / {{ d.pumpKw }}kW
                <span class="sep">|</span>
                <span class="ml">{{ tl('阀门') }}</span> {{ d.valve }}%
                <span class="sep">|</span>
                <span class="ml">{{ tl('漏液') }}</span> <span :class="d.leakStatus!=='正常'?'a':''">{{ d.leakStatus }}</span>
                <span class="sep">|</span>
                <span>{{ d.runHrs }}h</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 二次侧 CDU ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('二次侧 CDU') }} · {{ tl('按区域分组') }}</span>
          <span class="pill" :class="s.secondaryCDUs.filter(d=>d.state==='运行').length >= 6 ? 'g' : 'a'">{{ s.secondaryCDUs.filter(d=>d.state==='运行').length }}/{{ s.secondaryCDUs.length }} {{ tl('运行') }}</span>
        </div>
        <div class="device-list">
          <div class="device-row cdu-row" v-for="d in s.secondaryCDUs" :key="d.id">
            <div class="d-info">
              <span class="d-status" :class="d.state==='运行'?'g':d.state==='预警'?'a':'m'">●</span>
              <span class="d-name">{{ d.name }}</span>
              <span class="d-code zone-tag">{{ d.rackGroup }}</span>
            </div>
            <div class="cdu-metrics-block">
              <div class="cdu-metrics">
                <span class="ml">{{ tl('供/回液') }}</span> {{ fmtV(d.supplyTemp) }}→{{ fmtV(d.returnTemp) }}°C · {{ d.flow }}m³/h · ΔP={{ d.dp }}bar
                <span class="sep">|</span>
                <span class="ml">{{ tl('泵速/功率') }}</span> {{ d.pumpSpeed }}% / {{ d.pumpKw }}kW
              </div>
              <div class="cdu-metrics">
                <span class="ml">{{ tl('冷板') }}</span> {{ d.coldPlateOnline }}/{{ d.coldPlateCount }} <span :class="d.coldPlateOnline < d.coldPlateCount ? 'a' : ''">{{ tl('在线') }}</span>
                <span class="sep">|</span>
                <span class="ml">{{ tl('漏液') }}</span> <span :class="d.leakStatus!=='正常'?'a':''">{{ d.leakStatus }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== GPU 冷板级温度监控 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('GPU 冷板级温度监控') }} · {{ tl('进液/出液温度 + 8路GPU核心') }}</span>
          <span class="pill" :class="s.coldPlates.filter(p=>p.state==='预警').length === 0 ? 'g' : 'a'">{{ s.coldPlates.length }} {{ tl('机柜') }} · {{ s.coldPlates.filter(p=>p.state==='预警').length }} {{ tl('预警') }}</span>
        </div>
        <div class="gpu-list" v-if="s.coldPlates.length">
          <div class="gpu-row" v-for="p in s.coldPlates" :key="p.rackId">
            <div class="gpu-head">
              <span class="d-status" :class="p.state==='正常'?'g':'a'">●</span>
              <span class="gpu-rack">{{ p.rackId }}</span>
              <span class="gpu-type">{{ p.nodeType }}</span>
              <span class="gpu-io">{{ tl('进') }}{{ p.inletTemp }}°C → {{ tl('出') }}{{ p.outletTemp }}°C · {{ p.flow }}L/min · ΔP={{ p.dp }}bar</span>
            </div>
            <div class="gpu-cores">
              <span v-for="(t, i) in p.gpuTemp" :key="i" class="gpu-core" :class="t > 75 ? 'r' : t > 70 ? 'a' : 'g'">
                GPU{{ i }} {{ t.toFixed(1) }}
              </span>
            </div>
          </div>
        </div>
        <div class="empty-tip" v-else>{{ tl('暂无冷板温度数据') }}</div>
      </div>

      <!-- ======== 分集液管路 + 漏液检测 ======== -->
      <div class="grid cols-2" v-if="s">
        <!-- 分集液管路 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('分集液管路') }} (Manifold)</span>
          </div>
          <div class="device-list">
            <div class="device-row" v-for="m in s.manifoldsSupply" :key="'s-'+m.id">
              <div class="d-info"><span class="d-status g">●</span><span class="d-name">{{ m.id }} ({{ m.zone }} {{ tl('供液') }})</span></div>
              <div class="d-metrics">{{ m.temp }}°C · {{ m.pressure }}bar · {{ m.flow }}m³/h · {{ m.valvesOpen }}/{{ m.branchCount }}{{ tl('阀') }}</div>
            </div>
            <div class="device-row" v-for="m in s.manifoldsReturn" :key="'r-'+m.id" style="color:var(--txt3)">
              <div class="d-info"><span class="d-status m">●</span><span class="d-name">{{ m.id }} ({{ m.zone }} {{ tl('回液') }})</span></div>
              <div class="d-metrics">{{ m.temp }}°C · {{ m.pressure }}bar · {{ m.flow }}m³/h</div>
            </div>
          </div>
        </div>

        <!-- 漏液检测 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('漏液检测') }} · {{ s.leakTotalSensors }} {{ tl('传感器') }}</span>
            <span class="pill" :class="s.leakAlarmCount === 0 ? 'g' : 'r'">{{ s.leakAlarmCount }}{{ tl('告警') }} / {{ s.leakWarningCount }}{{ tl('预警') }}</span>
          </div>
          <div class="device-list">
            <div class="device-row" v-for="lr in s.leakRope" :key="lr.id">
              <div class="d-info">
                <span class="d-status" :class="lr.status==='报警'?'r':lr.status==='预警'?'a':'g'">●</span>
                <span class="d-name">{{ lr.location }}</span>
              </div>
              <div class="d-metrics">
                <span>{{ lr.status }}</span>
                <span class="sep">|</span>
                <span>{{ lr.length }}m · {{ lr.coverage }}%</span>
              </div>
            </div>
            <div class="device-row" v-for="lp in s.leakPoint" :key="lp.id">
              <div class="d-info">
                <span class="d-status" :class="lp.alarmCount ? 'a' : 'g'">●</span>
                <span class="d-name">{{ lp.id }} ({{ lp.zone }})</span>
              </div>
              <div class="d-metrics">
                {{ lp.count }}{{ tl('点') }}
                <span class="sep">|</span>
                <span :class="lp.alarmCount ? 'a' : ''">{{ lp.alarmCount }}{{ tl('告警') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 冷却液品质 + 热排放 ======== -->
      <div class="grid cols-2" v-if="s">
        <!-- 冷却液品质 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('冷却液品质') }} · {{ s.coolantQuality.type }}</span>
            <span class="pill" :class="s.coolantQuality.status==='正常'?'g':'a'">{{ s.coolantQuality.status }}</span>
          </div>
          <div class="quality-grid">
            <div class="q-item"><span class="q-label">{{ tl('电导率') }}</span><span class="q-val" :class="s.coolantQuality.conductivity > 30 ? 'a' : 'g'">{{ s.coolantQuality.conductivity }} μS/cm</span><span class="q-ref">{{ tl('上限') }} {{ s.control.conductivityMax }}</span></div>
            <div class="q-item"><span class="q-label">pH</span><span class="q-val">{{ s.coolantQuality.ph }}</span><span class="q-ref">8.0~8.5</span></div>
            <div class="q-item"><span class="q-label">{{ tl('乙二醇浓度') }}</span><span class="q-val" :class="s.coolantQuality.glycolConcentration < s.control.glycolMin ? 'a' : 'g'">{{ s.coolantQuality.glycolConcentration }}%</span><span class="q-ref">{{ tl('下限') }} {{ s.control.glycolMin }}%</span></div>
            <div class="q-item"><span class="q-label">{{ tl('腐蚀抑制剂') }}</span><span class="q-val">{{ s.coolantQuality.corrosionInhibitor }}%</span></div>
            <div class="q-item"><span class="q-label">{{ tl('颗粒数') }}</span><span class="q-val">{{ s.coolantQuality.particleCount }} /mL</span></div>
            <div class="q-item"><span class="q-label">{{ tl('上次/下次检测') }}</span><span class="q-val small">{{ fmtDate(s.coolantQuality.lastTested) }} / {{ fmtDate(s.coolantQuality.nextTest) }}</span></div>
          </div>
        </div>

        <!-- 热排放 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('二次侧热排放') }} · {{ s.totalHeatRejected }}MW</span>
            <span class="pill" :class="s.freeCoolingAvailable ? 'g' : ''">{{ s.freeCoolingAvailable ? tl('自然冷可用') : tl('机械制冷') }}</span>
          </div>
          <div class="device-list">
            <div class="sub-section-title">{{ tl('闭式冷却塔') }} ({{ s.approachTemp }}°C {{ tl('逼近') }})</div>
            <div class="device-row" v-for="f in s.towerFans" :key="f.id">
              <div class="d-info"><span class="d-status" :class="f.state==='运行'?'g':'m'">●</span><span class="d-name">{{ f.id }}</span></div>
              <div class="d-metrics">{{ f.fanHz }}Hz · {{ fmtV(f.outletTemp) }}°C · {{ tl('逼近') }}={{ fmtV(f.approach) }}°C</div>
            </div>
            <div class="sub-section-title">{{ tl('干冷器') }}</div>
            <div class="device-row" v-for="dc in s.dryCoolers" :key="dc.id">
              <div class="d-info"><span class="d-status m">●</span><span class="d-name">{{ dc.id }}</span></div>
              <div class="d-metrics">{{ dc.state }} · {{ tl('环温') }} {{ dc.ambientT }}°C</div>
            </div>
            <div class="sub-section-title">{{ tl('排放泵') }}</div>
            <div class="device-row" v-for="rp in s.rejectionPumps" :key="rp.id">
              <div class="d-info"><span class="d-status" :class="rp.state==='运行'?'g':'m'">●</span><span class="d-name">{{ rp.id }}</span></div>
              <div class="d-metrics">{{ rp.hz }}Hz · {{ rp.kw }}kW</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 余热回收 + 控制策略 ======== -->
      <div class="grid cols-2" v-if="s">
        <!-- 余热回收 -->
        <div class="card" v-if="s.heatRecovery.enabled">
          <div class="card-head">
            <span class="ct">{{ tl('余热回收') }} · {{ s.heatRecovery.usageType }}</span>
            <span class="pill g">{{ tl('已启用') }}</span>
          </div>
          <div class="quality-grid">
            <div class="q-item"><span class="q-label">{{ tl('回收功率') }}</span><span class="q-val">{{ s.heatRecovery.recoveryRate }} MW</span></div>
            <div class="q-item"><span class="q-label">{{ tl('供/回热温度') }}</span><span class="q-val">{{ s.heatRecovery.recoveryTemp }}/{{ s.heatRecovery.returnTemp }}°C</span></div>
            <div class="q-item"><span class="q-label">{{ tl('流量') }}</span><span class="q-val">{{ s.heatRecovery.flow }} m³/h</span></div>
            <div class="q-item"><span class="q-label">{{ tl('年CO₂减排') }}</span><span class="q-val g">{{ s.heatRecovery.co2Reduction }} t</span></div>
            <div class="q-item" style="grid-column: span 2"><span class="q-label">{{ tl('年节约费用') }}</span><span class="q-val g">￥{{ (s.heatRecovery.annualSaving / 10000).toFixed(0) }}{{ tl('万') }}</span></div>
          </div>
        </div>

        <!-- 控制策略 -->
        <div class="card" v-if="s.control.description">
          <div class="card-head">
            <span class="ct">{{ tl('控制策略与告警阈值') }}</span>
          </div>
          <div class="ctrl-detail">
            <p class="ctrl-desc">{{ s.control.description }}</p>
            <div class="ctrl-grid">
              <div class="ctrl-kv"><span class="ck">{{ tl('一次侧供液设定') }}</span><span class="cv">{{ s.control.primarySupplySetpoint }}°C</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('二次侧供液设定') }}</span><span class="cv">{{ s.control.secondarySupplySetpoint }}°C</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('逼近温差目标') }}</span><span class="cv">{{ s.control.approachTarget }}°C</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('乙二醇下限') }}</span><span class="cv">{{ s.control.glycolMin }}%</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('电导率上限') }}</span><span class="cv">{{ s.control.conductivityMax }} μS/cm</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('漏液响应') }}</span><span class="cv">{{ s.control.leakResponseTime }}s</span></div>
              <div class="ctrl-kv"><span class="ck">{{ tl('泵冗余') }}</span><span class="cv">{{ s.control.pumpRedundancy }}</span></div>
              <div class="ctrl-kv"><span class="ck">CDU {{ tl('冗余') }}</span><span class="cv">{{ s.control.cdurRedundancy }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('液冷系统') }} · {{ s.total }} {{ tl('台 CDU') }} · {{ s.secondaryCDUs.length }} {{ tl('台二次侧CDU') }} · {{ s.coldPlates.length }} {{ tl('机柜冷板监控') }} · {{ s.leakTotalSensors }} {{ tl('路漏液检测') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getLiquidCooling, type LiquidCoolingSummary } from '@/api/hvac'
const { t: tl } = useI18n()

const s = ref<LiquidCoolingSummary | null>(null)
const error = ref('')

function fmtV(v: number | string): string {
  if (v === '-' || v === null || v === undefined) return '—'
  return String(v)
}

function fmtDate(iso: string): string {
  if (!iso) return '—'
  try { return iso.substring(5, 10).replace('-', '/') + ' ' + iso.substring(11, 16) } catch { return iso }
}

async function load() {
  error.value = ''
  try { s.value = await getLiquidCooling() } catch (e: any) { error.value = e?.message || String(e) }
}
onMounted(load)
</script>

<style scoped>
/* ---- card / head / pill ---- */
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }
.pill.r { background: rgba(255,77,94,0.12); color: var(--red); }

/* ---- 通用 ---- */
.device-list { border-top: 1px solid var(--border); padding-top: 8px; max-height: 520px; overflow-y: auto; }
.device-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; font-size: 11.5px; border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.device-row:last-child { border-bottom: none; }
.d-info { display: flex; align-items: center; gap: 5px; min-width: 0; flex-shrink: 0; }
.d-status { font-size: 8px; flex-shrink: 0; }
.d-status.g { color: var(--green); }
.d-status.r { color: var(--red); }
.d-status.a { color: var(--amber); }
.d-status.m { color: var(--muted); }
.d-name { font-weight: 500; white-space: nowrap; }
.d-code { color: var(--muted); font-size: 10px; }
.d-metrics { color: var(--muted); font-size: 11px; display: flex; gap: 4px; align-items: center; flex-shrink: 0; }
.d-metrics .sep { opacity: 0.3; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
.zone-tag { background: rgba(22,119,255,0.08); color: var(--primary); padding: 1px 6px; border-radius: 4px; font-size: 10px; }

/* ---- CDU 多行 ---- */
.cdu-row { flex-direction: column; gap: 2px; padding: 6px 0; }
.cdu-row .d-info { width: 100%; margin-bottom: 1px; }
.cdu-metrics-block { width: 100%; display: flex; flex-direction: column; gap: 1px; }
.cdu-metrics { display: flex; gap: 2px; align-items: center; width: 100%; font-size: 10.5px; color: var(--txt2); padding: 0 14px; flex-wrap: wrap; }
.cdu-metrics .ml { color: var(--txt3); font-size: 9.5px; min-width: 36px; }
.cdu-metrics .sep { opacity: 0.25; color: var(--muted); }

/* ---- GPU 冷板 ---- */
.gpu-list { border-top: 1px solid var(--border); padding-top: 8px; max-height: 560px; overflow-y: auto; }
.gpu-row { padding: 6px 0; border-bottom: 1px solid var(--border-light, rgba(255,255,255,0.04)); }
.gpu-row:last-child { border-bottom: none; }
.gpu-head { display: flex; align-items: center; gap: 5px; font-size: 11px; margin-bottom: 3px; }
.gpu-rack { font-weight: 600; color: var(--cyan); }
.gpu-type { font-size: 10px; background: var(--bg2); padding: 1px 5px; border-radius: 4px; }
.gpu-io { color: var(--muted); font-size: 10.5px; }
.gpu-cores { display: flex; gap: 4px; flex-wrap: wrap; padding-left: 13px; }
.gpu-core { font-size: 10px; padding: 1px 5px; border-radius: 4px; background: var(--bg2); }
.gpu-core.g { color: var(--green); }
.gpu-core.a { color: var(--amber); }
.gpu-core.r { color: var(--red); }

/* ---- 分集液管路 subtitles ---- */
.sub-section-title { font-size: 10px; color: var(--txt3); padding: 4px 0 2px; border-bottom: 1px dashed rgba(255,255,255,0.05); margin-bottom: 2px; }

/* ---- 冷却液品质 / 余热回收 ---- */
.quality-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px; border-top: 1px solid var(--border); padding-top: 8px; }
.q-item { text-align: center; padding: 5px 4px; border-radius: 6px; background: var(--bg2); }
.q-label { display: block; font-size: 10px; color: var(--txt3); margin-bottom: 2px; }
.q-val { font-size: 14px; font-weight: 700; }
.q-val.g { color: var(--green); }
.q-val.a { color: var(--amber); }
.q-val.small { font-size: 11px; }
.q-ref { display: block; font-size: 9px; color: var(--txt3); margin-top: 1px; }

/* ---- 控制策略 ---- */
.ctrl-detail { border-top: 1px solid var(--border); padding-top: 8px; }
.ctrl-desc { font-size: 11px; color: var(--muted); line-height: 1.5; margin-bottom: 8px; }
.ctrl-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 3px; }
.ctrl-kv { display: flex; justify-content: space-between; align-items: center; padding: 3px 6px; background: var(--bg2); border-radius: 4px; font-size: 11px; }
.ctrl-kv .ck { color: var(--txt3); }
.ctrl-kv .cv { font-weight: 600; color: var(--cyan); }

/* ---- footer ---- */
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
