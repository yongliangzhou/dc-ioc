<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.securityAndFire') }}</h1>
      <span class="sub"
        >{{ tl('nav.securityCctv') }} / {{ tl('nav.securityAcs') }} / {{ tl('nav.securityIds') }} /
        {{ tl('nav.securityFire') }} {{ tl('·') }} {{ tl('总览 · 点击进入子系统') }}</span
      >
    </div>

    <!-- 总览 KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard
        metric-name="sec-total"
        :label="tl('安防设备总数')"
        :value="overview.totalEquipment"
        unit="台"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="sec-online"
        :label="tl('在线率')"
        :value="onlinePercent"
        unit="%"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="sec-fault"
        :label="tl('故障')"
        :value="overview.faultCount"
        unit="台"
        :quality="overview.faultCount ? 'bad' : 'good'"
        :online="true"
        :severity="overview.faultCount ? 'crit' : 'normal'"
      />
      <MetricCard
        metric-name="sec-warning"
        :label="tl('告警')"
        :value="overview.warningCount"
        unit="台"
        :quality="overview.warningCount ? 'uncertain' : 'good'"
        :online="true"
        :severity="overview.warningCount ? 'warn' : 'normal'"
      />
    </div>

    <!-- 四子系统入口卡片 -->
    <div class="grid cols-2" v-if="overview">
      <router-link to="/monitor/security/cctv" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.securityCctv') }}</span
          ><span class="pill" :class="pillCls(overview.cctv)"
            >{{ overview.cctv.online }}/{{ overview.cctv.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('视频监控 · 实时录像与回放') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('今日事件') }}</span
          ><span class="v">{{ overview.cctv.eventsToday ?? 0 }}</span
          ><span class="k">{{ tl('今日告警') }}</span
          ><span class="v">{{ overview.cctv.alertsToday ?? 0 }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/security/acs" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.securityAcs') }}</span
          ><span class="pill" :class="pillCls(overview.acs)"
            >{{ overview.acs.online }}/{{ overview.acs.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('门禁管理 · 出入控制与授权') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('今日事件') }}</span
          ><span class="v">{{ overview.acs.eventsToday ?? 0 }}</span
          ><span class="k">{{ tl('今日告警') }}</span
          ><span class="v">{{ overview.acs.alertsToday ?? 0 }}</span>
        </div>
      </router-link>
    </div>
    <div class="grid cols-2" v-if="overview" style="margin-top: 12px">
      <router-link to="/monitor/security/ids" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.securityIds') }}</span
          ><span class="pill" :class="pillCls(overview.ids)"
            >{{ overview.ids.online }}/{{ overview.ids.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('防入侵系统 · 周界与内部探测') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('今日事件') }}</span
          ><span class="v">{{ overview.ids.eventsToday ?? 0 }}</span
          ><span class="k">{{ tl('今日告警') }}</span
          ><span class="v">{{ overview.ids.alertsToday ?? 0 }}</span>
        </div>
      </router-link>
      <router-link to="/monitor/security/fire" class="entry-card">
        <div class="card-head">
          <span class="ct">{{ tl('nav.securityFire') }}</span
          ><span class="pill" :class="pillCls(overview.fire)"
            >{{ overview.fire.online }}/{{ overview.fire.total }} {{ tl('在线') }}</span
          >
        </div>
        <div class="sub-label">{{ tl('消防报警 · 烟感/温感/灭火') }}</div>
        <div class="kvs">
          <span class="k">{{ tl('今日事件') }}</span
          ><span class="v">{{ overview.fire.eventsToday ?? 0 }}</span
          ><span class="k">{{ tl('今日告警') }}</span
          ><span class="v">{{ overview.fire.alertsToday ?? 0 }}</span>
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
import {
  getSecurityOverview,
  type SecurityOverview,
  type SecuritySystemSummary,
} from '@/api/security'
const { t: tl } = useI18n()

const overview = ref<SecurityOverview | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!overview.value || !overview.value.totalEquipment) return 0
  return Number(((overview.value.onlineCount / overview.value.totalEquipment) * 100).toFixed(1))
})

function pillCls(s: SecuritySystemSummary) {
  return s.online === s.total ? 'g' : 'a'
}

async function load() {
  error.value = ''
  try {
    overview.value = await getSecurityOverview()
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
  margin-bottom: 4px;
}
.ct {
  font-weight: 600;
  font-size: 14px;
}
.sub-label {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 8px;
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
