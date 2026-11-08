import type { Page } from '@playwright/test'

/**
 * E2E 自带 API 桩 — 让冒烟用例真正脱离后端。
 *
 * 背景: webServer 只启动 Vite dev server, /api/* 与 /ws 的代理目标 8000 端口无人监听,
 * 于是每个请求都得到 ECONNREFUSED -> HTTP 500。前端 request.ts 的 Mock 兜底只覆盖
 * 显式登记过的端点, 其余数据源落到 AsyncSection 的 "加载失败" 错误态, 导致
 * 驾驶舱出现多条失败横幅、设备台账表格被错误态替换, 且 CI 日志被代理报错刷屏。
 *
 * 本桩在浏览器侧拦截全部 /api/** 请求并返回结构兼容的最小数据, 同时模拟一条
 * 永远保持打开的 /ws 连接。因此:
 *   - 无代理请求、无 ECONNREFUSED 噪音;
 *   - 不修改生产代码 (不会把真实后端故障"静默降级"成空数据);
 *   - 页面走完整的成功态渲染路径, 断言稳定且有意义。
 */

type JsonBody = Record<string, unknown> | unknown[]

const USER = { id: 1, username: 'admin', roles: ['admin'], is_active: true }

const AUTH = {
  access_token: 'e2e-access-token',
  refresh_token: 'e2e-refresh-token',
  token_type: 'bearer',
  user: USER,
}

/** 驾驶舱 KPI / 顶栏共用的总览数据 (字段与 DashboardOverview 对齐) */
const OVERVIEW = {
  total_devices: 200,
  online_devices: 198,
  online_rate: 99,
  today_alarms: 3,
  pue: 1.247,
  wue: 0.32,
  it_load_mw: 3.2,
  total_load_mw: 4.1,
  cool_load_mw: 0.9,
  availability: 99.98,
  free_cool_hours: 1200,
  alarms: { crit: 0, warn: 2, info: 1 },
  domain_online: {},
}

/** 至少两行数据: 设备台账的 AsyncSection 以 !items.length 判空, 空列表不会渲染 <table> */
const EQUIPMENT = {
  items: [
    {
      id: 1,
      code: 'E2E-CH-01',
      name: '冷机 1#',
      domain: 'hvac',
      category: '冷机',
      vendor: 'E2E',
      model: 'Mock-3500',
      status: '运行',
      load_pct: 62,
      run_hours: 12000,
    },
    {
      id: 2,
      code: 'E2E-CRAC-01',
      name: '精密空调 A1',
      domain: 'hvac',
      category: '精密空调',
      vendor: 'E2E',
      model: 'Mock-80',
      status: '运行',
      load_pct: 48,
      run_hours: 8600,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
}

const AUDIT_LOGS = {
  items: [
    {
      id: 1,
      ts: '2026-11-08T08:00:00Z',
      method: 'POST',
      action: 'create',
      resource: 'tickets',
      path: '/api/ops/tickets',
      username: 'admin',
      ip: '127.0.0.1',
      status_code: 201,
      detail: '{}',
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
}

/** 精确端点表: 命中即返回, 与后端响应形状保持一致 */
const ROUTES: Record<string, JsonBody> = {
  '/api/auth/me': USER,
  '/api/auth/login': AUTH,
  '/api/auth/refresh': AUTH,
  '/api/auth/logout': { ok: true },

  '/api/dashboard/overview': OVERVIEW,
  '/api/dashboard/overview/trends': { points: [] },
  '/api/dashboard/campus-comparison': { comparisons: [] },

  '/api/alarms/active': { total: 0, items: [] },
  '/api/alarm-rules': [],
  '/api/alarm-rules/state': { running: true, rules: [] },
  '/api/alarm-history': { items: [], total: 0 },

  // getHvacOverview() 的 mapChiller/mapCrac/mapLiquid 对空数组做防御式映射
  '/api/hvac/chiller-plant': { chillers: [] },
  '/api/hvac/crac': { units: [], rooms: [], freshAir: [], humidifiers: [] },
  '/api/hvac/liquid-cooling': { primaryCDUs: [], secondaryCDUs: [] },

  '/api/ops/alarms': { active: [], history: [], convergence: { raw: 0, converged: 0, rate: 0 } },
  '/api/ops/tickets': { items: [], total: 0 },
  '/api/ops/graphic-config/dashboard': {},
  '/api/plugins/manifest': { plugins: [] },

  '/api/equipment': EQUIPMENT,
  '/api/cabinets': { items: [], total: 0 },
  '/api/audit-logs': AUDIT_LOGS,
}

/** 未登记的端点: 返回"字段齐全的空集合", 兼容列表页与详情页两种消费方式 */
const GENERIC: JsonBody = {
  items: [],
  list: [],
  records: [],
  comparisons: [],
  points: [],
  total: 0,
  page: 1,
  page_size: 50,
  ok: true,
  success: true,
}

function responseFor(url: URL, method: string) {
  const body = ROUTES[url.pathname] ?? (method === 'get' ? GENERIC : { ok: true, success: true })
  return {
    status: 200,
    contentType: 'application/json; charset=utf-8',
    headers: { 'cache-control': 'no-store' },
    body: JSON.stringify(body),
  }
}

/**
 * 为单个 page 安装 API 桩。需在 page.goto() 之前调用 (每个测试一次)。
 * routeWebSocket 保持连接打开且不转发到后端, 避免重连风暴与 ws 代理报错。
 */
export async function installApiMocks(page: Page): Promise<void> {
  // 必须用「路径以 /api/ 开头」的锚定正则: glob `**/api/**` 会连 Vite 的
  // /src/api/*.ts 模块请求一起拦截, 前端拿到 JSON 当 JS 执行就会整页空白。
  await page.route(/^https?:\/\/[^/]+\/api\//, async (route) => {
    const req = route.request()
    let url: URL
    try {
      url = new URL(req.url())
    } catch {
      await route.fulfill(
        responseFor(new URL('http://127.0.0.1/api/unknown'), req.method().toLowerCase()),
      )
      return
    }
    await route.fulfill(responseFor(url, req.method().toLowerCase()))
  })

  // 同理只拦截同源 /ws, 不能碰 Vite HMR 的 ws://host/ 连接
  await page.routeWebSocket(/^wss?:\/\/[^/]+\/ws$/, (ws) => {
    // 不调用 ws.connectToServer(): Playwright 会用一条本地模拟连接替代,
    // 客户端 onopen 正常触发, 但不会有任何后端请求。
    ws.onMessage(() => {})
  })
}
