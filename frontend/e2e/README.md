# DC-IOC E2E 基线（Playwright）

独立的 npm 包，**不修改** `frontend/package.json` 与 `frontend/package-lock.json`，因此主工程的 `npm ci` 完全不受影响。

## 运行

```bash
cd frontend/e2e
npm install
npx playwright install chromium
npm test              # 自动拉起 frontend/ 的 Vite dev server 并跑 10 条关键路径
npm run test:ui       # 交互模式
npm run report        # 查看 HTML 报告
```

## 为什么不需要后端

`frontend/src/api/request.ts` 在后端不可达时会走 `mockData.ts` 兜底，登录与业务列表页仍可渲染。因此 E2E 断言只针对**页面结构与导航行为**（可见文本 / URL / 控件存在），不依赖具体数值，也不强依赖某个 Mock 字段。若将来关闭 Mock 兜底，需要在 `playwright.config.ts` 的 `webServer` 中追加后端启动命令（或在 CI 里用 `docker compose up -d backend`）。

## 用例清单（`specs/smoke.spec.ts`）

| # | 路径 | 断言要点 |
|---|---|---|
| 1 | 登录页 | 标题 / 用户名密码输入 / 演示账号提示可见 |
| 2 | 登录跳转 | 提交后离开 `/login`，到达受保护页面 |
| 3 | 驾驶舱 | KPI 卡片区域渲染，无错误横幅 |
| 4 | 告警中心 | 导航可达，页面标题可见 |
| 5 | 告警 → 工单 | 告警中心存在「转工单」入口且工单路由可达 |
| 6 | 工单中心 | 列表/筛选控件渲染 |
| 7 | 设备台账 | 表格或卡片容器渲染 |
| 8 | 机柜管理 | 页面可达且无白屏 |
| 9 | 审计日志 | 页面可达，导出控件存在 |
| 10 | 侧边栏 | 分组折叠/展开后菜单项数正确，切换语言不产生死链 |

## 新增用例约定

1. 用 `page.goto('/xxx')` + `expect(...).toBeVisible()`，避免 `waitForTimeout`。
2. 断言用宽容匹配（`getByText(/xxx/)`），不要断言 Mock 的具体数值。
3. 依赖真实后端数据的用例请加 `test.skip()` 并注明原因，等 CI 提供完整服务后再启用。
4. 新增页面必须同步补一条导航可达性用例（配合 `scripts/check_nav_routes.py`）。
