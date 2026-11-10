# DCIM 全平台诊断与视觉规范 · 文档集索引

| 项 | 内容 |
| --- | --- |
| **版本** | **v1.1**（8 项待确认已由用户答复并经只读代码核实，2026-11-10 修订） |
| **日期** | 2026-11-10 |
| **范围** | 全平台统一：驾驶舱、设施监控、告警、工单、资产、能耗等 **77 个页面**（71 路由） |
| **视觉方向** | 沿用「暗色科技风为主 + 亮色」双主题，统一 token / 字体 / 间距 / 圆角 / 组件风格，**不重构设计语言** |
| **落地节奏** | 阶段 1 设计系统 → 阶段 2 四个总览页标杆 → 阶段 3 批量推广 → 阶段 4 响应式与验证 |

> ## ⚠️ 本轮只交付文档，不改代码
>
> 本轮**未修改**任何 `.vue` / `.ts` / `.scss` / `.css` / 配置 / CI / 路由 / i18n 文件，未 commit、未 push，运行时影响为零（blast radius = 0）。
> 所有页面改造、组件收敛、响应式实现均写在 [06_ROADMAP.md](./06_ROADMAP.md)，**待用户审阅认可后另开一轮**执行。
> `docs/adr/`、`docs/IMPLEMENTATION_PLAN.md`、`CHANGELOG.md` 等既有文档保持不变。

---

## 1. 阅读顺序

文档按「为什么改 → 改什么 → 改成什么样 → 按什么顺序改」组织，共享同一套编号与术语。

| 顺序 | 文档 | 回答的问题 | 关键产出 |
| --- | --- | --- | --- |
| 1 | [01_BENCHMARK.md](./01_BENCHMARK.md) | 同类开源项目怎么做？我们差在哪？ | 11 个经核实仓库（DCIM 6 / CMDB 3 / ITAM 2）、5 个界面/信息架构范式、能力对照矩阵、8 条借鉴项 **B-01~B-08** |
| 2 | [02_DIAGNOSIS.md](./02_DIAGNOSIS.md) | 现有页面有哪些问题？ | 四维诊断（数据展示 / 信息层级 / 交互流程 / 视觉一致性）+ **77 页逐页问题清单**（路径 + 行号 + 问题代码 + 优先级） |
| 3 | [03_METRICS_IA.md](./03_METRICS_IA.md) | 展示哪些指标？按什么优先级与分组？ | 7 类设备 **90+ 指标**字典、P0/P1/P2 矩阵、角色视图、标杆页四块结构、**四层容量图层来源映射**、单位与阈值契约 |
| 4 | [04_VISUAL_SPEC.md](./04_VISUAL_SPEC.md) | 视觉上改成什么样？ | 双主题 28 项 token 表、别名清理、字体/间距/圆角尺度、组件唯一实现、图表规范、可访问性检查表 |
| 5 | [05_RESPONSIVE_SPEC.md](./05_RESPONSIVE_SPEC.md) | 桌面与移动端如何一致？ | 四档断点（375/768/1024/1440）、18 种现有断点迁移表、四档降级矩阵、抽屉交互契约、逐类验收清单 |
| 6 | [06_ROADMAP.md](./06_ROADMAP.md) | 按什么顺序改、怎么验收？ | 四阶段「文件清单 → 改动点 → 验收标准 → 门禁/E2E」、风险回滚、**§7 决策登记（8 项已确认，含核实结论与不变量例外）**、交接说明 |

**快速路径**：只关心结论 → 读 [02](./02_DIAGNOSIS.md) §2 摘要 + [01](./01_BENCHMARK.md) §4 对照矩阵；准备实施 → 直接读 [06](./06_ROADMAP.md) 并以 [02](./02_DIAGNOSIS.md) §7 作为销账基线。

---

## 2. 关键数字速查（均为 2026-11-10 只读核查结果）

| 指标 | 数值 | 出处 |
| --- | --- | --- |
| 页面 / 路由 | 77 个 `.vue` / 71 路由（静态菜单 66 + 插件 5） | `frontend/src/views/`；`check_nav_routes.py --strict` |
| 硬编码色值 | 71/77 文件、约 **1975 匹配行**、32 个文件 >20 处 | [02](./02_DIAGNOSIS.md) D-1 |
| 未定义 CSS 变量 | 10 个别名，约 130 处引用 | [02](./02_DIAGNOSIS.md) D-2 |
| 同名类重复定义 | **15 组** | [02](./02_DIAGNOSIS.md) D-3 |
| 响应式断点 | 70 处 `@media` / 36 文件 / **18 种** max-width 值 | [02](./02_DIAGNOSIS.md) C-2 |
| 移动端能力 | 侧栏抽屉 / 汉堡 / 视口监听 **全部为 0** | `layouts/DefaultLayout.vue` |
| 统一异步组件覆盖 | **55/77** 文件；22+ 页手写 6 种错误 DOM | [02](./02_DIAGNOSIS.md) C-3 |
| 宽表 / KPI 平铺 | 33 页含表格、9 处 >8 列；`HvacLiquid.vue` 单页约 23 张 KPI | [02](./02_DIAGNOSIS.md) A-3 |
| 监控指标 | 电力 / 暖通 / 液冷 / 网络 / 安防 / 能耗 **90+ 项** | [03](./03_METRICS_IA.md) §2 |
| 容量维度 | **五维 dims**（机柜空间 U / 电力容量 MW / 制冷容量 MW / 承重容量 % / 网络端口 口），图层用其中四层 | `backend/app/services/capacity_energy.py:345-365` |
| 刷新周期现状 | `useAsyncPage.ts` 无轮询；页面 env 3s + 硬编码 5s/15s/30s/10s 混合；后端 mock collector 5s | [03](./03_METRICS_IA.md) §5.2（v1.1 实测） |
| DCIM 相关端点 | `openapi.json` 中 29 个；契约总量 200 paths / 271 operations | `check_api_contract.py` |
| i18n | zh / en 各 **3072** 键，0 缺失 | `check_i18n_keys.py --json` |
| E2E | `frontend/e2e/specs/smoke.spec.ts` **10 条**冒烟 | 实测 `Select-String "test("` |

---

## 3. 证据采集方法与口径

| 项 | 说明 |
| --- | --- |
| 采集方式 | 只读静态扫描（`search_content` / `read_file`）+ 两个 `code-explorer` 子代理交叉核对；`ui-ux-pro-max` 技能仅用**只读查询**（`--design-system -f markdown`、`--domain chart\|ux\|typography\|color`、`--stack vue`），**未使用 `--persist`**，未产生额外文件 |
| 对标方式 | GitHub REST API `GET /repos/{owner}/{repo}` + 官方文档页只读抓取；star 数为 2026-11-10 快照；**未截图、未登录试用**，界面结论只来自官方功能说明 |
| 统计口径 | 「命中数」= `search_content --count` 的**匹配行数**，同行多个色值计 1；不等于出现次数 |
| 路径简写 | `V/` = `frontend/src/views/`，`C/` = `frontend/src/components/`，`S/` = `frontend/src/assets/styles/`，`ST/` = `frontend/src/styles/`，`L/` = `frontend/src/layouts/`，`P/` = `packages/dc-ioc-ui/src/`，`A/` = `frontend/src/api/` |
| 行号有效性 | 行号基于当前工作区代码；后续代码轮改动后需重新核对，不能直接复用 |
| 门禁基线 | 已实跑复核：`check_i18n_keys.py --json` ok=true（3072/3072）、`check_api_contract.py` 200 paths / 271 ops、`check_nav_routes.py --strict` 71 路由 / 0 死链 / 0 孤儿 |

**不臆造原则（v1.1 修订）**：v1.0 曾把「机柜制冷字段」「空间/承重数据源」「刷新频率」列为待核实项。用户答复后已逐项**只读核实**，结论见 [06](./06_ROADMAP.md) §7 决策登记：

- 机柜级「制冷能力 / 额定制冷容量 kW」**契约中不存在**（`backend/app/models/cabinet.py:15-29` 无该字段），用户确认要在契约中存在 → 代码轮需新增字段与迁移，这是「不新增后端字段」不变量的**唯一例外**；
- 空间 / 承重数据源**确实存在**（`capacity_energy.py:345-365` 五维 dims），四层图层全部可落地，承重为**估算值**需显式标注；
- 刷新频率**已实测**（`useAsyncPage.ts` 无轮询，页面级 3s/5s/15s/30s/10s 混合），设计建议与现状严格分离，不得把建议值当现状；
- 仍未确认的只有 NVR 存储天数阈值 N 与真实采集器周期，分别标注「待业务确认」「待后端确认」。

---

## 4. 术语表

| 术语 | 含义 |
| --- | --- |
| **token** | `frontend/src/assets/styles/index.scss:1-40` 中 `:root[data-theme]` 定义的 CSS 变量；本规范要求其为唯一色彩来源 |
| **四档断点** | 设计视口 375 / 768 / 1024 / 1440；CSS 实现边界 420 / 768 / 1024 / 1440（见 [05](./05_RESPONSIVE_SPEC.md) §2） |
| **P0 / P1 / P2** | 指标展示优先级：需立即动作 / 需判断 / 需查证（[03](./03_METRICS_IA.md) §3） |
| **四块结构** | 标杆页统一布局：页头 → P0 指标行 → 子系统入口卡 → 趋势与告警联动区 |
| **四层容量图层 / LayerSwitch** | 温度 / 电力 / 空间 / 承重四层共用的交互契约；第五维「网络端口」不进图层；承重为估算值（[03](./03_METRICS_IA.md) §2.6） |
| **问题代码 `C*` / `L*` / `I*` / `D*`** | 视觉一致性 / 信息层级 / 交互流程 / 数据展示 四类问题的编号，字典见 [02](./02_DIAGNOSIS.md) §7 |
| **借鉴项 `B-01~B-08`** | 同类项目可借鉴的落地动作，见 [01](./01_BENCHMARK.md) §5 |
| **AsyncSection 四态** | loading / error / empty / success 统一托管（`C/common/AsyncSection.vue:3-42`） |
| **可信度标记 / useMockFlag** | `frontend/src/composables/useAsyncPage.ts:138-164` 的 `none / partial / full` 三档；页头 `DataBadge` + 区块 `MockDataBanner` 两级展示；`partial` 必须点名模拟字段（[03](./03_METRICS_IA.md) §5.1） |
| **双主题** | `:root[data-theme="dark"]`（默认）与 `:root[data-theme="light"]`，由 `frontend/src/theme.ts` 切换 |
| **门禁** | `check_nav_routes.py` / `check_api_contract.py` / `check_i18n_keys.py` / `check_except_hygiene.py` / `vue-tsc` / `vitest` / `pytest` / Playwright E2E |
| **blast radius** | 本轮为 0：不触碰任何运行文件 |

---

## 5. 与既有文档的关系

| 既有文档 | 关系 |
| --- | --- |
| `docs/IMPLEMENTATION_PLAN.md` | 四阶段功能升级（v0.16.0）的实施记录；**本设计文档集不修改它**，但沿用其中的 CI/门禁事实 |
| `docs/adr/0001–0005` | 架构决策记录，保持不变；后续若引入 `metricsCatalog` 等新约定，另开 ADR |
| `CHANGELOG.md` | 本轮不追加条目；代码轮实施时按阶段记录 |
| `frontend/e2e/README.md` | E2E 自带 API 桩机制说明；响应式阶段新增四档用例时需同步 |
| `README.md` / `README.en.md` | 项目说明，保持不变 |

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| v1.0 | 2026-11-10 | 首次发布：7 篇文档（索引 + 对标 + 诊断 + 指标与信息架构 + 视觉规范 + 响应式规范 + 路线图）。范围全平台 77 页；本轮仅文档，代码实施待用户确认后另开一轮 |
| v1.1 | 2026-11-10 | 用户逐项答复原 8 项待确认，转为「§7 决策登记」。三处事实经只读核实更正：① 机柜制冷字段契约中不存在，登记为需新增字段的唯一不变量例外；② 空间/承重数据源存在（`capacity_energy.py` 五维 dims），容量图层由「先两层」改为**四层全落地**，新增 §2.6 来源映射；③ `useAsyncPage.ts` 无轮询但页面级轮询真实存在，§5.1 改 `useMockFlag` 三档、§5.2 重写为「现状实测 / 设计建议」分离。另确认分页默认 20 / 审计页 50 例外、3D 降级 2D 概览、保存视图 `localStorage`、网络端点单独评估、NVR 阈值仍待业务确认。7 篇文档同步版本号与引用 |

---

## 7. 下一步

1. 审阅本索引与 6 篇正文，重点确认 [02](./02_DIAGNOSIS.md) §7 的逐页销账基线、[03](./03_METRICS_IA.md) 的指标优先级，以及 [06](./06_ROADMAP.md) §7 决策登记中**决策 1 的契约字段例外**（唯一突破「不新增后端字段」不变量的改动）。
2. 认可后**另开一轮**执行 [06](./06_ROADMAP.md) 阶段 1（设计系统统一），并在阶段 3 前完成决策 1 的模型字段 / schema / Alembic 迁移 / `openapi.json` 同步。
3. 阶段 2 结束设「标杆页确认」闸门，再进入阶段 3/4；仍开放项（NVR 阈值 N、真实采集器周期）需业务 / 后端确认后登记。
