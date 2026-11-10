# 05 · 响应式规范（四档断点与渐进式降级）

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **核查日期** 2026-11-10
> **本轮只交付文档，不修改任何运行文件。**

## 1. 目标与现状

**目标**：桌面端与移动端获得**一致的体验**——同一信息层级、同一组件语义、同一交互契约，只是布局密度与导航形态不同；不允许出现「移动端看不到某块内容」或「横向溢出被裁切」。

**现状**（证据见 [02_DIAGNOSIS.md](./02_DIAGNOSIS.md) §5 / C-2）：

| 事实 | 证据 |
| --- | --- |
| 70 处 `@media` / 36 文件 / **18 种 max-width 值**，全部为 max-width，无 min-width、无移动优先 | 02 文档 C-2 断点表 |
| 全局自身 5 套不一致边界 | `S/index.scss:185`(1180)、`:191`(768) 作用于裸 `.cols-*`；`:350`(1200)、`:351`(900)、`:352`(720) 作用于 `.grid.cols-*` |
| 无侧栏抽屉 / 汉堡 / 视口监听 | `L/DefaultLayout.vue:6,8,42,54-55,291-296,307-371` 全部 0 命中 |
| 固定 236px 侧栏 + 禁整页滚动 | `S/index.scss:71` `.body{grid-template-columns:236px 1fr}`；`:46` `body{overflow:hidden}` |
| 表格强制 680px 最小宽 | `S/index.scss:179,:182` |
| 顶栏不换行、时钟定宽 | `S/index.scss:52-56` 无 `flex-wrap`；`:65` `.clock{min-width:160px}`；`C/layout/TopBar.vue:1-171` 无 `<style>` / 无 `@media` |
| 唯一窄屏降级 | `S/index.scss:194` `@media(max-width:768px){.global-kpis{display:none}}` |
| 打印规则分散 | `V/ops/HealthReport.vue:945` 与 `ST/print.css:2` 两处 `@media print` |

**375px 下的实际后果**：侧栏仍占 236px → 主区约 139px；`.grid.cols-*` 与 680px 表格横向溢出；`body{overflow:hidden}` 禁止整页横向滚动 → **内容被裁切且无法触达**；顶栏 logo / tools / `.runmode` / 160px 时钟互相挤压。

> 路径简写：`V/` = `frontend/src/views/`，`S/` = `frontend/src/assets/styles/`，`ST/` = `frontend/src/styles/`（`p3.css` / `print.css`），`L/` = `frontend/src/layouts/`，`C/` = `frontend/src/components/`。

---

## 2. 四档断点定义

| 档位 | 设计视口 | CSS 边界 | 典型设备 | 导航形态 | 栅格 |
| --- | --- | --- | --- | --- | --- |
| **XS 小屏手机** | **375px** | `@media (max-width: 420px)` | 手机竖屏 | 侧栏抽屉（默认关闭）+ 精简顶栏 | 单列 |
| **S 手机/小平板** | **768px** | `@media (max-width: 768px)` | 大屏手机、小平板竖屏 | 侧栏抽屉 + 顶栏保留主题/语言 | 单列 / 双列（卡片） |
| **M 平板/小桌面** | **1024px** | `@media (max-width: 1024px)` | 平板横屏、小笔记本 | 侧栏抽屉（可记忆展开态） | 最多 2 列 |
| **L 标准桌面** | **1440px** | `@media (max-width: 1440px)` | 常规显示器 | 侧栏常驻 236px | 3–4 列，KPI 行用 `.cols-auto` |
| 宽桌面 | >1440px | 默认样式（无媒体查询） | 大屏 / 监控墙 | 侧栏常驻 | 4–6 列，仅在确认不拥挤时启用 |

**四条实施规则**：

1. **全库只允许上述 4 条 `max-width` 边界**（420 / 768 / 1024 / 1440）+ `@media print` + `@media (prefers-reduced-motion: reduce)`。页面 scoped 样式中不得出现任何其他 max-width 数值。
2. 用 `min-width` 的场景仅限**宽桌面增强**（如大屏/3D 画布放大），且必须写成 `@media (min-width: 1441px)`。
3. 断点值集中在 `S/index.scss` 顶部以注释/变量声明；SCSS 用统一 mixin（如 `@include bp-down(md)`）生成，避免各页再写字面量。
4. `@media print` 只允许 `ST/print.css` 一处输出；`V/ops/HealthReport.vue:945` 的页内打印规则并入。

---

## 3. 现有 18 种断点的迁移映射表

**归并原则**：把原 `@media (max-width: Xpx)` 归入「**不小于 X 的最小标准边界**」。这样规则在原宽度下**仍会生效**（适用范围只增不减，保守防溢出），代价是在更宽的屏幕上更早降级；因此 1024–1440 区间是重点回归区。

| 原值 | 处数 | 归入边界 | 代表位置 | 回归重点 |
| --- | --- | --- | --- | --- |
| 1440 | 1 | **1440** | `V/overview/Index.vue:1586` | 无变化 |
| 1280 | 5 | **1440** | `V/monitor/PowerLv.vue:1796`、`PowerHv.vue:1858`、`PowerGenset.vue:1581`、`PowerFuel.vue:2582`、`V/ops/Risk.vue:1167` | 1280–1440 是否过度降列 |
| 1200 | 4 | **1440** | `V/overview/Index.vue:1594`、`V/monitor/HvacLiquid.vue:1060`、`HvacCrac.vue:942`、`S/index.scss:350` | 1200–1440 |
| 1180 | 2 | **1440** | `V/monitor/NetworkSwitches.vue:994`、`S/index.scss:185` | 1180–1440；裸 `.cols-*` 与 `.grid.cols-*` 必须统一后再迁 |
| 1100 | 12 | **1440** | `V/monitor/SecurityIds.vue:1000`、`ThermalCloud.vue:488`、`V/ops/Tickets.vue:1136`、`Alarms.vue:1986`、`C/SecurityKnowledge.vue:153` 等 | **最大一组**：1100–1440 大范围提前降级，逐页确认 |
| 1000 | 3 | **1024** | `V/monitor/HvacLiquid.vue:1112,1141,1221` | 1000–1024 新增生效 |
| 980 | 3 | **1024** | `V/ops/WorkflowCenter.vue:1509`、`RoomAccess.vue:643`、`V/monitor/PowerBattery.vue:1656` | 980–1024 |
| 920 | 1 | **1024** | `V/ops/UPosition.vue:350` | U 位网格在 920–1024 的可读性 |
| 900 | 7 | **1024** | `S/index.scss:351`、`V/monitor/HvacLiquid.vue:1124,1164`、`HvacCrac.vue:1004,1059`、`V/ops/CapacityWhatIf.vue:288`、`V/energy/EnergyDashboard.vue:1081` | 900–1024 |
| 860 | 6 | **1024** | `V/monitor/PowerFuel.vue:2593`、`PowerLv.vue:1807`、`PowerHv.vue:1875`、`PowerGenset.vue:1592`、`ThermalCloud.vue:502`、`V/ops/HealthReport.vue:939` | 860–1024 |
| 768 | 4 | **768** | `S/index.scss:191`、`V/overview/Index.vue:1611`、`V/ops/Alarms.vue:2001`、`IntegrationHub.vue:797` | 无变化 |
| 760 | 2 | **768** | `ST/p3.css:152`、`V/ops/Risk.vue:1175` | 消除与 768 差 8px 的错位 |
| 720 | 6 | **768** | `S/index.scss:352`、`V/ops/Tickets.vue:1151`、`MaintenanceCalendar.vue:635`、`DataCenterManage.vue:883`、`DataCenterCompare.vue:675`、`V/energy/EnergyDashboard.vue:1093` | 720–768 |
| 700 | 1 | **768** | `V/monitor/HvacLiquid.vue:1209` | 同上 |
| 640 | 7 | **768** | `C/common/ErrorBanner.vue:122`、`V/monitor/HvacLiquid.vue:1065`、`HvacCrac.vue:947`、`PowerFuel.vue:1948`、`NetworkWireless.vue:745`、`NetworkRouters.vue:1207`、`NetworkFirewalls.vue:933` | 640–768 |
| 600 | 2 | **768** | `V/monitor/HvacLiquid.vue:1129`、`PowerLinkage.vue:1465` | 同上 |
| 560 | 1 | **768** | `V/monitor/ThermalCloud.vue:528` | 同上 |
| 500 | 1 | **768**（或按需下沉到 420） | `V/monitor/HvacLiquid.vue:1169` | 若规则针对极窄屏排版，允许例外登记后归入 420 |
| `print` | 2 | 保留，但**只留 `ST/print.css`** | `ST/print.css:2`、`V/ops/HealthReport.vue:945` | 打印输出统一亮色 |

**回归例外登记**：若某条规则归并到 1440 后在桌面造成明显过度降级（例如 1100 组的 12 处规则），允许下沉到 1024，但必须在 `S/index.scss` 对应规则上方注释「例外原因 + 原断点值」，并在验收清单里逐条复核。

---

## 4. 四档布局降级矩阵

| 组件 / 区域 | L（1440） | M（1024） | S（768） | XS（375） |
| --- | --- | --- | --- | --- |
| **应用外壳 `.body`** | `grid-template-columns:236px 1fr`（`S/index.scss:71`） | 单列：侧栏脱离文档流改 `position:fixed` 抽屉 | 同 M | 同 M |
| **侧栏 `.side`** | 常驻、分组可折叠（`L/DefaultLayout.vue:291-296`） | 抽屉，默认关闭，汉堡打开；遮罩 `.modal-mask` | 抽屉，宽度 `min(86vw, 320px)` | 抽屉，宽度 `100vw - 32px` |
| **顶栏 `.topbar`** | 完整（logo + `.global-kpis` + tools + clock + 主题/语言） | 隐藏 `.clock` 与次要 tools | 隐藏 `.global-kpis`（沿用 `S/index.scss:194` 语义）、`.runmode` 收为图标 | 只保留汉堡 + 页面标题 + 主题 + 语言；`flex-wrap:nowrap`，溢出项收进「更多」菜单 |
| **主区 `.main`** | `padding:14px 16px 28px`（`:88`） | `padding:16px` | `padding:12px` | `padding:12px 8px 24px` |
| **栅格** | `.grid.cols-auto`（`minmax(200px,1fr)`）、3–4 列 | 最多 2 列 | 单列（卡片列表）；KPI 允许 2 列 `.cols-auto-sm` | 单列；`.cols-auto-sm` 也降为 1 列 |
| **P0 指标行** | 4 张横排 | 2×2 | 2×2（最小 140px/卡） | 纵向堆叠，数值不缩小（≥24px） |
| **子系统入口卡** | 3 列 | 2 列 | 1 列 | 1 列，卡内 3 指标改为 2 行紧凑排版 |
| **表格** | 完整列集 | 列 >8 时启用「默认列集」，其余进列配置抽屉 | 保留列集；容器 `.scroll-x` 内横向滚动，`table{min-width:680px}` 仅在容器内生效 | 同 S；**整页不得出现横向滚动**（`body` 保持 `overflow-x:hidden`，滚动只发生在 `.scroll-x`） |
| **图表 ECharts** | 高度 260–320px，完整图例 + 阈值线 | 高度 240px，图例换行 | 高度 200px，图例置于图下方，坐标轴标签隔行显示 | 高度 180px，只显示主序列 + 阈值线，其余进「更多序列」；**不重建实例**，仅 `resize()` + `setOption` |
| **手写 SVG 系统图** | 原始 viewBox，可平移缩放 | 保持 viewBox，去除次要标注 | 外层 `.scroll-x` 可横向滚动，图例移到图下方 | 提供「简化视图」开关（隐藏文字标注，仅保留拓扑与状态点） |
| **热力图 / 平面图** | 多图层完整 | 图层切换收为下拉 | 单列，下钻层级改为面包屑 | 同 S，色标图例纵向 |
| **3D / 大屏** | 完整（`V/monitor/Scene3D.vue`、`BigScreen.vue`） | 保留但降低渲染分辨率 | **降级为 2D 概览 + 「在桌面打开」提示**（不在移动端加载 3D 场景） | 同 S |
| **弹窗 `.modal`** | `max-width:520px`，居中 | 同 L | `width:100%`，`max-height:90vh`，底部安全区 | 全屏底部抽屉形态（`.modal.as-drawer`），圆角仅上方 |
| **表单 / 筛选栏** | 一行多控件 | 两行 | 纵向堆叠，按钮组整行 | 纵向堆叠，主按钮 `width:100%`、高 ≥44px |
| **分页** | 完整页码 + 每页条数 | 简页码 | 上一页/下一页 + 当前页 | 同 S |
| **打印** | — | — | — | 统一 `@media print`：`ST/print.css` 隐藏 `.side`/`.topbar`、强制亮色输出 |

---

## 5. 移动端交互契约（侧栏抽屉）

现状 `L/DefaultLayout.vue` 的 `collapsed` 只控制导航分组展开（`:291-296`），**不是侧栏折叠**。后续代码轮需新增（本轮只写规范）：

| 项 | 规范 |
| --- | --- |
| 触发 | 顶栏汉堡按钮（`Menu` 图标，lucide），`aria-label="打开导航"` / `aria-expanded` 同步 |
| 视口判定 | `matchMedia('(max-width: 1024px)')` 单一真值源；`resize` 只更新布尔，**不在 resize 回调里操作 DOM 布局** |
| 打开态 | 侧栏 `position:fixed; inset-block:0; left:0`，遮罩用全局 `.modal-mask`（`S/index.scss:330`）；`body` 滚动锁定（不用 `overflow:hidden` 硬切，避免 `index.scss:46` 的裁切问题） |
| 关闭 | 点击遮罩、按 `Esc`、选中任一导航项后自动关闭 |
| 焦点 | 打开时焦点移入抽屉，关闭后回到汉堡按钮；抽屉内 `Tab` 焦点陷阱 |
| 键盘 | 所有导航项 `<router-link>` 有可见 focus 环（见 [04](./04_VISUAL_SPEC.md) §8） |
| 状态记忆 | M 档（1024）可记忆用户展开偏好；S/XS 档每次进入默认关闭 |
| 安全区 | 底部交互区 `padding-bottom: max(12px, env(safe-area-inset-bottom))` |
| 动画 | 位移 200ms `ease-out`；`prefers-reduced-motion` 时无动画 |
| 禁止 | 移动端隐藏侧栏入口；用 `body.kiosk .side{display:none}`（`S/index.scss:256`）代替响应式；整页 `overflow:hidden` 裁切内容 |

---

## 6. 实施约束（防返工）

1. **先合并两套栅格再迁断点**：`S/index.scss:95-99` 的裸 `.cols-*` 与 `:340-344` 的 `.grid.cols-*` 必须先统一（见 [04](./04_VISUAL_SPEC.md) §5），否则同一页混用两类名会在同一宽度得到不同列数（`V/monitor/NetworkWireless.vue:609-611`）。
2. **禁止页面内新增 `@media (max-width: …)` 字面量**：所有降级规则通过全局 mixin 或统一的 `.scroll-x` / `.as-drawer` / 响应式工具类表达。
3. **允许的唯一数值例外**：`.scroll-x > table { min-width: 680px }`（`S/index.scss:179`）保留，但**必须**位于 `overflow-x:auto` 容器内；整页滚动条只在 `.main` 纵向出现。
4. **不改变路由**：抽屉只是导航呈现方式，`L/DefaultLayout.vue` 的 `staticNav` / `mergePluginNav()` 与 `frontend/src/router/index.ts` 的 71 路由不动；`scripts/check_nav_routes.py --strict` 仍应为 0 死链 / 0 孤儿。
5. **示例数据提示在窄屏不可丢**：`MockDataBanner` / `DataBadge` 在 XS 档仍可见（可折行但不得 `display:none`），否则违背「绝不静默降级」。
6. **P0 信息不降级**：告警 / 故障 / 越限指标在四档都必须首屏可见，只允许改变排版密度，不允许隐藏。
7. **打印**：`V/ops/HealthReport.vue:945` 的页内 `@media print` 并入 `ST/print.css`，避免两套打印规则互相覆盖。

## 7. 逐类页面验收清单

| 页面类别 | 数量 | 375 / 768 / 1024 / 1440 检查项 |
| --- | --- | --- |
| 4 个总览页（`*Dashboard.vue`） | 4 | 页头不换行溢出；P0 指标全部可见；入口卡 3→2→1 列；`cursor`/focus 在触屏与键盘均可见 |
| 电力/暖通 SVG 系统图（PowerHv/Lv/Genset/Fuel/Linkage、HvacLinkage） | 6 | SVG 在 `.scroll-x` 内可横滚；图例在 S/XS 移到图下；状态点颜色 + 文字双标示 |
| 宽表页（>8 列，9 处） | 9 | 默认列集可配置；`.scroll-x` 内横滚；表头 sticky；整页无横向滚动条 |
| 驾驶舱 `V/overview/Index.vue` | 1 | 六区块可配置布局在窄屏变单列；`DataBadge` 6 处仍可见；ECharts 只 resize 不重建 |
| 3D / 大屏 / 设计器 | 3 | S/XS 档降级为 2D 概览 + 提示，不加载 3D；设计器表单纵向堆叠 |
| 表格/表单密集页（`ops/` 39 + `ops/components/` 6） | 45 | 筛选栏纵向堆叠、重置按钮可见、分页触摸目标 ≥44px、弹窗改底部抽屉 |
| 审计 / 日历 / 报表 | 6 | 打印输出统一亮色；日历在 S/XS 改为列表视图；CSV 导出按钮可见；**审计页每页 50 条为唯一登记例外**（[06](./06_ROADMAP.md) §7 决策 8），其余页面默认 20 / 可选 50 |
| 登录页 `V/auth/Login.vue` | 1 | 表单居中、输入框 ≥44px、渐变背景硬编码色值 token 化 |

**通用验收（四档逐页）**：

- [ ] 无整页横向滚动（`document.documentElement.scrollWidth <= window.innerWidth`）。
- [ ] 主区可用宽度：375px 档 ≥ 343px（即侧栏不占用文档流）。
- [ ] 侧栏抽屉可开合，Esc / 遮罩 / 选中导航均可关闭，焦点可返回。
- [ ] P0 指标与示例数据标记在四档均可见。
- [ ] 主题切换后布局不变，仅颜色变化（不触发路由重载或图表重建）。
- [ ] 打印视图隐藏侧栏/顶栏且为亮色。
- [ ] `prefers-reduced-motion` 下无循环动画。

## 8. 落地改动清单（**本轮不执行**）

| 文件 | 改动点 | 验收标准 |
| --- | --- | --- |
| `S/index.scss` | 合并两套栅格；4 条断点 mixin；`.body`/`.side`/`.topbar` 四档规则；`.scroll-x` 与 `.modal.as-drawer`；`prefers-reduced-motion`；删除 `:194` 之外的零散降级 | 全库 `@media` 阈值集合 = `{420, 768, 1024, 1440}` + `print`/`reduced-motion` |
| `ST/p3.css`、`ST/print.css` | 760 → 768；打印规则统一到 `print.css` | 无 760 断点；打印规则单一来源 |
| `L/DefaultLayout.vue` | 新增 `isCompact`(`matchMedia`)、抽屉开合状态、汉堡按钮、Esc/遮罩/焦点管理 | 四档抽屉契约逐项通过；`check_nav_routes.py --strict` 仍 0 死链 / 0 孤儿 |
| `C/layout/TopBar.vue` | 增加窄屏结构（汉堡 + 精简 tools + 「更多」菜单），样式走全局 mixin | 375/768 顶栏不溢出 |
| `V/**/*.vue`（77） | 删除页内 70 处 `@media` 中的非标准阈值，按 §3 映射表归并；栅格统一 `.grid.cols-*` | 逐页四档验收清单通过 |
| `C/charts/BaseChart.vue`、`C/monitor/HeatmapView.vue` | 暴露 `compact` 响应式表现（高度/图例/序列数），`resize()` 而非重建 | 主题切换 + 视口切换不重建实例 |
| `V/monitor/Scene3D.vue`、`BigScreen.vue`、`BigScreenDesigner.vue` | S/XS 档 2D 概览降级与提示文案（i18n 双键） | `check_i18n_keys.py` 双键对齐 |
| `frontend/e2e/specs/` | 新增 375/768/1024/1440 四档冒烟（可与现有 10 条并列，`workflow_dispatch` 触发） | `npm test` / `CI=1 npm test` 全通过 |

## 9. 风险、性能与回滚

| 风险 | 缓解 |
| --- | --- |
| 断点保守归并导致 1024–1440 桌面过度降列 | 按 §3「例外登记」把个别规则下沉 1024，并做 1280/1366/1440 三档视觉回归 |
| 抽屉改动影响 `DefaultLayout.vue` 的插件菜单合并 / 实时联动 | 不动 `staticNav`、`mergePluginNav()`、`onMounted` 的 WS 逻辑；只增视口状态与渲染分支 |
| 主题切换 + 视口切换同时触发时图表重复初始化 | `BaseChart` 用 `watch` 合并更新，节流 `resize()`；不销毁实例 |
| 移动端加载 3D 造成卡顿/流量 | S/XS 档不加载 3D，降级 2D 概览 |
| 长列表在窄屏渲染过多 DOM | 沿用 `C/common/VirtualList.vue`；>8 列宽表默认列集 |
| 回滚 | 每次改动限定在单阶段（`[06_ROADMAP.md](./06_ROADMAP.md)` 阶段 4），样式文件可整段 revert；抽屉逻辑以 `isCompact` 布尔开关隔离，关闭即回到原桌面行为 |

---

**阅读下一步**：[06_ROADMAP.md](./06_ROADMAP.md)（四阶段实施、验收门禁与交接）→ [README.md](./README.md)（文档集索引与术语表）。
