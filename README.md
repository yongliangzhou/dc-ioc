# DC-IOC Platform · 数据中心智能运营中心

> **v0.12.0** | 统一图形编辑入口（12 个图形页）· 统一告警触达中心 · 告警自动建单 · 上架模拟器 · 全项目体检（41 用例测试基线 / i18n 对齐门禁 / 裸 except 可观测）| 技术栈: **Vue 3 + TypeScript + Vite**（前端） · **Python FastAPI**（后端） · **PostgreSQL/TimescaleDB + Redis**（存储） · **three.js**（3D 孪生）

---

## 一、项目目录结构（分层架构）

```
dc-ioc-platform/
├── .github/workflows/                 # ===== CI/CD =====
│   └── ci.yml                         #   GitHub Actions: lint + test + build + scan
│
├── backend/                           # ===== 后端 FastAPI =====
│   ├── app/
│   │   ├── main.py                    # 应用入口 (启动顺序: 密钥检查→日志→监控→DB→Kafka→Mock→KPI广播)
│   │   ├── core/                      # 核心基础设施
│   │   │   ├── config.py              #   pydantic-settings 读取 .env (连接池/速率限制/外部接入/告警 Webhook 等)
│   │   │   ├── security.py            #   JWT 签发/验证 + bcrypt 密码哈希
│   │   │   ├── deps.py                #   RBAC 依赖注入 (require_role / require_permission / get_current_user)
│   │   │   ├── logging_config.py      #   结构化日志 (loguru: 控制台彩色 / JSON文件轮转) + 告警 Handler 挂载
│   │   │   ├── monitoring.py          #   Prometheus 指标 (HTTP 延迟/QPS/WS连接/告警数/KPI)
│   │   │   ├── secret_check.py        #   启动密钥安全检查 (prod 环境阻止默认凭据)
│   │   │   ├── cache.py               #   Redis 响应缓存装饰器 cache_json (+ invalidate_prefix 失效工具)
│   │   │   └── alert_bridge.py        #   日志/审计告警联动 (关键审计动作 + ERROR 日志 → 统一告警通道)
│   │   ├── api/v1/
│   │   │   ├── router.py              #   路由聚合 (28 个业务域 + 认证)
│   │   │   └── endpoints/
│   │   │       ├── auth.py            #   JWT 登录/刷新/改密/用户管理 + 自助注册 (register, 受开关控制)
│   │   │       ├── dashboard.py       #   IOC 驾驶舱 (overview/campuses/campus-comparison, 缓存)
│   │   │       ├── equipment.py       #   统一设备台账 (11 个域)
│   │   │       ├── hvac.py            #   暖通 (冷源/空调末端/液冷)
│   │   │       ├── power.py           #   电力 (10KV/0.4KV/柴发/燃油/电池)
│   │   │       ├── security.py        #   安防消防
│   │   │       ├── ops.py            #   运维作业
│   │   │       ├── alarms.py          #   告警中心
│   │   │       ├── alarm_history.py   #   告警历史
│   │   │       ├── alarm_rules.py     #   告警规则引擎
│   │   │       ├── tickets.py        #   事件工单 (含状态机校验)
│   │   │       ├── inspect.py        #   巡检管理
│   │   │       ├── maintain.py       #   维保管理
│   │   │       ├── shift.py          #   排班管理
│   │   │       ├── drill.py          #   演练管理
│   │   │       ├── risk.py           #   风险管理
│   │   │       ├── knowledge.py       #   知识库 (含批量导入)
│   │   │       ├── cabinets.py        #   机柜管理
│   │   │       ├── assistant.py       #   AI 运维助手
│   │   │       ├── metrics.py         #   测点数据
│   │   │       ├── external.py        #   外部设备接入 (注册/测点上报/告警评估)
│   │   │       ├── thing_model.py     #   物模型 CRUD (property/service/event 三要素, 接管 GET /thing-models)
│   │   │       ├── idc.py             #   多数据中心 (CRUD/切换/跨中心对比/统一告警)
│   │   │       ├── runbooks.py        #   运维预案 (告警关联处置预案, /api/runbooks/related)
│   │   │       ├── audit.py           #   审计日志查询 (/api/audit-logs, 过滤/分页/CSV 导出)
│   │   │       ├── uploads.py         #   通用文件上传 (/api/uploads/avatar|attachment|batch)
│   │   │       ├── graphic_editor.py  #   统一图形编辑入口 (场景覆盖层) + 加油记录 CRUD
│   │   │       ├── notification.py    #   通知中心 (通道 CRUD / 发送记录 / 测试发送)
│   │   │       ├── network.py         #   网络监控 (交换机/路由/防火墙/无线)
│   │   │       ├── domain.py          #   域名/路由监控
│   │   │       ├── demo.py            #   v2 演示/兜底数据
│   │   │       └── ws.py              #   WebSocket 实时遥测
│   │   ├── models/                    # SQLAlchemy ORM (User/Role/Permission/audit_logs/equipment/ticket/thing_model/idc 等)
│   │   ├── schemas/                   # Pydantic DTO (请求/响应校验, 含 UserRegister/ThingModel/Idc)
│   │   ├── crud/                      # 数据访问层 (含 ticket 状态机 + SLA 计算 + thing_model + idc 聚合)
│   │   ├── services/                  # 业务逻辑层
│   │   │   ├── dc_aggregator.py       #   ** 统一聚合出口 ** (真实链路→回退生成器, 35 个函数)
│   │   │   ├── alarm_engine.py        #   告警引擎 (13类设备阈值+收敛+抑制+通知)
│   │   │   ├── alarm_notify_webhook.py#   告警 Webhook 通知 (钉钉/邮件/微信)
│   │   │   ├── ws_broadcaster.py      #   WebSocket 广播管理器
│   │   │   ├── notification_service.py#   统一告警触达中心 (级别路由/静默/去重/重试/留痕)
│   │   │   ├── alarm_ticket_bridge.py #   告警→工单自动建单桥 (幂等, 双向联动)
│   │   │   └── capacity_whatif.py     #   上架模拟器 (容量 What-if 纯函数推演)
│   │   │   └── dc_ioc_data.py         #   兜底数据生成器 (22 个业务域, 34 个函数)
│   │   ├── db/session.py              # SQLAlchemy 引擎 (连接池参数配置化) + lifespan 建表
│   │   ├── collectors/                # 采集层 (MockCollector / Kafka 消费)
│   │   └── cache/                     # Redis 客户端
│   │   ├── seed_admin.py              # 种子脚本: 幂等创建 admin/operator/viewer 三角色账号
│   │   ├── seed_demo.py               # 种子脚本: 演示数据 (IDC/机房/机柜/服务器/设备/知识库, 支持 --force)
│   │   ├── api_endpoints.md           # 后端 API 端点静态提取清单 (gen_api.py 生成)
│   │   └── deploy/sql/                 # 第五阶段新增文档 (与根 deploy/sql 迁移脚本互补):
│   │       ├── 010_data_dictionary.md  #   数据字典 (27 表反射)
│   │       ├── 011_er_diagram.md       #   ER 图 (Mermaid)
│   │       ├── 012_permission_matrix.md#   权限矩阵
│   │       ├── 009_index_optimization.sql    # 高频查询索引
│   │       └── 013_timeseries_optimization.sql # 时序超表/压缩/连续聚合
│   ├── alembic/                       # Alembic 迁移 (0001~0012: 核心表/审计软删/CHECK/BIGINT/FK/行级审计/超表/图形编辑/通知)
│   ├── tests/                         # 测试 (Phase 2 核心 / 负载)
│   ├── requirements.txt               # Python 依赖
│   ├── Dockerfile
│   ├── .env.example                   # 环境变量模板
│   ├── .env.dev                       # 开发环境配置
│   ├── .env.staging                   # 预发环境配置
│   └── .env.prod                      # 生产环境模板
│
├── packages/                          # ===== 共享组件库 =====
│   └── dc-ioc-ui/                     #   @dc-ioc/ui (StatusBadge / AlarmBadge / KpiCard)
│       ├── package.json               #     独立 npm 包 (Vite library mode)
│       ├── src/
│       └── dist/                      #     ESM + UMD + CSS + .d.ts
│
├── frontend/                          # ===== 前端 Vue3+TS+Vite =====
│   ├── src/
│   │   ├── App.vue / main.ts          # 入口 (Pinia/Router 挂载 + Token 初始化)
│   │   ├── api/
│   │   │   ├── request.ts             #   axios 实例 (Bearer 注入 + 401 自动刷新 + Mock 兜底)
│   │   │   └── index.ts              #   业务域 API (含 registerUser 自助注册)
│   │   │   ├── thingModel.ts          #   物模型 CRUD 封装
│   │   │   ├── idc.ts                 #   数据中心 CRUD/切换/对比/告警封装
│   │   │   ├── twin.ts                #   3D 孪生设备拓扑封装 (复用 /api/external/devices)
│   │   │   ├── generated/index.ts     #   orval 自动生成 (OpenAPI → TS, 1600+ 行)
│   │   │   ├── generatedWrapper.ts    #   axios 桥接层 (封装所有 generated API)
│   │   ├── openapi.json               #   API 契约 (29 端点 / 9 Schema)
│   │   ├── views/
│   │   │   ├── auth/Login.vue         #   登录页 (含可选自助注册表单)
│   │   │   ├── overview/Index.vue     #   IOC 驾驶舱总览
│   │   │   ├── hvac/                  #   暖通监控 (3 页面)
│   │   │   │   ├── Chiller.vue        #     冷源系统 (8台冷机 4+2+N)
│   │   │   │   ├── Crac.vue           #     空调末端
│   │   │   │   └── LiquidCooling.vue  #     液冷系统 (CDU/冷板/漏液/余热回收)
│   │   │   ├── power/                 #   电力监控 (5 页面)
│   │   │   │   ├── Hv.vue / Lv.vue    #     10KV中压 / 0.4KV低压
│   │   │   │   ├── Genset.vue         #     柴发并机系统
│   │   │   │   └── Fuel.vue / Battery.vue  # 燃油 / 电池
│   │   │   ├── security/              #   安防消防 (4 页面)
│   │   │   │   ├── Cctv.vue / Acs.vue #     视频监控 / 门禁管理
│   │   │   │   └── Fire.vue / Ids.vue #     消防报警 / 防入侵
│   │   │   ├── monitor/               #   设施监控 (27 页面: 暖通 / 电力 / 安防消防 / 网络 / 健康度 / 数字可视)
│   │   │   │   ├── HvacDashboard.vue  #     暖通总览
│   │   │   │   ├── HvacChiller.vue / HvacCrac.vue / HvacLiquid.vue  #   冷源 / 空调末端 / 液冷
│   │   │   │   ├── HvacLinkage.vue / ThermalCloud.vue  #   制冷链路可视化 / 温度云图
│   │   │   │   ├── PowerDashboard.vue #     电力总览
│   │   │   │   ├── PowerHv.vue / PowerLv.vue / PowerLinkage.vue  #   10KV / 0.4KV / 配电链路
│   │   │   │   ├── PowerGenset.vue / PowerFuel.vue / PowerBattery.vue  #   柴发 / 燃油 / 电池
│   │   │   │   ├── SecurityDashboard.vue  #   安防消防总览
│   │   │   │   ├── SecurityCctv.vue / SecurityAcs.vue / SecurityIds.vue / SecurityFire.vue  #   视频 / 门禁 / 入侵 / 消防
│   │   │   │   ├── NetworkDashboard.vue  #   网络总览
│   │   │   │   ├── NetworkSwitches.vue / NetworkRouters.vue  #   核心交换机 / 路由器
│   │   │   │   ├── NetworkFirewalls.vue / NetworkWireless.vue  #   防火墙 / 无线网络
│   │   │   │   ├── HealthDashboard.vue #     设备健康度
│   │   │   │   └── Scene3D.vue / BigScreen.vue / BigScreenDesigner.vue  #   3D 视图 / 定制大屏 / 大屏定制
│   │   │   ├── ops/                   #   运维 / 资产 / 知识AI / 平台集成 (32 页面)
│   │   │       ├── Alarms.vue         #     告警中心
│   │   │       ├── AlarmHistory.vue   #     告警历史
│   │   │       ├── AlarmRules.vue     #     告警规则引擎
│   │   │       ├── Tickets.vue        #     事件工单中心
│   │   │       ├── Inspection.vue     #     巡检管理
│   │   │       ├── InspectionTemplate.vue # 电子巡检
│   │   │       ├── Maintenance.vue    #     维保管理
│   │   │       ├── MaintenanceCalendar.vue # 维保日历
│   │   │       ├── Duty.vue           #     值班管理
│   │   │       ├── DutyCalendar.vue   #     排班日历
│   │   │       ├── RoomAccess.vue     #     机房进出登记
│   │   │       ├── FaultImpact.vue    #     故障影响分析
│   │   │       ├── DrillPlan.vue      #     应急演练
│   │   │       ├── Risk.vue           #     风险管理
│   │   │       ├── PowerAiHazards.vue #     供配电 AI 隐患
│   │   │       ├── HealthReport.vue   #     iHealth 月度健康报告
│   │   │       ├── Supplier.vue       #     供应商管理
│   │   │       ├── Equipment.vue      #     统一设备台账
│   │   │       ├── UPosition.vue      #     U 位识别
│   │   │       ├── Cabinets.vue       #     机柜管理
│   │   │       ├── AssetLifecycle.vue #     资产生命周期
│   │   │       ├── TenantManage.vue   #     租户管理
│   │   │       ├── KnowledgeCenter.vue #    知识库
│   │   │       ├── KnowledgeCollaboration.vue # 知识协作
│   │   │       ├── Assistant.vue      #     AI 运维助手
│   │   │       ├── ThingModelEditor.vue #   物模型图形化编辑器 (属性/服务/事件 + 实时预览 + 校验)
│   │   │       ├── Collector.vue      #     采集器接入
│   │   │       ├── Telemetry.vue      #     设备遥测
│   │   │       ├── WorkflowCenter.vue #     ITIL 流程
│   │   │       ├── IntegrationHub.vue #     集成验证中心
│   │   │       ├── DataCenterManage.vue #   多数据中心管理 (增改删/启停/设为当前)
│   │   │       ├── DataCenterCompare.vue #  跨中心对比仪表盘 + 统一告警视图
│   │   │       ├── NotificationCenter.vue #  统一告警触达中心 (通道/记录/测试)
│   │   │       └── CapacityWhatIf.vue #     上架模拟器 (容量 What-if)
│   │   │   ├── energy/
│   │   │       └── EnergyDashboard.vue #   电量预测与节能 (含 iCooling 制冷策略优化)
│   │   │   ├── twin/
│   │   │       ├── TwinDashboard.vue  #   数字孪生总览 (Raptor/方舟)
│   │   │       └── Twin3D.vue         #   3D 数字孪生拓扑 (three.js: 旋转/缩放/分层/实时映射)
│   │   ├── stores/modules/
│   │   │   ├── auth.ts                #   认证状态 (Pinia: login/refresh/logout)
│   │   │   ├── metrics.ts             #   实时指标状态
│   │   │   ├── tickets.ts             #   工单状态 (持久化)
│   │   │   └── datacenter.ts          #   当前数据中心 (Pinia: 切换持久化 + 影响拓扑/监控范围)
│   │   ├── composables/
│   │   │   ├── useAsyncPage.ts        #   异步页状态机 (useAsyncPage / useAsyncPageAll / toErrorMessage)
│   │   │   └── useGraphicEditor.ts    #   统一图形编辑状态机 (场景覆盖层: 覆盖/删除/自建)
│   │   ├── hooks/useWebSocket.ts      #   WebSocket 组合式函数 (自动重连)
│   │   ├── engine/
│   │   │   └── realtimeLinkage.ts     #   实时越限联动引擎
│   │   ├── router/index.ts            #   路由 + Auth Guard (63 条路由)
│   │   ├── layouts/DefaultLayout.vue   #   主布局 (9 组可折叠侧边栏菜单, 折叠态按分组 id 记忆)
│   │   ├── components/layout/NavIcon.vue # 侧边栏图标 (内联 lucide SVG, 55+ 图标)
│   │   ├── components/                #   通用/图表/业务组件
│   │   │   ├── MetricCard.vue         #     指标卡片
│   │   │   ├── KnowledgePanels.vue    #     知识库面板
│   │   │   ├── Pagination.vue         #     分页
│   │   │   ├── common/                #     通用区块 (AsyncSection / ErrorBanner / GraphicEditDrawer 等)
│   │   │   ├── charts/                #     图表 (BaseChart / TrendChart)
│   │   │   └── business/              #     业务组件 (DeviceMonitor / TicketFormModal / SlaSummary)
│   │   ├── types/
│   │   │   ├── index.ts               #   TS 类型定义
│   │   │   ├── graphic.ts             #   图形场景覆盖层 + 加油记录契约
│   │   │   └── capacity.ts            #   上架模拟器契约
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── deploy/                            # ===== 部署运维 =====
│   ├── docker-compose.yml             # 基础编排 (pg16 + redis7 + backend + frontend)
│   ├── docker-compose.dev.yml         # 开发覆盖 (热重载 + Prometheus + 前端 dev server :5173)
│   ├── docker-compose.staging.yml     # 预发覆盖 (2副本 + Prometheus + Grafana + NodeExporter)
│   ├── docker-compose.prod.yml        # 生产覆盖 (3副本 + Loki + Promtail + 资源限制)
│   ├── prometheus/
│   │   ├── prometheus.yml             #   抓取配置 (backend / node-exporter)
│   │   └── rules/alerts.yml           #   12 条告警规则
│   ├── grafana/
│   │   ├── datasources/               #   Prometheus + Loki 数据源自动加载
│   │   └── dashboards/                #   仪表盘自动加载
│   ├── loki/loki-config.yaml          #   日志聚合 (30天保留)
│   ├── promtail/promtail-config.yaml  #   日志采集 (app/error/external)
│   ├── nginx/                         #   前端静态托管/反向代理
│   ├── sql/
│   │   ├── init.sql                    #   初始化 (数据库/扩展)
│   │   ├── 002_core_tables.sql         #   核心表 DDL
│   │   ├── 003_point_data_hypertable.sql   # TimescaleDB 超表
│   │   ├── 004_schema_design.md         #   数据库设计文档
│   │   ├── 005_metric_raws_hypertable.sql # metric_raws 超表+压缩+保留+连续聚合
│   │   ├── 006_seed_auth.sql            #   默认角色 + admin 用户
│   │   ├── 007_metric_raw_unique.sql    #   唯一约束修正
│   │   └── 008_capacity_energy_history.sql # 容量/能耗历史表
│   ├── scripts/
│   │   ├── backup.sh                   #   pg_dump 备份 (SQL/自定义格式 + S3 + 自动清理)
│   │   └── restore.sh                  #   pg_restore 恢复 (并行 + 自动重建)
│   ├── README.md                       #   迁移与初始化策略 (create_all 兜底 + Alembic 受控变更)
│   ├── redis_backup.md                 #   Redis 持久化/备份策略 (RDB/AOF/容量淘汰)
│   ├── cache_strategy.md               #   缓存策略 (推广/失效/预热 + cache_json TTL)
│   └── thing_models.example.json       #   物模型配置覆盖文件示例
│
├── tests/                             # ===== pytest 测试基线 (41 用例, SQLite+依赖覆盖) =====
│   ├── conftest.py                    #   共享设施 (FakeUser / 轻量 FastAPI / SQLite 内存库)
│   ├── test_graphic_editor.py         #   图形编辑入口 + 加油记录
│   ├── test_notification_center.py    #   通知中心 (路由/静默/去重/重试/端点)
│   ├── test_alarm_ticket_bridge.py    #   告警自动建单 (幂等/级别/回写)
│   ├── test_capacity_whatif.py        #   上架模拟器推演
│   ├── test_tenants_row_audit.py      #   租户 / 行级审计冒烟
│   └── load/
│       ├── locustfile.py              #   Locust 压测 (只读/写入 9 端点)
│       └── requirements.txt
│
├── scripts/
│   └── check_i18n_keys.py             # i18n zh/en 键对齐审计 (CI 门禁, --json)
│
├── start.bat                          # Windows 一键启动
├── docker-compose.yml                 # 根编排 (指向 deploy/ 下配置)
└── .gitignore                         # 排除 .env* 备份 日志 数据卷
```

---

## 二、后端分层职责

| 层 | 目录 | 职责 | 依赖方向 |
|---|---|---|---|
| 控制层 | `api/v1/endpoints` | 解析请求、校验、调用 service | → service |
| 业务层 | `services` | 业务规则、告警引擎、聚合编排、WS 广播 | → crud / cache |
| 数据访问层 | `crud` | 纯 DB 增删改查 | → models |
| DTO | `schemas` | Pydantic 请求/响应模型 | — |
| 模型层 | `models` | SQLAlchemy ORM (User/Role/Device/MetricRaw) | — |
| 基础设施 | `core` / `db` / `cache` | 配置、安全、日志、监控、会话、Redis | — |

> 约定：上层只依赖下层，禁止反向依赖；接口出参统一用 `schemas` 序列化。

---

## 三、业务模块全景

### 3.0 侧边导航结构（9 组，可折叠）

左侧栏由 `layouts/DefaultLayout.vue` 的 `nav` 计算属性驱动（**非路由自动生成**），按业务域划分为 9 组。
组标题可点击折叠/展开（`ChevronDown` 展开 / `ChevronRight` 收起，默认全展开），折叠状态按分组 `id` 记忆
（不随 i18n 语言切换丢失），路由变化时自动展开当前页所属分组，避免跳转后菜单项"消失"。

| # | 分组 | 内容 |
|---|---|---|
| 1 | **总览** | IOC 驾驶舱 |
| 2 | **设施监控** | 暖通空调（冷源/末端/液冷/制冷链路/温度云图）· 电力监控（10KV/0.4KV/配电链路/柴发/燃油/电池）· 物理安防与消防（视频/门禁/入侵/消防）· 网络监控（交换/路由/防火墙/无线）· 设备健康度 · 数字可视（3D/大屏/大屏定制） |
| 3 | **告警** | 告警中心 · 告警历史 · 告警规则引擎 |
| 4 | **运维作业** | 巡检（+电子巡检）· 维保（+维保日历）· 值班（+排班日历）· 事件工单中心 · 机房进出登记 · 故障影响分析 · 应急演练 · 通知中心 · 风险管理 · 供配电 AI 隐患 · iHealth 报告 · 供应商管理 |
| 5 | **资产** | 统一设备台账 · U 位识别 · 机柜管理 · 上架模拟器 · 资产生命周期 · 租户管理 |
| 6 | **能效** | 电量预测与节能 |
| 7 | **知识与 AI** | 知识库 · 知识协作 · AI 运维助手 |
| 8 | **平台集成** | 物模型 · 采集器接入 · 设备遥测 · ITIL 流程 · 集成验证中心 · 数据中心（管理/对比） |
| 9 | **系统管理** | 操作审计 · 行级变更审计 |

> 约定：菜单项与路由一一对应（**65 条路由 ↔ 65 个菜单项**，v0.12 新增通知中心/上架模拟器后）。新增页面需**同时**在 `router/index.ts`
> 注册路由并在 `DefaultLayout.vue` 的 `nav` 中登记入口，否则会成为无入口的孤儿页。

### 3.1 总览（Overview）

| 页面 | 路由 | 说明 |
|---|---|---|
| IOC 驾驶舱 | `/overview` | 园区/机房级 KPI 总览、PUE 迷你趋势、分域健康度与在线率、活跃告警；campus KPI 真实时序由 `/api/dashboard/overview/trends` 提供 |

### 3.2 设施监控（Facility Monitoring）

#### 暖通空调 `/monitor/hvac`

| 页面 | 路由 | 规模 | 核心指标 |
|---|---|---|---|
| 暖通总览 | `/monitor/hvac` | 4 张聚合 KPI + 冷源/末端/液冷入口卡 | 分域健康度、在线设备数 |
| **冷源系统** | `/monitor/hvac/chiller` | **8台冷机 (4+2+N)**, 8冷却塔, 8冷冻泵/冷却泵/二次泵, 4板换, 8电动阀, 6000m³蓄冷罐 | 总装机 28MW, 供水温度, PLR, COP, 三级自然冷 |
| **空调末端** | `/monitor/hvac/crac` | 精密空调群组 + 新风 + 恒湿 + 包间环境（12 列可显隐、包间卡片联动筛选） | 送风温度, 回风温度, 能耗, 室内外温差 |
| **液冷系统** | `/monitor/hvac/liquid` | 4台一次侧CDU, 8台二次侧CDU (A/B/C/D区), 冷板监控, 分集液管路, 漏液检测, 余热回收 | 供液35/45℃, ΔT, PUE贡献0.06, 自然冷4380h, 余热1.2MW |
| 制冷链路可视化 | `/monitor/hvac/linkage` | 冷机 → 水泵 → 板换 → 末端全链路 | 链路流向、节点状态、供回水温差 |
| 温度云图 | `/monitor/hvac/thermal` | 通道层 / 机柜层温度场（响应式 1280/760 断点） | 温度分布、热点定位 |

> 液冷系统架构：一次侧中温水 32/38℃ 经 CDU 板换 → 二次侧洁净冷却液 35/45℃ → 冷板直触 GPU。支持 GPU 节点级温度监控 (H800/H100/A800)，闭塔+干冷器自然冷覆盖率 >50%，N+1 冗余自动切换。

#### 电力监控 `/monitor/power`

| 页面 | 路由 | 规模 |
|---|---|---|
| 电力总览 | `/monitor/power` | 4 张聚合 KPI + 5 个电力子系统入口卡（栅格已统一 `cols-2`） |
| **10KV 中压配电** | `/monitor/power/hv` | 两路市电 + 母联, 变压器群 |
| **0.4KV 低压配电** | `/monitor/power/lv` | UPS 双总线, 列头柜, 机柜级 PDU |
| 配电链路可视化 | `/monitor/power/linkage` | 市电 → 变压器 → UPS → 列头柜 → 机柜 全链路 |
| **柴发并机系统** | `/monitor/power/genset` | N+1 柴发群, 并机逻辑, 自动切换 |
| **燃油监控** | `/monitor/power/fuel` | 油罐液位, 日耗量, 补油周期 |
| **电池监控** | `/monitor/power/battery` | 蓄电池组电压/内阻/温度, 放电测试（含空态与错误重试） |

#### 物理安防与消防 `/monitor/security`

| 页面 | 路由 | 功能 |
|---|---|---|
| 安防消防总览 | `/monitor/security` | 4 张聚合 KPI + 视频/门禁/入侵/消防入口卡 |
| 视频监控 | `/monitor/security/cctv` | 摄像头在线状态与画面轮巡 |
| 门禁管理 | `/monitor/security/acs` | 门禁点、刷卡记录、授权管理 |
| 防入侵系统 | `/monitor/security/ids` | 入侵探测与防区状态 |
| 消防报警 | `/monitor/security/fire` | 消防主机、探测器、联动设备 |

#### 网络监控 `/monitor/net`

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 网络总览 | `/monitor/net` | admin/operator | 全网拓扑概览与 KPI 仪表盘 |
| 核心交换机 | `/monitor/net/switches` | admin/operator | 交换机运行状态、端口流量、CPU/内存 |
| 路由器 | `/monitor/net/routers` | admin/operator | BGP 状态、吞吐量、会话数、路由表 |
| 防火墙 | `/monitor/net/firewalls` | admin/operator | 并发会话、吞吐量、规则命中统计（磁盘占用为模拟字段，页面已 `partial` 标注） |
| 无线网络 | `/monitor/net/wireless` | admin/operator | AP 在线状态、2.4G/5G 信道利用率、客户端分布 |

#### 设备健康度与数字可视

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 设备健康度 | `/monitor/health` | admin/operator | 全量设备健康评分分布与劣化趋势 |
| 3D 视图 | `/monitor/visual/3d` | admin/operator | three.js 机房场景：按 location 分层（机房→机柜→设备）；OrbitControls 旋转/缩放；分层显隐；轮询实时染色（在线青 / 离线灰 / 高温红）；点击设备弹出指标卡 |
| 定制大屏 | `/monitor/visual/bigscreen` | admin/operator | 大屏展示态 |
| 大屏定制 | `/monitor/visual/designer` | admin/operator | 可视化拖拽编排大屏 |

### 3.3 告警（Alarms）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 告警中心 | `/ops/alarms` | — | 活跃告警（含实时联动引擎产生项）、确认 / 关单 / 一键转工单 |
| 告警历史 | `/ops/alarm-history` | — | 历史告警回溯与趋势（多通道告警已并入） |
| 告警规则引擎 | `/ops/alarm-rules` | admin/operator | 13 类设备阈值规则、5min 收敛窗口、设备抑制、规则启停 |

### 3.4 运维作业（Ops）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 巡检管理 | `/ops/inspection` | admin/operator | 巡检计划与执行记录 |
| 电子巡检 | `/ops/inspection-template` | admin/operator | 巡检模板配置与移动端填报 |
| 维保管理 | `/ops/maintenance` | admin/operator | 维保计划、工单与执行 |
| 维保日历 | `/ops/maintenance-calendar` | admin/operator | 维保排期日历视图 |
| 值班管理 | `/ops/duty` | admin/operator | 值班编排与交接 |
| 排班日历 | `/ops/duty-calendar` | admin/operator | 排班日历视图 |
| 事件工单中心 | `/ops/tickets` | admin/operator | 工单 CRUD + 状态机流转（`done→open` 等非法跳转返回 400）+ SLA 超时 |
| 机房进出登记 | `/ops/room-access` | admin/operator | 进出登记与审批留痕 |
| 故障影响分析 | `/ops/fault-impact` | admin/operator | 故障源 → 关键链路 → 受影响业务域；缓解建议、故障源遥测、报告存档与会签 |
| 应急演练 | `/ops/drill-plan` | admin/operator | 演练计划（level/scope/duration/steps）与演练记录；「演练预演」可映射候选故障源 |
| 风险管理 | `/ops/risk` | admin/operator | 风险清单 + P×I 风险矩阵（按等级着色、点击格筛选）+ 筛选/排序/分页/导出 |
| 供配电 AI 隐患 | `/ops/power-ai-hazards` | admin/operator | 供配电隐患识别与处置跟踪 |
| iHealth 健康报告 | `/ops/health-report` | admin/operator | 月度健康报告：7 大域评分 → 总分/等级/环形图 + 关键发现与改进建议 |
| 供应商管理 | `/ops/supplier` | admin/operator | 供应商档案与多维度评分（滑块录入 + 删除二次确认） |
| 通知中心 | `/ops/notifications` | admin/operator | 告警触达通道配置（类型/最低级别/静默窗口/启停）+ 发送记录留痕查询 + 连通性测试；后端按级别路由分发（复用告警引擎 notify_handler 机制） |

### 3.5 资产（Asset）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 统一设备台账 | `/ops/equipment` | admin/operator | 11 个域设备统一台账 |
| U 位识别 | `/ops/u-position` | admin/operator | 电子工单台账（基准）+ RFID/资产标签（实测）双源融合；42U 立面冲突检测与来源置信度 |
| 机柜管理 | `/ops/cabinets` | admin/operator | 机柜空间 / 电力 / 制冷容量 |
| 资产生命周期 | `/ops/asset-lifecycle` | admin/operator | 资产从入库到退役全周期跟踪 |
| 租户管理 | `/ops/tenant-manage` | admin/operator | 租户档案与配额（机柜/设备/功耗/带宽）+ 实时用量与健康状态 |
| 上架模拟器 | `/ops/capacity-whatif` | admin/operator | 容量 What-if 推演：给定新增机柜数与单柜功率，推演电力/制冷/空间/U 位四维余量、85%/100% 到达月份与瓶颈排序（区别于 twin 的故障注入 What-if） |

### 3.6 能效（Energy）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 电量预测与节能 | `/analysis/energy` | admin/operator | 能耗分析与电量预测；含 iCooling 制冷策略优化（策略卡 / 验证进度 / 收益） |

### 3.7 知识与 AI（Knowledge & AI）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 知识库 | `/ops/knowledge` | admin/operator | 知识条目管理、批量导入（PDF/Word，PyMuPDF 优先）、检索 |
| 知识协作 | `/ops/knowledge-collab` | admin/operator | 知识评审与协作流程 |
| AI 运维助手 | `/ops/assistant` | admin/operator | 本地知识库检索生成 + 可选大模型润色；多模型注册表运行时热切换与连通性诊断 |

### 3.8 平台集成（Platform & Integration）

| 能力 | 路由 | 权限 | 说明 |
|---|---|---|---|
| **物模型编辑器** | `/ops/thing-model` | admin/operator | 图形化编辑设备「属性/服务/事件」三要素模板；左列表 + 中表单 + 右实时 JSON 预览；保存前校验 key 唯一性/必填/标识符格式/重复 |
| **采集器接入** | `/ops/collector` | admin/operator | 外部采集器注册与接入状态（消费 `/api/external/*`） |
| **设备遥测** | `/ops/telemetry` | admin/operator | 设备测点实时/历史遥测（`/api/external/devices/{id}/metrics/realtime|history`） |
| **ITIL 流程** | `/ops/workflow` | admin/operator | 服务端流程引擎：创建/推进/关闭/重开/审批/日志；审批权限按角色判定 |
| **集成验证中心** | `/ops/integration-hub` | admin/operator | 外部系统对接与连通性验证 |
| **多数据中心管理** | `/ops/datacenter` | admin/operator | 数据中心卡片网格（增改删/启停/设为当前）；切换写入 `/api/idc/current` 全局生效 |
| **跨中心对比** | `/ops/datacenter/compare` | admin/operator | 各中心电力/制冷/机柜/告警并排 KPI 卡 + 对比柱状图 + 统一告警视图 |

> **后端支撑**（v0.9 新增）：`thing_models` / `thing_model_items` 双表承接物模型全生命周期（接管原只读 `GET /thing-models`）；`IDC` 模型扩展 `capacity_kw` / `description` / `is_current` 字段，`ExternalDevice` 增加可空 `idc_id` 实现设备归属站点聚合。新增 `/api/thing-models`（CRUD）、`/api/idc`（CRUD + `/current` 切换 + `/compare` 对比 + `/alarms` 统一告警）。

### 3.9 系统管理（System）

| 页面 | 路由 | 权限 | 功能 |
|---|---|---|---|
| 操作审计 | `/admin/audit` | admin/operator | 审计日志查询（过滤/分页/CSV 导出，`/api/audit-logs`） |
| 行级变更审计 | `/admin/row-audit` | admin/operator | 敏感表（users/roles/tenant）行级 I/U/D 镜像与操作人追溯（DB 触发器落库，`/api/row-audit`） |

> **历史遗留（当前未接入路由）**：数字孪生 `/ops/twin`、链路拓扑 `/ops/topology`、容量管理 `/ops/capacity`、
> 3D 数字孪生 `/twin/3d` 四条路由均已移除——3D 能力现由 `/monitor/visual/3d` 承载，容量类能力并入
> 「3.5 资产」（U 位识别 / 机柜管理）。

---

## 四、版本演进

### v0.1 (骨架)
- FastAPI + Vue3 + PostgreSQL + Redis 基础架构
- 11 个业务域端点占位
- 驾驶舱静态 Mock 数据

### v0.2 — Phase 1+2 (2026-07)

**Phase 1 — 统一数据流向**
```
MockCollector (模拟采集器) 或 真实采集器
  └─ POST /api/external/device/register
  └─ POST /api/external/metrics/upload
      └─ external_devices / metric_raws (落库)
          └─ dc_aggregator.py (聚合层)
              ├─ 有真实数据 → 聚合返回 (_source: "aggregated")
              └─ 无真实数据 → 回退生成器 (_source: "generated")
                  └─ 22 个业务端点统一消费
```

**Phase 2 — 上线刚需**

| 模块 | 文件 | 功能 |
|------|------|------|
| JWT + RBAC | `security.py` `auth.py` `deps.py` | Bearer Token 认证 + admin/operator/viewer 三角色 + 权限字符串 |
| TimescaleDB | `005_metric_raws_hypertable.sql` | 超表 → 7天压缩 → 90天保留 → 5min/1h 连续聚合 |
| 告警引擎 | `alarm_engine.py` | 13 类设备阈值规则 + 5min 收敛窗口 + 设备抑制 + 通知回调 |
| WebSocket 实时推送 | `ws_broadcaster.py` `useWebSocket.ts` | KPI 快照 (5s) + 告警实时推送到驾驶舱全客户端 |

### v0.3 — Phase 3 (2026-07) 生产化

| 模块 | 文件 | 功能 |
|------|------|------|
| CI/CD | `.github/workflows/ci.yml` | Backend: ruff lint + bandit + safety + pytest + coverage; Frontend: vue-tsc + build; Docker: build + Trivy |
| 环境隔离 | `.env.{dev,staging,prod}` `docker-compose.{dev,staging,prod}.yml` | 三套环境: dev (debug+mock)、staging (2副本+监控)、prod (3副本+Loki) |
| 密钥管理 | `secret_check.py` | 启动时检查: prod 环境拒绝 SECRET_KEY<16 字符和默认 admin 密码 |
| 结构化日志 | `logging_config.py` | loguru: dev→彩色控制台, prod→JSON 文件轮转 (30d) + 错误独立 (90d) + 敏感脱敏 |
| Prometheus 监控 | `monitoring.py` `prometheus.yml` `alerts.yml` | HTTP 指标 + WS 连接数 + 活跃告警 + KPI Gauge + 12 条告警规则 |
| Grafana + Loki | `grafana/` `loki/` `promtail/` | 仪表盘自动加载 + 日志聚合 (30d) + 采集管道 |
| 备份恢复 | `backup.sh` `restore.sh` | pg_dump (SQL / 自定义格式) + S3 上传 + pg_restore 并行恢复 + 自动重建 |
| 压测 | `locustfile.py` | ReadOnlyUser + WriteUser, 覆盖 9 个核心端点, 支持 headless CI 模式 |

### v0.4 — 前端增强 (2026-07)

| 模块 | 文件 | 功能 |
|------|------|------|
| Mock 兜底链路补全 | `frontend/src/api/mockData.ts` | 补充 `/api/demo/overview`、`/api/demo/devices` 的 Mock 兜底, v2 演示视图在后端离线时也能展示数据 |
| 随机游走遥测 | `frontend/src/api/mockData.ts` | 外部设备 / 机柜 / 设备台账测点改为一阶惯性随机游走, 趋势曲线连续且动态; 偶发越限窗口用于驱动联动告警 |
| 越限联动引擎 | `frontend/src/engine/realtimeLinkage.ts` | 周期消费实时遥测, 经持续窗口判定后自动生成活动告警 (按设备类别作用域匹配, 支持启停 / 确认 / 关单) |
| 告警 → 工单闭环 | `frontend/src/views/ops/Alarms.vue` | 告警中心合并实时联动告警, 一键转工单 (`ticketsStore` 持久化) 并自动确认, 形成 "遥测越限 → 告警 → 工单" 闭环 |

### v0.5 — 智算中心级暖通 (2026-07)

| 模块 | 文件 | 功能 |
|------|------|------|
| **液冷系统** | `backend/app/services/dc_ioc_data.py` `frontend/src/views/hvac/LiquidCooling.vue` | 完整液冷分配系统：一次侧 CDU (4台) / 二次侧 CDU (8台, 按 A/B/C/D 区分区) / 冷板级 GPU 温度监控 (H800/H100/A800) / 分集液管路 / 漏液检测 (绳式+点式 128传感器) / 冷却液品质 (电导率/pH/乙二醇) / 闭塔+干冷器热排放 / 余热回收 1.2MW → 园区供暖 / 三级自然冷切换策略 / 故障知识库 |
| **冷源系统扩容** | `backend/app/services/dc_ioc_data.py` `frontend/src/views/hvac/Chiller.vue` | 冷站规模从 2+1 扩容至 **4+2+N (8台冷机)**: CH-01~08、8台冷却塔、8套冷冻/冷却水泵、6套二次泵、4台板换、8个电动阀、6000m³蓄冷罐。总装机 28MW（单台 3500kW≈1000RT）。前端所有硬编码数字改为动态计算 (运行/备用/维保计数、COP均值、板换投入率) |
| 前端路由补全 | `frontend/src/router/index.ts` | 新增 `/hvac/liquid-cooling` 路由，侧边栏「暖通监控系统」分组新增液冷系统入口 |

### v0.6 — 网络监控深化 + 代码质量 (2026-08)

| 模块 | 文件 | 功能 |
|------|------|------|
| **网络监控套件** | `frontend/src/views/monitor/NetworkDashboard.vue` `NetworkSwitches.vue` `NetworkRouters.vue` `NetworkFirewalls.vue` `NetworkWireless.vue` | 5 个子页面完整覆盖数据中心网络：总览仪表盘、核心交换机（端口/CPU/内存）、路由器（BGP/吞吐量/路由表）、防火墙（并发会话/规则统计）、无线网络（AP/2.4G+5G 信道） |
| API 类型补全 | `frontend/src/api/monitor.ts` `frontend/src/api/hvac.ts` | `NetworkRouterSummary`/`NetworkSwitchSummary`/`NetworkFirewallSummary`/`NetworkWirelessSummary` 类型完善；`mapChiller` 补充 `chillerGroups` 映射 |
| vue-tsc 零错误 | 全项目 | 修复全部 TypeScript 类型错误：string→number 实参类型 (fmtNum/fmtBps 返回值)、数组字面量联合类型推断、接口可选字段补全，`vue-tsc --noEmit` 通过 |
| Ruff 代码质量 | `backend/app/services/dc_ioc_data.py` | 修复 E741 模糊变量名，ruff check 零告警 |

### v0.7 — 后端及数据库全面排查与补齐 (2026-08)

> 经实扫代码，后端实际成熟度远超预期，多数能力已具备。本阶段重点补齐唯一真实 API 缺口、缺失文档/脚本，并做若干增强。

| 模块 | 文件 | 功能 |
|------|------|------|
| API 缺口补齐 | `app/api/v1/endpoints/runbooks.py` `router.py` | 新增 `/api/runbooks/related`（告警关联处置预案，复用知识库 related 逻辑），对齐前端 `Alarms.vue` |
| 通用文件上传 | `app/api/v1/endpoints/uploads.py` `main.py` | `/api/uploads/avatar`、`/attachment`、`/batch`，含类型/大小校验；`main.py` 挂载 `/uploads` 静态目录 |
| 工单业务规则引擎 | `app/crud/ticket.py` `tickets.py` | 状态机流转校验（拒绝非法跳转如 `done→open`）+ SLA `due_at` 计算 + `is_overdue` |
| 日志/审计告警联动 | `app/core/alert_bridge.py` `audit.py` `logging_config.py` | 关键审计动作（用户删/角色变更）→ 统一告警通道；ERROR 级日志 `AlertLogHandler` 告警 |
| 自助注册 | `app/api/v1/endpoints/auth.py` `schemas/auth.py` `views/auth/Login.vue` | `POST /api/auth/register`（受 `ALLOW_SELF_REGISTER` 开关控制，固定 viewer 角色）+ 前端注册表单 |
| 缓存修复 + 推广 | `app/core/cache.py` | 修复 `cache_json` 签名保留 bug（否则 Request 注入失败）；dashboard 三端点缓存；`invalidate_prefix()` 失效工具 |
| 数据字典/API 文档 | `backend/deploy/sql/010~012` `api_endpoints.md` | 27 表数据字典、ER 图、权限矩阵、100 端点清单（反射生成） |
| 索引/时序优化 | `backend/deploy/sql/009_index_optimization.sql` `013_timeseries_optimization.sql` | 高频查询复合索引 + TimescaleDB 超表/压缩/连续聚合 |
| 种子数据 | `seed_admin.py`（重写幂等三角色） `seed_demo.py`（新建演示数据） | 一键初始化账号与演示环境 |
| 运维文档 | `deploy/backup.sh`（新建） `deploy/README.md` `redis_backup.md` `cache_strategy.md` | 备份自动化+告警、迁移策略、Redis 持久化、缓存策略 |

### v0.8 — 代码工程化 (2026-08)

| 模块 | 文件 | 功能 |
|------|------|------|
| **Type 系统统一** | `frontend/src/types/index.ts` `stores/modules/alarms.ts` `engine/realtimeLinkage.ts` | 告警类型字段重命名 (lv→level / sys→system / desc→message / state→status / ts→time)，消除 86+ vue-tsc 类型错误，`vue-tsc --noEmit` 零错误通过 |
| **OpenAPI 代码生成** | `frontend/openapi.json` `orval.config.js` `src/api/generated/index.ts` `src/api/generatedWrapper.ts` | 后端 API 契约 (29 端点 / 9 Schema) → orval 自动生成 1604 行 TypeScript 客户端，含 axios 桥接层 (`import { api } from '@/api/generatedWrapper'`) |
| **组件库化** | `packages/dc-ioc-ui/` | StatusBadge / AlarmBadge / KpiCard 抽取为独立内部 npm 包 `@dc-ioc/ui`，Vite library mode 构建 (ESM + UMD + CSS)，24 个引用文件批量迁移，自包含样式 (零外部 class 依赖) |
| **Pre-commit 检查** | `frontend/scripts/check-templates.mjs` `.husky/pre-commit` | 提交前自动扫描 Vue SFC 模板语法 (多行 @click/@change 等)，从根源预防 CI 构建失败 |
| **Docker HMR 修复** | `frontend/Dockerfile` `deploy/docker-compose.dev.yml` | Vite `--poll` 轮询模式解决 WSL2/Docker 卷挂载 inotify 不触发问题，`.vite` 缓存卷持久化，前后端热重载配置完整 |

### v0.9 — 物模型 / 3D 数字孪生 / 多数据中心 (2026-08)

| 模块 | 文件 | 功能 |
|------|------|------|
| **物模型后端** | `models/thing_model.py` `schemas/thing_model.py` `crud/thing_model.py` `api/v1/endpoints/thing_model.py` | `thing_models` + `thing_model_items`（type 区分 property/service/event）双表；CRUD 接管原只读 `GET /thing-models`；写操作 `require_role("admin")` |
| **物模型编辑器** | `frontend/src/views/ops/ThingModelEditor.vue` `api/thingModel.ts` | 三栏布局（列表 / 属性·服务·事件 Tab 表单 / 实时 JSON 预览）；保存前校验 key 唯一性、必填、标识符格式与重复 |
| **3D 数字孪生** | `frontend/src/views/twin/Twin3D.vue` `api/twin.ts` | three.js 机房场景，按 location 分层（机房→机柜→设备）；OrbitControls 旋转/缩放；分层显隐开关；每 8s 轮询实时染色（在线青 / 离线灰 / 高温红）；点击设备信息卡；卸载 `dispose` 防泄漏 |
| **多数据中心后端** | `models/idc.py`（扩展 `capacity_kw`/`description`/`is_current`）`models/external.py`（`idc_id` 软关联）`crud/idc.py` `api/v1/endpoints/idc.py` | IDC CRUD + `set_current`（全局唯一当前中心）+ `compare`（按 `idc_id` 聚合设备/在线/告警）+ `unified_alarms`（告警映射回归属中心） |
| **多数据中心前端** | `views/ops/DataCenterManage.vue` `DataCenterCompare.vue` `stores/datacenter.ts` `api/idc.ts` | 中心卡片网格增改删/启停/设为当前（`PUT /api/idc/current` 全局生效）；跨中心对比 KPI 卡 + 电力/制冷/告警柱状图 + 统一告警视图 |
| **CI 修复** | `.github/workflows/ci.yml` `frontend/Dockerfile` | `npm ci` 同步 `package-lock.json`（含 three）；Docker 前端构建显式 `--file frontend/Dockerfile`；复用已入库 `@dc-ioc-ui/dist` 避免 vite 清空 `.d.ts` 导致 TS7016 |

### v0.10 — 多模型 AI / iHealth 报告 / 运维页面优化 (2026-08)

| 模块 | 文件 | 功能 |
|------|------|------|
| **AI 多模型注册表** | `backend/app/services/assistant_service.py` `api/v1/endpoints/assistant.py` | 模块级模型注册表 `_MODEL_REGISTRY` + 激活状态 `_ACTIVE_MODEL`；`LLM_MODELS` 环境变量覆盖默认列表；`get_models` / `set_active_model` / `check_model_status`；`_llm_config` 读取当前激活模型 |
| **模型切换端点** | `backend/app/api/v1/endpoints/assistant.py` | `GET /api/ops/assistant/models`、`POST /api/ops/assistant/models/select` (`require_role admin/operator`)、`GET /api/ops/assistant/models/status` |
| **模型选择前端** | `frontend/src/views/ops/Assistant.vue` `api/index.ts` `types/index.ts` | 模型下拉框 + 切换激活模型 + 当前模型诊断；新增 `getAssistantModels` / `selectAssistantModel` / `assistantModelStatus` 与 `AssistantModel` 类型 |
| **iHealth 健康报告** | `frontend/src/views/ops/HealthReport.vue` | 新增月度健康报告页 (`/ops/health-report`)：聚合供配电/制冷/网络/隐患/演练/供应商/维修 7 大域评分 → 总分/等级/环形图；关键发现与改进建议；数据取自各模块 localStorage（隐患/供应商/演练/维修）按权重聚合 |
| **i18n 补全** | `frontend/src/i18n/locales/zh-CN.json` `en-US.json` | 新增 `healthReport` 段（标题/域/说明/建议等 30+ 键）与 `assistant` 模型相关键 |
| **运维页面美化** | 生命周期 / 供配电 AI 隐患 / 供应商管理 / 应急演练 / 故障影响分析 / 维保日历 / 集成验证中心 | 统一暗色科技风卡片、栅格与配色；ITIL 流程 SVG 渲染修复 |
| **链路图布局优化** | `frontend/src/components/power/PowerLinkageDiagram.vue` `views/monitor/PowerLinkage.vue` `components/hvac/CoolingLinkageDiagram.vue` `views/monitor/HvacLinkage.vue` | 配电链路增大 viewBox / 层间 Y 间距 / 层内 gap，收紧组框 padding，消除组件堆叠；制冷链路放大容器并改保守 gap 公式，确保设备完整显示在边界内 |
| **HealthReport 运行时防护** | `frontend/src/views/ops/HealthReport.vue` | `generate()` 中 i18n 取值统一经 `s()` 安全包装，缺失翻译时回退空串，避免 `Cannot read properties of undefined (reading 'replace')` 导致面板崩溃 |

> 部署提示：改后端 `.py` 后若用 `uvicorn --reload` 已挂载则自动重载（必要时 `docker restart dc-ioc-platform-backend-1`）；改 `.env` 的 `LLM_*` 后必须**重建**后端容器而非 `restart`。前端改源码后在 Docker 挂载下 HMR 不生效，需清 `.vite` 缓存并 `restart` 前端容器 + 浏览器硬刷新。
>
> 大模型相关环境变量（`LLM_API_KEY` 等）见「七、环境变量 → AI 运维助手大模型接入」。

### v0.11 — 侧边导航重组 / 图标补全 / 原生弹窗收敛 (2026-08)

| 模块 | 文件 | 功能 |
|------|------|------|
| **侧边栏 9 组重组** | `frontend/src/layouts/DefaultLayout.vue` | 一级分组由 6 组按业务域拆细为 **9 组**（总览 / 设施监控 / 告警 / 运维作业 / 资产 / 能效 / 知识与 AI / 平台集成 / 系统管理）；原 20+ 项的「运维作业管理」按职能拆开，告警、能效、知识 AI、平台集成各自独立成组；数字可视并入设施监控。详见「三、3.0 侧边导航结构」 |
| **分组可折叠** | `layouts/DefaultLayout.vue` | 组标题由静态 `div` 改为可点击 `button`，带 `ChevronDown`/`ChevronRight` 箭头与 `:aria-expanded`；子项由 `v-show` 控制（默认全展开）；`watch(route.path)` 自动展开当前页所属分组。`NavGroup` 新增稳定 `id` 字段，折叠态按 `id` 记忆，中英切换不丢失 |
| **图标体系补全** | `components/layout/NavIcon.vue` | 补齐 `ChevronDown`/`ChevronRight` 折叠箭头，以及此前**静默回退成通用圆圈**的 13 个图标（`Boxes`/`Box`/`Monitor`/`Settings2`/`GitBranch`/`GitCompare`/`Smartphone`/`CalendarDays`/`LogIn`/`Workflow`/`Blocks`/`Building2`/`Users`）；菜单用到的 55 个图标现已 0 缺失 |
| **i18n 分组键** | `i18n/locales/zh-CN.json` `en-US.json` | 新增 `alarmGroup` / `energyGroup` / `knowledgeAi` / `platformIntegration` 四个分组标题键（中英同步） |
| **原生弹窗收敛收口** | `views/ops/FaultImpact.vue` `views/ops/TenantManage.vue` | 补齐 D21 改造遗留的声明缺失：`FaultImpact` 补 `const toast = useToast()`（保存 / 会签 / 推送结果反馈），`TenantManage` 补 `import { useConfirm } from '@/hooks/useConfirm'`（删除二次确认）。此前两处会在用户点击时抛 `toast / useConfirm is not defined` **运行时异常** |
| **pre-commit 钩子修复** | `frontend/.husky/pre-commit` `frontend/package.json` | husky 此前**从未激活**（`core.hooksPath` 为空）：`package.json` 在 `frontend/` 而 git 根在上一级，husky 按 cwd 写出的路径 git 无法解析，且 `prepare` 的 `\|\| true` 把失败静默吞掉，导致模板语法/lint 问题只能等 CI 暴露。现改为 `cd .. && husky frontend/.husky`，并让钩子先 `cd frontend`（git 一律从工作区根执行钩子） |

> **校验结果**：菜单引用的 72 个 i18n 键中英 **0 缺失**；**63 条路由 ↔ 63 个菜单项** 一一对应（0 孤儿页 / 0 死链）；`vue-tsc --noEmit` **0 错误**（修复前 6 个）。
>
> **扩展约定**：新增页面需**同时**在 `router/index.ts` 注册路由、在 `DefaultLayout.vue` 的 `nav` 登记入口、
> 并确认所用图标已存在于 `NavIcon.vue` 的 `ICONS` 映射（缺失会静默回退为通用圆圈图标）。
>
> **部署提示**：前端改 `.vue`/`.ts` 后在 Docker 挂载下 HMR 不生效，需
> `docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite` →
> `docker restart dc-ioc-platform-frontend-1` → 浏览器硬刷新 (Ctrl+Shift+R)。

### v0.12 — 统一图形编辑入口 / 告警触达中心 / 告警自动建单 / 上架模拟器 / 全项目体检 (2026-09)

| 模块 | 文件 | 功能 |
|------|------|------|
| **统一图形编辑入口** | `backend/app/models/graphic_config.py` `crud/graphic_editor.py` `schemas/graphic_editor.py` `api/v1/endpoints/graphic_editor.py` `alembic/versions/0011_graphic_editor.py`；`frontend/src/composables/useGraphicEditor.ts` `components/common/GraphicEditDrawer.vue` | 按 kind 存一份 JSON「场景覆盖层」（改名/坐标/参数=覆盖，removed=删除，新 id=自建节点），12 个图形页（冷源工艺/制冷链路/温度云图/10KV/0.4KV/柴发/储油/电池组/配电链路/门禁/周界/消防）通过「编辑」按钮增删改图形内容；未编辑时渲染与原版逐像素一致；后端不可达落 localStorage 并显式标注 |
| **统一告警触达中心** | `models/notification.py` `crud/notification.py` `schemas/notification.py` `services/notification_service.py` `api/v1/endpoints/notification.py` `alembic/versions/0012_notification.py`；`views/ops/NotificationCenter.vue` | 通道配置落库（dingtalk/email/wechat/sms/custom + 最低级别路由 + 静默窗口 + 启停）；同告警+通道 10 分钟去重；失败退避重试 ≤2；每次触达留痕（sent/failed/muted/dedup）；注册为告警引擎第 4 个 notify_handler（与 WS 广播、env Webhook 并存）；前端 `/ops/notifications` 通道管理 + 发送记录 + 测试发送 |
| **告警→工单自动化** | `services/alarm_ticket_bridge.py` `crud/ticket.py` `api/v1/endpoints/tickets.py`；`views/ops/Alarms.vue` `views/ops/Tickets.vue` | 级别 ≥ `ALARM_AUTO_TICKET_MIN_LEVEL`（默认 crit）的告警自动建单（`source=auto-alarm`、SLA crit=1h/warn=4h/info=8h、同告警未关单幂等跳过、建单即确认）；工单进入终态自动回写 `resolve_alarm`；`GET /tickets/by-alarm/{id}` 与 source 过滤；前端告警行「已建单 WO-xxx」徽标 + 工单来源标识（告警自动/告警转单/手工） |
| **上架模拟器** | `services/capacity_whatif.py` `api/v1/endpoints/ops.py`（`POST /capacity/what-if`、`GET /capacity/what-if/baseline`）；`views/ops/CapacityWhatIf.vue` | 给定新增机柜数与单柜功率，推演电力/制冷/空间/U 位四维余量与 85%/100% 到达月份（复用 `capacity_forecast` 年度增长率），输出瓶颈排序与处置建议；滑块 debounce 自动推演 + 双层对比条 + 瓶颈高亮 |
| **加油记录真实 CRUD** | `models/refuel_record.py` `api/v1/endpoints/graphic_editor.py`（refuel-records 路由）`views/ops/PowerFuel.vue` | `refuel_record` 表 + `/api/ops/refuel-records` CRUD，替换前端 computed 生成的假数据；接口不可用时回退本地示例并显式标注 |
| **全项目体检** | `scripts/check_i18n_keys.py` `tests/conftest.py` `tests/test_*.py`（6 份）+ 16 个后端文件 + 多个前端页面 | ① i18n 键对齐审计脚本（`--json`/CI 门禁，zh=en=2960 键 0 缺失）；② pytest 基线 41 用例全绿（通知中心/工单桥/What-if/图形编辑/租户与审计，SQLite+依赖覆盖模式）；③ 后端 16 文件裸 `except` 补 logger（单次性 warning / 高频 debug，零控制流变化）；④ 前端空 catch 与 `console.log` 清零；⑤ 多源页统一 `useAsyncPageAll`+`ErrorBanner`、分页筛选复位、写操作 `toErrorMessage` 归一；⑥ **修复 `crud/tenant.py` 真缺陷**：`_to_snake` 盲转导致 camelCase 字段建单 `TypeError`（改为按模型列名映射）；⑦ Alembic 与 lifespan 自愈一致性核对（新增 0011/0012，漂移列补齐） |

> **部署提示**：本次新增 `alembic/versions/0011_graphic_editor.py` 与 `0012_notification.py`（graphic_config / refuel_record / notification_channel / notification_record 四表，均幂等可回滚）。升级存量环境执行 `alembic upgrade head`；全新环境由 lifespan `create_all` 自动建表。其余前后端热重载/清缓存事项同 v0.11 部署提示。

### API 域汇总（附录）

后端统一挂载于 `/api`，共 28 个业务域 + 认证。主要分组：

| 分组 | 典型端点 |
|------|----------|
| 认证 `auth` | `POST /api/auth/login`、`/refresh`、`/change-password`、`/users`、`/register`（v0.7 新增，受 `ALLOW_SELF_REGISTER` 控制） |
| 驾驶舱 `dashboard` | `GET /api/dashboard/overview`、`/campuses`、`/campus-comparison`、`/overview/trends`（均缓存 30s） |
| 设备台账 `equipment` | 11 个域 CRUD（冷机/空调末端/配电/机柜/柴发/消防/动环/安防等） |
| 暖通 `hvac` / 电力 `power` | 冷源/空调末端/液冷、10KV/0.4KV/柴发/燃油/电池 |
| 安防消防 `security` | 视频监控/门禁/消防报警主机/探测器/联动设备 |
| 运维作业 `ops` | 设备资产、维保计划、采集器接入、设备遥测 |
| 告警 `alarms` / `alarm_history` / `alarm_rules` | 告警中心、历史、规则引擎 |
| 工单 `tickets` | 事件工单 CRUD + 状态机流转（`done→open` 等非法跳转被拒，返回 400） |
| 巡检/维保/排班/演练/风险/知识库 | 运维全流程管理 |
| 预案 `runbooks`（v0.7 新增） | `GET /api/runbooks/related`（告警关联处置预案，对齐前端 `Alarms.vue`） |
| 审计 `audit`（v0.7 确认） | `GET /api/audit-logs`（分页/过滤/CSV 导出，前端 `AuditLogs.vue` 已对接） |
| 上传 `uploads`（v0.7 新增） | `POST /api/uploads/avatar` / `/attachment` / `/batch`（类型/大小校验） |
| 网络 `network` / 域名 `domain` | 交换机/路由/防火墙/无线、域名路由监控 |
| 外部接入 `external` | 采集器注册/测点上报/告警评估（独立 `X-Collector-Token` 鉴权） |
| 物模型 `thing-models` (v0.9) | `GET/POST/PUT/DELETE /api/thing-models`（property/service/event 三要素，接管只读出口） |
| 多数据中心 `idc` (v0.9) | `GET/POST/PUT/DELETE /api/idc`、`GET/PUT /api/idc/current`、`GET /api/idc/compare`、`GET /api/idc/alarms` |
| AI 助手 `assistant` | 知识库问答 + 多模型端点 `/api/ops/assistant/models*` + NIM 诊断端点 `/api/ops/assistant/status` |
| 图形编辑/加油记录 `graphic_editor` (v0.12) | `GET/PUT/DELETE /api/ops/graphic-config/{kind}`（场景覆盖层）、`GET/POST/PUT/DELETE /api/ops/refuel-records` |
| 通知中心 `notifications` (v0.12) | `GET/POST/PUT/DELETE /api/ops/notifications/channels`、`GET /api/ops/notifications/records`、`POST /api/ops/notifications/test` |
| 上架模拟器 `ops` (v0.12) | `POST /api/ops/capacity/what-if`、`GET /api/ops/capacity/what-if/baseline` |

> 完整端点清单（含方法/路径/鉴权）见 `backend/api_endpoints.md`（由 `gen_api.py` 静态反射生成）。

---

## 五、快速开始

### 方式 A: Docker Compose (推荐, 一键启动全部服务)

```bash
# 开发环境 (热重载 + Prometheus + 前端 dev server)
docker compose -f docker-compose.yml -f deploy/docker-compose.dev.yml up -d --build

# 或双击 Windows 脚本
start.bat
```

启动后访问:
| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080 (生产) / http://localhost:5173 (开发) |
| 后端 API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (staging/prod) |
| 默认登录 | `admin` / `admin123` |

### 方式 B: 本地开发 (不依赖 Docker)

**1. 启动数据库**
```bash
cd deploy
docker compose up -d postgres redis
```

**2. 启动后端**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.dev .env                                # 开发环境
uvicorn app.main:app --reload --port 8000
```

**3. 启动前端**
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### 方式 C: 预发/生产部署

```bash
# 1. 注入安全凭据
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -hex 16)
export EXTERNAL_COLLECTOR_TOKEN=$(openssl rand -hex 32)

# 2. 启动预发环境
docker compose -f docker-compose.yml -f deploy/docker-compose.staging.yml up -d

# 3. 启动生产环境
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d
```

---

## 六、关键依赖说明

### 后端 `requirements.txt`

| 分类 | 包 | 用途 |
|------|-----|------|
| Web 框架 | `fastapi` `uvicorn` | 异步 API 服务 |
| 数据库 | `sqlalchemy` `psycopg[binary]` `alembic` | ORM + PG 驱动 + 迁移 |
| 认证 | `python-jose[cryptography]` `passlib[bcrypt]` | JWT 签发/验证 |
| 缓存 | `redis` | 响应缓存 / 遥测最新值 |
| 实时 | `websockets` | WebSocket 推送 |
| 采集 | `aiokafka` | Kafka 消费端 |
| 任务 | `celery` `apscheduler` | 异步任务 / 定时 |
| 文档 | `pymupdf` `pdfplumber` `python-docx` | PDF/Word 文档解析 (知识库导入) |
| 监控 | `prometheus-fastapi-instrumentator` `prometheus-client` | Prometheus 指标导出 |
| 日志 | `loguru` | 结构化日志 |
| 工具 | `httpx` `python-dotenv` `orjson` | HTTP 客户端 / 环境变量 / JSON |
| 测试 | `pytest` `pytest-asyncio` `ruff` | 测试 / 代码质量 |

### 前端 `package.json`

| 包 | 用途 |
|------|------|
| `vue` `vue-router` `pinia` | 框架三件套 |
| `echarts` | IOC 可视化图表 |
| `axios` | HTTP 客户端 |
| `lucide-vue-next` | SVG 图标库 |
| `dayjs` | 日期处理 |
| `three` | 3D 数字孪生拓扑 (机房级 three.js 场景) |
| `@dc-ioc/ui` | 共享 UI 组件库 (StatusBadge / AlarmBadge / KpiCard) |
| `vite` `vue-tsc` `typescript` | 构建与类型 |
| `orval` | OpenAPI → TypeScript 代码生成 (devDep) |
| `sass` | 样式预处理 |

---

## 七、环境变量

| 文件 | 用途 | 环境 |
|------|------|------|
| `backend/.env.example` | 环境变量模板 (所有可用配置) | — |
| `backend/.env.dev` | 开发: debug + mock + 8h token | dev |
| `backend/.env.staging` | 预发: 凭据外部注入 + 保留 mock | staging |
| `backend/.env.prod` | 生产: 全部凭据外部注入 + mock 关闭 | prod |

**安全约定:**
- `.env*` 已在 `.gitignore` 排除 (仅 `.env.example` 提交仓库)
- 生产环境 `SECRET_KEY` 必须 ≥32 字符随机密钥
- 生产环境 `EXTERNAL_COLLECTOR_TOKEN` 必填 (外部采集器认证)
- 启动时 `secret_check.py` 自动校验, 不通过则抛出 `RuntimeError` 阻止启动

### 新增配置项 (v0.7)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ALLOW_SELF_REGISTER` | 是否开放自助注册 (`POST /api/auth/register`)；开启后注册账号固定为 `viewer` 只读角色 | `false` |
| `UPLOAD_DIR` | 通用上传文件保存根目录 (`/api/uploads/*`) | `backend/uploads/` |
| `UPLOAD_MAX_BYTES` | 单文件上传大小上限（字节） | `10485760` (10MB) |
| `BACKUP_DIR` | `deploy/backup.sh` 备份输出目录 | `./backups` |
| `RETENTION_DAYS` | `deploy/backup.sh` 备份保留天数 | `14` |
| `BACKUP_ALERT_WEBHOOK` | 备份成功/失败告警 webhook（可选） | 空 |

> 缓存 TTL、连续聚合刷新周期等以代码内常量为准（dashboard 缓存 30s；详见 `deploy/cache_strategy.md`）。

### AI 运维助手大模型接入 (`LLM_API_KEY` 等)

`/ops/assistant` 的 AI 运维助手默认走**本地知识库检索生成** (无需任何外部依赖)；配置以下
环境变量后可启用**大模型自然语言润色** (`assistant_service._call_llm` 基于标准库 `urllib`
调用 OpenAI 兼容的 `/chat/completions` 接口，任何异常自动回退检索生成，保证离线可用)。

**多模型支持 (v0.10 新增)：** 后端维护模型注册表与「当前激活模型」状态，支持运行时切换——
无需重启即可在多个免费/授权模型间热切换。前端 `Assistant.vue` 提供模型下拉框，可查看可用模型、
一键切换激活模型、并对当前模型做连通性诊断。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ops/assistant/models` | GET | 返回可用模型列表（含 id / name / 是否激活） |
| `/api/ops/assistant/models/select` | POST | 切换当前激活模型 (`{ "model": "<id>" }`，`require_role admin/operator`) |
| `/api/ops/assistant/models/status` | GET | 探测当前激活模型 `/chat/completions` 真实连通性与错误体 |
| `/api/ops/assistant/status` | GET | 诊断端点（v0.9 既有，直接探测 chat/completions 避免误报） |

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | 大模型 API Key (`Authorization: Bearer <key>`)，留空则不启用大模型 | 空 |
| `LLM_BASE_URL` | OpenAI 兼容接口 Base URL (代码自动拼接 `/chat/completions`) | `https://api.openai.com/v1` |
| `LLM_MODEL` | 默认激活模型（被 `LLM_MODELS` 覆盖时取列表首项） | `gpt-4o-mini` |
| `LLM_MODELS` | 逗号分隔的可用模型 id 列表，注入模型注册表；留空则回退默认单模型 | 空 |

支持任意 OpenAI 兼容端点（OpenAI / 通义 / 本地 vLLM 等）。当前开发环境默认接入**英伟达 NIM**:

```bash
# 根目录 .env (被 deploy/docker-compose.dev.yml 经 ${LLM_API_KEY:-} 等插值读取)
LLM_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.1-8b-instruct
LLM_MODELS=meta/llama-3.1-8b-instruct,nvidia/llama-3.3-70b-instruct,nvidia/nemotron-mini-4b-instruct,nvidia/nemotron-super-49b-instruct,openai/gpt-oss-120b,openai/gpt-oss-20b,zai-ai/glm-5.2,minimax/minimax-m3,stepfun/step-3.7-flash
```

> 修改 `.env` 后需**重建后端容器** (`docker compose -f docker-compose.yml -f deploy/docker-compose.dev.yml up -d backend`) 才能生效——环境变量在容器启动时注入，`docker compose restart` **不会**重新读取 `.env`。NIM 端点没有 `gpt-4o-mini`，`LLM_MODEL` 必须填 NVIDIA 托管的模型 id。注意：**并非列表里所有模型都能调用**——部分 `nvidia/*` 大模型（如 `nvidia/llama-3.1-nemotron-70b-instruct`）对当前 API Key 账号未授权，会返回 `404 Function '...' not found for account`。可用 `meta/llama-3.1-8b-instruct` 等已授权模型；若要用 70B 等大模型，需换用具备相应授权的 Key/账号，或用 `/api/ops/assistant/models/status` 一键自查。

---

## 八、数据库备份与恢复

```bash
# 备份 (全量 pg_dump + gzip 压缩 + 保留 14 天 + 文件校验 + 可选 webhook 告警)
# 脚本位于根 deploy/ 目录
cd deploy
chmod +x backup.sh
./backup.sh

# 恢复 (使用 PostgreSQL 自带 pg_restore / psql 还原 dump)
# 示例: 解压后还原
# gunzip -c backups/dc_ioc_YYYYMMDD_HHMMSS.sql.gz | psql "$DATABASE_URL"

# 定时备份 (crontab: 每天凌晨 2 点)
# 0 2 * * * /path/to/deploy/backup.sh >> /var/log/dc-ioc-backup.log 2>&1

# 可选环境变量: BACKUP_DIR / RETENTION_DAYS / BACKUP_ALERT_WEBHOOK
# 备份成功后通过 BACKUP_ALERT_WEBHOOK (JSON POST) 上报成功/失败
```

> 注：根 `deploy/scripts/restore.sh` 亦可用（并行恢复 + 自动重建）；`deploy/backup.sh` 为 v0.7 新增的轻量备份脚本（含告警钩子），两者择一即可。详见 `deploy/README.md`。

---

## 九、压测

```bash
cd tests/load
pip install -r requirements.txt

# 带 Web UI
locust -f locustfile.py --host=http://localhost:8000

# 无 UI 模式 (CI 用)
locust -f locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m --headless --html=report.html
```

---

## 十、常用运维命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 重启服务
docker compose restart backend

# 前端改源码后清除 Vite 缓存 (HMR 在 Docker 挂载下不生效时)
docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite
docker restart dc-ioc-platform-frontend-1

# 修改 @dc-ioc/ui 组件后重新构建 (Docker 会自动挂载 dist/)
cd packages/dc-ioc-ui && npm run build

# 重新生成 API 客户端 (openapi.json 有变更时)
cd frontend && npm run generate:api

# 重置全部数据 (⚠ 危险)
docker compose down -v
docker compose up -d --build

# Prometheus 配置热重载
curl -X POST http://localhost:9090/-/reload
```

---

## 十一、架构图 (数据流总览)

```
┌────────────────────────────────────────────────────────────────┐
│                       外部采集层                                │
│  MockCollector ─┐                                              │
│  Kafka Consumer ─┤── HTTP /api/external/* ──→ 告警引擎评估      │
│  真实 DCIM/BMS ─┘                                              │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              metric_raws (TimescaleDB Hypertable)                │
│  7天压缩 · 90天保留 · 5min/1h 连续聚合                           │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    dc_aggregator.py (35 个聚合函数)               │
│  真实链路优先 → 回退生成器 → _source 标记                         │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       ▼          ▼          ▼          ▼          ▼
   dashboard   hvac      power    security     ops
   (驾驶舱)  (暖通6页)  (电力7页)  (安防5页)  (运维32页)
       │     冷源/末端/液冷 10KV/0.4KV/柴发 CCTV/ACS/IDS/火警
       │     /制冷链路/温度云图 /配电链路/燃油/电池
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   实时推送层                                      │
│  ws_broadcaster ←── KPI 快照 (5s) ──→ WebSocket ──→ 所有客户端   │
│                  ←── 告警通知 ───────────────────────────────────→│
└──────────────────────────────────────────────────────────────────┘

                   认证层
┌──────────────────────────────────────────────────────────────────┐
│  POST /api/auth/login → JWT (Bearer) → RBAC (admin/op/viewer)   │
│  401 自动刷新 · 令牌持久化 · 路由守卫                              │
└──────────────────────────────────────────────────────────────────┘

                   监控层 (v0.3)
┌──────────────────────────────────────────────────────────────────┐
│  /metrics (Prometheus) ← HTTP/QPS/Latency/WS/Alarm/KPI         │
│  logs/ (Loki+Promtail) ← JSON 结构化日志 (30d)                   │
│  /health /ready ← K8s liveness/readiness probe                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 十二、冷源与液冷设计说明

### 冷源系统 (Chiller Plant)

采用 **8台冷机 (4+2+N) 架构**，单台制冷量 3500kW (≈1000RT)，总装机 **28MW**。

| 设备 | 数量 | 运行 | 备用/待机 | 检修 | 冗余模式 |
|---|---|---|---|---|---|
| 离心式冷水机组 | 8 | 4 | 3 | 1 | N+2 |
| 冷却塔 | 8 | 5 | 2 | 1 | N+3 |
| 冷冻水泵 | 8 | 5 | 2 | 1 | N+2 |
| 冷却水泵 | 8 | 5 | 2 | 1 | N+2 |
| 二次泵 | 6 | 4 | 2 | 0 | N+2 |
| 板式换热器 | 4 | 3 | 1 | 0 | N+1 |
| 电动阀 | 8 | — | — | — | — |
| 蓄冷罐 | 1 | — | — | — | 6000m³ / 20min 保冷 |

**三级自然冷切换：** 制冷模式 → 预冷模式 → 自然冷却模式（基于室外湿球温度和进出水温差自动决策）

### 液冷系统 (Liquid Cooling)

面向智算中心 GPU 集群 (H800/H100/A800)，冷却架构：

```
一次侧中温水 32/38℃ → CDU 板换 → 二次侧洁净冷却液 35/45℃ → 冷板直触 GPU
```

| 层级 | 设备 | 数量 | 备注 |
|---|---|---|---|
| 一次侧 | CDU 冷却液分配单元 | 4台 | N+1 冗余，板换效率 92-94% |
| 二次侧 | 机柜级 CDU | 8台 | 按 A/B/C/D 区分区 (GPU训练/推理集群) |
| 终端 | 冷板 Cold Plate | 384路 | 每机柜 8 GPU 独立温度监测 |
| 管路 | 分/集液 Manifold | 8路 (4供+4回) | 双路冗余 |
| 排热 | 闭式冷却塔 + 干冷器 | 4+2台 | 自然冷覆盖率 >50% |
| 安全 | 漏液检测 | 128传感器 (绳式+点式) | 30s 响应自动关阀 |
| 节能 | 余热回收 | 1.2MW | 园区供暖，年减碳3200吨 |

**PUE 贡献：** 液冷对 PUE 贡献仅 0.06，配合自然冷可将整体 PUE 从 1.4 降至 1.1 以下。
