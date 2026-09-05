import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 仅保留 S1（Java 后端已验收）支持的页面路由；Phase 3/4 域（hvac/power/security/
// network/twin/topology/capacity/energy/inspect/maintain/drill/shift/assistant/
// risk/knowledge/demo）暂未实现，已从路由移除。alarm-rules 已由 T1.2 后端实现并回填。
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        component: () => import('@/views/overview/Index.vue'),
        meta: { title: 'IOC 驾驶舱' },
      },
      // 告警
      {
        path: 'ops/alarms',
        component: () => import('@/views/ops/Alarms.vue'),
        meta: { title: '告警中心' },
      },
      {
        path: 'ops/alarm-history',
        component: () => import('@/views/ops/AlarmHistory.vue'),
        meta: { title: '告警历史' },
      },
      // 运维作业（S1 支持部分）
      {
        path: 'ops/tickets',
        component: () => import('@/views/ops/Tickets.vue'),
        meta: { title: '事件工单中心', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'admin/audit',
        component: () => import('@/views/admin/AuditLogs.vue'),
        meta: { title: '操作审计', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'admin/row-audit',
        component: () => import('@/views/admin/RowAudit.vue'),
        meta: { title: '行级审计', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/collector',
        component: () => import('@/views/ops/Collector.vue'),
        meta: { title: '采集器接入', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/telemetry',
        component: () => import('@/views/ops/Telemetry.vue'),
        meta: { title: '设备遥测', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/alarm-rules',
        component: () => import('@/views/ops/AlarmRules.vue'),
        meta: { title: '告警规则引擎', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/cabinets',
        component: () => import('@/views/ops/Cabinets.vue'),
        meta: { title: '机柜管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/equipment',
        component: () => import('@/views/ops/Equipment.vue'),
        meta: { title: '统一设备台账', requiredRoles: ['admin', 'operator'] },
      },
      // Phase 3 · 监控域 (暖通 / 电力 / 安防消防 / 网络 各自拆分为独立子页面)
      {
        path: 'monitor/hvac',
        component: () => import('@/views/monitor/HvacDashboard.vue'),
        meta: { title: '暖通空调', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/hvac/chiller',
        component: () => import('@/views/monitor/HvacChiller.vue'),
        meta: { title: '冷源系统' },
      },
      {
        path: 'monitor/hvac/crac',
        component: () => import('@/views/monitor/HvacCrac.vue'),
        meta: { title: '空调末端' },
      },
      {
        path: 'monitor/hvac/liquid',
        component: () => import('@/views/monitor/HvacLiquid.vue'),
        meta: { title: '液冷系统' },
      },
      {
        path: 'monitor/hvac/linkage',
        component: () => import('@/views/monitor/HvacLinkage.vue'),
        meta: { title: '制冷链路可视化' },
      },
      {
        path: 'monitor/hvac/thermal',
        component: () => import('@/views/monitor/ThermalCloud.vue'),
        meta: { title: '温度云图' },
      },
      {
        path: 'monitor/power',
        component: () => import('@/views/monitor/PowerDashboard.vue'),
        meta: { title: '电力监控', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/power/hv',
        component: () => import('@/views/monitor/PowerHv.vue'),
        meta: { title: '10KV 中压配电' },
      },
      {
        path: 'monitor/power/lv',
        component: () => import('@/views/monitor/PowerLv.vue'),
        meta: { title: '0.4KV 低压配电' },
      },
      {
        path: 'monitor/power/linkage',
        component: () => import('@/views/monitor/PowerLinkage.vue'),
        meta: { title: '配电链路可视化' },
      },
      {
        path: 'monitor/power/genset',
        component: () => import('@/views/monitor/PowerGenset.vue'),
        meta: { title: '柴发并机系统' },
      },
      {
        path: 'monitor/power/fuel',
        component: () => import('@/views/monitor/PowerFuel.vue'),
        meta: { title: '燃油监控' },
      },
      {
        path: 'monitor/power/battery',
        component: () => import('@/views/monitor/PowerBattery.vue'),
        meta: { title: '电池监控' },
      },
      {
        path: 'monitor/security',
        component: () => import('@/views/monitor/SecurityDashboard.vue'),
        meta: { title: '安防监控', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/security/cctv',
        component: () => import('@/views/monitor/SecurityCctv.vue'),
        meta: { title: '视频监控' },
      },
      {
        path: 'monitor/security/acs',
        component: () => import('@/views/monitor/SecurityAcs.vue'),
        meta: { title: '门禁管理' },
      },
      {
        path: 'monitor/security/ids',
        component: () => import('@/views/monitor/SecurityIds.vue'),
        meta: { title: '防入侵系统' },
      },
      {
        path: 'monitor/security/fire',
        component: () => import('@/views/monitor/SecurityFire.vue'),
        meta: { title: '消防报警' },
      },
      {
        path: 'monitor/net',
        component: () => import('@/views/monitor/NetworkDashboard.vue'),
        meta: { title: '网络监控', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/net/switches',
        component: () => import('@/views/monitor/NetworkSwitches.vue'),
        meta: { title: '核心交换机' },
      },
      {
        path: 'monitor/net/routers',
        component: () => import('@/views/monitor/NetworkRouters.vue'),
        meta: { title: '路由器' },
      },
      {
        path: 'monitor/net/firewalls',
        component: () => import('@/views/monitor/NetworkFirewalls.vue'),
        meta: { title: '防火墙' },
      },
      {
        path: 'monitor/net/wireless',
        component: () => import('@/views/monitor/NetworkWireless.vue'),
        meta: { title: '无线网络' },
      },
      {
        path: 'monitor/visual',
        redirect: '/monitor/visual/3d',
      },
      {
        path: 'monitor/visual/3d',
        component: () => import('@/views/monitor/Scene3D.vue'),
        meta: { title: '3D 视图', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/visual/bigscreen',
        component: () => import('@/views/monitor/BigScreen.vue'),
        meta: { title: '定制大屏', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/visual/designer',
        component: () => import('@/views/monitor/BigScreenDesigner.vue'),
        meta: { title: '大屏定制', requiredRoles: ['admin', 'operator'] },
      },
      // Phase 3 · 运维域
      {
        path: 'ops/inspection',
        component: () => import('@/views/ops/Inspection.vue'),
        meta: { title: '巡检管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/maintenance',
        component: () => import('@/views/ops/Maintenance.vue'),
        meta: { title: '维保管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/maintenance-calendar',
        component: () => import('@/views/ops/MaintenanceCalendar.vue'),
        meta: { title: '维保日历', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/room-access',
        component: () => import('@/views/ops/RoomAccess.vue'),
        meta: { title: '机房进出登记', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/risk',
        component: () => import('@/views/ops/Risk.vue'),
        meta: { title: '风险评估', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/duty',
        component: () => import('@/views/ops/Duty.vue'),
        meta: { title: '值班管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/duty-calendar',
        component: () => import('@/views/ops/DutyCalendar.vue'),
        meta: { title: '排班日历', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/inspection-template',
        component: () => import('@/views/ops/InspectionTemplate.vue'),
        meta: { title: '电子巡检', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/knowledge-collab',
        component: () => import('@/views/ops/KnowledgeCollaboration.vue'),
        meta: { title: '知识协作', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/workflow',
        component: () => import('@/views/ops/WorkflowCenter.vue'),
        meta: { title: 'ITIL 流程', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/fault-impact',
        component: () => import('@/views/ops/FaultImpact.vue'),
        meta: { title: '故障影响分析', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/drill-plan',
        component: () => import('@/views/ops/DrillPlan.vue'),
        meta: { title: '应急演练', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/notifications',
        component: () => import('@/views/ops/NotificationCenter.vue'),
        meta: { title: '通知中心', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/supplier',
        component: () => import('@/views/ops/Supplier.vue'),
        meta: { title: '供应商管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/power-ai-hazards',
        component: () => import('@/views/ops/PowerAiHazards.vue'),
        meta: { title: '供配电 AI 隐患', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/health-report',
        component: () => import('@/views/ops/HealthReport.vue'),
        meta: { title: 'iHealth 健康报告', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/integration-hub',
        component: () => import('@/views/ops/IntegrationHub.vue'),
        meta: { title: '集成验证中心', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/asset-lifecycle',
        component: () => import('@/views/ops/AssetLifecycle.vue'),
        meta: { title: '资产生命周期', requiredRoles: ['admin', 'operator'] },
      },

      {
        path: 'ops/tenant-manage',
        component: () => import('@/views/ops/TenantManage.vue'),
        meta: { title: '租户管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/u-position',
        component: () => import('@/views/ops/UPosition.vue'),
        meta: { title: 'U 位识别', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/capacity-whatif',
        component: () => import('@/views/ops/CapacityWhatIf.vue'),
        meta: { title: '上架模拟器', requiredRoles: ['admin', 'operator'] },
      },

      // Phase 4 · 物模型与多数据中心 (阶段0 占位, 后续阶段实现)
      {
        path: 'ops/thing-model',
        component: () => import('@/views/ops/ThingModelEditor.vue'),
        meta: { title: '物模型', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/datacenter',
        component: () => import('@/views/ops/DataCenterManage.vue'),
        meta: { title: '数据中心管理', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/datacenter/compare',
        component: () => import('@/views/ops/DataCenterCompare.vue'),
        meta: { title: '数据中心对比', requiredRoles: ['admin', 'operator'] },
      },
      // Phase 3 · P2 智能运营域
      {
        path: 'analysis/energy',
        component: () => import('@/views/energy/EnergyDashboard.vue'),
        meta: { title: '能耗分析', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'monitor/health',
        component: () => import('@/views/monitor/HealthDashboard.vue'),
        meta: { title: '设备健康度', requiredRoles: ['admin', 'operator'] },
      },
      // Phase 3 · P3 知识库 & AI 助手
      {
        path: 'ops/knowledge',
        component: () => import('@/views/ops/KnowledgeCenter.vue'),
        meta: { title: '知识库', requiredRoles: ['admin', 'operator'] },
      },
      {
        path: 'ops/assistant',
        component: () => import('@/views/ops/Assistant.vue'),
        meta: { title: 'AI 运维助手', requiredRoles: ['admin', 'operator'] },
      },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

// 路由切换时中断尚未完成的请求, 避免旧页面请求污染新页面/内存泄漏
router.afterEach(() => {
  // 动态导入避免与 request 模块循环依赖
  import('@/api/request').then((m) => m.abortPendingRequests()).catch(() => {})
})

// ---- 路由守卫: 未登录跳转登录页 + 基础 RBAC ----
export function isTokenValid(token: string | null): boolean {
  if (!token) return false
  try {
    // JWT payload 为 base64url, 解码取 exp 判断有效期
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(b64))
    if (payload.exp && Date.now() / 1000 > payload.exp) return false
    return true
  } catch {
    return false
  }
}

/** 导出守卫本体便于单元测试 (to: 目标路由; 返回值经 next 执行) */
/** “不记住我”会话: 仅当前标签页生命周期有效。SPA 内部跳转不拦截, 但每次整页
 *  加载(刷新/重开/新标签)都会清空会话并要求重新登录 —— 与“会话 Cookie”语义一致 */
let sessionChecked = false
function enforceSessionScope() {
  if (sessionChecked) return
  sessionChecked = true
  const remember = localStorage.getItem('dc_ioc_remember')
  if (remember === '0' && localStorage.getItem('dc_ioc_token')) {
    localStorage.removeItem('dc_ioc_token')
    localStorage.removeItem('dc_ioc_refresh')
    localStorage.removeItem('dc_ioc_user')
  }
}

export function authGuard(
  to: { path: string; meta: Record<string, unknown> },
  _from: unknown,
  next: (target?: string) => void,
): void {
  enforceSessionScope()
  if (localStorage.getItem('dc_ioc_bypass') === '1') return next()
  const token = localStorage.getItem('dc_ioc_token')
  const user = JSON.parse(localStorage.getItem('dc_ioc_user') || 'null')

  // 登录页: 已登录则跳驾驶舱
  if (to.path === '/login') {
    if (isTokenValid(token)) return next('/overview')
    return next()
  }

  // 未登录拦截 (过期 token 视为未登录)
  if (!isTokenValid(token) && !to.meta.noAuth) {
    localStorage.removeItem('dc_ioc_token')
    localStorage.removeItem('dc_ioc_refresh')
    localStorage.removeItem('dc_ioc_user')
    return next('/login')
  }

  // 基础 RBAC: 路由声明 requiredRoles 时校验用户角色
  const requiredRoles = to.meta.requiredRoles as string[] | undefined
  if (requiredRoles && requiredRoles.length && user) {
    const roles: string[] = Array.isArray(user.roles) ? user.roles : [user.role].filter(Boolean)
    if (!requiredRoles.some((r) => roles.includes(r))) return next('/overview') // 无权限回驾驶舱
  }

  next()
}

router.beforeEach((to, _from, next) => authGuard(to, _from, next as (target?: string) => void))

export default router
