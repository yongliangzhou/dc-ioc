<template>
  <div class="app">
    <!-- ===== 顶栏 (独立组件, 高频更新不驱动 router-view 重渲染) ===== -->
    <TopBar />

    <div class="body">
      <!-- ===== 侧边导航 ===== -->
      <nav class="side">
        <div v-for="g in nav" :key="g.title" class="nav-group">
          <div class="gtitle">{{ g.title }}</div>
          <router-link
            v-for="it in g.items" :key="it.path" :to="it.path"
            class="nav-item" :class="{ active: isActive(it.path) }">
            <span class="ico">{{ it.ico }}</span>{{ it.title }}
            <span v-if="it.badge" class="badge" :class="{ alert: it.alert }">{{ it.badge }}</span>
          </router-link>
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
import ErrorBoundary from "@/components/common/ErrorBoundary.vue";
import { realtimeLinkage } from "@/engine/realtimeLinkage";

const route = useRoute();
const isActive = (p: string) => route.path === p;
const { t } = useI18n();

interface NavItem { path: string; title: string; ico: string; badge?: string; alert?: boolean }
interface NavGroup { title: string; items: NavItem[] }

const nav = computed<NavGroup[]>(() => [
  { title: t("nav.overview"), items: [
    { path: "/overview", title: t("nav.dashboard"), ico: "◈" },
  ] },
  {
    title: t("nav.opsPlatform"), items: [
      { path: "/twin/dashboard", title: t("nav.twin"), ico: "🌀" },
      { path: "/analysis/capacity", title: t("nav.capacity"), ico: "📊" },
      { path: "/analysis/energy", title: t("nav.energy"), ico: "🌱" },
      { path: "/ops/alarms", title: t("nav.alarms"), ico: "🔔", badge: "7", alert: true },
      { path: "/ops/alarm-history", title: t("nav.alarmHistory"), ico: "🕘" },
      { path: "/ops/knowledge", title: t("nav.knowledge"), ico: "📚" },
      { path: "/ops/assistant", title: t("nav.assistant"), ico: "🤖" },
    ],
  },
  {
    title: t("nav.facilityMonitoring"), items: [
      { path: "/monitor/hvac", title: t("nav.hvacMonitor"), ico: "❄" },
      { path: "/monitor/power", title: t("nav.powerMonitor"), ico: "⚡" },
      { path: "/monitor/security", title: t("nav.securityAndFire"), ico: "🛡" },
      { path: "/monitor/network", title: t("nav.networkMonitor"), ico: "🌐" },
      { path: "/monitor/health", title: t("nav.health"), ico: "💚" },
    ],
  },
  {
    title: t("nav.opsManagement"), items: [
      { path: "/ops/inspection", title: t("nav.inspect"), ico: "🔍" },
      { path: "/ops/maintenance", title: t("nav.maintain"), ico: "🔧" },
      { path: "/ops/drill", title: t("nav.drill"), ico: "🎯" },
      { path: "/ops/risk", title: t("nav.risk"), ico: "⚠" },
      { path: "/ops/duty", title: t("nav.duty"), ico: "🕐" },
      { path: "/ops/tickets", title: t("nav.tickets"), ico: "📋", badge: "6", alert: true },
      { path: "/ops/collector", title: t("nav.collector"), ico: "🛰" },
      { path: "/ops/telemetry", title: t("nav.telemetry"), ico: "📡" },
    ],
  },
  {
    title: t("nav.assetManagement"), items: [
      { path: "/ops/cabinets", title: t("nav.cabinets"), ico: "🗄" },
      { path: "/ops/equipment", title: t("nav.equipment"), ico: "📇" },
    ],
  },
  {
    title: t("admin.title"), items: [
      { path: "/admin/audit", title: t("admin.audit"), ico: "🧾" },
    ],
  },
]);

/* 实时联动 (应用级, 不在模板中使用, 不会驱动 router-view 重渲染) */
onMounted(() => {
  realtimeLinkage.start(Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000));
});
onBeforeUnmount(() => { realtimeLinkage.stop(); });
</script>
