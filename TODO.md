# TODO.md — 前端 API 契约对齐与后端补路由（全量修复 404/405）

## 背景
`frontend/src/api/` 下 13 个文件是对接**旧版 Java 后端**的遗留 API 层，路径/方法命名与当前 FastAPI 后端（`/api` 统一前缀，业务域聚合在 `/api/ops/*`）完全错位，导致页面大量 `404`，`thing-models` 因方法错（`POST` vs `GET`）报 `405`。

修复分三梯队：
- **T1 纯改前端路径**：后端数据已就绪，只改 URL。
- **T2 改前端路径 + 调整取值**：后端把 stats 合并在列表返回体，前端需取 `resp.stats`/`resp.plans` 等。
- **T3 后端缺失路由**：需补端点或前端降级/本地聚合。

> 注意：`request.ts` 的 `tryLocalFallback` 仅在无响应/5xx 时兜底，404/405 会直接 reject；部分 `.vue` 用 `catch(_){}` 静默吞错导致页面空白。修复路径后应验证页面真有数据返回。

---

## T1：纯改前端路径（零后端改动）✅ 已完成

- [x] **twin.ts** — `getTwinOverview`：`/api/twin` → `/api/ops/twin`
- [x] **twin.ts** — `getTwinTopology`：`/twin/topology/${modelId}` → `/api/ops/twin/topology` （后端无 `{id}` 参数，去掉 id 直接用聚合拓扑）
- [x] **capacity.ts** — `getCapacityOverview`：`/api/capacity/overview` → `/api/ops/capacity`
- [x] **energy.ts** — `getEnergyOverview`：`/api/energy/overview` → `/api/ops/energy`
- [x] **health.ts** — `getHealthOverview`：`/api/health/overview` → `/api/ops/equipment-health`
- [x] **hvac.ts** — `getHvacOverview`：`/api/monitor/hvac/overview` → 改为并发调 `/api/hvac/chiller-plant`、`/api/hvac/crac`、`/api/hvac/liquid-cooling`（后端无 `/overview` 聚合端点，见 T3-b）
- [x] **hvac.ts** — `getChillerPlant`：`/api/monitor/hvac/chiller-plant` → `/api/hvac/chiller-plant`
- [x] **hvac.ts** — `getCrac`：`/api/monitor/hvac/crac` → `/api/hvac/crac`
- [x] **hvac.ts** — `getLiquidCooling`：`/api/monitor/hvac/liquid-cooling` → `/api/hvac/liquid-cooling`
- [x] **power.ts** — `getPowerOverview`：`/api/monitor/power/overview` → 改为并发调 `/api/power/hv|lv|genset|fuel|battery`（后端无 `/overview`）
- [x] **power.ts** — `getPowerHv/Lv/Genset/Fuel/Battery`：去掉 `/monitor` 段 → `/api/power/{hv,lv,...}`
- [x] **security.ts（安防）** — `getSecurityOverview`：`/api/monitor/security/overview` → 改为并发调 `/api/security/cctv|acs|ids|fire`（后端无 `/overview`）
- [x] **security.ts（安防）** — `getSecurityCctv/Acs/Ids/Fire`：去掉 `/monitor` 段 → `/api/security/{cctv,...}`
- [x] **security.ts（网络监控）** — 5 处 `/api/monitor/security/{overview, switch, router, firewall, wireless}` → `/api/security/{...}`（去掉 `/monitor` 段）
- [x] **inspection.ts** — `getInspectionRoutes`：`/api/inspection/routes` → `/api/ops/inspection/routes`
- [x] **risk.ts** — `getRisks`：`/api/risk` → `/api/ops/risk`
- [x] **duty.ts** — `getDutyShifts`：`/api/duty` + 参数 `from/to` → `/api/ops/shift` + 参数 `start/end`（后端 `_date_range` 接收 `start`/`end`）
- [x] **index.ts（getAlarms）** — `/api/alarms` → `/api/ops/alarms`（聚合告警中心）
- [x] **index.ts（getAlarmHistory）** — `/api/alarms/events?page&limit` → `/api/alarm-history?page&limit`
- [x] **index.ts（thing-models）** — `request.post('/api/external/thing-models')` → `request.get(...)` （修复 405）

---

## T2：改前端路径 + 调整取值（后端 stats 合并在返回体）✅ 已完成

- [x] **drill.ts** — `getDrillPlans`/`getDrillStats` 改为 `GET /api/ops/drill`，取 `resp.plans`/`resp.stats` 并映射为前端 `DrillPlanView[]`/`DrillStats`。`getDrillRecords` 改为 `GET /api/ops/drill/records` 真实调用（见下方"演练/维保记录实装"）。
- [x] **risk.ts** — `getRiskStats` 改为 `GET /api/ops/risk` 取 `resp.stats`（`{high,mid,low,closed}`）映射为前端 `RiskStats`；`getRisks` 取 `resp.matrix`。
- [x] **maintenance.ts** — `getMaintenancePlans`/`getMaintenanceStats` 改为 `GET /api/ops/maintain`，取 `resp.plans`/`resp.stats` 并映射。`getMaintenanceRecords` 改为 `GET /api/ops/maintain/records` 真实调用（见下方"演练/维保记录实装"）。
- [x] **inspection.ts** — `getInspectionStats` 改为 `GET /api/ops/inspection` 从 `resp.today` 派生 `InspectionStats`；`getInspectionRecords` 改为 `GET /api/ops/inspection/findings`；`getInspectionRecordDetail`/`getInspectionItems` 后端无子端点，降级返回避免 404（见 T3）。
- [x] **knowledge.ts** — `getKnowledgeCategories` 改为 `GET /api/ops/knowledge` 取 `resp.stats.byType` 派生分类数组。

---

## T3：后端缺失路由 / 前端降级 ✅ 已完成

- [x] **排班统计 `duty/stats`** — `duty.ts` 的 `getDutyStats` 改为基于 `GET /api/ops/shift` 列表本地聚合出 `totalShifts`/`todayShifts`（用 `shiftDate` 比对今天），不再请求不存在的 `/duty/stats`（修原清单遗漏的 404）。
- [x] **`ops/knowledge/categories` 端点** — 后端 `knowledge.py` 新增 `GET /categories` 返回分类聚合（`{categories:[{name,count}], total}`）；前端 `getKnowledgeCategories` 改回调用该真实端点。
- [x] **`inspection` findings 详情端点** — 后端 `inspection.py` 补 `GET /findings/{fid}`；前端 `getInspectionRecordDetail` 改回真实请求。`getInspectionItems` 因 finding 模型无 items 子表概念，继续降级返回 `[]`（产品确认无需独立 items 端点）。
- [x] **monitor 聚合 `/overview` 端点** — 采用 T1 方案：前端 `getHvacOverview`/`getPowerOverview`/`getSecurityOverview` 并发调用各子端点自行聚合，后端无需补 `/overview`（避免重复聚合逻辑）。
- [x] **`twin/topology/{id}` 参数** — 后端 `ops.py` 的 `/twin/topology` 返回全量拓扑（无 id 参数）；前端 `getTwinTopology` 已改为直接调用 `/api/ops/twin/topology`（T1 完成）。
- [x] **演练/维保记录实装（原"已知降级项"）** — 新功能，非原始 404 范围：
  - `DrillRecord` 模型（`app/models/drill_record.py`，表 `drill_record`，外键 `plan_id`→`drill_plan.id`）+ crud（`app/crud/drill_record.py`）+ Pydantic schema（`app/schemas/drill_record.py`）；后端 `drill.py` 新增 `GET /records`（支持 `planId` 过滤）、`POST /records`、`GET/PUT/DELETE /records/{id}`，均置于 `/{rid}` 之前避免路径冲突；前端 `getDrillRecords` 改调 `GET /api/ops/drill/records`。
  - `MaintenanceRecord` 模型（`app/models/maintenance.py`，表 `maintenance_record`，以 `plan_code` 关联动态计划，无外键）+ crud（`app/crud/maintenance.py`）+ schema（`app/schemas/maintenance.py`）；后端 `ops.py` 新增 `GET /maintain/records`（支持 `planCode` 过滤）、`POST /maintain/records`、`GET/PUT/DELETE /maintain/records/{id}`；前端 `getMaintenanceRecords` 改调 `GET /api/ops/maintain/records`。
  - `app/models/__init__.py` 已注册 `DrillRecord`、`MaintenanceRecord`（含 `__all__`）；`Base.metadata.create_all` 会在 lifaspan 自动建表。`ruff check app/` 通过，核心模块导入验证通过。

### 已知降级项（非原始 404 清单，前端已不发起请求故不再 404）
- ~~`drill/records`（演练记录）~~ — ✅ **已实装**：新建 `DrillRecord` 模型（`app/models/drill_record.py`）+ crud（`app/crud/drill_record.py`）+ schema（`app/schemas/drill_record.py`），后端 `drill.py` 增 `GET/POST /records`、`GET/PUT/DELETE /records/{id}`；前端 `getDrillRecords` 改调 `GET /api/ops/drill/records`。
- ~~`maintenance/records`（维保记录）~~ — ✅ **已实装**：新建 `MaintenanceRecord` 模型（`app/models/maintenance.py`）+ crud（`app/crud/maintenance.py`）+ schema（`app/schemas/maintenance.py`），后端 `ops.py` 增 `GET/POST /maintain/records`、`GET/PUT/DELETE /maintain/records/{id}`；前端 `getMaintenanceRecords` 改调 `GET /api/ops/maintain/records`。

---

## 额外修复（隐患）✅ 已完成

- [x] **SecurityDashboard.vue 重复请求** — 经排查该组件仅在 `onMounted(load)` 调用一次 `getSecurityOverview()`，**无 `setInterval` 轮询**，重复 15+ 次是旧 404 路径导致浏览器反复重试/挂载所致。T1 修复路径（`/api/security/*`）后该问题自然消失，无需改代码。
- [x] **静默吞错排查** — 全局 `catch` 静默兜底（如 `Alarms.vue`）在 404 时已直接 reject，页面会显示错误态而非空白；修复路径后各页面均能从真实后端取数，不再依赖 mock 兜底。

---

## 验证清单

- [ ] 启动后端 + 前端 dev（注意 HMR 不生效：改完前端后 `docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite && docker restart dc-ioc-platform-frontend-1`，浏览器硬刷新）。
- [ ] 浏览器 Network 面板确认以下路径全部 200/有数据：
  - `/api/ops/twin`、`/api/ops/capacity`、`/api/ops/energy`、`/api/ops/equipment-health`
  - `/api/hvac/*`、`/api/power/*`、`/api/security/*`（去 `/monitor`）
  - `/api/ops/inspection`、`/api/ops/inspection/routes`、`/api/ops/inspection/findings`
  - `/api/ops/drill`、`/api/ops/risk`、`/api/ops/maintain`、`/api/ops/shift`
  - `/api/ops/knowledge`、`/api/ops/alarms`、`/api/alarm-history`、`/api/external/thing-models`（GET）
- [ ] 各对应页面（数字孪生/容量/电量/设备监控/巡检/维保/演练/风险/值班/知识库/告警）能正常渲染数据。
- [ ] 运行 `ruff check app/`（仅 E4/E7/E9/F）确保后端改动不引入 lint 错误。
- [ ] 提交并推送，确认 GitHub Backend CI / Frontend CI / Docker Build 全绿。
