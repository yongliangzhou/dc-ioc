# 01 · GitHub 同类项目对标与可借鉴的信息架构范式

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **核实日期** 2026-11-10
> **本轮只交付文档，不修改任何运行文件。** 本文所有代码改造建议均作为后续代码轮的输入。

## 1. 核实方法与可信度约定

| 项 | 说明 |
| --- | --- |
| 数据源 | GitHub REST API `GET /repos/{owner}/{repo}`（只读）、各项目官方文档页、openDCIM 官方功能页 |
| 核实时间 | 2026-11-10（`stargazers_count` 为当时快照，会变化，不作为质量结论依据） |
| 未做的事 | **未打开产品截图、未登录试用、未逐行阅读竞品前端源码**。界面结论只来自官方功能说明与文档，属于「可借鉴范式」而非像素级对标 |
| 不确定项 | 标注「待核实」；仓库 License 字段为 `null` / `NOASSERTION` 时如实标注，不推断 |
| 仓库重定向 | `snipe/snipe-it` 的 API 返回 `full_name = grokability/snipe-it`，本文以返回值为准 |

## 2. 项目清单（按 DCIM / CMDB / ITAM 分类）

### 2.1 DCIM · 机房与物理基础设施

| 仓库 | 主语言 / License | ★（快照） | 最近 push | 官方定位 | 与本项目关系 |
| --- | --- | --- | --- | --- | --- |
| [`netbox-community/netbox`](https://github.com/netbox-community/netbox) | Python / Apache-2.0 | 21,867 | 2026-11-10 | "The premier source of truth powering network automation"；topics 含 `dcim` `ipam` `cabling` | **首要对标**：物理层级与「单一事实源」信息架构 |
| [`opendcim/openDCIM`](https://github.com/opendcim/openDCIM) | PHP / 自述 GPL v3（API `license: null`） | 371 | 2026-10-28 | "An open source (GPL v3) Data Center Inventory Management (DCIM) application" | **容量视图**对标 |
| [`allegro/ralph`](https://github.com/allegro/ralph) | Python / Apache-2.0 | 2,532 | 2026-11-06 | "CMDB / Asset Management system for data center and back office hardware"；默认分支 `ng` | 资产全生命周期 + 机架可视化 |
| [`RackTables/racktables`](https://github.com/RackTables/racktables) | PHP / GPL-2.0 | 813 | 2026-06-26 | "RackTables current development repository"；topics `dcim` `ipam` | 机架 / IP / 线缆台账 |
| [`gituib/idc_assest`](https://github.com/gituib/idc_assest) | JavaScript / NOASSERTION | 84 | 2026-11-06 | 「现代化 IDC 设备管理系统，机房/机柜/设备全生命周期管理，具备 3D 可视化」 | 用户最初给出的参考项目；与本项目 3D 孪生定位最接近 |
| [`AlertBoy/django-idcops`](https://github.com/AlertBoy/django-idcops) | CSS（GitHub 主语言判定）/ Apache-2.0 | 7 | 2018-12-26 | "A data center inventory management software" | 用户最初给出的参考项目；**已停更多年**，仅作历史信息架构参考，不宜作技术选型依据 |

### 2.2 CMDB · 模型与关系

| 仓库 | 主语言 / License | ★（快照） | 最近 push | 官方定位 | 与本项目关系 |
| --- | --- | --- | --- | --- | --- |
| [`TencentBlueKing/bk-cmdb`](https://github.com/TencentBlueKing/bk-cmdb) | Go / NOASSERTION | 5,764 | 2026-10-22 | 「蓝鲸智云配置平台」；topics `cmdb` `microservice` | 动态模型 / 业务拓扑，对照本项目 `ops/CiRelations.vue` |
| [`veops/cmdb`](https://github.com/veops/cmdb) | Python / AGPL-3.0 | 2,277 | 2026-10-25 | "CMDB: configuration and management of IT resources"；topics 含 `dcim` `ipam` `antd-vue` | 前端同为 Vue 系，UI 组织方式可参考 |
| [`Combodo/iTop`](https://github.com/Combodo/iTop) | PHP / AGPL-3.0 | 1,215 | 2026-11-09 | "A simple, web based CMDB & IT Service Management tool"；topics 含 `impact-analysis` `itil` | **影响分析**范式，对照 `ops/FaultImpact.vue` |

### 2.3 ITAM / ITSM · 资产与工单

| 仓库 | 主语言 / License | ★（快照） | 最近 push | 官方定位 | 与本项目关系 |
| --- | --- | --- | --- | --- | --- |
| [`grokability/snipe-it`](https://github.com/grokability/snipe-it) | PHP / AGPL-3.0 | 15,167 | 2026-11-09 | "A free open source IT asset/license management system" | 表格筛选、许可证/维保到期、导出 |
| [`glpi-project/glpi`](https://github.com/glpi-project/glpi) | PHP / GPL-3.0 | 6,575 | 2026-11-09 | "Free Asset and IT Management Software… Data center management, ITIL Service Desk, licenses tracking" | 资产 + 服务台 + 仪表盘卡片密度 |

## 3. 五个可借鉴的界面 / 信息架构范式

以下每条都给出「竞品做法 → 本平台现状 → 可落地动作」，动作对应 [02_DIAGNOSIS.md](./02_DIAGNOSIS.md) 的问题编号与 [06_ROADMAP.md](./06_ROADMAP.md) 的阶段。

### 范式 A · 单一事实源的物理层级 + 机架立面图（NetBox）

**竞品做法**（来源：[NetBox Docs · Racks](https://netboxlabs.com/docs/netbox/models/dcim/rack/)）：
- 层级明确且可导航：`Region → Site Group → Site → Location → Rack Group → Rack → U 位 → Device → 组件`。设备直接冗余存 site/location/rack 引用以加速过滤，界面上每层都是可点击进入的列表页。
- 机柜高度以 **U** 度量，提供「U 位升序/降序」切换； Rack 模型带 `Status`、`Role`、`Facility ID`、`Asset Tag`、`Serial`。
- 机柜模型显式带 `Cooling Capability`（`Air-only` / `Hybrid` / `Liquid-only`）与 `Cooling Capacity (kW)`，用于阻止把液冷设备装进风冷机柜——**容量约束写进数据模型，而不是只写在告警文案里**。
- DCIM 菜单按对象类型平铺（Cables / Devices / Racks / Power Panel / Power Feed / Cooling Feed …），列表页统一「筛选 + 表格 + 批量操作 + 导出」结构。

**本平台现状**：`frontend/src/views/ops/UPosition.vue:5` 已有 U 位可视化（`ErrorRetry` 接入，`index.scss` 无对应立面图规范）；`ops/Cabinets.vue:4` 为机柜表格 + `tf-mask` 抽屉；层级信息散落在 `ops/DataCenterManage.vue`、`ops/RoomAccess.vue`、`ops/CiRelations.vue`。没有「园区 → 机房 → 机柜 → U 位 → 设备」的可点击面包屑，也没有机柜制冷能力字段的界面表达（而 `monitor/HvacLiquid.vue` 已有大量液冷遥测）。

**可落地动作**（P1，阶段 3）：
1. 在 `Cabinets.vue` / `UPosition.vue` 页头增加统一面包屑（复用 `.view-head` + `vh-right`），层级写入 URL query（见范式 C 的深链接）。
2. 机柜详情抽屉增加「制冷能力 / 额定制冷容量 kW」两个只读字段。**v1.1 只读核实：契约中不存在该字段** —— `backend/app/models/cabinet.py:15-29` 的 `Cabinet` 仅有 `u_total / u_used / rated_power_kw / current_power_kw / status`；`cooling_capacity_mw` 是**园区级**（`backend/app/models/idc.py:24`），`capacity_kw` 是「机柜额定**功率** kW」（`backend/app/schemas/idc.py:25`），均不能替代；`frontend/openapi.json` 的 `/api/cabinets*` 4 端点（`:602,624,655,686`）响应 schema 为 `type: object`，同样无该字段。用户已确认「字段要在契约中存在」→ 后续代码轮需**新增模型字段 + Pydantic schema + Alembic 迁移 + `openapi.json` 同步**，这是 [06](./06_ROADMAP.md) §6「不新增后端字段」不变量的用户确认例外（§7 决策 1）。本轮仍不造展示数据、不改契约。
3. `UPosition.vue` 的 U 位网格增加 U 位升序/降序切换与占用率条，样式统一走 [04_VISUAL_SPEC.md](./04_VISUAL_SPEC.md) 的 `.rack-*` 规范。

### 范式 B · 容量叠加层（openDCIM）

**竞品做法**（来源：[openDCIM Features](https://opendcim.org/features.html)）：
- 自定义图片映射，为每个机柜创建**可点击区域**；地图上可叠加 **Power / Space / Temperature / Weight 四层容量视图**——同一空间对象，按维度切换信息层。
- 供电链路按 `device → power strip → panel → source feed` 建模并可追溯；支持面板/源馈电中断的**影响模拟**。
- 图形化机柜视图（需提供图形素材）、设备正反面照片、按 `cost per U` / `cost per Watt` 生成托管成本报表。
- 菜单按功能分组，提供 `Data Center / Zone / Row / Container / Power Panel / Power Source` 等对象层级。

**本平台现状**：`monitor/ThermalCloud.vue:4` 已有「机房 / 通道 / 机柜进风温度」三层下钻热力图；`ops/CapacityWhatIf.vue:19` 已有 What-If 表单 + ECharts；`monitor/PowerLinkage.vue:5` 与 `monitor/HvacLinkage.vue:4` 有手写 SVG 链路图。但三者**各自独立**，没有统一的「图层切换」交互，也没有把电量/空间/温度/承重放在同一坐标系下。

**可落地动作**（P1，阶段 3）：
1. 把 `ThermalCloud.vue` 的「三层下钻」抽象为通用 `LayerSwitch` 交互契约，**按用户确认做四层：温度 / 电力 / 空间 / 承重**。**v1.1 只读核实：四层数据源均已存在** —— `backend/app/services/capacity_energy.py:345-365` 的 `capacity()` 返回**五维 dims**（`机柜空间 U / 电力容量 MW / 制冷容量 MW / 承重容量 % / 网络端口 口`），`capacity_whatif.py:6-7,23-29` 与 `openapi.json:2465`（summary「当前五维容量」）佐证；空间另有 `/api/cabinets/{id}/u-position`（`openapi.json:655`）。第五维「网络端口」按用户确认**不进图层**，仍留在 What-If 结果区。**承重为按设备数占比的估算值**（`capacity_energy.py:359`），必须显式标注「估算 · 非实测称重」。逐层来源与可信度见 [03](./03_METRICS_IA.md) §2.6。
2. `CapacityWhatIf.vue` 的结果区与 `PowerLinkage.vue` 的链路图共用同一套影响高亮色（见 04 规范 `--red`/`--amber` 语义）。
3. 四个容量维度的卡片展示顺序按 [03_METRICS_IA.md](./03_METRICS_IA.md) 的 P0/P1 矩阵固定，避免各页自定义。

### 范式 C · 可复用筛选视图 + URL 深链接（NetBox / Snipe-IT）

**竞品做法**（来源：[NetBox Docs · Saved Filters](https://netboxlabs.com/docs/netbox/models/extras/savedfilter/)）：
- 在任意对象列表页应用筛选后，可把条件**保存为命名对象**：`Name` / `Slug` / `User` / `Weight` / `Enabled` / `Shared` / `Parameters(JSON)`。
- 参数即查询串：`?status=active&region_id=51&tag=alpha` 存为 `{"status":"active","region_id":51,"tag":["alpha"]}`；通过 `?filter=my-slug` 在 **UI 与 REST API 同时复用**。
- `Weight` 控制排序、`Shared` 控制是否对全员可见、`Enabled` 控制是否在列表页出现——筛选本身是一等公民数据，不是临时 UI 状态。
- NetBox Extras 另有 `Table Configs` 管理列表列；Snipe-IT / GLPI 的资产列表均支持自定义列与导出。

**本平台现状**（证据见 02 文档「交互流程」章）：`查询|筛选|搜索` 命中 21 个文件，但 `重置` 只命中 4 个；分页有 4 种实现、每页条数 10/12/20/50 不一；筛选条件不写 URL，刷新即丢失；33 个表格页无统一列配置。

**可落地动作**（P0，阶段 1 定规范 / 阶段 3 推广）：
1. 统一筛选栏组件契约：查询 + 重置 + 保存视图 + 列配置（按钮顺序、尺寸、状态见 04 规范）。
2. 筛选条件与分页写入 URL query（`?status=&page=&size=`），保证深链接与前进/后退可用；这与 UI/UX 知识库 `Navigation / Deep Linking` 准则一致。
3. **不新增后端表**：保存视图先落 `localStorage`（按用户 + 路由键隔离），后续若要跨设备共享再评估新增契约端点，避免 `check_api_contract.py`（200 paths）漂移。

### 范式 D · 仪表盘卡片密度与状态优先级（GLPI / iTop）

**竞品做法**：GLPI 定位「Data center management + ITIL Service Desk」，首页以「待办/到期/异常」优先级组织，资产统计与 KPI 分列；iTop 的 `impact-analysis` 把「受影响业务/服务」放在故障页首屏。共同点是**先呈现需要动作的异常，再呈现统计**，且统计卡片按对象类型分组而非全部平铺。

**本平台现状**：四个总览页（`PowerDashboard.vue:12-47` 等）把「设备总数 / 在线率 / 故障 / 告警」四张同尺寸卡放在最前，故障与告警仅靠 `quality` / `severity` 着色区分；`monitor/HvacLiquid.vue` 单页约 23 张 KPI 卡；`overview/Index.vue:6` 驾驶舱六区块可配置但卡片外观与监控页不一致。

**可落地动作**（P0，阶段 2 标杆）：按 03 文档的四块结构统一总览页——页头（含数据源可信度标记）→ P0 异常指标行 → 按设备类型分组的子系统入口卡（**每类展示差异化指标**）→ 趋势与告警联动区。标杆页即 `Hvac/Power/Network/Security Dashboard` 四页。

### 范式 E · 时序阈值标注与状态可辨识（通用监控可视化）

**竞品/知识库做法**（来源：`ui-ux-pro-max` 只读检索 `--domain chart`）：
- 趋势用折线，实际值实线、预测值虚线，置信区间浅色带；多序列必须用**不同线型/标记**而不只是颜色，并附图例（色盲可达）。
- 异常检测用折线 + 异常点圆形标记 + **文字告警标注**，不能只靠红色。
- 实时流数据必须提供「暂停」入口，避免闪烁元素；深色背景下网格线保持低对比。
- 交付检查表：375 / 768 / 1024 / 1440 四档响应式、亮色主题文字对比 ≥ 4.5:1、可见 focus 态、150–300ms 过渡、不用 emoji 作图标、`prefers-reduced-motion`。

**本平台现状**：阈值判断散落在模板三元表达式（如 `monitor/NetworkSwitches.vue:95` 的 `cpu_pct > 80 → #ef4444`），图表配色写死在 JS option（`monitor/PowerBattery.vue:721` 起多处 hex/rgba），`components/charts/TrendChart.vue` 与 `components/monitor/TrendChart.vue` 两套实现并存，`MetricCard.vue` 内嵌手写 sparkline。

**可落地动作**（P0，阶段 1 定规范 / 阶段 2 落地）：把阈值改为「配置表 + 统一渲染」，阈值线用同一 `markLine` 样式（虚线 + 文案），图表颜色全部从 CSS 变量读取（主题切换时 `setOption` 只更新 `color`/`axisLine` 等少数项，不重建实例）。

## 4. 能力对照矩阵

图例：`●` 已具备 / `◐` 部分具备 / `○` 未具备或待核实。**本平台列均基于本次只读代码核查，不依赖竞品推断。**

| 能力 | NetBox | openDCIM | Ralph | GLPI | Snipe-IT | 本平台 | 本平台证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 物理层级（园区→机房→机柜→U 位） | ● | ● | ● | ◐ | ○ | ◐ | `ops/Cabinets.vue:4`、`ops/UPosition.vue:5`，缺统一面包屑 |
| 机架立面图 / U 位占用可视化 | ● | ● | ● | ○ | ○ | ◐ | `ops/UPosition.vue:335` 起网格样式，无前后视图 |
| 容量叠加层（电/空间/温度/承重） | ◐ | ● | ○ | ○ | ○ | ◐ | `monitor/ThermalCloud.vue:4`、`ops/CapacityWhatIf.vue:19` |
| 供电链路与中断影响模拟 | ● | ● | ○ | ○ | ○ | ● | `monitor/PowerLinkage.vue:5`、`ops/FaultImpact.vue:20` |
| 资产台账 / 全生命周期 | ◐ | ● | ● | ● | ● | ● | `ops/Equipment.vue:4`、`ops/AssetLifecycle.vue:18` |
| IPAM | ● | ◐ | ○ | ◐ | ○ | ● | `ops/Ipam.vue:4`（阶段 P3 已交付） |
| 自动发现 | ◐ | ○ | ◐ | ● | ○ | ● | `ops/Discovery.vue:4`、`ops/Collector.vue:4` |
| **实时遥测（暖通/电力/液冷）** | ○ | ◐ | ○ | ○ | ○ | ● | `monitor/` 27 页，90+ 指标 |
| 3D 孪生 / 大屏 | ○ | ○ | ○ | ○ | ○ | ● | `monitor/Scene3D.vue:3`、`BigScreen.vue:12` |
| 告警 → 工单闭环 | ○ | ○ | ○ | ● | ○ | ● | `ops/Alarms.vue:5` → `ops/Tickets.vue:5` |
| AI 助手 / 知识库 | ○ | ○ | ○ | ○ | ○ | ● | `ops/Assistant.vue:5`、`ops/KnowledgeCenter.vue:4` |
| 可配置个人仪表盘 | ◐ | ○ | ○ | ◐ | ○ | ● | `overview/Index.vue:6` + `composables/useDashboardLayout.ts` |
| 明暗双主题 | ◐ | ○ | ○ | ◐ | ○ | ◐ | `index.scss:1-40` 两套 token，但 22 页硬编码使亮色失效 |
| 移动端响应式 | ◐ | ○ | ○ | ◐ | ◐ | ○ | `index.scss:71` 固定 236px 侧栏，无抽屉 |
| 保存筛选视图 / 列配置 / 深链接 | ● | ○ | ◐ | ◐ | ● | ○ | 21 页有筛选，0 个保存视图，重置仅 4 页 |

**结论**：本平台在**实时监控深度、链路闭环、3D 可视化、AI 与 DevOps 完备度**上明显强于同类开源项目，属于「监控 + CMDB + ITSM 融合」而非纯资产台账。差距集中在两处：① **信息架构的基础设施**（层级导航、保存视图、列配置、深链接）；② **设计系统的一致性**（双主题 token 未被一致消费、无移动端布局）。这两处正好是本次「全平台统一」要解决的范围，不需要重构业务能力。

## 5. 借鉴清单（映射到本平台文件，供路线图引用）

| 编号 | 借鉴项 | 目标文件 | 优先级 | 阶段 | 数据/契约前提 |
| --- | --- | --- | --- | --- | --- |
| B-01 | 页头物理层级面包屑 + URL 参数 | `ops/Cabinets.vue`、`ops/UPosition.vue`、`ops/DataCenterManage.vue` | P1 | 3 | 复用现有路由，不改契约 |
| B-02 | 机柜制冷能力/容量字段展示（**需先补契约字段**） | `ops/Cabinets.vue` 抽屉 + `backend/app/models/cabinet.py`、`schemas/idc.py`、Alembic 迁移、`openapi.json` | P2 | 3 | **v1.1 核实字段不存在**；用户确认「要在契约中存在」→ 先新增字段与迁移再展示；[06](./06_ROADMAP.md) §7 决策 1 为不变量例外 |
| B-03 | 容量图层切换**四层**（温度 / 电力 / 空间 / 承重） | `monitor/ThermalCloud.vue`、`ops/CapacityWhatIf.vue` | P1 | 3 | **v1.1 核实数据源已存在**：`capacity_energy.py:345-365` 五维 dims；承重为估算需标注；第五维「网络端口」不进图层 |
| B-04 | 筛选栏统一 + 重置 + 保存视图 + 深链接 | 21 个含筛选页面 | P0 | 1 定规范 / 3 推广 | 保存视图先 `localStorage`，**不新增 API** |
| B-05 | 表格列配置 + CSV 导出 | 33 个表格页（先 `ops/Equipment.vue`、`admin/AuditLogs.vue`） | P1 | 3 | `AuditLogs.vue` 已有客户端 CSV 导出可复用 |
| B-06 | 四块式总览页 + 差异化指标 | 4 个 `*Dashboard.vue` | P0 | 2 | 指标字段已存在，见 03 文档 |
| B-07 | 阈值线 / 图例 / 异常标注统一 | `components/charts/*`、`components/monitor/TrendChart.vue`、`MetricCard.vue` | P0 | 1 定规范 / 2 落地 | 不新增端点 |
| B-08 | 状态优先级（异常先行） | `overview/Index.vue`、4 个总览页、`ops/Alarms.vue` | P0 | 2 | 复用 `/api/alarms/active` |

## 6. 明确的「不借鉴」项（避免过度改造）

- **不引入第三方组件库**（Element Plus / Ant Design Vue / shadcn）：项目已有自建组件体系与 3072 个 i18n 键，替换会扩大改动面并破坏 `check_nav_routes.py` / i18n 门禁。
- **不照搬 NetBox 的对象类型菜单**（数十个平铺列表页）：本项目已有 71 路由的分组导航，重排会触发死链/孤儿路由门禁，收益低于风险。
- **不为了对标新增后端接口**：`frontend/openapi.json` 已有 200 paths / 271 operations，任何新增都需同步 `check_api_contract.py`；本轮所有借鉴项都限定在前端展示层。
- **不重构设计语言**：沿用暗色科技风 + 亮色双主题，只做 token 收敛（已由用户确认）。

---

**阅读下一步**：[02_DIAGNOSIS.md](./02_DIAGNOSIS.md)（为什么改，逐页证据）→ [03_METRICS_IA.md](./03_METRICS_IA.md)（改什么内容与层级）。
