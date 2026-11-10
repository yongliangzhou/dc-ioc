# 02 · 全平台四维诊断报告（逐页证据）

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **核查日期** 2026-11-10
> **本轮只交付文档，不修改任何运行文件。** 所有结论均可在当前代码库定位到文件与行号。

## 1. 范围、方法与证据口径

| 项 | 说明 |
| --- | --- |
| 诊断范围 | **全平台** `frontend/src/views/` 共 **77 个 `.vue`**（`ops/` 39 + `ops/components/` 6 + `monitor/` 27 + `admin/` 2 + `auth/` 1 + `energy/` 1 + `overview/` 1），另有全局样式、布局、组件库、路由与接口契约作为支撑证据 |
| 四个维度 | 数据展示 / 信息层级 / 交互流程 / 视觉一致性 |
| 采集方式 | 只读静态扫描（`search_content` / `read_file`）+ 两个 `code-explorer` 子代理的交叉核对；**未运行页面、未截图**，视觉结论基于样式代码 |
| 统计口径 | 「命中数」= `search_content --count` 的**匹配行数**，不是出现次数；同一行多个色值只计 1 |
| 路径简写 | `V/` = `frontend/src/views/`，`C/` = `frontend/src/components/`，`S/` = `frontend/src/assets/styles/`，`ST/` = `frontend/src/styles/`，`L/` = `frontend/src/layouts/`，`P/` = `packages/dc-ioc-ui/src/` |
| 逐页清单口径 | 目录级结论（如「含硬编码色值」）来自全量扫描，表中行号是该页**可定位的锚点**；单页独有结论均给出精确行号 |

## 2. 结论摘要（Top 10，均可量化复核）

| # | 问题 | 量化证据 | 影响 | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | 双主题 token 被硬编码架空 | 77 页中 71 页含 hex/rgb 字面量，约 **1975 匹配行**，32 个文件 >20 处（`V/monitor/PowerFuel.vue:1786` 起 134 行） | 亮色主题大面积失效 | **P0** |
| 2 | 全局样式同名类二次定义 | **15 组**选择器重复，如 `.view-head` `S/index.scss:89 → :265`、`.btn-sm` `:257 → :296` | 后定义覆盖，页面观感不可预测 | **P0** |
| 3 | 引用未定义 CSS 变量 | 10 个别名全库无定义；`S/index.scss:108`、`:111`、`:115`，`V/monitor/SecurityAcs.vue:576-594` 等 | `var()` 失效，文字/边框消失，历史「按钮看不到字」 | **P0** |
| 4 | 移动端无布局降级 | `L/DefaultLayout.vue:6,8,42,54-55,291-296,307-371` 全无抽屉/汉堡/视口监听；`S/index.scss:71` 固定 `236px 1fr` + `:46 overflow:hidden` | 375px 下主区仅约 139px，内容被裁切且不可滚动触达 | **P0** |
| 5 | 断点各自为政 | **70 处 `@media` / 36 文件 / 18 种 max-width 值**，45 处不在全局 5 值内；`V/monitor/HvacLiquid.vue` 单页 7 个阈值 | 降级行为无法枚举、无法验收 | **P0** |
| 6 | 四个总览页指标同质化 | `V/monitor/PowerDashboard.vue:60-63,74-77,88-91,102-105,116-119` 五卡全为「平均负载率/平均电压」；`NetworkDashboard.vue:63-113`、`SecurityDashboard.vue:60-110` 同样 | 入口卡不传递设备域特征，用户无法判断去哪 | **P0** |
| 7 | 异步四态未统一接入 | 统一组件仅覆盖 **55/77** 文件；`AsyncSection` 32、`ErrorBanner` 12、`ErrorRetry` 3、`EmptyStateCard` 2、`DataBadge` 5、`MockDataBanner` 21；**22+ 页手写 6 种错误 DOM** | 错误被当空态、重试入口缺失、可读性与可信度不一致 | **P0** |
| 8 | 组件体系三套并存 | 3 套 KPI（`C/common/MetricCard.vue:92-108` / `P/KpiCard.vue:4-32` / `C/monitor/KpiCard.vue:35-63`）、2 套 TrendChart、2 套 Badge、2 套 Loading | 同一指标在不同页视觉与 API 不同 | **P1** |
| 9 | 宽表与指标平铺 | 33 页含 `<table`、35 页含 `<th`、**9 处 >8 列**（`V/monitor/PowerLv.vue:351-368` 达 18 列）；`V/monitor/HvacLiquid.vue` 单页约 23 张 KPI | 首屏信息密度过高，关键异常无视觉权重 | **P1** |
| 10 | 交互原子类不统一 | 筛选 21 页仅 4 页有「重置」；分页 4 种实现、每页 10/12/20/50 不一；遮罩 ≥5 种类名；4 个总览页 `cursor` 检索 0 命中 | 学习成本高，键盘/触屏可达性差 | **P1** |

> 另有数据层发现：监控页实调 16 个后端路径，`frontend/openapi.json` 中 DCIM 相关端点 29 个，其中 `/api/network/bandwidth`、`/api/network/ping` **契约存在但前端 0 引用**（`openapi.json:2295,2339`）；总览 KPI 多为前端 `Promise.all` 聚合（`api/power.ts:1148-1150` 等），无独立后端聚合接口。

---

## 3. 维度 A · 数据展示

### A-1 指标同质化（P0）

四个总览页是同一模板的四次复制，只有 `HvacDashboard.vue` 做了按设备类型的差异化指标。

| 页 | 入口卡 | 实际指标 | 证据 |
| --- | --- | --- | --- |
| `V/monitor/PowerDashboard.vue` | 6（HV/LV/柴发/燃油/电池/链路） | 前 5 张**全部**「平均负载率 / 平均电压」，共用 `avgLoadPercent`/`avgVoltage` | `:52-65`、`:66-79`、`:80-93`、`:94-107`、`:108-121`；格式化 `:171-176` |
| `V/monitor/NetworkDashboard.vue` | 4 | 全部「平均延迟 / 带宽利用率」 | `:63-66`、`:78-81`、`:95-98`、`:110-113` |
| `V/monitor/SecurityDashboard.vue` | 4 | 全部「今日事件 / 今日告警」 | `:60-63`、`:75-78`、`:92-95`、`:107-110` |
| `V/monitor/HvacDashboard.vue`（正面参照） | 5 | 冷源：负载率/进出水温；CRAC：送回风温/湿度/风机转速；液冷：流量/CDU 进出水温 | `:51-66`、`:68-85`、`:87-109` |

**影响**：柴发、燃油、电池三类设备的核心风险（续航、SOC、SOH、油压）在入口层完全不可见，与详情页已有指标（`V/monitor/PowerFuel.vue:412-442` 续航阈值、`PowerBattery.vue:66-131` SOC/SOH/后备时间）严重脱节。
**建议**：按 [03_METRICS_IA.md](./03_METRICS_IA.md) 的「每类设备 3 个判别性指标」重排入口卡，字段均取现有接口，不新增契约。

### A-2 单位与阈值散落（P1）

- 单位写法混用：`℃` / `°C`、`L/min` / `m³/h`、`bar` / `MPa`、`cps`、`dBm`、`μS/cm`（详见 `V/monitor/HvacLiquid.vue:38-263`、`V/monitor/HvacCrac.vue:56-79`）。
- 阈值硬编码在模板三元表达式：`V/monitor/NetworkSwitches.vue:14,19,23,28,40,45,95`（CPU/内存 >80/>60、端口可用率 <95）、`V/monitor/PowerBattery.vue:51-131`（电压 <200、SOC <80、后备时间 <10/<15）、`V/monitor/PowerFuel.vue:74,412-442`（压力 >0.5、续航 <8/<12/<24）。
- **后果**：同一「warning」语义在不同页用不同数值与不同颜色字面量，无法统一阈值线、无法做全局告警一致性校验。
**建议**：抽 `metricsCatalog.ts`（名称/单位/阈值/严重度/格式化），模板只引用 key；图表阈值线由同一份配置生成。

### A-3 宽表与首屏密度（P1）

| 页 | 表头列数 | 证据 |
| --- | --- | --- |
| `V/monitor/PowerLv.vue` | 18 | `:351-368` |
| `V/monitor/PowerHv.vue` | 14 / 10 / 12 | `:253-266`、`:303-312`、`:516-527` |
| `V/monitor/PowerGenset.vue` | 11 | `:257-267` |
| `V/monitor/PowerFuel.vue` | 11 | `:573-583` |
| `V/monitor/NetworkSwitches.vue` | 10 | `:276-285` |
| `V/ops/Tickets.vue` | 11 | `:177-197` |
| `V/admin/AuditLogs.vue` | 9 | `:70-78` |
| `V/ops/DrillPlan.vue` | 9 | `:69-77` |

同屏还叠加大量 KPI：`V/monitor/HvacLiquid.vue:35,73,114` 三排 `.kpi-row` + `:231-260` + `:316-357` 共约 23 张卡；`V/monitor/HvacChiller.vue:50-108` 单排 8 张；`V/monitor/PowerLv.vue:192-240` 6 张 KPI 与 18 列表格同屏。
**建议**：列 >8 的表格启用「默认列集 + 列配置抽屉」（借鉴 [01 范式 C](./01_BENCHMARK.md)），KPI 按 P0/P1/P2 分层，P2 收进「更多指标」折叠区。

### A-4 数据来源与可信度标记（P1）

- 三层来源：`frontend/src/api/{power,hvac,monitor,security}.ts`（16 端点）→ `frontend/openapi.json`（29 个 DCIM 端点）→ `frontend/src/api/request.ts:125-139,164-169` 在 404/405/网络错误时全量回退 `mockData.ts`。
- 25 个页面用 `MockDataBanner` / `DataBadge` 标记示例数据（如 `V/monitor/PowerHv.vue:9`、`V/overview/Index.vue:62,138,257,276,368,373`、`V/energy/EnergyDashboard.vue:143`），但另 4 个网络页自带本地 `mockData()`（`V/monitor/NetworkSwitches.vue:386,576,738` 等），提示方式不统一。
- 契约端点 `/api/network/bandwidth`、`/api/network/ping`（`openapi.json:2295,2339`）前端 0 引用。
**建议**：统一为「页头 `DataBadge` + 区块级 `MockDataBanner`」两级；`request.ts` 的兜底**保留但必须显式标记**（项目约定「绝不静默降级」），不得改成静默返回空数据。

---

## 4. 维度 B · 信息层级

### B-1 标题层级混乱（P1）

同为页面主标题却 h1/h2 混用：`V/monitor/PowerDashboard.vue:4` 用 `<h1>`，`V/monitor/HvacChiller.vue:5`、`V/monitor/SecurityCctv.vue:5`、`V/overview/Index.vue:6` 用 `<h2 class="page-title">`。全局 `<h1` 57 处、`<h2` 33 处。`V/monitor/ThermalCloud.vue:4` 同页 `<h1>` 与 `:61,:84,:114` 三个 `<h2>`；`V/monitor/HvacChiller.vue:5 → :113` 从 `<h2>` 直接到 `<h3 class="section-title">`，整页无 `<h1>`。
**影响**：无障碍读屏与大纲导航失效；全局 `.view-head h1`（`S/index.scss:90`、`:268`）只作用于用 h1 的页面，用 h2 的页面标题未被样式覆盖。

### B-2 页头 / 栅格不统一（P1）

- 页头四页同构（`div.view-head > h1 + span.sub`），但 `S/index.scss:89-92` 与 `:265-272` 两套 `.view-head` 定义叠加，导致部分页是裸 flex 行、部分页是带背景的卡片。
- 栅格：`V/monitor/PowerDashboard.vue:49-51` 注释自称「统一 cols-2 与 Security/Network 对齐」，但 `V/monitor/HvacDashboard.vue:50` 用 `cols-3`，且另有 2 个单行 `grid`（`:112,:127`）。
- 两套栅格并存：裸 `.cols-2..6`（`S/index.scss:95-99`）与 `.grid.cols-2..6`（`:340-344`），各配一套断点（见 C-2）。

### B-3 关键异常无视觉权重（P0）

`V/monitor/PowerDashboard.vue:12-47`、`HvacDashboard.vue:12-47`、`SecurityDashboard.vue:12-47` 四张 KPI 同尺寸，故障/告警仅靠 `:34,:36,:43,:45` 的 `quality/severity` 着色；入口卡 `.kvs` 统一 `font-size:12.5px`、`.v` 仅 `font-weight:500`（`V/monitor/HvacDashboard.vue:197-210`）。`V/monitor/NetworkSwitches.vue:20,29,37,46` 四张 KPI 全部 `size="sm"`。
**建议**：按 03 文档四块结构，把「未处理告警 / 故障设备 / 越限指标」提到 P0 行并给予更大字号与状态条，统计类降到 P1。

---

## 5. 维度 C · 交互流程

### C-1 筛选 / 分页 / 遮罩（P1）

| 现象 | 证据 |
| --- | --- |
| `查询\|筛选\|搜索` 命中 21 文件，`重置` 仅 4 文件 | `V/admin/RowAudit.vue:70`、`V/admin/AuditLogs.vue:50`、`V/ops/Collector.vue:48`、`V/ops/RoomAccess.vue:212`（仅日志文本） |
| 无重置的筛选栏 | `V/ops/Equipment.vue:12-37`、`V/ops/Cabinets.vue:12-25`、`V/ops/Alarms.vue:305-328`、`V/monitor/SecurityCctv.vue:101-111` |
| 分页 4 种实现 | 组件 `<Pagination>`（`V/ops/AlarmHistory.vue:125,253`）；手写 `btn-sm`（`V/admin/RowAudit.vue:158,165`、`V/ops/Equipment.vue:179-184`）；自定义 `.kb-pager button`（`V/ops/KnowledgeCenter.vue:122-134`）；`btn-sm pg-btn`（`V/ops/Risk.vue:220,224`） |
| 每页条数 10/12/20/50 不一 | `V/ops/Risk.vue:526`=10、`V/ops/Telemetry.vue:118`=12、`V/ops/Cabinets.vue:170`=20、`V/admin/AuditLogs.vue:170`=50 |
| 遮罩 ≥5 种类名 | `.mask` `V/ops/WorkflowCenter.vue:222`；`.modal-mask` `V/ops/DrillPlan.vue:175`；`.drawer-mask` `V/ops/DataCenterManage.vue:132`；`.tf-mask` `V/ops/Cabinets.vue:109`；`.ai-corrmask` `V/ops/Assistant.vue:202` |
| 按钮类名 6 套 | `btn-sm` 28 文件 / 196 次，`btn-primary` 10 文件 / 30 次，`btn-ghost` 9 文件 / 31 次，另有 `btn-refresh`（`V/monitor/HvacChiller.vue:23`）、`hv-edit`（`V/monitor/PowerHv.vue:33`）、`chip-clear`（`V/monitor/HvacCrac.vue:102`）、组合式 `btn-sm primary`（`V/ops/Equipment.vue:37`） |

### C-2 断点与响应式（P0）

全库 **70 处 `@media` / 36 文件**，18 种 max-width 值 + `@media print` ×2，**没有任何 min-width 断点**。全局自身 5 套：`S/index.scss:185`(1180)、`:191`(768) 作用于裸 `.cols-*`；`:350`(1200)、`:351`(900)、`:352`(720) 作用于 `.grid.cols-*`。其余 13 个非全局值共 **45 处**各自为政。

| 值 | 处数 | 代表位置 |
| --- | --- | --- |
| 1440 | 1 | `V/overview/Index.vue:1586` |
| 1280 | 5 | `V/monitor/PowerLv.vue:1796`、`PowerHv.vue:1858`、`PowerGenset.vue:1581`、`PowerFuel.vue:2582`、`V/ops/Risk.vue:1167` |
| 1200 | 4 | `V/overview/Index.vue:1594`、`V/monitor/HvacLiquid.vue:1060`、`HvacCrac.vue:942`、`S/index.scss:350` |
| 1180 | 2 | `V/monitor/NetworkSwitches.vue:994`、`S/index.scss:185` |
| 1100 | 12 | `V/monitor/SecurityIds.vue:1000`、`ThermalCloud.vue:488`、`V/ops/Tickets.vue:1136` 等 |
| 1000 | 3 | `V/monitor/HvacLiquid.vue:1112,1141,1221` |
| 980 | 3 | `V/ops/WorkflowCenter.vue:1509`、`RoomAccess.vue:643`、`V/monitor/PowerBattery.vue:1656` |
| 920 / 900 | 1 / 7 | `V/ops/UPosition.vue:350`；`S/index.scss:351`、`V/ops/CapacityWhatIf.vue:288` 等 |
| 860 | 6 | `V/monitor/PowerFuel.vue:2593`、`V/ops/HealthReport.vue:939` 等 |
| 768 | 4 | `S/index.scss:191`、`V/overview/Index.vue:1611` 等 |
| 760 | 2 | `ST/p3.css:152`、`V/ops/Risk.vue:1175`（与全局 768 差 8px 且互不感知） |
| 720 | 6 | `S/index.scss:352`、`V/ops/Tickets.vue:1151` 等 |
| 700 / 640 / 600 / 560 / 500 | 1 / 7 / 2 / 1 / 1 | `V/monitor/HvacLiquid.vue` 单文件即含 1200/1000/900/700/640/600/500 **七个**阈值 |

**移动端根因**（`L/DefaultLayout.vue` + `S/index.scss`）：
- 无侧栏抽屉/汉堡按钮，无 `isMobile`/`innerWidth`/`resize`/`matchMedia` 监听（`:6,:8,:42,:54-55,:307-371` 全 0 命中）；`:291-296` 的 `collapsed` 只是**分组展开**。
- `S/index.scss:71` `.body{display:grid;grid-template-columns:236px 1fr}`；`:46` `body{overflow:hidden}`；`:179,:182` 表格强制 `min-width:680px`；`:256` 唯一隐藏侧栏途径是 `body.kiosk .side`（需手工加 class，非响应式）；`:194` 唯一窄屏降级是隐藏 `.global-kpis`。
- `C/layout/TopBar.vue:1-171` 全文件无 `<style>` / 无 `@media`；`S/index.scss:52-56` 顶栏 flex 无 `flex-wrap`，`:65` `.clock{min-width:160px}`。
- **375px 后果**：侧栏仍占 236px，主区约 139px；680px 表格与多列栅格横向溢出，而 `body{overflow:hidden}` 禁止整页滚动 → 内容被直接裁切且无法触达。

### C-3 异步四态与错误态（P0）

统一组件接入（分母 77 文件）：`AsyncSection` 32、`ErrorBanner` 12、`ErrorRetry` 3、`EmptyStateCard` 2、`DataBadge` 5、`MockDataBanner` 21 —— 去重后仅 **55 文件**接入任一组件。而 `C/common/AsyncSection.vue:3-42` 已内置 loading→error→empty→success 四态与重试（`C/common/ErrorRetry.vue:26-30`）。

手写状态的 6 种互不一致 DOM：

| 型 | 结构 | 证据 |
| --- | --- | --- |
| A 卡片式 | `div.grid.cols-4 > SkeletonCard×6` + `Panel.err-card > err-title + err-detail + button.btn` | `V/monitor/PowerLv.vue:13-22`（同型复用于 PowerHv / PowerGenset / PowerFuel / Network* `:11-22`） |
| B 裸 span 式 | `div.flex.center > span.muted` / `span.muted.a-text` | `V/monitor/NetworkSwitches.vue:359-364`；`V/monitor/HvacDashboard.vue:143-152`（内联 `style="color: var(--red)"`） |
| C 状态点 + 组件混用（唯一合规） | `span.refresh-hint > i.dot` + `Panel.center-box` + `ErrorRetry` | `V/monitor/PowerBattery.vue:9-32` |
| D 行内告警带 | `div.inline-warn > AlertTriangle + span + button.link-btn` | `V/energy/EnergyDashboard.vue:33-37` |
| E 全局类混搭 | `div.loading-box` + `div.result.bad` | `V/ops/FaultImpact.vue:145,452`、`V/ops/DrillPlan.vue:348,352` |
| F 错误当空态 / 表格三元 | `SkeletonCard + EmptyState text="…加载失败"`；`{{ loading ? '加载中…' : '暂无数据' }}` | `V/monitor/HvacChiller.vue:925-926`；`V/admin/RowAudit.vue:120`、`V/ops/Cabinets.vue:134` |

其余手写页面（共 22+）：`V/monitor/HvacCrac.vue:11,86`、`V/monitor/Scene3D.vue:70,433`、`V/monitor/HvacLiquid.vue:11,538`、`V/monitor/HvacLinkage.vue:294`、`V/monitor/PowerLinkage.vue:1072`、`V/ops/Alarms.vue:520,762`、`V/ops/Collector.vue:14,226`、`V/ops/Equipment.vue:149,259`、`V/admin/AuditLogs.vue:121,197`、`V/ops/UPosition.vue:31,32`、`V/ops/KnowledgeCenter.vue:68`、`V/ops/PowerAiHazards.vue:70`、`V/ops/components/CollectorMetricsModal.vue:44`、`CollectorMetricDefsModal.vue:50`。

### C-4 可达性细节（P1）

- 4 个总览页可点击 `router-link.entry-card` 检索 `cursor` **0 命中**（`V/monitor/PowerDashboard.vue:216-233`、`HvacDashboard.vue:212-229`、`NetworkDashboard.vue:202-219`、`SecurityDashboard.vue:197-214` 只有 hover，无 `cursor:pointer`）；对比 `V/monitor/SecurityCctv.vue:534`、`:594` 有显式声明，`V/monitor/PowerBattery.vue:329` 用行内 `style="cursor: pointer"`。
- 筛选条件不写 URL，`刷新即丢失`；无保存视图、无列配置（见 [01 范式 C](./01_BENCHMARK.md)）。

---

## 6. 维度 D · 视觉一致性

### D-1 硬编码色值（P0）

71/77 文件含 hex/rgb 字面量，约 **1975 匹配行**，32 个文件 >20 处。高频文件：

| 文件（`:` 后为 `<style scoped>` 起始行） | 命中 | 代表证据 |
| --- | --- | --- |
| `V/monitor/PowerFuel.vue:1778` | 134 | `:1786` `var(--text-primary,#e5e7eb)`、`:1791` `var(--text-muted,#6b7280)` |
| `V/monitor/PowerLv.vue:1338` | 99 | `:1346,:1351` 同上 |
| `V/monitor/PowerGenset.vue:1066` | 99 | `:1074,:1079` 同上 |
| `V/overview/Index.vue:1055` | 89 | `:1060` `color:#c8d6e5` |
| `V/monitor/PowerHv.vue:1369` | 82 | `:1377,:1382` 同上 |
| `V/monitor/PowerLinkage.vue:1085` | 73 | `:1099` `#e2e8f0`、`:1102` `#64748b` |
| `V/monitor/PowerBattery.vue:1159` | 73 | `:1342` `#fff`、`:1355` `rgba(34,227,255,.06)`（另有 `:721-1016` ECharts JS 色值） |
| `V/energy/EnergyDashboard.vue:677` | 72 | `:697`、`:702`、`:721` `#22e3ff` |
| `V/ops/TenantManage.vue:541` | 69 | `:557` `#94a3b8` |
| `V/ops/components/AlarmListPanel.vue:316` | 60 | `:336` `#22e3ff`、`:345` `#2bd47a` |
| `V/monitor/SecurityFire.vue:705` | 61 | `:739-744` |
| `V/monitor/SecurityAcs.vue:556` | 46 | `:578` `var(--text-2)`、`:586` `var(--border)` |
| `V/monitor/NetworkFirewalls.vue:636` | 45 | `:644,:649` 未定义变量 fallback |
| `V/monitor/HvacChiller.vue:1588` | 45 | `:1592` `var(--bg2,#0f172a)` |
| `V/monitor/NetworkWireless.vue:592` | 43 | `:598,:603` |
| `V/monitor/SecurityIds.vue:584` | 42 | `:604,:618-619` |
| `V/monitor/NetworkRouters.vue:924` | 37 | `:932,:937` |
| `V/monitor/ThermalCloud.vue:291` | 36 | `:303,:310,:312` |
| `V/ops/NotificationCenter.vue:464` | 36 | `:479,:484` |
| `V/ops/InspectionTemplate.vue:286` | 34 | `:298,:301,:312` |
| `V/ops/CiRelations.vue:320` | 33 | `:323,:333,:343` |
| `V/ops/Tickets.vue:748` | 32 | `:754-755` |
| `V/monitor/SecurityCctv.vue:497` | 31 | `:517,:530,:539` |
| `V/ops/WorkflowCenter.vue:907` | 30 | `:923,:933,:964` |
| `V/ops/CapacityWhatIf.vue:281` | 30 | `:336` |
| `V/monitor/BigScreen.vue:173` | 28 | `:176-183` 自建 `.light` 类 |
| `V/monitor/HvacLinkage.vue:303` | 27 | `:315,:318,:322` |
| `V/ops/UPosition.vue:335` | 49 | `:336,:341,:345` |
| `V/monitor/Scene3D.vue:488` | 24 | `:494,:510,:512` |
| `V/ops/Assistant.vue:451` | 24 | `:544,:562,:583` |
| `V/auth/Login.vue:161` | 21 | `:167,:172,:182` |

**主题不跟随的三类**：
1. 纯字面量（`#e5e7eb`、`#1e293b`、`#060b16`、`#f59e0b` 等）——dark→light 恒定。
2. `var(--未定义, #fallback)` —— fallback 永久生效，例如 `V/monitor/NetworkFirewalls.vue:644,:649`、`V/monitor/HvacChiller.vue:1592-1593`、`V/energy/EnergyDashboard.vue:702-705`，以及**全局自身** `S/index.scss:108,:111`。
3. JS 图表 option 里的 hex/rgba（`V/monitor/PowerBattery.vue:721,769-771,822,875,944,1008`）——主题切换完全不影响；`V/monitor/BigScreen.vue:180-183` 甚至自建 `.bigscreen.light` 用 JS class 做主题分支。

**全局样式自身也没完全 token 化**：`S/index.scss:58`（logo 渐变）、`:134` `#3a4a66`、`:142-143` 徽章配色、`:214` `#bff`、`:260` `#0a1220`、`:287` `#fff`、`:331` `rgba(0,0,0,.5)` 在亮色主题下仍是暗色值。

### D-2 未定义变量（P0）

定义侧 0 处：`--bg-card` / `--border` / `--text-primary` / `--text-2` / `--text-muted` / `--border-light` / `--bg-1` / `--text-1` / `--brand` / `--strong` 全库搜索无定义。

| 规则 | 后果 |
| --- | --- |
| `S/index.scss:108`、`:111` | `.moni-card` 背景/边框/文字恒为暗色 fallback，亮色主题下深色卡片 |
| `S/index.scss:115` | `var(--text-2)` **无 fallback** → `var()` 失效，`.card-sub` 无颜色 |
| `V/monitor/SecurityAcs.vue:576,586,588,594` | `--text-2/--border/--bg-1/--text-1/--brand` 全部失效 |
| `V/monitor/SecurityIds.vue:604,627`、`SecurityFire.vue:725,748,963`、`SecurityCctv.vue:517,530,545` | 文字色与虚线边框失效 |
| `V/ops/Risk.vue:767,880`、`Maintenance.vue:496,569,599`、`Inspection.vue:546,616,661`、`Duty.vue:580,584,664` | `--border`/`--border-light` 失效 |
| `C/monitor/PortPanel.vue:143,254`、`C/SecurityKnowledge.vue:113,117,130,142,150` | 组件内同样失效 |
| `V/ops/WorkflowCenter.vue:923,933,935` | 混用已定义别名 `--muted/--panel-2/--text` 与误用的 `--text-muted` |

`S/index.scss:16-19` 与 `:38` 已把 `--text/--muted/--panel-2` 映射为正式 token（注释自述「按钮看不到字」的历史问题），但其余 10 个别名未收口。引用侧约 16 文件 130 处。

### D-3 同名类重复定义（P0）

`S/index.scss` 存在两套「业务页组件库」叠加，**15 组**同名选择器被定义两次：

| 选择器 | 前 → 后 | 冲突 |
| --- | --- | --- |
| `.view-head` | `:89 → :265` | 裸 flex 行 → 带背景/圆角的卡片，所有页头被迫变卡片 |
| `.view-head h1` | `:90 → :268` | 18px/700 → 19px/800 + `--txt-strong` |
| `.view-head .sub` | `:91 → :269` | 新增 `margin-top:3px` 与 `:89` 的 gap 叠加 |
| `.card-head` | `:113 → :282` | `margin-bottom` 10→12px、gap 0→10px |
| `.card-title` | `:114 → :283` | 600/14px 无颜色 → 700 + `--txt-strong` |
| `.section-title` | `:126 → :284` | cyan / `margin:18px 0 10px` → `--txt` / `4px 0 8px` |
| `.section-title::before` | `:127 → :285` | 4×14 纯 cyan → 3×13 渐变条 |
| `.btn-sm` | `:257 → :296` | 11px/5px 12px/7px 圆角且自带边框背景 → 12px/5px 10px/6px 且**丢失 border/background** |
| `.grid` | `:94 → :339` | 两次重复声明 |
| `.pill` / `.pill.g` / `.pill.a` / `.pill.b` | `:117-123 → :313-318` | 内边距/圆角/边框、绿色与琥珀色 rgba 全被覆盖 |
| `@keyframes blink` | `:135 → :231` | 同名动画重复 |
| `select option` | `:301 → :304` | 同一规则写两遍（`:302-303` 注释说明） |

另有语义重复但选择器不同名：裸 `.cols-2..6`（`:95-99`）vs `.grid.cols-2..6`（`:340-344`）、`.twin`（`:183`）vs `.grid.twin`（`:348`）、`.scroll-x`（`:178-179`）vs `.table-wrap`（`:181-182`）。

### D-4 组件体系重复（P1）

| 重复对 | API 差异证据 |
| --- | --- |
| 3 套 KPI | `C/common/MetricCard.vue:92-108`（`metricName/value/unit/quality/online/sparkData/severity/stale`，emits `select` `:122`）vs `P/KpiCard.vue:4-32` 与 `C/monitor/KpiCard.vue:35-63`（props 完全同名，仅类名前缀 `dui-kpi-*` / `kpi-*` 不同；默认条色 `var(--cyan,#06b6d4)` vs `var(--cyan)`） |
| 2 套 TrendChart | `C/charts/TrendChart.vue:90-109`（`metrics/active/series/unitMap`，emits `select/rangeChange`，自带时间范围 + BaseChart）vs `C/monitor/TrendChart.vue:67-105`（`title/option/xAxisData/series/height`，emits `rangeChange/pointClick`）；同名 `series` 类型不同：`Record<string,MetricHistoryPoint[]>` vs `unknown[]` |
| 2 套 Badge | `C/monitor/AlarmBadge.vue:10-18` vs `P/AlarmBadge.vue:4-12`（props 相同，仅 class 前缀）；`C/monitor/StatusBadge.vue:11-19` vs `P/StatusBadge.vue:4-12`（`P/StatusBadge.vue:31` 有 `'dui-'+'dui-o'` 双前缀瑕疵） |
| 2 套 Empty / Loading | `C/common/EmptyStateCard.vue:31-36`（`title/desc/icon/minHeight` + `actions` slot）vs `C/monitor/EmptyState.vue:9-18`（`text/icon`，默认图标 `📊` **为 emoji**，违反「不用 emoji 作图标」）；`C/common/LoadingState.vue:21-30` 三形态 vs `C/monitor/SkeletonCard.vue:14` 仅 `size` |

`C/domain/` 为**空目录**；`C/monitor/index.ts` 把 `KpiCard`/`StatusBadge`/`AlarmBadge` 从 `@dc-ioc/ui` 重导出，与同目录同名文件并存，import 来源不同会得到不同样式。

---

## 7. 逐页问题清单

**问题代码字典**（建议映射见第 8 节）：

| 代码 | 含义 | 代码 | 含义 |
| --- | --- | --- | --- |
| `C1` | 硬编码色值 / 主题不跟随 | `L1` | 标题层级 h1/h2 混用 |
| `C2` | 引用未定义 CSS 变量 | `L2` | KPI 平铺、无主次 |
| `C3` | 同名类 / 重复组件 | `L3` | 入口卡指标同质化 |
| `C4` | 断点散乱 | `L4` | 宽表 >8 列 |
| `C5` | 无移动端布局降级 | `L5` | 栅格 cols-* 不统一 |
| `C6` | 图表配色 / 实现不统一 | `I1` | 筛选缺重置/保存视图/深链接 |
| `D1` | 单位与阈值散落 | `I2` | 分页实现/每页条数不一 |
| `D2` | 示例数据可信度标记分散 | `I3` | 遮罩/弹窗类名不一 |
| `D3` | 契约端点未接线 | `I4` | cursor / focus / 过渡缺失 |
| `D4` | 总览 KPI 前端聚合 | `I5` | 异步四态手写 |
| `D5` | 错误态当空态 / 文案不一 | `I6` | 错误态 DOM 结构不一 |

> `C1/C4/C5` 为全量扫描得到的目录级结论，下表每页给出的是**该页可定位的锚点行**，不代表该行就是唯一问题位置。优先级：`P0` 影响可用性/双主题/移动端，`P1` 影响一致性，`P2` 增强项。

### monitor/（27 页，全部受 `C1/C4/C5` 影响）

| 文件:行 | 形态 | 本页关键问题 | 优先级 |
| --- | --- | --- | --- |
| `V/monitor/PowerDashboard.vue:4` | KPI + 6 入口卡 | `L3` 五卡同指标 `:60-119`、`L5` `:49-51`、`I4` `:216-233`、`C3` | **P0** |
| `V/monitor/HvacDashboard.vue:4` | KPI + 5 入口卡 | `I5/I6` 手写错误态 `:143-152`、`L5` `:50`、`:112,:127`、`I4`；差异化指标为**正面参照** | P1 |
| `V/monitor/NetworkDashboard.vue:4` | KPI + 4 入口卡 | `L3` 四卡同指标 `:63-113`、`I4` `:202-219`、`C3` | **P0** |
| `V/monitor/SecurityDashboard.vue:4` | KPI + 4 入口卡 | `L3` 四卡同指标 `:60-110`、`C2` `:202`、`I4` `:197-214` | **P0** |
| `V/monitor/PowerHv.vue:5` | SVG 一次图 + 14 列表 | `C1` `:1377-1382`、`L4` `:253-266`、`I5` `:13-19`、`D2` `:9`、`I4` 自定义 `hv-edit` `:33` | **P0** |
| `V/monitor/PowerLv.vue:5` | SVG + 18 列表 | `L4` `:351-368`（18 列）、`L2` `:192-240`、`I5` `:13-22`、`C1` `:1346` | **P0** |
| `V/monitor/PowerGenset.vue:5` | 并机图 + 11 列表 | `L4` `:257-267`、`D1` `:54-75` 阈值、`I5` `:13-19`、`C1` `:1074` | P1 |
| `V/monitor/PowerFuel.vue:5` | 储油图 + 多表 | `D1` `:412-442` 续航阈值、`L4` `:573-583`、`C1` **134 行** `:1786-1791`、`C4` `:2582,:2593` | **P0** |
| `V/monitor/PowerBattery.vue:4` | 电池组图 + ECharts | `C6` JS 色值 `:721-1008`、`D1` `:51-131`、唯一合规异步态 `:9-32`、`:329` 行内 cursor | **P0** |
| `V/monitor/PowerLinkage.vue:5` | SVG 链路 | `C1` `:1099-1102`、`I5` `:1072`、`C4` `:1457,:1465` | P1 |
| `V/monitor/HvacChiller.vue:5` | 8 KPI + SVG + ECharts | `L1` `:5 → :113` 整页无 h1、`L2` `:50-108`、`D5` `:925-926`、`C1/C2` `:1592-1593` | **P0** |
| `V/monitor/HvacCrac.vue:6` | 机房看板 + ECharts | `L2` `:27,54,176-225`、`I5` `:11,86`、`I1` `:102` `chip-clear`、`C4` 7 处阈值 | P1 |
| `V/monitor/HvacLiquid.vue:6` | 23 KPI + 水质表 | `L2` `:35,73,114,231-260,316-357`、`C4` **单页 7 个断点** `:1060-1221`、`D1` 单位混用 `:38-263` | **P0** |
| `V/monitor/HvacLinkage.vue:4` | SVG 制冷链路 | `I5` `:294`、`C1` `:315-322` | P1 |
| `V/monitor/ThermalCloud.vue:4` | 三层温度热力图 | `C1` `:303-312`、`C4` `:488,:502,:528`、`D2` `DataBadge:52`（范式 B 起点） | P1 |
| `V/monitor/NetworkSwitches.vue:4` | Spine-Leaf 图 + 10 列表 | `L4` `:276-285`、`D1` `:14-45,95` 阈值硬编码、`I5` `:360-364`、`D3` 本地 `mockData()` `:386,576,738` | **P0** |
| `V/monitor/NetworkRouters.vue:5` | SVG + ECharts | `I5` `:11-17,:282`、`C1` `:932-937`、`D3` `:406,884,899` | P1 |
| `V/monitor/NetworkFirewalls.vue:5` | ECharts + 表格 | `C1/C2` `:644-649`、`I5` `:11-17,:225`、`D3` `:392,559,621` | P1 |
| `V/monitor/NetworkWireless.vue:5` | 热力图 + ECharts | `C1` `:598-603`、`I5` `:11-17,:164`、`D3` `:339,511,545,577` | P1 |
| `V/monitor/SecurityCctv.vue:5` | 分屏预览 + 筛选 | `L1` `:5` 用 h2、`C2` `:517,530,545`、`I1` `:101-111` 无重置、`I4` `:534,:594` 显式 cursor（正例） | P1 |
| `V/monitor/SecurityAcs.vue:5` | 门禁平面图 | `C2` **5 个别名全失效** `:576-594`、`C1` `:599`、`C4` `:947` | **P0** |
| `V/monitor/SecurityIds.vue:5` | 周界示意 + 事件表 | `C2` `:604,:627`、`C1` `:618-619`、`C4` `:1000` | P1 |
| `V/monitor/SecurityFire.vue:5` | 消防平面图 | `C2` `:725,:748,:963`、`C1` 61 行 `:739-744`、`C4` `:1259` | P1 |
| `V/monitor/HealthDashboard.vue:4` | KPI + 健康度表 | `I5` `:47` 裸「加载中...」、`C1` 3 行 `:160` | P1 |
| `V/monitor/BigScreen.vue:12` | 大屏 | `C1/C3` 自建 `.bigscreen.light` `:180-183` 绕开 token、`D2` `:12` | **P0** |
| `V/monitor/BigScreenDesigner.vue:4` | 表单 + 预览 | `C1` 18 行 `:113`、`I3` 预览与大屏样式不一致 | P2 |
| `V/monitor/Scene3D.vue:3` | 3D 孪生 | `C1` `:494-512`、`I5` `:70,:433` 错误只写 script 变量、`D2` `:3` | P1 |

### overview / energy / auth / admin（5 页）

| 文件:行 | 形态 | 本页关键问题 | 优先级 |
| --- | --- | --- | --- |
| `V/overview/Index.vue:6` | 驾驶舱六区块 | `L1` 用 h2、`C1` 89 行 `:1060`、`C4` `:1586,:1594,:1611`、`D2` 6 处 `DataBadge`、`C3` `:6` `ph-refresh` | **P0** |
| `V/energy/EnergyDashboard.vue:5` | KPI + ECharts + 表 | `C1/C2` `:697-705`、`I6` 行内告警带 `:33-37`、`D2` `:143,:272`、`C4` `:1081,:1093` | P1 |
| `V/auth/Login.vue:5` | 登录表单 | `C1` `:167-182` 全硬编码渐变、`C5` 无窄屏表单规范 | P1 |
| `V/admin/AuditLogs.vue:4` | 9 列审计表 | `L4` `:70-78`、`I2` `:131,138` 手写分页 + `page_size=50` `:170`、`I5` `:121,197`、`I1` 有重置（**正例**） | P1 |
| `V/admin/RowAudit.vue:4` | 行级审计表 | `I2` `:158,165`、`I5` `:120,246`、`I1` 有重置（**正例**） | P1 |

### ops/（39 页，全部受 `C1/C4/C5` 影响；`I1/I2/I3` 按证据标注）

| 文件:行 | 形态 | 本页关键问题 | 优先级 |
| --- | --- | --- | --- |
| `V/ops/Equipment.vue:4` | 设备台账表 | `I1` `:12-37` 无重置、`I2` `:179-184`、`I5` `:149,259`、组合按钮 `:37` | P1 |
| `V/ops/Cabinets.vue:4` | 机柜表 + 抽屉 | `I1` `:12-25`、`I3` `tf-mask:109`、`I5` `:134,200`、`I2` `:98,102`、B-01 面包屑目标 | P1 |
| `V/ops/UPosition.vue:5` | U 位可视化 | `C4` `:350`(920)、`C1` `:336-345`、`I5` `:31,32`、B-01 目标 | P1 |
| `V/ops/Alarms.vue:5` | 告警看板 + 大表 | `I1` `:305-328`、`I3` `modal-mask:500,529`、`I5` `:520,762-763`、`C1` 47 行 `:1275-1282`、B-08 | **P0** |
| `V/ops/Tickets.vue:5` | 11 列工单表 | `L4` `:177-197`、`I3` `tf-mask:288,383`、`I2` `:1151`、空态内才给清除 `:270` | P1 |
| `V/ops/AlarmHistory.vue:5` | 告警表 + 触达表 | `I2` 组件化 `<Pagination>:125,253`（**正例**）、`D2` `:2` | P2 |
| `V/ops/AlarmRules.vue:20` | 8 列规则表 + 弹窗 | `C1` 6 行 `:295`、`I3` 表单弹窗遮罩 | P2 |
| `V/ops/AssetBusiness.vue:4` | 资产业务表 | 无 scoped style（**正例**），`C5` 表格窄屏 | P2 |
| `V/ops/AssetLifecycle.vue:18` | KPI + 表 + 弹窗 | `I3` `modal-mask:134` | P2 |
| `V/ops/Assistant.vue:5` | AI 对话看板 | `C1` `:544,:562,:583` 状态色硬编码、`I3` `ai-corrmask:202` | P1 |
| `V/ops/CapacityWhatIf.vue:19` | What-If 表单 + ECharts | `D2` `:30`、`C4` `:288`、B-03 目标 | P1 |
| `V/ops/CiRelations.vue:4` | CI 关系表 + SVG 影响图 | `L1` `:4` h1 + `:13,38,80,105` 多 h2、`C1` 33 行 `:323-343`、B-08 影响分析参照 | P1 |
| `V/ops/Collector.vue:4` | 采集器表 + 弹窗 | `I1` 有重置 `:48`（**正例**）、`I3` `:113`、`I5` `:14,226`、`C1` 10 行 `:435` | P2 |
| `V/ops/CustomFields.vue:4` | 表单 + 预览表 | `L1` `:4` h1 + `:11,39,49` h2 | P2 |
| `V/ops/DataCenterCompare.vue:4` | 多园区对比 | `C1` 17 行 `:428`、`C4` `:675` | P2 |
| `V/ops/DataCenterManage.vue:4` | 园区表 + 抽屉 | `I3` `drawer-mask:132,202,233`、`btn-sm` 17 次 `:17`、B-01 层级起点 | P1 |
| `V/ops/Discovery.vue:4` | 发现候选 + 待办 | 无 scoped style（**正例**）、`C5` 表格窄屏 | P2 |
| `V/ops/DrillPlan.vue:18` | KPI + 9 列表 | `L4` `:69-77`、`I3` `:175,272,339`、`I6` `:348,352` | P1 |
| `V/ops/Duty.vue:4` | 排班表/看板 | `C2` `:580,584,664`、`C1` 5 行 `:565` | P1 |
| `V/ops/DutyCalendar.vue:4` | 排班日历 | `C1` 19 行 `:208`、`C4` `:635` | P2 |
| `V/ops/FaultImpact.vue:20` | 影响图 + 报告 | `I6` `:145,452`、B-08 影响分析参照 | P1 |
| `V/ops/HealthReport.vue:5` | 健康度报告 + ECharts | `D2` `:19`、`C4` `:939` + `@media print` `:945` | P2 |
| `V/ops/Inspection.vue:4` | 巡检表 + 看板 | `C2` `:546,616,661`、`C1` 11 行 `:527` | P1 |
| `V/ops/InspectionTemplate.vue:4` | 模板表单 + 表 | `C1` 34 行 `:298-312` | P1 |
| `V/ops/IntegrationHub.vue:24` | 集成表 + 看板 | `C1` 8 行 `:491`、`C4` `:797` | P2 |
| `V/ops/Ipam.vue:4` | VLAN/子网/地址多表 | 无 scoped style（**正例**）、`L4` 多表并列、`C5` | P1 |
| `V/ops/KnowledgeCenter.vue:4` | 知识看板 + 表 | `I2` 自定义 `.kb-pager` `:122-134` + CSS `:846-855`、`C1` 27 行 `:579` | P1 |
| `V/ops/KnowledgeCollaboration.vue:5` | 协作 KPI + 表 | `C1` 13 行 `:468` | P2 |
| `V/ops/Maintenance.vue:4` | 维护表 + 日历 | `C2` `:496,569,599`、`C1` 10 行 `:477` | P1 |
| `V/ops/MaintenanceCalendar.vue:18` | 维护日历 | `C1` 11 行 `:360`、`C4` `:635` | P2 |
| `V/ops/NotificationCenter.vue:4` | 渠道/记录表 | `I2` `<Pagination>:165`（**正例**）、`C1` 36 行 `:479-484` | P2 |
| `V/ops/PowerAiHazards.vue:21` | 隐患表 | `D2` `:3`、`I5` `:70` | P2 |
| `V/ops/Risk.vue:5` | 风险表 + 表单 | `C2` `:767,880`、`I2` `pg-btn:220,224` + `size=10:526`、`C4` `:1167,:1175` | P1 |
| `V/ops/RoomAccess.vue:9` | KPI + 出入表 | `C1` 16 行 `:376`、`C4` `:643`、`I1` `:212` 仅日志文本 | P1 |
| `V/ops/Supplier.vue:21` | 供应商表 | `D2` `:3` | P2 |
| `V/ops/Telemetry.vue:4` | 遥测表 | `I2` `:70,72` + `size=12:118`、`C1` 3 行 `:282` | P2 |
| `V/ops/TenantManage.vue:180` | 租户表 + 22 控件表单 | `C1` 69 行 `:557`、表单密度 `L2` | P1 |
| `V/ops/ThingModelEditor.vue:5` | 物模型编辑器 | `C1` 5 行 `:395` | P2 |
| `V/ops/WorkflowCenter.vue:5` | KPI + 流程看板 | `I3` `.mask:222`、`C1` 30 行 `:923-964`、`C2` 别名混用 `:923,933,935`、`C4` `:1509` | P1 |

### ops/components/（6 个子组件）

| 文件:行 | 形态 | 本页关键问题 | 优先级 |
| --- | --- | --- | --- |
| `V/ops/components/AlarmListPanel.vue:1` | 告警列表（10 `<th`） | `C1` 60 行 `:336-345`、`L4` | P1 |
| `V/ops/components/AlarmRulePanel.vue:1` | 规则表单面板 | 0 硬编码（**正例**） | P2 |
| `V/ops/components/CollectorDeviceForm.vue:1` | 采集设备表单 | `I3` `modal-mask:3`、约 70 处表单控件 `L2` | P1 |
| `V/ops/components/CollectorDeviceTable.vue:1` | 采集设备表（12 `<th`） | `L4` `:23` `<th min-width>` | P1 |
| `V/ops/components/CollectorMetricDefsModal.vue:1` | 测点定义表 + 表单 | `I3` `modal-mask:3` / `drawer-mask:60` **同页两种遮罩**、`I5` `:50` | P1 |
| `V/ops/components/CollectorMetricsModal.vue:1` | 测点查看表 | `I3` `:3`、`I5` `:44`、`C1` 2 行 `:88` | P1 |

---

## 8. 问题 → 建议 → 规范映射

| 代码 | 建议（本轮只写规范，不实施） | 规范文档 | 阶段 |
| --- | --- | --- | --- |
| `C1`/`C2`/`C3` | token 单一来源；清理未定义变量与兼容别名；合并同名类；组件按唯一实现收敛 | [04](./04_VISUAL_SPEC.md) §2–§5 | 1 |
| `C4`/`C5` | 断点收敛 375/768/1024/1440；新增侧栏抽屉与四档降级规则 | [05](./05_RESPONSIVE_SPEC.md) §2–§4 | 1 定规范 / 4 实施 |
| `C6` | 阈值标注、图例、双主题图表配色、`BaseChart` 唯一实现边界 | [04](./04_VISUAL_SPEC.md) §7 | 1 定规范 / 2 落地 |
| `L1`/`L5` | 统一 `h1` 页标题与四块式页头；栅格只用 `.grid.cols-*` | [04](./04_VISUAL_SPEC.md) §4、§6 | 1 / 2 |
| `L2`/`L3`/`L4` | P0/P1/P2 指标分层；每类设备 3 个判别性指标；列 >8 用列配置 | [03](./03_METRICS_IA.md) §3–§5 | 2 / 3 |
| `I1`/`I2`/`I3` | 筛选栏 / 分页 / 遮罩统一契约；筛选写 URL；保存视图落 `localStorage` | [04](./04_VISUAL_SPEC.md) §6、[01](./01_BENCHMARK.md) 范式 C | 1 定规范 / 3 推广 |
| `I4` | `cursor:pointer`、可见 focus、150–300ms 过渡、`prefers-reduced-motion` | [04](./04_VISUAL_SPEC.md) §8 | 1 / 2 |
| `I5`/`I6` | 异步四态统一由 `AsyncSection` 托管，错误与空态严格区分 | [04](./04_VISUAL_SPEC.md) §6 | 1 / 3 |
| `D1` | `metricsCatalog.ts` 统一单位与阈值 | [03](./03_METRICS_IA.md) §2 | 2 |
| `D2`/`D5` | 两级可信度标记；统一加载/错误/空文案（含 i18n 双语键） | [03](./03_METRICS_IA.md) §6、[04](./04_VISUAL_SPEC.md) §6 | 2 / 3 |
| `D3`/`D4` | 未接线端点评估（先不改契约）；总览聚合逻辑保持前端但显式标注 | [03](./03_METRICS_IA.md) §2、§6 | 3 |

## 9. 后续代码轮的验收口径（本轮不执行）

| 检查 | 期望 |
| --- | --- |
| `search_content` 统计 `V/**/*.vue` 中 hex/rgb 字面量 | 从约 1975 行降到 0（允许 `S/index.scss` 与图表配置常量集中定义） |
| 全库 `var(--` 未定义变量检索 | 0 处 |
| 全库 `@media` 阈值集合 | 仅 `375/768/1024/1440` + `@media print` |
| 375px 视口 | 无横向滚动，侧栏可开合，表格在 `.scroll-x` 内可横向滚动，主区可用宽度 ≥ 343px |
| 双主题 | 逐页切换 `data-theme`，文字对比 ≥ 4.5:1，无恒定暗色块 |
| `AsyncSection` 接入 | 77 页全覆盖；错误态与空态不混用 |
| 门禁 | `check_nav_routes.py --strict`（71 路由 / 0 死链 / 0 孤儿）、`check_api_contract.py`（200 paths / 271 ops）、`check_i18n_keys.py`（zh/en 各 3072 键且对齐）、`vue-tsc`、`vitest`、`pytest --cov-fail-under=15`、Playwright 10 条 E2E 全通过 |

---

**阅读下一步**：[03_METRICS_IA.md](./03_METRICS_IA.md)（改什么内容与层级）→ [04_VISUAL_SPEC.md](./04_VISUAL_SPEC.md)（改成什么样）。
