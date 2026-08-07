<template>
  <div class="dc-cmp">
    <div class="view-head">
      <h1>{{ tl('datacenter.cmpTitle') }}</h1>
      <span class="sub">{{ tl('datacenter.cmpSub') }}</span>
      <router-link class="btn-sm" style="margin-left:auto" :to="{ path: '/ops/datacenter' }">{{ tl('datacenter.title') }}</router-link>
    </div>

    <div v-if="loading" class="empty">{{ tl('common.loading') }}</div>
    <template v-else>
      <!-- 并排 KPI 卡 -->
      <div class="cards">
        <div v-for="c in cmp.centers" :key="c.id" class="card" :class="{ cur: c.id === cmp.currentIdcId }">
          <div class="c-name">{{ c.name }} <span class="c-code mono">{{ c.code }}</span></div>
          <div class="c-region">{{ c.region }}</div>
          <div class="c-grid">
            <div><b>{{ c.powerCapacityMw.toFixed(1) }}</b><label>{{ tl('datacenter.cmpPower') }}</label></div>
            <div><b>{{ c.coolingCapacityMw.toFixed(1) }}</b><label>{{ tl('datacenter.cmpCooling') }}</label></div>
            <div><b>{{ c.rackUsed }}/{{ c.rackCapacity }}</b><label>{{ tl('datacenter.cmpRack') }}</label></div>
            <div><b :class="lvl(c.activeAlarmCount)">{{ c.activeAlarmCount }}</b><label>{{ tl('datacenter.cmpAlarm') }}</label></div>
            <div><b>{{ c.deviceCount }}</b><label>{{ tl('datacenter.kpiDevice') }}</label></div>
            <div><b>{{ c.onlineCount }}</b><label>{{ tl('datacenter.kpiOnline') }}</label></div>
          </div>
        </div>
        <div v-if="!cmp.centers.length" class="empty">{{ tl('common.error') }}</div>
      </div>

      <!-- 对比柱状图 -->
      <Panel class="charts">
        <div class="chart-block">
          <div class="cb-title">{{ tl('datacenter.cmpPower') }}</div>
          <div class="bar-row" v-for="c in cmp.centers" :key="'p' + c.id">
            <span class="bl">{{ c.name }}</span>
            <div class="bar"><i :style="{ width: pct(c.powerCapacityMw, maxPower) + '%', background: 'linear-gradient(90deg,#0ea5e9,#22d3ee)' }" /></div>
            <span class="bv">{{ c.powerCapacityMw.toFixed(1) }}</span>
          </div>
        </div>
        <div class="chart-block">
          <div class="cb-title">{{ tl('datacenter.cmpCooling') }}</div>
          <div class="bar-row" v-for="c in cmp.centers" :key="'c' + c.id">
            <span class="bl">{{ c.name }}</span>
            <div class="bar"><i :style="{ width: pct(c.coolingCapacityMw, maxCooling) + '%', background: 'linear-gradient(90deg,#3b82f6,#22d3ee)' }" /></div>
            <span class="bv">{{ c.coolingCapacityMw.toFixed(1) }}</span>
          </div>
        </div>
        <div class="chart-block">
          <div class="cb-title">{{ tl('datacenter.cmpAlarm') }}</div>
          <div class="bar-row" v-for="c in cmp.centers" :key="'a' + c.id">
            <span class="bl">{{ c.name }}</span>
            <div class="bar"><i :style="{ width: pct(c.activeAlarmCount, maxAlarm) + '%', background: c.activeAlarmCount ? 'linear-gradient(90deg,#f59e0b,#ef4444)' : '#22c55e' }" /></div>
            <span class="bv">{{ c.activeAlarmCount }}</span>
          </div>
        </div>
      </Panel>

      <!-- 统一告警 -->
      <Panel class="alarms">
        <div class="list-head">{{ tl('datacenter.unifiedAlarms') }}
          <span class="sub2">{{ tl('datacenter.unifiedAlarmsSub') }}</span>
        </div>
        <div class="a-row ah">
          <span>{{ tl('datacenter.title') }}</span>
          <span>{{ tl('datacenter.alarmDevice') }}</span>
          <span>{{ tl('datacenter.alarmMetric') }}</span>
          <span>{{ tl('datacenter.alarmLevel') }}</span>
          <span>{{ tl('common.status') }}</span>
        </div>
        <div v-for="(a, i) in alarms.items" :key="i" class="a-row">
          <span>{{ a.idcName }} <em class="mono">{{ a.idcCode }}</em></span>
          <span class="mono">{{ a.deviceId }}</span>
          <span>{{ a.metricName }}</span>
          <span><span class="tag" :class="a.level === 'critical' ? 'r' : a.level === 'warn' ? 'a' : 'b'">{{ a.level }}</span></span>
          <span>{{ a.state }}</span>
        </div>
        <div v-if="!alarms.items.length" class="empty">{{ tl('datacenter.noAlarm') }}</div>
      </Panel>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import { compareIdcs, unifiedAlarms, type IdcCompare, type IdcAlarmResp } from '@/api/idc'

const { t: tl } = useI18n()
const loading = ref(true)
const cmp = ref<IdcCompare>({ centers: [], currentIdcId: null })
const alarms = ref<IdcAlarmResp>({ total: 0, items: [], byIdc: {} })

const maxPower = computed(() => Math.max(1, ...cmp.value.centers.map((c) => c.powerCapacityMw)))
const maxCooling = computed(() => Math.max(1, ...cmp.value.centers.map((c) => c.coolingCapacityMw)))
const maxAlarm = computed(() => Math.max(1, ...cmp.value.centers.map((c) => c.activeAlarmCount)))

function pct(v: number, max: number) {
  return Math.round((v / max) * 100)
}
function lvl(n: number) {
  return n >= 5 ? 'crit' : n > 0 ? 'warn' : 'ok'
}

function load() {
  loading.value = true
  Promise.all([compareIdcs(), unifiedAlarms()])
    .then(([c, a]) => {
      cmp.value = c
      alarms.value = a
    })
    .finally(() => (loading.value = false))
}

onMounted(load)
</script>

<style scoped>
.dc-cmp { display: flex; flex-direction: column; gap: 14px; }
.btn-sm { color: var(--txt2); border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 5px 10px; font-size: 12px; cursor: pointer; text-decoration: none; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
.card.cur { border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan) inset; }
.c-name { font-weight: 700; color: var(--txt-strong); font-size: 14px; }
.c-code { font-size: 10px; color: var(--muted); margin-left: 6px; }
.c-region { font-size: 11px; color: var(--muted); margin: 4px 0 10px; }
.c-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.c-grid div { background: var(--track); border-radius: 8px; padding: 8px; text-align: center; }
.c-grid b { font-size: 15px; color: var(--txt-strong); display: block; }
.c-grid b.crit { color: var(--red); }
.c-grid b.warn { color: var(--amber); }
.c-grid b.ok { color: var(--green); }
.c-grid label { font-size: 10px; color: var(--muted); }
.charts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.chart-block { display: flex; flex-direction: column; gap: 8px; }
.cb-title { font-size: 12px; font-weight: 700; color: var(--txt-strong); }
.bar-row { display: grid; grid-template-columns: 90px 1fr 48px; gap: 8px; align-items: center; }
.bl { font-size: 11px; color: var(--txt2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar { height: 14px; background: var(--track); border-radius: 7px; overflow: hidden; }
.bar > i { display: block; height: 100%; border-radius: 7px; transition: width .4s; }
.bv { font-size: 11px; color: var(--txt2); text-align: right; }
.list-head { font-size: 14px; font-weight: 700; color: var(--txt-strong); margin-bottom: 10px; }
.sub2 { font-size: 11px; color: var(--muted); font-weight: 400; margin-left: 8px; }
.a-row { display: grid; grid-template-columns: 1.4fr 1.2fr 1fr 0.8fr 1fr; gap: 8px; padding: 8px; border-top: 1px solid var(--line); font-size: 12px; color: var(--txt2); }
.a-row.ah { color: var(--muted); font-weight: 600; border-top: none; }
.mono { font-family: monospace; font-size: 11px; }
.empty { text-align: center; color: var(--muted); padding: 24px; font-size: 13px; }
</style>
