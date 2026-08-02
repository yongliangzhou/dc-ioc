<template>
  <div class="app">
    <!-- ===== 顶栏 (独立组件, 高频更新不驱动 router-view 重渲染) ===== -->
    <TopBar />

    <div class="body">
      <!-- ===== 侧边导航 ===== -->
      <nav class="side">
        <div v-for="g in nav" :key="g.title" class="nav-group">
          <div class="gtitle">{{ g.title }}</div>
          <template v-for="it in g.items" :key="it.path">
            <router-link
              :to="it.path"
              class="nav-item"
              :class="{ active: isActive(it.path) }">
              <NavIcon :name="it.ico" />{{ it.title }}
              <span v-if="it.badge" class="badge" :class="{ alert: it.alert }">{{ it.badge }}</span>
            </router-link>
            <router-link
              v-for="c in (it.children ?? [])"
              :key="c.path"
              :to="c.path"
              class="nav-item sub"
              :class="{ active: isActive(c.path) }">
              <NavIcon :name="c.ico" />{{ c.title }}
            </router-link>
          </template>
        </div>
      </nav>

      <!-- ===== 主内容 (ErrorBoundary 包裹: 单面板崩溃不白屏) ===== -->
      <main class="main">
        <ErrorBoundary>
          <router-view />
        </ErrorBoundary>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import TopBar from "@/components/layout/TopBar.vue";
import NavIcon from "@/components/layout/NavIcon.vue";
import ErrorBoundary from "@/components/common/ErrorBoundary.vue";
import { realtimeLinkage } from "@/engine/realtimeLinkage";

const route = useRoute();
const isActive = (p: string) => route.path === p || route.path.startsWith(p + "/");
const { t } = useI18n();

interface NavItem { path: string; title: string; ico: string; badge?: string; alert?: boolean; children?: NavItem[] }
interface NavGroup { title: string; items: NavItem[] }

const nav = computed<NavGroup[]>(() => [
  { title: t("nav.overview"), items: [
    { path: "/overview", title: t("nav.dashboard"), ico: "LayoutDashboard" },
  ] },
  {
    title: t("nav.opsPlatform"), items: [
      { path: "/twin/dashboard", title: t("nav.twin"), ico: "Map" },
      { path: "/analysis/capacity", title: t("nav.capacity"), ico: "BarChart3" },
      { path: "/analysis/energy", title: t("nav.energy"), ico: "Leaf" },
      { path: "/ops/alarms", title: t("nav.alarms"), ico: "Bell", badge: "7", alert: true },
      { path: "/ops/alarm-history", title: t("nav.alarmHistory"), ico: "Clock" },
      { path: "/ops/knowledge", title: t("nav.knowledge"), ico: "BookOpen" },
      { path: "/ops/assistant", title: t("nav.assistant"), ico: "Bot" },
    ],
  },
  {
    title: t("nav.facilityMonitoring"), items: [
      { path: "/monitor/hvac", title: t("nav.hvacMonitor"), ico: "Snowflake", children: [
        { path: "/monitor/hvac/chiller", title: t("nav.chiller"), ico: "Thermometer" },
        { path: "/monitor/hvac/crac", title: t("nav.crac"), ico: "Wind" },
        { path: "/monitor/hvac/liquid", title: t("nav.liquidCooling"), ico: "Droplets" },
      ] },
      { path: "/monitor/power", title: t("nav.powerMonitor"), ico: "Zap", children: [
        { path: "/monitor/power/hv", title: t("nav.hv"), ico: "PlugZap" },
        { path: "/monitor/power/lv", title: t("nav.lv"), ico: "Gauge" },
        { path: "/monitor/power/genset", title: t("nav.genset"), ico: "Zap" },
        { path: "/monitor/power/fuel", title: t("nav.fuel"), ico: "Fuel" },
        { path: "/monitor/power/battery", title: t("nav.battery"), ico: "BatteryFull" },
      ] },
      { path: "/monitor/security", title: t("nav.securityAndFire"), ico: "Shield", children: [
        { path: "/monitor/security/cctv", title: t("nav.securityCctv"), ico: "Video" },
        { path: "/monitor/security/acs", title: t("nav.securityAcs"), ico: "DoorOpen" },
        { path: "/monitor/security/ids", title: t("nav.securityIds"), ico: "Eye" },
        { path: "/monitor/security/fire", title: t("nav.securityFire"), ico: "Flame" },
      ] },
      { path: "/monitor/net", title: t("nav.networkMonitor"), ico: "Globe", children: [
        { path: "/monitor/net/switches", title: t("nav.networkSwitch"), ico: "Network" },
        { path: "/monitor/net/routers", title: t("nav.networkRouter"), ico: "Router" },
        { path: "/monitor/net/firewalls", title: t("nav.networkFirewall"), ico: "ShieldCheck" },
        { path: "/monitor/net/wireless", title: t("nav.networkWireless"), ico: "Wifi" },
      ] },
      { path: "/monitor/health", title: t("nav.health"), ico: "HeartPulse" },
    ],
  },
  {
    title: t("nav.opsManagement"), items: [
      { path: "/ops/inspection", title: t("nav.inspect"), ico: "Search" },
      { path: "/ops/maintenance", title: t("nav.maintain"), ico: "Wrench" },
      { path: "/ops/drill", title: t("nav.drill"), ico: "Target" },
      { path: "/ops/risk", title: t("nav.risk"), ico: "AlertTriangle" },
      { path: "/ops/duty", title: t("nav.duty"), ico: "Clock" },
      { path: "/ops/tickets", title: t("nav.tickets"), ico: "ClipboardList", badge: "6", alert: true },
      { path: "/ops/collector", title: t("nav.collector"), ico: "Antenna" },
      { path: "/ops/telemetry", title: t("nav.telemetry"), ico: "Radio" },
    ],
  },
  {
    title: t("nav.assetManagement"), items: [
      { path: "/ops/cabinets", title: t("nav.cabinets"), ico: "ServerCog" },
      { path: "/ops/equipment", title: t("nav.equipment"), ico: "FileText" },
    ],
  },
  {
    title: t("admin.title"), items: [
      { path: "/admin/audit", title: t("admin.audit"), ico: "ScrollText" },
    ],
  },
]);

/* 实时联动 (应用级, 不在模板中使用, 不会驱动 router-view 重渲染) */
onMounted(() => {
  realtimeLinkage.start(Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000));
});
onBeforeUnmount(() => { realtimeLinkage.stop(); });
</script>

<style scoped>
.nav-item.sub {
  padding-left: 36px;
  font-size: 12px;
  opacity: 0.82;
}
.nav-item.sub :deep(.nav-icon) {
  opacity: 0.7;
}
</style>
