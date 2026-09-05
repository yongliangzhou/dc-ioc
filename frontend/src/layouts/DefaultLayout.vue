<template>
  <div class="app">
    <!-- ===== 顶栏 (独立组件, 高频更新不驱动 router-view 重渲染) ===== -->
    <TopBar />

    <div class="body">
      <!-- ===== 侧边导航 ===== -->
      <nav class="side">
        <div v-for="g in nav" :key="g.id" class="nav-group">
          <button
            type="button"
            class="gtitle"
            :aria-expanded="!collapsed[g.id]"
            @click="toggle(g.id)"
          >
            <span class="gtitle-text">{{ g.title }}</span>
            <NavIcon
              class="gtitle-arrow"
              :name="collapsed[g.id] ? 'ChevronRight' : 'ChevronDown'"
            />
          </button>
          <div class="nav-items" v-show="!collapsed[g.id]">
            <template v-for="it in g.items" :key="it.path">
              <router-link :to="it.path" class="nav-item" :class="{ active: isActive(it.path) }">
                <NavIcon :name="it.ico" />{{ it.title }}
                <span v-if="it.badge" class="badge" :class="{ alert: it.alert }">{{
                  it.badge
                }}</span>
              </router-link>
              <router-link
                v-for="c in it.children ?? []"
                :key="c.path"
                :to="c.path"
                class="nav-item sub"
                :class="{ active: isActive(c.path) }"
              >
                <NavIcon :name="c.ico" />{{ c.title }}
              </router-link>
            </template>
          </div>
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
import { computed, onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import TopBar from '@/components/layout/TopBar.vue'
import NavIcon from '@/components/layout/NavIcon.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import { realtimeLinkage } from '@/engine/realtimeLinkage'

const route = useRoute()
const isActive = (p: string) => route.path === p || route.path.startsWith(p + '/')
const { t } = useI18n()

interface NavItem {
  path: string
  title: string
  ico: string
  badge?: string
  alert?: boolean
  children?: NavItem[]
}
interface NavGroup {
  /** 稳定标识: 折叠状态按 id 记忆, 避免语言切换导致 title 变化时折叠状态错位 */
  id: string
  title: string
  items: NavItem[]
}

const nav = computed<NavGroup[]>(() => [
  // G1 · 总览
  {
    id: 'overview',
    title: t('nav.overview'),
    items: [{ path: '/overview', title: t('nav.dashboard'), ico: 'LayoutDashboard' }],
  },
  // G2 · 设施监控（暖通 / 电力 / 安防消防 / 网络 / 设备健康度 / 数字可视）
  {
    id: 'facility',
    title: t('nav.facilityMonitoring'),
    items: [
      {
        path: '/monitor/hvac',
        title: t('nav.hvacMonitor'),
        ico: 'Snowflake',
        children: [
          { path: '/monitor/hvac/chiller', title: t('nav.chiller'), ico: 'Thermometer' },
          { path: '/monitor/hvac/crac', title: t('nav.crac'), ico: 'Wind' },
          { path: '/monitor/hvac/liquid', title: t('nav.liquidCooling'), ico: 'Droplets' },
          { path: '/monitor/hvac/linkage', title: t('nav.coolingLinkage'), ico: 'Snowflake' },
          { path: '/monitor/hvac/thermal', title: t('nav.tempCloud'), ico: 'Thermometer' },
        ],
      },
      {
        path: '/monitor/power',
        title: t('nav.powerMonitor'),
        ico: 'Zap',
        children: [
          { path: '/monitor/power/hv', title: t('nav.hv'), ico: 'PlugZap' },
          { path: '/monitor/power/lv', title: t('nav.lv'), ico: 'Gauge' },
          { path: '/monitor/power/linkage', title: t('nav.powerLinkage'), ico: 'GitBranch' },
          { path: '/monitor/power/genset', title: t('nav.genset'), ico: 'Zap' },
          { path: '/monitor/power/fuel', title: t('nav.fuel'), ico: 'Fuel' },
          { path: '/monitor/power/battery', title: t('nav.battery'), ico: 'BatteryFull' },
        ],
      },
      {
        path: '/monitor/security',
        title: t('nav.securityAndFire'),
        ico: 'Shield',
        children: [
          { path: '/monitor/security/cctv', title: t('nav.securityCctv'), ico: 'Video' },
          { path: '/monitor/security/acs', title: t('nav.securityAcs'), ico: 'DoorOpen' },
          { path: '/monitor/security/ids', title: t('nav.securityIds'), ico: 'Eye' },
          { path: '/monitor/security/fire', title: t('nav.securityFire'), ico: 'Flame' },
        ],
      },
      {
        path: '/monitor/net',
        title: t('nav.networkMonitor'),
        ico: 'Globe',
        children: [
          { path: '/monitor/net/switches', title: t('nav.networkSwitch'), ico: 'Network' },
          { path: '/monitor/net/routers', title: t('nav.networkRouter'), ico: 'Router' },
          { path: '/monitor/net/firewalls', title: t('nav.networkFirewall'), ico: 'ShieldCheck' },
          { path: '/monitor/net/wireless', title: t('nav.networkWireless'), ico: 'Wifi' },
        ],
      },
      { path: '/monitor/health', title: t('nav.health'), ico: 'HeartPulse' },
      {
        path: '/monitor/visual',
        title: t('nav.digitalVisual'),
        ico: 'Boxes',
        children: [
          { path: '/monitor/visual/3d', title: t('nav.scene3d'), ico: 'Box' },
          { path: '/monitor/visual/bigscreen', title: t('nav.bigScreen'), ico: 'Monitor' },
          { path: '/monitor/visual/designer', title: t('nav.bigScreenDesigner'), ico: 'Settings2' },
        ],
      },
    ],
  },
  // G3 · 告警（告警中心 / 告警历史 / 告警规则引擎）
  {
    id: 'alarm',
    title: t('nav.alarmGroup'),
    items: [
      { path: '/ops/alarms', title: t('nav.alarms'), ico: 'Bell', badge: '7', alert: true },
      { path: '/ops/alarm-history', title: t('nav.alarmHistory'), ico: 'Clock' },
      { path: '/ops/alarm-rules', title: t('nav.alarmRules'), ico: 'SlidersHorizontal' },
    ],
  },
  // G4 · 运维作业（巡检 / 维保 / 值班 / 工单 / 演练 / 故障 / 风险 / 隐患）
  {
    id: 'ops',
    title: t('nav.opsManagement'),
    items: [
      {
        path: '/ops/inspection',
        title: t('nav.inspect'),
        ico: 'Search',
        children: [
          { path: '/ops/inspection', title: t('nav.inspect'), ico: 'Search' },
          {
            path: '/ops/inspection-template',
            title: t('nav.electronicInspection'),
            ico: 'Smartphone',
          },
        ],
      },
      {
        path: '/ops/maintenance',
        title: t('nav.maintain'),
        ico: 'Wrench',
        children: [
          { path: '/ops/maintenance', title: t('nav.maintain'), ico: 'Wrench' },
          { path: '/ops/maintenance-calendar', title: t('nav.mntCalendar'), ico: 'CalendarDays' },
        ],
      },
      {
        path: '/ops/duty',
        title: t('nav.duty'),
        ico: 'Clock',
        children: [
          { path: '/ops/duty', title: t('nav.duty'), ico: 'Clock' },
          { path: '/ops/duty-calendar', title: t('nav.dutyCalendar'), ico: 'CalendarDays' },
        ],
      },
      {
        path: '/ops/tickets',
        title: t('nav.tickets'),
        ico: 'ClipboardList',
        badge: '6',
        alert: true,
      },
      { path: '/ops/room-access', title: t('nav.roomAccess'), ico: 'LogIn' },
      { path: '/ops/fault-impact', title: t('nav.faultImpact'), ico: 'GitBranch' },
      { path: '/ops/drill-plan', title: t('nav.drillPlan'), ico: 'ClipboardCheck' },
      { path: '/ops/notifications', title: t('nav.notifications'), ico: 'BellRing' },
      { path: '/ops/risk', title: t('nav.risk'), ico: 'AlertTriangle' },
      { path: '/ops/power-ai-hazards', title: t('nav.powerAi'), ico: 'Zap' },
      { path: '/ops/health-report', title: t('nav.healthReport'), ico: 'HeartPulse' },
      { path: '/ops/supplier', title: t('nav.supplier'), ico: 'Truck' },
    ],
  },
  // G5 · 资产（台账 / U 位 / 机柜 / 生命周期 / 租户）
  {
    id: 'asset',
    title: t('nav.assetManagement'),
    items: [
      { path: '/ops/equipment', title: t('nav.equipment'), ico: 'FileText' },
      { path: '/ops/u-position', title: t('nav.uPosition'), ico: 'LayoutGrid' },
      { path: '/ops/capacity-whatif', title: t('nav.whatIf'), ico: 'Gauge' },
      { path: '/ops/cabinets', title: t('nav.cabinets'), ico: 'ServerCog' },
      { path: '/ops/asset-lifecycle', title: t('nav.assetLifecycle'), ico: 'GitBranch' },
      { path: '/ops/tenant-manage', title: t('nav.tenantManage'), ico: 'Building2' },
    ],
  },
  // G6 · 能效
  {
    id: 'energy',
    title: t('nav.energyGroup'),
    items: [{ path: '/analysis/energy', title: t('nav.energy'), ico: 'Leaf' }],
  },
  // G7 · 知识与 AI
  {
    id: 'knowledge',
    title: t('nav.knowledgeAi'),
    items: [
      { path: '/ops/knowledge', title: t('nav.knowledge'), ico: 'BookOpen' },
      { path: '/ops/knowledge-collab', title: t('nav.knowledgeCollab'), ico: 'Users' },
      { path: '/ops/assistant', title: t('nav.assistant'), ico: 'Bot' },
    ],
  },
  // G8 · 平台集成（物模型 / 采集 / 遥测 / 流程 / 集成 / 多数据中心）
  {
    id: 'platform',
    title: t('nav.platformIntegration'),
    items: [
      { path: '/ops/thing-model', title: t('nav.thingModel'), ico: 'Blocks' },
      { path: '/ops/collector', title: t('nav.collector'), ico: 'Antenna' },
      { path: '/ops/telemetry', title: t('nav.telemetry'), ico: 'Radio' },
      { path: '/ops/workflow', title: t('nav.workflow'), ico: 'Workflow' },
      { path: '/ops/integration-hub', title: t('nav.integrationHub'), ico: 'Cable' },
      {
        path: '/ops/datacenter',
        title: t('nav.datacenter'),
        ico: 'Building2',
        children: [
          { path: '/ops/datacenter', title: t('nav.datacenter'), ico: 'Building2' },
          { path: '/ops/datacenter/compare', title: t('nav.datacenterCompare'), ico: 'GitCompare' },
        ],
      },
    ],
  },
  // G9 · 系统管理
  {
    id: 'system',
    title: t('admin.title'),
    items: [
      { path: '/admin/audit', title: t('admin.audit'), ico: 'ScrollText' },
      { path: '/admin/row-audit', title: t('admin.rowAudit'), ico: 'History' },
    ],
  },
])

/* ---- 分组折叠: 默认全部展开; 状态按分组 id 记忆, 语言切换不会错位 ---- */
const collapsed = reactive<Record<string, boolean>>(
  Object.fromEntries(nav.value.map((g): [string, boolean] => [g.id, false])),
)
const toggle = (id: string) => {
  collapsed[id] = !collapsed[id]
}
/** 路由变化时展开当前页面所属分组, 避免跳转后菜单项"消失"(其余组保留用户的折叠选择) */
const expandActiveGroup = () => {
  const hit = nav.value.find((g) =>
    g.items.some((it) => isActive(it.path) || (it.children ?? []).some((c) => isActive(c.path))),
  )
  if (hit) collapsed[hit.id] = false
}
watch(() => route.path, expandActiveGroup, { immediate: true })

/* 实时联动 (应用级, 不在模板中使用, 不会驱动 router-view 重渲染) */
onMounted(() => {
  realtimeLinkage.start(Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000))
})
onBeforeUnmount(() => {
  realtimeLinkage.stop()
})
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

/* ---- 可折叠分组标题: button 化, 沿用全局 .gtitle 的 10px / 字间距 / 小写大写排版 ---- */
.nav-group > .gtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px 4px;
  background: transparent;
  border: 0;
  font-family: inherit;
  color: var(--txt3);
  text-align: left;
  cursor: pointer;
  border-radius: 6px;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}
.nav-group > .gtitle:hover {
  background: var(--panel);
  color: var(--txt2);
}
.nav-group > .gtitle:focus-visible {
  outline: 1px solid var(--cyan);
  outline-offset: 1px;
}
.gtitle-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gtitle-arrow {
  display: inline-flex;
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity 0.18s ease;
}
.gtitle-arrow :deep(svg) {
  width: 13px;
  height: 13px;
}
</style>
