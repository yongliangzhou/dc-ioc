# 04 · 双主题视觉规范（配色 / 字体 / 间距 / 组件 / 图表）

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **核查日期** 2026-11-10
> **本轮只交付文档，不修改任何运行文件。** 本文是后续代码轮的唯一视觉验收依据。

## 0. 设计定位与原则

**沿用现有「暗色科技风为主 + 亮色主题」双主题，不重构设计语言**（已由用户确认）。核心目标不是新增一套设计系统，而是让**已有 token 成为唯一色彩来源**。

| 原则 | 说明 | 对应诊断问题 |
| --- | --- | --- |
| 单一色彩来源 | 任何颜色只能来自 `frontend/src/assets/styles/index.scss:1-40` 的 `:root` token，或由 token 派生的 `rgba()`；页面 scoped 样式与 JS 图表 option 中不得出现 hex/rgb 字面量 | `C1`（约 1975 行） |
| 变量必须有定义 | 禁止 `var(--未定义, #fallback)`；兼容别名只允许在 `:root` 一处定义 | `C2`（10 个别名） |
| 一个类名一处定义 | 同名全局类只允许定义一次；组件只保留唯一实现 | `C3`（15 组重复 + 3 套 KPI） |
| 状态不靠颜色独断 | 状态色必须搭配文字或图标；色盲可达 | [02](./02_DIAGNOSIS.md) D-1、`C6` |
| 数字等宽对齐 | 所有指标数值 `font-variant-numeric:tabular-nums`，避免刷新时布局抖动 | [03](./03_METRICS_IA.md) §5.3 |
| 渐进增强 | hover/focus/过渡是增强，不改变布局；`prefers-reduced-motion` 时降级为无动效 | `I4` |

---

## 1. 双主题 Token 完整表（现状，来自 `index.scss:1-40`）

> 以下为**当前实现值**，本规范予以确认并冻结；后续优化只允许改 `:root` 定义，不允许在页面另写。

| Token | 暗色 `:root, :root[data-theme="dark"]` | 亮色 `:root[data-theme="light"]` | 用途 | 定义行 |
| --- | --- | --- | --- | --- |
| `--bg` | `#070d1a` | `#eef2f8` | 页面底色 | `:2` / `:24` |
| `--bg2` | `#0c1426` | `#f7f9fc` | 次级底、输入框底 | `:2` / `:24` |
| `--panel` | `#0f1b33` | `#ffffff` | 卡片/面板 | `:2` / `:24` |
| `--panel2` | `#13233f` | `#eef3fa` | 次级面板 | `:2` / `:24` |
| `--line` | `#1d2f4f` | `#d4deec` | 1px 边框、分隔线 | `:3` / `:25` |
| `--txt` | `#cfe0ff` | `#1e2a3c` | 正文 | `:3` / `:25` |
| `--txt2` | `#7e93b8` | `#5a6c88` | 辅助文字 | `:3` / `:25` |
| `--txt3` | `#54688e` | `#8595ad` | 弱化文字、placeholder | `:3` / `:25` |
| `--txt-strong` | `#ffffff` | `#0b1524` | 标题、强调 | `:4` / `:26` |
| `--cyan` | `#22e3ff` | `#0891b2` | 主强调、渐变起点 | `:5` / `:27` |
| `--blue` | `#3b82f6` | `#2563eb` | 次强调、渐变终点 | `:5` / `:27` |
| `--green` | `#2bd47a` | `#16a34a` | 正常 / 在线 | `:5` / `:27` |
| `--amber` | `#ffb020` | `#d97706` | 警告 / 越限 | `:5` / `:27` |
| `--red` | `#ff4d5e` | `#dc2626` | 严重 / 故障 | `:6` / `:28` |
| `--purple` | `#9b6bff` | `#7c3aed` | 计划 / 预测 | `:6` / `:28` |
| `--pink` | `#ff5fa2` | `#db2777` | 特殊标记 | `:6` / `:28` |
| `--glow` | `0 0 12px rgba(34,227,255,.45)` | `0 0 10px rgba(8,145,178,.25)` | 聚焦光晕 | `:7` / `:29` |
| `--track` | `#13233f` | `#dbe4f0` | 进度条底 | `:8` / `:30` |
| `--badge-bg` | `#1c2c4a` | `#e3eaf4` | 徽章底 | `:8` / `:30` |
| `--map-bg` | `#0a1322` | `#e8eef7` | 平面图/热力图底 | `:8` / `:30` |
| `--bg-glow` | `#10203f` | `#dde7f5` | 页头径向渐变 | `:9` / `:31` |
| `--topbar1/2` | `#0b1830` / `#0e2138` | `#ffffff` / `#f2f6fb` | 顶栏渐变 | `:10` / `:32` |
| `--side1/2` | `#0b1428` / `#0a1120` | `#f7f9fc` / `#eef2f8` | 侧栏渐变 | `:11` / `:33` |
| `--mask` | `rgba(3,8,18,.62)` | `rgba(30,42,60,.35)` | 弹窗/抽屉遮罩 | `:12` / `:34` |
| `--grid-line` | `rgba(34,227,255,.05)` | `rgba(8,145,178,.08)` | 图表网格线 | `:13` / `:35` |
| `--row-hover` | `rgba(34,227,255,.04)` | `rgba(8,145,178,.06)` | 表格行 hover | `:14` / `:36` |
| `--td-line` | `rgba(29,47,79,.55)` | `rgba(212,222,236,.8)` | 表格内线 | `:15` / `:37` |
| `color-scheme` | `dark` | `light` | 原生控件渲染 | `:21` / `:39` |

### 1.1 兼容别名的收口方案（P0）

`index.scss:16-19`、`:38` 已定义 `--text` / `--muted` / `--panel-2` 映射（注释 `:16-18` 自述「按钮看不到字」的历史修复）。**这 3 个别名予以保留**，但需在后续代码轮逐步把页面引用改为正式 token 后删除映射。

其余 **10 个全库未定义变量**按下表替换（禁止保留 fallback）：

| 未定义变量 | 现状引用（代表） | 替换为 | 说明 |
| --- | --- | --- | --- |
| `--bg-card` | `index.scss:108` | `var(--panel)` | `.moni-card` 背景 |
| `--border` | `index.scss:108`、`V/monitor/SecurityAcs.vue:586`、`SecurityIds.vue:627`、`SecurityFire.vue:963`、`V/ops/Risk.vue:767` 等 | `var(--line)` | 边框 |
| `--text-primary` | `index.scss:111`、`V/monitor/PowerFuel.vue:1786` 等 | `var(--txt-strong)` | 卡片主文字 |
| `--text-2` | `index.scss:115`（**无 fallback，已失效**）、`SecurityCctv.vue:517`、`SecurityIds.vue:604` | `var(--txt2)` | 辅助文字 |
| `--text-muted` | `PowerFuel.vue:1791`、`PowerHv.vue:1382`、`V/ops/WorkflowCenter.vue:935` | `var(--txt3)` | 弱化文字 |
| `--border-light` | `V/ops/Risk.vue:880` | `var(--line)` | 弱化边框 |
| `--bg-1` / `--text-1` | `V/monitor/SecurityAcs.vue:588,594` | `var(--bg2)` / `var(--txt)` | — |
| `--brand` | `V/monitor/SecurityAcs.vue:594` | `var(--cyan)` | — |
| `--strong` | `V/energy/EnergyDashboard.vue:705` | `var(--txt-strong)` | — |
| `--muted` | `V/energy/EnergyDashboard.vue:702` | 已定义别名 → `var(--txt2)` | 保留别名或直改 |

**全局样式自身的硬编码也需 token 化**：`index.scss:58`（logo 渐变 `#22e3ff,#9b6bff`）、`:134` `#3a4a66`、`:142-143` 徽章配色、`:214` `#bff`、`:260` `#0a1220`（`.heat-cell` 文字色）、`:287` `#fff`（`.btn-primary` 文字）、`:331` `rgba(0,0,0,.5)` 弹窗阴影。这些在亮色主题下仍是暗色值。

### 1.2 状态色语义（四级，必须搭配文字/图标）

| 状态 | Token | 语义 | 必须同时具备 |
| --- | --- | --- | --- |
| 正常 / 在线 | `--green` | 指标在阈值内、设备在线 | 文字「正常 / 在线」或 `Check` 图标 |
| 预警 / 越限 | `--amber` | 接近阈值、容量将满 | 文字「预警」+ 阈值数值 |
| 严重 / 故障 | `--red` | 越限、故障、中断 | 文字「严重 / 故障」+ `AlertTriangle` 图标 |
| 计划 / 预测 | `--purple` | 预测值、What-If、计划态 | 虚线线型 + 图例「预测」 |

**禁止**：只用颜色区分状态（现状 `V/monitor/NetworkSwitches.vue:95` 把 CPU 直接映射 `#ef4444`/`#f59e0b` 而无文字）；禁止在 JS 里写状态色字面量。

---

## 2. 字体层级

| 层级 | 字号 / 字重 | 行高 | 用途 | 现状差异 |
| --- | --- | --- | --- | --- |
| 页面主标题 `h1` | **24px / 700** | 1.3 | 每页唯一，位于 `.view-head` | `index.scss:90` 18px、`:268` 19px 两处冲突；57 处 h1 / 33 处 h2 混用 |
| 区块标题 | **16px / 600** | 1.4 | `Panel` 标题、卡片头 | `.card-title` `:114` 600/14px → `:283` 700/14px 冲突 |
| 正文 | **13px / 400** | 1.5 | 表格、说明、标签 | `body` `index.scss:45` 已是 13px |
| 辅助 / 单位 | **11px / 400** | 1.4 | 单位、时间戳、脚注 | `.card .cv small` `:104` 12px |
| P0 指标数值 | **24px / 700** | 1.1 | 首屏关键指标 | `.card .cv` `:103` 24px/800（字重收为 700） |
| P1 指标数值 | **16–20px / 600** | 1.2 | 入口卡、次行 KPI | 现状 `.kvs .v` 仅 12.5px/500 |

**字体族**：沿用 `index.scss:44` 的 `"Segoe UI","PingFang SC","Microsoft YaHei",system-ui,sans-serif`，**不引入外部 Web Font**（离线部署与 CSP 约束）。数值统一 `font-variant-numeric:tabular-nums`，必要时追加 `ui-monospace, SFMono-Regular, Consolas, monospace` 作为**数字专用**栈（`.mono` 类已有）。

> 设计知识库建议的 `Fira Code + Fira Sans` 配对（`ui-ux-pro-max --domain typography`「Dashboard Data」）作为**可选增强**记录于此，但本规范不采用：引入 Google Fonts 会破坏离线环境与现有字体一致性，收益低于风险。

## 3. 间距、圆角、边框与阴影

| 尺度 | 值 | 用途 |
| --- | --- | --- |
| 间距 token | `4 / 8 / 12 / 16 / 24 px` | 只允许这 5 档；现状 `index.scss:88` 主区 `14px 16px 28px`、`:100` 卡片 `14px`、`:263` `page-wrap` `18px`、`:265` 页头 `14px 18px` 等需归并 |
| 网格间距 | **12px** | `.grid` `index.scss:94`、`:339` 已一致，保留 |
| 卡片内边距 | **14px** | `.card` `:100`；`.moni-card` `:108` 的 16px 归并 |
| 圆角 | **8 / 12 / 14px** 三档 | 8 = 按钮/输入/徽章；12 = 卡片；14 = 页头/弹窗/大面板。现状 `:257` 7px、`:296` 6px、`:108` 10px、`:100` 12px、`:265` 14px 需归并 |
| 边框 | `1px solid var(--line)` | 禁止自写 rgba 边框（现状 `index.scss:271` `rgba(34,227,255,.35)` 等） |
| 阴影 | `var(--glow)`（聚焦）；弹窗 `0 20px 60px var(--mask)` | 现状 `:331` `rgba(0,0,0,.5)` 需改 |
| 卡片顶部渐变光线 | 保留 1px，但统一为 `linear-gradient(90deg, transparent, var(--cyan), transparent)` + 固定透明度 token，**禁止各页自调透明度** | 现状 `:101` 与 `:109` 都写 `rgba(34,227,255,.5)` |

## 4. 组件唯一实现与 API 收敛（P1）

| 能力 | **唯一保留实现** | 收敛/废弃对象 | 迁移动作 |
| --- | --- | --- | --- |
| 指标卡（遥测向） | `C/common/MetricCard.vue:92-122`（`metricName/label/value/unit/quality/online/sparkData/severity/stale`，emits `select`） | — | 作为 P0/P1 指标的唯一组件 |
| 统计 KPI 卡 | `P/KpiCard.vue`（`@dc-ioc/ui`，`dui-kpi-*`） | 删除 `C/monitor/KpiCard.vue:35-63` 的同名副本 | `C/monitor/index.ts` 统一从 `@dc-ioc/ui` 重导出；统一默认条色 `var(--cyan)`（去掉 `#06b6d4` fallback） |
| 趋势图 | `C/charts/TrendChart.vue:90-109` + `BaseChart.vue` | `C/monitor/TrendChart.vue:67-105` 改为薄适配层或删除 | 统一 `series` 类型；`TimeRangePicker` 保留为独立组件 |
| 状态徽章 | `P/StatusBadge.vue` / `P/AlarmBadge.vue` | `C/monitor/StatusBadge.vue:11-19`、`AlarmBadge.vue:10-18` | 修 `P/StatusBadge.vue:31` 的 `'dui-'+'dui-o'` 双前缀瑕疵；统一 class 前缀 |
| 空态 | `C/common/EmptyStateCard.vue:31-36`（`title/desc/icon/minHeight` + `actions` slot） | `C/monitor/EmptyState.vue:9-18` | 删除默认 emoji 图标 `📊`，改 lucide-vue-next SVG |
| 加载态 | `C/common/LoadingState.vue:21-30`（spinner/skeleton/dots） | `C/monitor/SkeletonCard.vue:14` | `size` 映射为 `variant`；骨架色改 `var(--track)` |
| 异步四态 | `C/common/AsyncSection.vue:3-42` + `ErrorRetry.vue:26-30` + `ErrorBanner.vue` | 22+ 页手写 6 种错误 DOM | 逐页替换为统一组件；**错误态与空态严格区分** |
| 分页 | `C/Pagination.vue` | 4 种手写实现 | 每页条数统一 `20`（可选 20/50），筛选写 URL |
| 遮罩 | `.modal-mask`（`index.scss:330`）+ `.modal`（`:331`） | `.mask` / `.drawer-mask` / `.tf-mask` / `.ai-corrmask` / `drawer-mask` 共 ≥5 种 | 抽屉用 `.modal-mask` + `.modal.as-drawer` 变体，不再各页自造 |

> `C/domain/` 为空目录，直接删除或保留为空，不作为新组件落点。

## 5. 同名类合并清单（`index.scss`，P0）

**保留后定义（`:262` 起的「统一业务页组件库」），删除或合并前定义（`:89-134`）**，并消除两套栅格：

| 类 | 前 | 后 | 决策 |
| --- | --- | --- | --- |
| `.view-head` / `h1` / `.sub` | `:89-91` | `:265-269` | 保留后定义（卡片式页头），`h1` 字号改 24px/700（§2） |
| `.card-head` / `.card-title` | `:113-115` | `:282-285` | 保留后定义；修 `:115` `var(--text-2)` → `var(--txt2)` |
| `.section-title` / `::before` | `:126-127` | `:284-285` | 保留后定义（渐变条），字号改 16px/600 |
| `.btn-sm` | `:257-258` | `:296` | **必须合并**：后定义丢失 `border`/`background`，导致按钮在部分主题下不可见；合并为一套 12px / `5px 10px` / 8px 圆角 / `1px solid var(--line)` / `var(--panel)` |
| `.grid` / `.cols-*` | `:94-99` | `:339-344` | 只保留 `.grid.cols-*` 复合类；页面统一用 `<div class="grid cols-N">`；保留 `.grid.cols-auto` `:346` 与 `.cols-auto-sm` `:347` 作为首选（加减指标无需改类名） |
| `.pill` / `.g/.a/.b/.r/.c` | `:116-123` | `:313-319` | 保留后定义；删除 `:123` 冗余 fallback `#3b82f6` |
| `@keyframes blink` | `:135` | `:231` | 合并为一处 |
| `select option` | `:301` | `:304` | 保留全局 `:304`，删除 `:301` 重复 |
| `.scroll-x` / `.table-wrap` | `:178-182` | — | 统一为 `.scroll-x`（表格横向滚动容器，见 [05](./05_RESPONSIVE_SPEC.md) §4） |
| `.twin` / `.grid.twin` | `:183` | `:348` | 保留 `.grid.twin` |
| `.moni-card` | `:108-111` | — | 未定义变量全部替换为正式 token（§1.1），或直接由 `.card` 取代 |

## 6. 布局、页头与交互原子规范

### 6.1 页头与四块结构

```
.view-head（唯一 h1 + DataBadge + 最后刷新时间 + 时间范围 + 操作区 vh-right）
  ↓
.grid.cols-auto   P0 关键指标行（≤4 张 MetricCard）
  ↓
.grid.cols-3     子系统入口卡区（按设备域分组，每卡 3 个差异化指标）
  ↓
.grid.cols-2     趋势与告警联动区（BaseChart + 告警列表）
```

- 页面主标题**只允许一个 `<h1>`**，区块用 `h2`，卡内用 `h3`；修 `V/monitor/HvacChiller.vue:5` 整页无 h1、`V/overview/Index.vue:6` 用 h2 作主标题等 57/33 处混用。
- 栅格只用 `.grid.cols-N` / `.grid.cols-auto`；禁止裸 `.cols-N`（现状 `V/monitor/NetworkWireless.vue:609-611` 与全局两套规则并存导致同宽度下列数不同）。

### 6.2 按钮与表单

| 原子类 | 规范 | 现状归并 |
| --- | --- | --- |
| `.btn-primary` | 主操作（查询、保存、执行）；渐变 `var(--cyan)→var(--blue)`，文字 `var(--txt-strong)` 或白（按对比度校验），8px 圆角 | `index.scss:287-290`；修 `:288` `#fff` |
| `.btn-ghost` | 次操作（重置、取消） | `:291-293` |
| `.btn-danger` | 危险操作（删除） | `:294-295` |
| `.btn-sm` | 表格行内 / 分页 | 合并 `:257` 与 `:296` |
| 组合式 `btn-sm primary` | **废弃**，改用 `btn-sm btn-primary` | `V/ops/Equipment.vue:37`、`V/ops/Cabinets.vue:25` |
| 自定义按钮类 | `btn-refresh`（`HvacChiller.vue:23`、`PowerBattery.vue:13`）、`hv-edit`（`PowerHv.vue:33`）、`chip-clear`（`HvacCrac.vue:102`）、裸 `btn`（`SecurityAcs.vue:9`） → 全部改为 `.btn-ghost` / `.btn-sm` + lucide 图标 | — |
| 输入 | `.inp`（`index.scss:298-299`）+ `.field`（`:308-309`）；`select option` 统一 `:304`；`focus` 用 `var(--glow)` 可见环 | 多种 `ipt/sel/kb-input/dc-input` 归并 |
| 筛选栏 | `查询(.btn-primary) + 重置(.btn-ghost) + 保存视图 + 列配置`，顺序固定；筛选条件写 URL query（`?status=&page=&size=`） | 21 页有筛选、仅 4 页有重置 |
| 分页 | 统一 `C/Pagination.vue`，**默认 20 条，可选 20/50；审计页（`V/admin/AuditLogs.vue`）保留 50 并登记为唯一例外**（用户 v1.1 决策 8） | 现状 10/12/20/50 四种 |
| 弹窗/抽屉 | `.modal-mask` + `.modal`（抽屉加 `.as-drawer`）；Esc 关闭、点遮罩关闭、焦点陷阱 | ≥5 种遮罩类名 |

### 6.3 异步四态（统一由 `AsyncSection` 托管）

| 态 | 组件 / 文案 | 禁止 |
| --- | --- | --- |
| 加载 | `LoadingState` 骨架，保持容器高度（防抖） | 表格内 `{{ loading ? '加载中…' : '暂无数据' }}` 三元 |
| 错误 | `ErrorBanner` + `ErrorRetry`；文案含失败原因与「重试」 | 把错误写成 `EmptyState text="…加载失败"`（`HvacChiller.vue:925-926`）；错误只写 script 变量（`Scene3D.vue:70,433`） |
| 空 | `EmptyStateCard`（`title/desc/icon/actions`） | 用空态冒充错误 |
| 成功 | 正常内容 + 页头最后刷新时间 | — |

所有文案走 `tl()` / `t()`，zh/en 双语键同步（现状各 3072 键）。

**数据可信度标记独立于四态**：`frontend/src/composables/useAsyncPage.ts:138-164` 的 `useMockFlag` 提供 `none / partial / full` 三档，页头 `DataBadge` + 区块 `MockDataBanner` 两级展示；`partial` 必须在文案中点名哪些字段是模拟的（详见 [03](./03_METRICS_IA.md) §5.1）。承重容量等估算值按 `partial` 语义显式标注「估算 · 非实测称重」，不得用 `--red` 呈现为故障。

### 6.4 可达性

- 所有可点击元素 `cursor:pointer`（修 4 个总览页 `.entry-card` 0 命中，`V/monitor/PowerDashboard.vue:216-233` 等）。
- 可见 focus 环：`outline: 2px solid var(--cyan); outline-offset: 2px`，**不得** `outline:none` 而无替代。
- 状态变化过渡 **150–300ms**；hover 只改颜色/阴影/透明度，不改 `transform` 引起布局变化。
- `@media (prefers-reduced-motion: reduce)` 下禁用 `blink`/`spin`/`pillPulse` 等循环动画（现状 `index.scss:124-125,132,322`）。

---

## 7. 图表规范

### 7.1 实现边界

| 图表类型 | 唯一实现 | 说明 |
| --- | --- | --- |
| 折线/面积/柱状/饼/仪表 | `C/charts/BaseChart.vue`（ECharts） | 统一入口；`options.ts` 提供构造helper |
| 多指标趋势 + 时间范围 | `C/charts/TrendChart.vue` | 基于 `BaseChart`；`C/monitor/TrendChart.vue` 收敛 |
| Sparkline | `MetricCard.vue` 内嵌 SVG | 保留，但颜色取 `var(--cyan)`，去掉硬编码 |
| 热力图 | `C/monitor/HeatmapView.vue` / `V/monitor/ThermalCloud.vue` | 梯度从 token 派生；见 [01 范式 B](./01_BENCHMARK.md) |
| 系统拓扑 / 一次图 | 手写 SVG（Power*/Hvac*/Network* 页） | 保留，但 `fill`/`stroke` 全部用 token |
| 3D / 大屏 | `V/monitor/Scene3D.vue`、`BigScreen.vue` | 保留，主题色由 `:root` 读取，禁止自建 `.light` 类 |

### 7.2 配色、坐标轴、图例、阈值、空态

| 项 | 规范 | 依据（设计知识库 `--domain chart` 只读检索） |
| --- | --- | --- |
| 序列色 | `var(--cyan)` / `var(--blue)` / `var(--green)` / `var(--amber)` / `var(--purple)`，按序取用 | 多序列需可区分 |
| 预测 / 计划 | `var(--purple)` + **虚线** + 图例「预测」，实线为实际值 | Time-Series Forecast：Actual 实线、Forecast 虚线、置信带浅色 |
| 异常点 | 圆形/方形标记 + `--red` + **文字告警标注** | Anomaly Detection：marker + text annotation，不能只靠红色 |
| 面积填充 | 主色 20% 透明度（`color-mix` 或 token 派生），禁止写 `rgba(34,227,255,.06)` | Trend Over Time：fill 20% opacity |
| 网格线 | `var(--grid-line)`；坐标轴文字 `var(--txt2)`；轴线 `var(--line)` | 深色背景低对比网格 |
| 阈值线 | `markLine` 虚线 + `var(--amber)` / `var(--red)` + 文案「预警阈值 80%」，阈值值来自 `metricsCatalog`（[03](./03_METRICS_IA.md) §6） | 统一阈值标注 |
| 图例 | 必填；多序列须同时用线型/标记区分（色盲可达） | Accessibility：line patterns + legend |
| 空态 | 图表容器内显示 `EmptyStateCard`，保持容器高度，不显示空白坐标系 | 现状缺统一空态 |
| 实时流 | 提供「暂停」入口，禁止高频闪烁（修 `.dot.r` `blink 1.2s infinite` 无暂停） | Real-Time Streaming：⚠ 闪烁需 pause |
| 双主题 | 主题切换时只 `setOption` 更新 `color`/`axisLine`/`splitLine`/`textStyle`，**不销毁重建实例**；禁止 JS option 中写 hex（修 `V/monitor/PowerBattery.vue:721-1008`、`V/energy/EnergyDashboard.vue:435,447-451`） | 性能与一致性 |

### 7.3 图表类型选择表（避免滥用）

| 数据意图 | 用 | 不用 |
| --- | --- | --- |
| 单指标随时间 | 折线 / 面积 | 饼图 |
| 多指标同量纲对比 | 多序列折线（线型区分） | 多个仪表盘平铺 |
| 构成占比 | 堆叠柱 / 饼（≤6 类） | 折线 |
| 当前值 vs 阈值 | 仪表 / 进度条 + 阈值虚线 | 纯数字无参照 |
| 空间分布 | 热力图 / 平面图叠加 | 表格 |
| 拓扑 / 链路 | SVG 系统图 | 折线 |
| 异常定位 | 折线 + 异常点标记 + 文字标注 | 仅变色 |

---

## 8. 图标、动效与可访问性检查表

| 检查 | 要求 | 现状反例 |
| --- | --- | --- |
| 图标 | 统一 `lucide-vue-next` SVG，尺寸 16 / 20 / 24，颜色 `currentColor` | `C/monitor/EmptyState.vue` 默认 `📊`；`V/energy/EnergyDashboard.vue:589` `🎯` |
| 无 emoji 作图标 | 交付检查表硬性项 | 同上 |
| 触摸/点击目标 | ≥ 44×44px（移动端），≥ 32×32px（桌面紧凑表格） | 现状 `.btn-sm` `5px 10px` 约 24px 高 |
| 对比度 | 亮色主题正文 ≥ 4.5:1；暗色主题 ≥ 4.5:1；大字号 ≥ 3:1 | `--txt3` 在亮色下需复核 |
| 颜色非唯一指示 | 状态色 + 文字/图标/线型 | `NetworkSwitches.vue:95` |
| 动效 | 150–300ms；`prefers-reduced-motion` 降级 | `index.scss:124-125,132,322` 循环动画 |
| focus | 可见环，键盘可达所有交互 | 现状无统一规范 |
| 深链接 | 筛选/分页/时间范围写入 URL | 现状刷新即丢失 |

---

## 9. 落地改动清单（**本轮不执行**，供 [06_ROADMAP.md](./06_ROADMAP.md) 排期）

| 文件 | 改动点 | 验收标准 |
| --- | --- | --- |
| `frontend/src/assets/styles/index.scss` | 合并 15 组同名类；统一一套栅格；10 个未定义变量替换；全局自身 8 处硬编码 token 化；新增 `--space-*`/`--radius-*` token；新增 `prefers-reduced-motion` 段 | `rg '#[0-9a-fA-F]{3,8}'` 在该文件仅剩 `:root` 定义；同名类 0 组 |
| `frontend/src/views/**/*.vue`（77） | scoped 样式硬编码色值 → token；`var(--未定义,…)` → 正式 token；自定义按钮/遮罩类 → 统一原子类；主标题统一 `<h1>` | 页面文件中 hex/rgb 字面量 0 处（图表配置除外，见下条） |
| `frontend/src/views/monitor/PowerBattery.vue`、`energy/EnergyDashboard.vue` 等 | JS ECharts option 中的 hex/rgba → 读 CSS 变量或集中常量 | 主题切换后图表配色跟随，实例不重建 |
| `packages/dc-ioc-ui/src/StatusBadge.vue:31` | 修 `'dui-'+'dui-o'` 双前缀 | 单元测试覆盖状态映射 |
| `frontend/src/components/monitor/{KpiCard,TrendChart,StatusBadge,AlarmBadge,EmptyState,SkeletonCard}.vue` | 收敛为薄适配或删除；`index.ts` 统一重导出 | `C/monitor/` 与 `@dc-ioc/ui` 无同名重复实现 |
| `frontend/src/components/common/{MetricCard,AsyncSection,EmptyStateCard,LoadingState}.vue` | 按 §2/§4/§6 统一 API 与状态 | 4 个总览页 + 驾驶舱接入后 10 条 E2E 全通过 |
| `frontend/src/views/monitor/*Dashboard.vue`（4） | 按 [03](./03_METRICS_IA.md) §4.2 四块结构重排；入口卡差异化指标；补 `cursor`/focus | 视觉回归 + E2E 冒烟 |
| `frontend/src/i18n/locales/{zh-CN,en-US}.json` | 新增文案双键同步 | `check_i18n_keys.py --json` zh/en 对齐 |
| `frontend/src/router/index.ts` / `layouts/DefaultLayout.vue` | **不改路由**；仅新增抽屉与顶栏窄屏样式（见 [05](./05_RESPONSIVE_SPEC.md)） | `check_nav_routes.py --strict` 71 路由 0 死链 0 孤儿 |

## 10. 门禁与回归（后续代码轮）

- `vue-tsc --noEmit` 0 错误；`npm run test:run`（9 文件 / 52 用例）；`npm run build` 成功。
- `python scripts/check_i18n_keys.py --json`、`check_api_contract.py`、`check_nav_routes.py --strict`、`check_except_hygiene.py` 全通过。
- `frontend/e2e` Playwright 10 条冒烟（含 `CI=1` retries=1 / 2 workers 复跑）全通过。
- **双主题视觉回归**：逐页切换 `data-theme="dark|light"`，检查无恒定暗色块、无文字消失、图表配色跟随。
- **对比度**：亮色主题正文/辅助文字 ≥ 4.5:1（`--txt`/`--txt2`/`--txt3` 需实测）。

---

**阅读下一步**：[05_RESPONSIVE_SPEC.md](./05_RESPONSIVE_SPEC.md)（四档响应式降级）→ [06_ROADMAP.md](./06_ROADMAP.md)（分阶段实施与验收）。
