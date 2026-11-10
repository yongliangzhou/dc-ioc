# 06 · 分阶段实施路线图与交接说明

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **日期** 2026-11-10
>
> ## ⚠️ 本轮只交付文档，不修改任何运行文件
>
> 本文描述的是**用户审阅认可后另开一轮**的代码实施计划。本轮未改动任何 `.vue` / `.ts` / `.scss` / `.css` / 配置 / CI / 路由 / i18n 文件，未 commit、未 push。阶段 1–4 的所有内容均为**待执行**。

## 1. 四阶段总览

| 阶段 | 主题 | 覆盖 | 核心交付 | 依赖 |
| --- | --- | --- | --- | --- |
| **1** | 设计系统统一 | 全局样式 + 共享组件 + 规范用例 | token 单一来源、同名类合并、组件唯一实现、四档断点 mixin | 无 |
| **2** | 4 个总览页标杆 | `Hvac/Power/Network/Security Dashboard` | 四块式结构、差异化指标、P0 优先级、统一图表与异步态 | 阶段 1 |
| **3** | 子系统页与驾驶舱批量推广 | 其余 73 页 | 硬编码清理、筛选/分页/遮罩统一、指标分层、可信度标记 | 阶段 1、2 的范式 |
| **4** | 响应式与验证 | 全平台 77 页 | 侧栏抽屉、四档降级、视觉回归、E2E 扩展 | 阶段 1–3 |

```
阶段1 设计系统 ──► 阶段2 四个标杆页 ──► 阶段3 批量推广 ──► 阶段4 响应式与验证
   │                    │                    │                    │
   └ 全局 token/组件     └ 可复制的页面范式    └ 逐页改造清单        └ 四档验收 + 门禁
```

**已确认边界**（用户选择）：全平台统一（77 页）；沿用暗色为主 + 亮色双主题、统一 token、不重构设计语言；先标杆后推广。

---

## 2. 阶段 1 · 设计系统统一

**目标**：让 `index.scss` 的 token 成为唯一色彩来源，消除 [02](./02_DIAGNOSIS.md) 中的 `C1/C2/C3/C4` 根因，为后续所有页面改造提供可复制的基线。

### 2.1 文件清单 → 改动点 → 验收标准

| 文件 | 改动点 | 验收标准 |
| --- | --- | --- |
| `frontend/src/assets/styles/index.scss` | ① 合并 15 组同名类（`.view-head` `.card-head` `.section-title` `.btn-sm` `.grid` `.pill` `@keyframes blink` `select option` 等）；② 只保留 `.grid.cols-*` 一套栅格；③ 10 个未定义变量替换为正式 token（[04](./04_VISUAL_SPEC.md) §1.1）；④ 全局自身 8 处硬编码 token 化；⑤ 新增 `--space-*` / `--radius-*`；⑥ 定义 4 条断点 mixin；⑦ 新增 `prefers-reduced-motion` 段 | 同名类 0 组；`rg '#[0-9a-fA-F]{3,8}'` 在该文件**仅剩 `:root` 定义与注释**；`rg '@media' -o` 阈值集合 ⊆ `{420,768,1024,1440,print,reduced-motion}` |
| `frontend/src/styles/p3.css` | 760px → 768px | 全库无 760 断点 |
| `frontend/src/styles/print.css` | 吸收 `views/ops/HealthReport.vue:945` 的页内打印规则；统一亮色输出 | `@media print` 全库仅 1 处 |
| `packages/dc-ioc-ui/src/StatusBadge.vue` | 修 `:31` `'dui-'+'dui-o'` 双前缀瑕疵；统一默认条色 `var(--cyan)` | 新增/更新状态映射单测 |
| `frontend/src/components/monitor/{KpiCard,TrendChart,StatusBadge,AlarmBadge,EmptyState,SkeletonCard}.vue` + `index.ts` | 收敛为薄适配层或删除；`index.ts` 统一从 `@dc-ioc/ui` 重导出；删除 `EmptyState.vue` 的 emoji 默认图标 `📊` | `C/monitor/` 与 `@dc-ioc/ui` 无同名重复实现；无 emoji 作图标 |
| `frontend/src/components/common/{MetricCard,AsyncSection,EmptyStateCard,LoadingState,ErrorBanner,ErrorRetry}.vue` | 按 [04](./04_VISUAL_SPEC.md) §2/§4/§6 统一 API、四态与文案；错误态与空态严格区分 | 组件单测覆盖四态；无 `var(--未定义,…)` |
| `frontend/src/components/charts/{BaseChart,TrendChart,options}.ts/vue` | 配色从 CSS 变量读取；阈值 `markLine` 统一；`compact` 响应式表现；主题切换只 `setOption` 不重建 | 双主题切换后配色跟随，实例引用不变 |
| `frontend/src/config/metricsCatalog.ts`（**新建**） | 按 [03](./03_METRICS_IA.md) §6 定义 `MetricDef`（单位/阈值/严重度/端点/分组），把散落在模板三元表达式的数值收编 | 模板中数值型阈值表达式 0 处 |
| `frontend/src/i18n/locales/{zh-CN,en-US}.json` | 新增文案双键同步 | `check_i18n_keys.py --json` ok=true，zh/en 各 3072+ 且 0 缺失 |

### 2.2 门禁 / 验证

```
npx vue-tsc --noEmit                       # 0 错误
npm run test:run                            # 现有 9 文件 / 52 用例 + 新增状态映射单测
npm run build                               # 成功
python scripts/check_i18n_keys.py --json   # ok=true
python scripts/check_api_contract.py       # 200 paths / 271 ops（不得变化）
python scripts/check_nav_routes.py --strict# 71 路由 / 0 死链 / 0 孤儿
python scripts/check_except_hygiene.py
```

**阶段 1 出口判据**：以上全绿 + 在 `dark` / `light` 两个主题下打开驾驶舱、一个总览页、一个表格页，均无「按钮看不到字」「文字消失」「恒定暗色块」。

> **顺序约束**：先合并两套栅格，再做断点迁移（[05](./05_RESPONSIVE_SPEC.md) §6.1），否则同一宽度下裸 `.cols-*` 与 `.grid.cols-*` 会给出不同列数。

---

## 3. 阶段 2 · 四个总览页标杆

**目标**：产出可复制的页面范式，验证 [03](./03_METRICS_IA.md) §4.2 的四块结构与 [04](./04_VISUAL_SPEC.md) 的组件规范。

### 3.1 文件清单 → 改动点 → 验收标准

| 文件 | 改动点 | 验收标准 |
| --- | --- | --- |
| `frontend/src/views/monitor/PowerDashboard.vue` | 四块结构重排；5 张同质卡改为按设备域差异化（满载续航 / 后备时间 / THD-U / 自动模式等）；补 `cursor:pointer` + focus + 过渡；手写入口卡样式 → 全局类 | 任意两卡的 3 个指标组合不相同；字段全部来自现有接口 |
| `frontend/src/views/monitor/NetworkDashboard.vue` | 同上；4 卡差异化（CPU/端口可用率/温度/并发连接/在线率/dBm） | 同上；不引用未接线的 `/api/network/bandwidth` `/ping` |
| `frontend/src/views/monitor/SecurityDashboard.vue` | 同上；修 `var(--border)` 未定义变量（`:202`）；4 卡差异化 | 同上 |
| `frontend/src/views/monitor/HvacDashboard.vue` | **保留差异化指标**（`:51-109`）；补页头 `DataBadge` + 最后刷新时间；`:143-152` 手写错误态 → `AsyncSection` + `ErrorRetry` | 错误态与空态可区分，且可重试 |
| `frontend/src/views/overview/Index.vue`（可选同批） | 统一卡片/图表外观，六区块配置契约不变；`DataBadge` 6 处保留；主标题 h2 → h1 | `useDashboardLayout.ts` 的显隐/排序行为不变，单测通过 |

### 3.2 门禁 / 验证

- 上述阶段 1 全部门禁复跑。
- `frontend/e2e`：`npm test` 与 `CI=1 npm test` 各一遍（现有 10 条冒烟，含 `/overview` 与侧栏分组用例）。
- **视觉回归**：4 页 × 2 主题 × 4 档视口（375/768/1024/1440）= 32 组，检查 P0 指标可见、无横向滚动、卡片不重叠。
- **对比度**：亮色主题正文 ≥ 4.5:1。

**阶段 2 出口判据**：32 组视觉回归通过 + E2E 10/10；标杆页截图（或人工确认）经用户认可后再进入阶段 3 —— 这是「先标杆后推广」的关键闸门。

---

## 4. 阶段 3 · 子系统页与驾驶舱批量推广

**目标**：把阶段 1/2 的范式推广到其余页面，按 [02_DIAGNOSIS.md](./02_DIAGNOSIS.md) §7 的逐页清单逐项销账。

### 4.1 批次划分（建议按风险从低到高）

| 批次 | 页面 | 主要问题代码 | 改动要点 |
| --- | --- | --- | --- |
| 3-A 表格/表单页（45） | `V/ops/**`、`V/admin/**` | `I1/I2/I3/I4/I5`、`L4`、`C2` | 筛选栏统一（查询+重置+保存视图+列配置）、分页统一 `Pagination.vue`、遮罩统一、表格内三元 → `AsyncSection`、>8 列启用默认列集 |
| 3-B 电力/暖通 SVG 页（约 12） | `V/monitor/Power*`、`Hvac*` | `C1/C2`、`D1/D2`、`L2/L4` | 硬编码 → token；阈值 → `metricsCatalog`；KPI 按 P0/P1/P2 分层；示例数据按 `useMockFlag` 三档标记（`partial` 需点名模拟字段） |
| 3-C 网络/安防页（约 8） | `V/monitor/Network*`、`Security*` | `C2`（安防 4 页别名全失效）、`D3`、`I5` | 修未定义变量；4 个网络页本地 `mockData()` → 统一 `DataBadge`/`MockDataBanner`；`/api/network/bandwidth` 与 `/api/network/ping` 接线与否**单独评估**（§7 决策 5：不假定数据已存在） |
| 3-D 驾驶舱 / 能耗 / 3D / 大屏（5） | `V/overview/Index.vue`、`V/energy/EnergyDashboard.vue`、`V/monitor/{Scene3D,BigScreen,BigScreenDesigner}.vue` | `C1/C6`、`C3` 自建 `.light` | 图表配色 token 化；删除 `BigScreen.vue:180-183` 自建主题分支；`EnergyDashboard.vue:589` emoji 图标改 lucide；3D/大屏主题色读 `:root` |
| 3-E 登录 / 审计 / 报告（4） | `V/auth/Login.vue`、`V/admin/*`、`V/ops/HealthReport.vue` | `C1`、打印规则分散 | 登录渐变 token 化；打印规则并入 `print.css` |

### 4.2 通用改动清单（每页必须逐项核对）

- [ ] scoped 样式中 hex/rgb 字面量 → token（目标：页面文件 0 处）
- [ ] `var(--未定义,…)` → 正式 token
- [ ] 自定义按钮类（`btn-refresh` / `hv-edit` / `chip-clear` / 裸 `btn` / `btn-sm primary`）→ 统一原子类
- [ ] 遮罩类名 → `.modal-mask`（抽屉用 `.modal.as-drawer`）
- [ ] 手写 loading/error/empty → `AsyncSection`；错误与空态分离
- [ ] 主标题唯一 `<h1>`；栅格只用 `.grid.cols-*`
- [ ] 可点击元素 `cursor:pointer` + 可见 focus
- [ ] 示例数据 `DataBadge`（页头）+ `MockDataBanner`（区块）
- [ ] 阈值数值 → `metricsCatalog`
- [ ] 新增/修改文案 zh/en 双键同步

### 4.3 门禁 / 验证

- 阶段 1 全部门禁 + `frontend/e2e` 10 条冒烟。
- **逐页销账表**：以 [02](./02_DIAGNOSIS.md) §7 的 77 行为基线，每页标记「C1/C2/I5/L1… 已修 / 不适用 / 例外（注明原因）」；例外必须登记。
- 双主题逐页抽检：重点 `SecurityAcs.vue`（5 个别名失效）、`PowerFuel.vue`（134 行硬编码）、`HvacLiquid.vue`（23 KPI + 7 断点）、`BigScreen.vue`（自建主题）。

**阶段 3 出口判据**：`rg` 统计页面硬编码色值从约 1975 行降到 0；未定义变量 0；`AsyncSection` 覆盖 77 页；77 行销账表无未解释遗留。

---

## 5. 阶段 4 · 响应式与验证

**目标**：实现 [05](./05_RESPONSIVE_SPEC.md) 的四档降级，完成端到端验证。

### 5.1 文件清单 → 改动点 → 验收标准

| 文件 | 改动点 | 验收标准 |
| --- | --- | --- |
| `frontend/src/layouts/DefaultLayout.vue` | 新增 `isCompact`（`matchMedia('(max-width:1024px)')`）、抽屉状态、汉堡按钮、Esc/遮罩/焦点管理；**不动** `staticNav`、`mergePluginNav()`、WS 挂载逻辑 | 四档抽屉契约逐项通过；71 路由 0 死链 0 孤儿 |
| `frontend/src/components/layout/TopBar.vue` | 窄屏结构（汉堡 + 精简 tools + 「更多」菜单）；样式走全局 mixin | 375/768 顶栏不溢出、不换行错位 |
| `frontend/src/assets/styles/index.scss` | `.body/.side/.topbar` 四档规则；`.modal.as-drawer`；`.scroll-x` 约束；`prefers-reduced-motion` | 全库 `@media` 阈值集合 = `{420,768,1024,1440}` + print/reduced-motion |
| `V/**/*.vue`（77） | 按 [05](./05_RESPONSIVE_SPEC.md) §3 迁移表归并 70 处 `@media`；3D/大屏在 S/XS 降为 2D 概览 | 逐页四档验收清单通过 |
| `C/charts/BaseChart.vue`、`C/monitor/HeatmapView.vue` | `compact` 表现（高度/图例/序列数），`resize()` 而非重建 | 视口切换不重建实例 |
| `frontend/e2e/specs/` | 新增四档冒烟（375/768/1024/1440），与现有 10 条并列 | `npm test` / `CI=1 npm test` 全通过 |

### 5.2 验证矩阵

| 检查 | 375 | 768 | 1024 | 1440 |
| --- | --- | --- | --- | --- |
| 整页无横向滚动 | ✓ | ✓ | ✓ | ✓ |
| 主区可用宽度 ≥ 343px | ✓ | — | — | — |
| 侧栏可开合 / 焦点可返回 | ✓ | ✓ | ✓ | 常驻 |
| P0 指标与示例数据标记可见 | ✓ | ✓ | ✓ | ✓ |
| 图表图例与阈值线可见（或按档降级） | ✓ | ✓ | ✓ | ✓ |
| 主题切换后布局不变 | ✓ | ✓ | ✓ | ✓ |
| 打印隐藏侧栏/顶栏且亮色 | — | — | — | ✓ |

### 5.3 全量门禁（阶段 4 出口）

```
# 前端
npx vue-tsc --noEmit ; npm run test:run ; npm run build
cd frontend/e2e && npm ci && npm test            # 含四档新增用例
CI=1 npm test                                    # retries=1 / 2 workers

# 静态门禁（全库）
python scripts/check_except_hygiene.py
python scripts/check_i18n_keys.py --json
python scripts/check_api_contract.py
python scripts/check_nav_routes.py --strict
python -m ruff check backend/app/
python backend/scripts/sql_guard.py backend/app   # 按 CI 实际路径

# 后端（无前端业务变更，仍复跑以防共享门禁被牵连）
python -m pytest backend/tests/ tests/ -q --cov=app --cov-fail-under=15
```

> 当前基线（2026-11-10 复核）：i18n zh/en 各 **3072** 键 0 缺失；契约 **200 paths / 271 operations**；路由 **71 / 静态菜单 66 / 插件菜单 5，0 死链 0 孤儿**；`frontend/e2e/specs/smoke.spec.ts` **10 条**用例。以上数字在四个阶段中**不得漂移**。

---

## 6. 风险、回滚与不变量

| 风险 | 缓解 / 回滚 |
| --- | --- |
| 硬编码清理量大（约 1975 行）导致遗漏或误改 | 按批次（3-A~3-E）提交，每批单独 `rg` 统计 + 双主题抽检；单文件改动可整段 revert |
| 合并同名类改变既有页面观感 | 阶段 1 先做，阶段 2 用 4 个标杆页验证后再推广；保留 [04](./04_VISUAL_SPEC.md) §5 的「保留后定义」决策记录 |
| 断点保守归并导致 1024–1440 桌面过度降列 | [05](./05_RESPONSIVE_SPEC.md) §3 例外登记；1280/1366/1440 三档视觉回归 |
| 抽屉改动影响插件菜单 / 实时联动 | 不动 `staticNav`、`mergePluginNav()`、`onMounted`；`isCompact` 布尔开关隔离，关闭即回到原桌面行为 |
| 主题切换 + 视口切换同时触发图表重建 | `BaseChart` 合并 watch + 节流 `resize()` |
| i18n 双键遗漏 | 所有新文案走 `tl()`/`t()`；`check_i18n_keys.py --json` 每阶段必跑 |
| 契约 / 路由漂移 | **不新增端点、不新增表、不新增路由**；保存视图先落 `localStorage`。**唯一字段级例外**：机柜制冷能力（§7 决策 1，用户确认），须跑 `check_api_contract.py` / Alembic 迁移 / 后端测试并同步 `openapi.json`，不得外推到其它契约变更 |
| 移动端加载 3D 卡顿 | S/XS 档降为 2D 概览，不加载 3D 场景 |
| 「静默降级」回归 | 保留 `request.ts` 兜底但强制 `DataBadge`/`MockDataBanner`；`useMockFlag` 三档中 `partial` 必须写明模拟字段；P0 信息四档均不得隐藏 |
| 刷新策略误当现状 | 按 [03](./03_METRICS_IA.md) §5.2 的「现状实测 / 设计建议」分离执行；页面内不再硬编码 3s/5s/15s/30s/10s 混合数字 |

**全程不变量**（v1.1 修订第 2 条）：

1. 不引入第三方组件库（项目已有自建组件 + 3072 i18n 键）。
2. 不新增后端端点 / 数据库表 / 路由；**字段级例外仅限 §7 决策 1 的机柜制冷能力（用户确认「要在契约中存在」）**，不得外推。
3. 不重构设计语言（暗色科技风 + 亮色双主题保持不变）。
4. 不静默降级（示例数据必须显式标记）。
5. 不把设计建议写成现状（刷新频率、容量图层数据源均以核实结论为准）。
6. 每阶段结束都必须全绿，红灯不得带入下一阶段。

---

## 7. 决策登记（v1.1 · 用户已逐项答复，2026-11-10）

原「待确认清单」8 项已由用户答复确认。第 1–3 项经**只读代码核实**后有事实更正（v1.0 的判断有误），以本节为准；**代码轮不得再按 v1.0 的假设实施**。

| # | 用户答复 | 只读核实结论 | 落地约束 |
| --- | --- | --- | --- |
| 1 | 机柜「制冷能力 / 额定制冷容量 kW」字段**要在契约中存在** | **当前不存在**：`backend/app/models/cabinet.py:15-29` 的 `Cabinet` 仅有 `u_total/u_used/rated_power_kw/current_power_kw/status`；`cooling_capacity_mw` 是园区级（`models/idc.py:24`）、`capacity_kw` 是机柜额定**功率** kW（`schemas/idc.py:25`）；`openapi.json` 的 `/api/cabinets*` 4 端点（`:602,624,655,686`）响应为 `type: object` | 代码轮需**新增模型字段 + Pydantic schema + Alembic 迁移 + `openapi.json` 同步**；这是 §6 不变量 2 的**用户确认例外**；`check_api_contract.py` 的 200 paths / 271 ops 不变（只改 schema），但必须回归 |
| 2 | 空间 / 承重容量图层：**图层切换做四层** | **数据源已存在**：`backend/app/services/capacity_energy.py:345-365` 返回五维 dims，`capacity_whatif.py:6-7,23-29` 与 `openapi.json:2465` 佐证；空间另有 `/api/cabinets/{id}/u-position`（`:655`）。v1.0「先只落地温度 + 电力两层」的判断**作废** | 四层 = 温度 / 电力 / 空间 / 承重，第五维「网络端口」不进图层；承重为估算值需显式标注「估算 · 非实测称重」；见 [03](./03_METRICS_IA.md) §2.6 |
| 3 | 先核对 `useAsyncPage.ts` 与采集配置，**不把建议值当现状** | `useAsyncPage.ts` 全文 404 行**无轮询**；轮询真实存在于页面层：`.env.development` 的 `VITE_REFRESH_INTERVAL=3000`、页面硬编码 5s/15s/30s/10s、后端 `mock_collector.py:29` `PUSH_INTERVAL_SEC=5`。完整实测表见 [03](./03_METRICS_IA.md) §5.2 | 后续代码轮按「现状实测 / 设计建议」两列分离执行；真实采集器周期仍需与后端确认；**禁止把建议值写进注释当现状** |
| 4 | 默认 `localStorage`（按用户 + 路由隔离），**不新增 API** | 与 v1.0 一致 | 保存视图与列配置落本地，不引入后端表；跨设备共享留待后续评估 |
| 5 | `/api/network/bandwidth` `/api/network/ping` **单独评估**，本轮不假定数据已存在 | 契约端点存在、前端 0 引用（[02](./02_DIAGNOSIS.md) §3 A-4） | 接线与否作为独立任务；阶段 2/3 不假定数据存在；不新增端点 |
| 6 | NVR 存储天数合规阈值 N **待业务确认后登记** | `V/monitor/SecurityCctv.vue:44` 仅写「要求 ≥ N 天」，N 未在模板给出 | **仍开放**：业务给出 N 前不写入 `metricsCatalog`，界面只展示实测天数 |
| 7 | 3D / 大屏在 S/XS 档**默认 2D 概览 + 提示** | 与 v1.0 默认一致 | S/XS 不加载 3D 场景；提示文案需 i18n 双键 |
| 8 | 分页**默认 20，可选 20/50；审计页保留 50 作为例外登记** | 现状 10/12/20/50 四种（[02](./02_DIAGNOSIS.md) §5 C-1） | 审计页 50 为唯一登记例外，写入 [04](./04_VISUAL_SPEC.md) §6.2 与 [05](./05_RESPONSIVE_SPEC.md) 验收清单 |

### 7.1 决策 1 带来的不变量调整

§6 不变量 2 由「不新增后端端点 / 数据库表 / 路由」修订为：**不新增端点 / 表 / 路由；机柜制冷能力作为用户确认的字段级例外，允许新增字段与 Alembic 迁移**。风险表「契约 / 路由漂移」同步补充：字段新增必须跑 `check_api_contract.py`、Alembic 迁移与后端测试，`openapi.json` 由后端导出后与前端契约文件同步，避免 200 paths / 271 operations 之外的隐性漂移。**该例外仅适用于决策 1，不得外推到其他契约变更。**

### 7.2 仍开放项

仅第 6 项（NVR 阈值 N）与第 3 项中的「真实采集器周期」需业务 / 后端确认；其余 6 项已闭环，可直接进入代码轮。

## 8. 交接说明

本轮交付物为 `docs/design/` 下 7 篇 Markdown（本文件 + [README](./README.md) + 01–05），**不含任何运行文件改动**。请按以下顺序审阅：

1. [README.md](./README.md)：范围、术语、关键数字速查。
2. [01_BENCHMARK.md](./01_BENCHMARK.md)：对标结论与 8 条借鉴项（B-01~B-08）。
3. [02_DIAGNOSIS.md](./02_DIAGNOSIS.md)：四维诊断 + 77 页逐页问题清单（**重点审阅销账基线**）。
4. [03_METRICS_IA.md](./03_METRICS_IA.md)：指标字典、P0/P1/P2 与四块结构（**重点审阅内容层级是否符合业务**）。
5. [04_VISUAL_SPEC.md](./04_VISUAL_SPEC.md) / [05_RESPONSIVE_SPEC.md](./05_RESPONSIVE_SPEC.md)：视觉与响应式验收依据。
6. 本文件：四阶段排期、门禁与 §7 决策登记。

**审阅认可后另开一轮**执行阶段 1；阶段 2 结束设置「标杆页确认」闸门，再进入阶段 3/4。若审阅中对范围、优先级或 §7 决策登记有调整，先更新对应文档再动代码，避免规格漂移。
