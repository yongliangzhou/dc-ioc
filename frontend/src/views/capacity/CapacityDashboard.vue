<template>
  <div class="capacity-db">
    <div class="view-head">
      <h1>{{ tl('nav.capacity') }}</h1>
      <span class="sub">{{ tl('电力·制冷·空间·机柜 四维容量利用率') }}</span>
    </div>

    <!-- KPI -->
    <div class="grid cols-4" v-if="data">
      <MetricCard
        metricName="powerUtil"
        :label="tl('电力利用率')"
        :value="data.overallPowerUtilization"
        unit="%"
        :severity="
          data.overallPowerUtilization > 75
            ? 'crit'
            : data.overallPowerUtilization > 60
              ? 'warn'
              : 'normal'
        "
      />
      <MetricCard
        metricName="coolUtil"
        :label="tl('制冷利用率')"
        :value="data.overallCoolingUtilization"
        unit="%"
        :severity="
          data.overallCoolingUtilization > 75
            ? 'crit'
            : data.overallCoolingUtilization > 60
              ? 'warn'
              : 'normal'
        "
      />
      <MetricCard
        metricName="spaceUtil"
        :label="tl('空间利用率')"
        :value="data.overallSpaceUtilization"
        unit="%"
        :severity="
          data.overallSpaceUtilization > 80
            ? 'crit'
            : data.overallSpaceUtilization > 65
              ? 'warn'
              : 'normal'
        "
      />
      <MetricCard
        metricName="rackUtil"
        :label="tl('机柜利用率')"
        :value="data.overallRackUtilization"
        unit="%"
        :severity="
          data.overallRackUtilization > 80
            ? 'crit'
            : data.overallRackUtilization > 65
              ? 'warn'
              : 'normal'
        "
      />
    </div>
    <Panel v-else-if="loading"
      ><div class="flex center">
        <span class="muted">{{ tl('加载中...') }}</span>
      </div></Panel
    >
    <Panel v-else-if="err"
      ><div class="flex center">
        <span class="muted">{{ err }}</span>
      </div></Panel
    >

    <!-- 机房容量详情 -->
    <div class="grid cols-2" v-if="data?.rooms?.length">
      <Panel v-for="room in data.rooms" :key="room.roomName" :title="room.roomName">
        <div class="cap-bars">
          <div class="cap-row">
            <span class="cap-label">⚡ {{ tl('电力') }}</span>
            <div class="cap-bar-track">
              <div
                class="cap-bar-fill"
                :class="barCls(room.powerUtilization)"
                :style="{ width: (room.powerUtilization ?? 0) + '%' }"
              />
            </div>
            <span class="cap-val">{{ room.powerUtilization ?? '—' }}%</span>
          </div>
          <div class="cap-row">
            <span class="cap-label">❄ {{ tl('制冷') }}</span>
            <div class="cap-bar-track">
              <div
                class="cap-bar-fill"
                :class="barCls(room.coolingUtilization)"
                :style="{ width: (room.coolingUtilization ?? 0) + '%' }"
              />
            </div>
            <span class="cap-val">{{ room.coolingUtilization ?? '—' }}%</span>
          </div>
          <div class="cap-row">
            <span class="cap-label">📏 {{ tl('空间') }}</span>
            <div class="cap-bar-track">
              <div
                class="cap-bar-fill"
                :class="barCls(room.spaceUtilization)"
                :style="{ width: (room.spaceUtilization ?? 0) + '%' }"
              />
            </div>
            <span class="cap-val">{{ room.spaceUtilization ?? '—' }}%</span>
          </div>
          <div class="cap-row">
            <span class="cap-label">🗄 {{ tl('机柜') }}</span>
            <div class="cap-bar-track">
              <div
                class="cap-bar-fill"
                :class="barCls(room.rackUtilization)"
                :style="{ width: (room.rackUtilization ?? 0) + '%' }"
              />
            </div>
            <span class="cap-val">{{ room.rackUtilization ?? '—' }}%</span>
          </div>
        </div>
      </Panel>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getCapacityOverview, type CapacityOverview } from '@/api/capacity'
const { t: tl } = useI18n()

const loading = ref(true)
const err = ref('')
const data = ref<CapacityOverview | null>(null)

function barCls(v: number | null) {
  if (!v) return ''
  return v > 80 ? 'crit' : v > 60 ? 'warn' : 'ok'
}

onMounted(async () => {
  try {
    data.value = await getCapacityOverview()
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.capacity-db {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.cap-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cap-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.cap-label {
  width: 80px;
  font-size: 12px;
  color: var(--txt);
}
.cap-bar-track {
  flex: 1;
  height: 10px;
  background: var(--bg);
  border-radius: 5px;
  overflow: hidden;
}
.cap-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.5s ease;
}
.cap-bar-fill.ok {
  background: var(--green);
}
.cap-bar-fill.warn {
  background: var(--amber);
}
.cap-bar-fill.crit {
  background: var(--red);
}
.cap-val {
  width: 48px;
  text-align: right;
  font-size: 12px;
  color: var(--txt2);
  font-variant-numeric: tabular-nums;
}
</style>
