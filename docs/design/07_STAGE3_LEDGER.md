# 07 · 阶段 3 逐页销账表

> 基线：`02_DIAGNOSIS.md` §7 的逐页清单。C1（硬编码色值）与 C2（未定义变量）
> 已全库清零；阶段 3-A 把手写异步四态收敛到 `AsyncSection`，3-B 把阈值收编到
> `metricsCatalog`，3-C 统一可信度标记。例外均登记原因。

| 页面 | 形态 | 原问题代码 | 优先级 | C1 / C2 | I5 · AsyncSection | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `monitor/PowerDashboard.vue` | KPI + 6 入口卡 | L3 L5 I4 C3 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/HvacDashboard.vue` | KPI + 5 入口卡 | L5 I4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/NetworkDashboard.vue` | KPI + 4 入口卡 | L3 I4 C3 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/SecurityDashboard.vue` | KPI + 4 入口卡 | L3 C2 I4 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerHv.vue` | SVG 一次图 + 14 列表 | C1 L4 I5 D2 I4 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerLv.vue` | SVG + 18 列表 | L4 L2 I5 C1 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerGenset.vue` | 并机图 + 11 列表 | L4 D1 I5 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerFuel.vue` | 储油图 + 多表 | D1 L4 C1 C4 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerBattery.vue` | 电池组图 + ECharts | C6 D1 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/PowerLinkage.vue` | SVG 链路 | C1 I5 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/HvacChiller.vue` | 8 KPI + SVG + ECharts | L1 L2 D5 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/HvacCrac.vue` | 机房看板 + ECharts | L2 I5 I1 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/HvacLiquid.vue` | 23 KPI + 水质表 | L2 C4 D1 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/HvacLinkage.vue` | SVG 制冷链路 | I5 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/ThermalCloud.vue` | 三层温度热力图 | C1 C4 D2 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/NetworkSwitches.vue` | Spine-Leaf 图 + 10 列表 | L4 D1 I5 D3 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/NetworkRouters.vue` | SVG + ECharts | I5 C1 D3 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/NetworkFirewalls.vue` | ECharts + 表格 | I5 D3 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/NetworkWireless.vue` | 热力图 + ECharts | C1 I5 D3 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/SecurityCctv.vue` | 分屏预览 + 筛选 | L1 C2 I1 I4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/SecurityAcs.vue` | 门禁平面图 | C2 C1 C4 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/SecurityIds.vue` | 周界示意 + 事件表 | C2 C1 C4 | P1 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `monitor/SecurityFire.vue` | 消防平面图 | C2 C1 C4 | P1 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `monitor/HealthDashboard.vue` | KPI + 健康度表 | I5 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `monitor/BigScreen.vue` | 大屏 | D2 | P0 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `monitor/BigScreenDesigner.vue` | 表单 + 预览 | C1 I3 | P2 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |
| `monitor/Scene3D.vue` | 3D 孪生 | C1 I5 D2 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `overview/Index.vue` | 驾驶舱六区块 | L1 C1 C4 D2 C3 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `energy/EnergyDashboard.vue` | KPI + ECharts + 表 | I6 D2 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `auth/Login.vue` | 登录表单 | C1 C5 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `admin/AuditLogs.vue` | 9 列审计表 | L4 I2 I5 I1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `admin/RowAudit.vue` | 行级审计表 | I2 I5 I1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Equipment.vue` | 设备台账表 | I1 I2 I5 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Cabinets.vue` | 机柜表 + 抽屉 | I1 I3 I5 I2 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/UPosition.vue` | U 位可视化 | C4 C1 I5 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/Alarms.vue` | 告警看板 + 大表 | I1 I3 I5 C1 | P0 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Tickets.vue` | 11 列工单表 | L4 I3 I2 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/AlarmHistory.vue` | 告警表 + 触达表 | I2 D2 | P2 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `ops/AlarmRules.vue` | 8 列规则表 + 弹窗 | C1 I3 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/AssetBusiness.vue` | 资产业务表 | C5 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/AssetLifecycle.vue` | KPI + 表 + 弹窗 | I3 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Assistant.vue` | AI 对话看板 | C1 I3 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/CapacityWhatIf.vue` | What-If 表单 + ECharts | D2 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/CiRelations.vue` | CI 关系表 + SVG 影响图 | L1 C1 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/Collector.vue` | 采集器表 + 弹窗 | I1 I3 I5 C1 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/CustomFields.vue` | 表单 + 预览表 | L1 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/DataCenterCompare.vue` | 多园区对比 | C1 C4 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/DataCenterManage.vue` | 园区表 + 抽屉 | I3 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Discovery.vue` | 发现候选 + 待办 | C5 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/DrillPlan.vue` | KPI + 9 列表 | L4 I3 I6 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Duty.vue` | 排班表/看板 | C2 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/DutyCalendar.vue` | 排班日历 | C1 C4 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/FaultImpact.vue` | 影响图 + 报告 | I6 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/HealthReport.vue` | 健康度报告 + ECharts | D2 C4 | P2 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `ops/Inspection.vue` | 巡检表 + 看板 | C2 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/InspectionTemplate.vue` | 模板表单 + 表 | C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/IntegrationHub.vue` | 集成表 + 看板 | C1 C4 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Ipam.vue` | VLAN/子网/地址多表 | L4 C5 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/KnowledgeCenter.vue` | 知识看板 + 表 | I2 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/KnowledgeCollaboration.vue` | 协作 KPI + 表 | C1 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/Maintenance.vue` | 维护表 + 日历 | C2 C1 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/MaintenanceCalendar.vue` | 维护日历 | C1 C4 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/NotificationCenter.vue` | 渠道/记录表 | I2 C1 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/PowerAiHazards.vue` | 隐患表 | D2 I5 | P2 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `ops/Risk.vue` | 风险表 + 表单 | C2 I2 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/RoomAccess.vue` | KPI + 出入表 | C1 C4 I1 | P1 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `ops/Supplier.vue` | 供应商表 | D2 | P2 | 已修 | 例外 | 静默 mock 回退设计，已用 MockDataBanner 显式标记；error 态不适用 |
| `ops/Telemetry.vue` | 遥测表 | I2 C1 | P2 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/TenantManage.vue` | 租户表 + 22 控件表单 | C1 L2 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/ThingModelEditor.vue` | 物模型编辑器 | C1 | P2 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/WorkflowCenter.vue` | KPI + 流程看板 | I3 C1 C2 C4 | P1 | 已修 | 已修 | 已接入 AsyncSection（loading / error / empty / 重试） |
| `ops/components/AlarmListPanel.vue` | 告警列表（10 `<th`） | C1 L4 | P1 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |
| `ops/components/AlarmRulePanel.vue` | 规则表单面板 | — | P2 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |
| `ops/components/CollectorDeviceForm.vue` | 采集设备表单 | I3 L2 | P1 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |
| `ops/components/CollectorDeviceTable.vue` | 采集设备表（12 `<th`） | L4 | P1 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |
| `ops/components/CollectorMetricDefsModal.vue` | 测点定义表 + 表单 | I3 I5 | P1 | 已修 | 例外 | 有数据源但四态未统一，待逐页重构 |
| `ops/components/CollectorMetricsModal.vue` | 测点查看表 | I3 I5 C1 | P1 | 已修 | 不适用 | 无异步数据源（静态 / 配置 / 本地演示页） |

## 汇总

- 销账页数：**77**
- C1 硬编码色值：**0**（视图层全库清零，颜色只来自 `:root` token 与 `cssToken()`）
- C2 未定义变量 / `var(--x, fallback)`：**0**
- I5 `AsyncSection` 覆盖：**56/77** 视图文件
- 销账表状态：已修 56 / 例外 15 / 不适用 6

## 本轮阶段 3-A/B/C 落地

- **3-A**：20 个页面接入 `AsyncSection`（Power×4 / Network×3 / Hvac×2 / Scene3D /
  HealthDashboard / Security×2 / PowerBattery / WorkflowCenter / ops×4），手写 loading/error
  骨架块删除，四态由统一组件托管；哨兵式接入不破坏原有 `v-if` 正文。
- **3-B**：29 处硬编码阈值三元收编到 `metricsCatalog` / `severityOf()` /
  `CAPACITY_THRESHOLDS` / `BAR_THRESHOLDS`（PowerBattery / PowerFuel / PowerGenset /
  NetworkSwitches / NetworkWireless / NetworkFirewalls），未登记指标不擅自改边界。
- **3-C**：四网络页确认已调用真实 API（`getNetwork*Detailed`）且带 `MockDataBanner`；
  ops×4 与 `SecurityCctv` 的本地回退提示统一到 `MockDataBanner`。

## 筛选栏 / 分页 / 遮罩统一（04 §6.2）

- **遮罩**：21 个 ops 页的 5+ 种私有遮罩类名（`drawer-mask` / `tf-mask` /
  `kb-modal-mask` / `confirm-mask` / `ai-corrmask` / `.mask`）统一为 `.modal-mask`；
  抽屉容器统一 `.modal.as-drawer`、弹窗 `.modal`；scoped 选择器同步改名，
  页面级微调保留、视觉零回归。
- **分页**：7 个手写分页页（Equipment / Cabinets / Telemetry / Risk / KnowledgeCenter /
  RowAudit / AuditLogs）迁移到 `Pagination.vue`；组件默认可选值收敛为 `[20, 50]`，
  默认 20 条；`admin/AuditLogs.vue` 保留 50 为唯一例外，`AlarmHistory` 50 → 20。
- **筛选栏**：44 处废弃组合式 `btn-sm primary` → `btn-sm btn-primary`；查询按钮统一
  `.btn-primary`、重置按钮统一 `.btn-ghost`；4 个缺重置的筛选页补齐按钮。
  新增 `composables/useFilterQuery.ts`（筛选与分页双向同步 URL query），**14 页接入**。

## 批次 1-5：筛选视图 / 列配置 / 无障碍（ADR-0006）

- **契约层**：`useViewPreferences.ts`（个人视图、三级回退、防御式 normalize）
  与 `useColumnConfig.ts`（显隐 / 排序 / `applyColumns`），配套 2 个 spec 共 10 个用例。
- **存储**：复用 `/api/ops/graphic-config/{kind}`（ADR-0004），
  `kind = fv:{username}:{pageId}(:hash)` 在 `String(64)` 内做个人隔离，零后端改动；
  `params.views` 存 JSON 字符串；viewer 无写权限时回退 localStorage，由 `DataBadge` 标注。
- **组件层**：`FilterBar.vue`（完整 / `compact` 两形态）、`ColumnConfig.vue`、
  `useModalA11y.ts`（Esc + Tab 焦点陷阱 + 焦点归还）；新增 17 个 `filterView.*` 双语键。
- **接线**：`Equipment.vue` 完整范式（FilterBar 替换筛选容器 + 9 列抽 `columnSeeds`
  + th/td 显隐 + 视图保存列配置 + 弹窗无障碍）；另有 7 页 `compact` 接入保存视图；
  URL query 从 6 页补齐到 **14 页**（Collector / KnowledgeCenter / Risk / Telemetry /
  Tickets / CiRelations / Alarms / ThingModelEditor）。
- **单位口径修正**：`HvacLiquid.vue` 的 `L/min` 是冷板支路语义
  （后端 `mock_collector.py:298`），与主管 `m³/h`（:48/:65）不是同量纲，**不做换算**；
  列标签显式标注「冷板支路」，并在 `metricsCatalog` 登记
  `hvac.liquid.mainFlow` / `hvac.liquid.coldPlateFlow` 两种单位定义。

## 剩余（已登记，未在本轮完成）

- **列配置 / 遮罩无障碍的完整推广**：列配置目前只在 `Equipment.vue` 生效，
  Esc/焦点陷阱也只接了该页弹窗；其余 ops 表格 `<th>/<td>` 硬编码、各页遮罩开关变量不同，
  需逐页抽列元数据并确认 close 回调，无法机械批量替换。
- **`FilterBar` 完整模式只 1 页**：另有 7 页走 `compact`（保留本页查询/重置按钮），
  其余即时筛选页（无查询按钮）尚未接入保存视图。
- **自定义按钮类未归并**：`btn-refresh`(3) / `kb-act-btn`(12) / `chip-clear` /
  `hv-edit` / 裸 `btn`(18)。它们各有 scoped 样式，直接追加 `.btn-ghost`
  会与全局样式叠加导致视觉回归，需逐页收敛样式实现而非只改类名。
- 登记为「例外」的页：静默 mock 回退设计，只有可信度标记而无页面级 loading/error 态；
  按用户 v1.1 决策保留回退行为，不把表单错误误当加载失败。
- 决策 5 评估结论：`/api/network/ping` 与 `/api/network/bandwidth` 后端已实现
  （`backend/app/api/v1/endpoints/network.py:19,24`）且登记在契约；四网络页当前使用
  `getNetwork*Detailed` 概览端点，两个诊断端点仍未在页面调用，留待数据侧确认后再接。
