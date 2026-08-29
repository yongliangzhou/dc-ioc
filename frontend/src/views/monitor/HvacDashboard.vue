<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.hvacMonitor') }}</h1>
      <span class="sub"
        >{{ tl('冷源系统') }} / {{ tl('空调末端') }} / {{ tl('液冷系统') }} {{ tl('·') }}
        {{ tl('总览 · 点击进入子系统') }}</span
      >
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard
        metric-name="hvac-total"
        :label="tl('HVAC 设备总数')"
        :value="overview.totalEquipment"
        unit="台"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="hvac-online"
        :label="tl('在线率')"
        :value="onlinePercent"
        unit="%"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="hvac-fault"
        :label="tl('故障')"
        :value="overview.faultCount"
        unit="台"
        :quality="overview.faultCount ? 'bad' : 'good'"
        :online="true"
        :severity="overview.faultCount ? 'crit' : 'normal'"
      />
      <MetricCard
        metric-name="hvac-warning"
        :label="tl('告警')"
        :value="overview.warningCount"
        unit="台"
        :quality="overview.warningCount ? 'uncertain' : 'good'"
        :online="true"
        :severity="overview.warningCount ? 'warn' : 'normal'"
      />
    </div>

    <!-- 三子系统入口卡片 -->
    <div class="grid cols-3" v-if="overview">
      <router-link to="/monitor/hvac/chiller" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.chiller') }}</span>
          <span class="pill" :class="overview.chiller.online === overview.chiller.total ? 'g' : 'a'"
            >{{ overview.chiller.online }}/{{ overview.chiller.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均负载率') }}</span
          ><span class="v">{{ overview.chiller.avgLoadPercent?.toFixed(1) ?? '-' }}%</span>
          <span class="k">{{ tl('进水温度均值') }}</span
          ><span class="v">{{ overview.chiller.avgTemperatureIn?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('出水温度均值') }}</span
          ><span class="v">{{ overview.chiller.avgTemperatureOut?.toFixed(1) ?? '-' }}°C</span>
        </div>
      </router-link>

      <router-link to="/monitor/hvac/crac" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.crac') }} (CRAC)</span>
          <span class="pill" :class="overview.crac.online === overview.crac.total ? 'g' : 'a'"
            >{{ overview.crac.online }}/{{ overview.crac.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('送风温度均值') }}</span
          ><span class="v">{{ overview.crac.avgTemperatureOut?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('回风温度均值') }}</span
          ><span class="v">{{ overview.crac.avgTemperatureIn?.toFixed(1) ?? '-' }}°C</span>
          <span class="k">{{ tl('回风湿度均值') }}</span
          ><span class="v">{{ overview.crac.avgHumidityIn?.toFixed(1) ?? '-' }}%</span>
          <span class="k">{{ tl('风机转速均值') }}</span
          ><span class="v">{{ overview.crac.avgFanSpeed?.toFixed(0) ?? '-' }}%</span>
        </div>
      </router-link>

      <router-link to="/monitor/hvac/liquid" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.liquidCooling') }}</span>
          <span
            class="pill"
            :class="overview.liquidCooling.online === overview.liquidCooling.total ? 'g' : 'a'"
            >{{ overview.liquidCooling.online }}/{{ overview.liquidCooling.total }}
            {{ tl('在线') }}</span
          >
        </div>
        <div class="kvs">
          <span class="k">{{ tl('平均流量') }}</span
          ><span class="v">{{ overview.liquidCooling.avgFlowRate?.toFixed(1) ?? '-' }} L/min</span>
          <span class="k">{{ tl('CDU进水温度均值') }}</span
          ><span class="v"
            >{{ overview.liquidCooling.avgCdiTemperature?.toFixed(1) ?? '-' }}°C</span
          >
          <span class="k">{{ tl('CDU出水温度均值') }}</span
          ><span class="v"
            >{{ overview.liquidCooling.avgCdoTemperature?.toFixed(1) ?? '-' }}°C</span
          >
        </div>
      </router-link>
    </div>
    <!-- 制冷链路可视化入口 -->
    <div class="grid" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/hvac/linkage" class="entry-card linkage-entry">
        <div class="card-head">
          <span class="ct">{{ tl('制冷链路可视化') }}</span>
          <span class="pill">{{ tl('一次系统') }}</span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('循环') }}</span
          ><span class="v">{{ tl('冷却水 / 冷冻水双循环') }}</span>
          <span class="k">{{ tl('特性') }}</span
          ><span class="v">{{ tl('水流方向 · 设备状态跳转') }}</span>
        </div>
      </router-link>
    </div>
    <!-- 温度云图入口 -->
    <div class="grid" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/hvac/thermal" class="entry-card linkage-entry">
        <div class="card-head">
          <span class="ct">{{ tl('温度云图') }}</span>
          <span class="pill">{{ tl('三层') }}</span>
        </div>
        <div class="kvs">
          <span class="k">{{ tl('层级') }}</span
          ><span class="v">{{ tl('机房 / 通道 / 机柜') }}</span>
          <span class="k">{{ tl('特性') }}</span
          ><span class="v">{{ tl('TOP5 热点 · 区间可调') }}</span>
        </div>
      </router-link>
    </div>

    <!-- 加载 / 错误态 -->
    <Panel v-if="!overview && !error">
      <div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('加载中...') }}</span>
      </div>
    </Panel>
    <Panel v-if="error">
      <div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ tl('加载失败') }}: {{ error }}</span>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { toErrorMessage } from '@/composables/useAsyncPage'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getHvacOverview, type HvacOverview } from '@/api/hvac'

const overview = ref<HvacOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

async function load() {
  error.value = ''
  try {
    overview.value = await getHvacOverview()
  } catch (e: unknown) {
    error.value = toErrorMessage(e)
  }
}

onMounted(load)
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
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
  margin-bottom: 4px;
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
