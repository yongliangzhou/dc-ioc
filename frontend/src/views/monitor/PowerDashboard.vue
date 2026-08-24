<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }}</h1>
      <span class="sub"
        >{{ tl('nav.hv') }} / {{ tl('nav.lv') }} / {{ tl('nav.genset') }} / {{ tl('nav.fuel') }} /
        {{ tl('nav.battery') }} {{ tl('·') }} {{ tl('总览 · 点击进入子系统') }}</span
      >
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard
        metric-name="power-total"
        :label="tl('电力设备总数')"
        :value="overview.totalEquipment"
        unit="台"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="power-online"
        :label="tl('在线率')"
        :value="onlinePercent"
        unit="%"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="power-fault"
        :label="tl('故障')"
        :value="overview.faultCount"
        unit="台"
        :quality="overview.faultCount ? 'bad' : 'good'"
        :online="true"
        :severity="overview.faultCount ? 'crit' : 'normal'"
      />
      <MetricCard
        metric-name="power-warning"
        :label="tl('告警')"
        :value="overview.warningCount"
        unit="台"
        :quality="overview.warningCount ? 'uncertain' : 'good'"
        :online="true"
        :severity="overview.warningCount ? 'warn' : 'normal'"
      />
    </div>

    <!-- 五子系统入口卡片 -->
    <div class="grid cols-2" v-if="overview">
      <router-link to="/monitor/power/hv" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.hv') }}</span
          ><span class="pill" :class="pillCls(overview.hv)"
            >{{ overview.hv.online }}/{{ overview.hv.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ pct(overview.hv.avgLoadPercent) }}</span
          ><span class="k">{{ tl('平均电压') }}</span
          ><span class="v">{{ volt(overview.hv.avgVoltage) }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/power/lv" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.lv') }}</span
          ><span class="pill" :class="pillCls(overview.lv)"
            >{{ overview.lv.online }}/{{ overview.lv.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ pct(overview.lv.avgLoadPercent) }}</span
          ><span class="k">{{ tl('平均电压') }}</span
          ><span class="v">{{ volt(overview.lv.avgVoltage) }}</span>
        </div>
      </router-link>
    </div>
    <!-- 配电链路可视化入口 -->
    <div class="grid" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/power/linkage" class="entry-card linkage-entry">
        <div class="card-head">
          <span class="ct">{{ tl('配电链路可视化') }}</span>
          <span class="pill">{{ tl('端到端') }}</span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('链路') }}</span
          ><span class="v">{{ tl('市电 → 中压 → 变压器 → 低压 → UPS → 机柜') }}</span>
          <span class="k">{{ tl('特性') }}</span
          ><span class="v">{{ tl('实时状态 · 告警点击定位') }}</span>
        </div>
      </router-link>
    </div>
    <div class="grid cols-3" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/power/genset" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.genset') }}</span
          ><span class="pill" :class="pillCls(overview.genset)"
            >{{ overview.genset.online }}/{{ overview.genset.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ pct(overview.genset.avgLoadPercent) }}</span
          ><span class="k">{{ tl('平均电压') }}</span
          ><span class="v">{{ volt(overview.genset.avgVoltage) }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/power/fuel" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.fuel') }}</span
          ><span class="pill" :class="pillCls(overview.fuel)"
            >{{ overview.fuel.online }}/{{ overview.fuel.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ pct(overview.fuel.avgLoadPercent) }}</span
          ><span class="k">{{ tl('平均电压') }}</span
          ><span class="v">{{ volt(overview.fuel.avgVoltage) }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/power/battery" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.battery') }}</span
          ><span class="pill" :class="pillCls(overview.battery)"
            >{{ overview.battery.online }}/{{ overview.battery.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ pct(overview.battery.avgLoadPercent) }}</span
          ><span class="k">{{ tl('平均电压') }}</span
          ><span class="v">{{ volt(overview.battery.avgVoltage) }}</span>
        </div>
      </router-link>
    </div>

    <!-- 加载 / 错误态 -->
    <Panel v-if="!overview && !error">
      <div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div>
    </Panel>
    <Panel v-if="error">
      <div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ tl('common.error') }}: {{ error }}</span>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getPowerOverview, type PowerOverview, type PowerSystemSummary } from '@/api/power'
const { t: tl } = useI18n()

const overview = ref<PowerOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

function pillCls(s: PowerSystemSummary) {
  return s.online === s.total ? 'g' : 'a'
}
function pct(v: number | null) {
  return v != null ? v.toFixed(1) + '%' : '-'
}
function volt(v: number | null) {
  return v != null ? v.toFixed(0) + 'V' : '-'
}

async function load() {
  error.value = ''
  try {
    overview.value = await getPowerOverview()
  } catch (e: unknown) {
    error.value = (e as ErrorLike)?.message || String(e)
  }
}

onMounted(load)
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.ct {
  font-weight: 600;
  font-size: 14px;
}

.kvs {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  font-size: 12.5px;
}
.k {
  color: var(--muted);
}
.v {
  text-align: right;
  font-weight: 500;
}

.entry-card {
  display: block;
  text-decoration: none;
  color: inherit;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  transition:
    border-color 0.2s,
    transform 0.15s,
    box-shadow 0.2s;
}
.entry-card:hover {
  border-color: rgba(34, 227, 255, 0.45);
  box-shadow: var(--glow);
  transform: translateY(-2px);
}
</style>
