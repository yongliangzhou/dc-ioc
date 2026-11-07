# ADR-0005: 引入 CMDB 关系层与四阶段升级路线

- 状态: 已接受
- 日期: 2026-11-08
- 决策者: 平台架构

## 背景

对同类开源项目（NetBox、Ralph、RackTables、openDCIM、idcops、蓝鲸 bk-CMDB、veops/cmdb、iTop、Snipe-IT、GLPI）横向对比后确认：

- 本项目在**设施监控深度**（液冷/柴发/温云图/3D 孪生）、**实时闭环**（告警引擎 → 通知 → 自动建单）、**工程化**（CI/三环境/监控/压测）上明显领先，应作为差异化保持；
- 但缺少同类系统的三项底座能力：**CI 之间的关系建模**（NetBox/iTop/蓝鲸的核心价值）、**IPAM**（NetBox/RackTables 标配）、**自动发现**（GLPI/veops 让台账自己长出来）；
- 资产侧还缺商业属性（采购/合同/保修到期）与动态字段（不同机房台账字段不一致）；
- 工程侧存在具体债：`frontend/openapi.json` 只覆盖 29/100+ 端点、41 个后端用例对 28 个域偏薄、65 条路由零 E2E、新增页面要改两处硬编码、多租户只做配额未做行级隔离。

## 决策

**不自研替代，也不整机引入**：保留 FastAPI + Vue3 主体，按四个阶段渐进补齐能力（完整任务/文件/验收见 `docs/IMPLEMENTATION_PLAN.md`）：

| 阶段 | 版本 | 决策要点 |
|---|---|---|
| P1 | v0.13 | 文档体系（英文 README / CHANGELOG / CONTRIBUTING / 5 篇 ADR）、CI 覆盖率门禁、独立 Playwright E2E 包 |
| P2 | v0.14 | 全量 OpenAPI 契约 + 契约漂移门禁；新增 `ci_relation` 关系层；`FaultImpact` 在既有 `twin_graph` BFS 上**叠加**真实关系链 |
| P3 | v0.15 | IPAM；TCP 探测式自动发现（结果只进「待确认区」）；采购合同/盘点；设备自定义字段 |
| P4 | v0.16 | 插件清单注册中心；GraphQL 只读出口；`tenant_id` 行级隔离（ORM 全局过滤 + 显式豁免）；仪表盘可配置 |

关系层的关键取舍：

- CI 标识采用**字符串** `source_ci` / `target_ci`（如 `equipment:123`、`cabinet:A01`、`external:dev-9`），不建跨表外键——兼容现有设备台账/机柜/外部设备三套 ID 体系，避免一次性重构。
- 关系类型限定枚举：`connects_to` / `powers` / `cools` / `depends_on` / `hosts`；影响分析为有环保护的有向 BFS，深度上限 6。
- 影响分析**向后兼容**：新增 `topologySource` / `realRelations` 字段，未建任何关系时输出与改造前完全一致。
- 所有新表预留可空 `tenant_id`，但 P4 之前**不做过滤**（避免半成品隔离破坏现有功能）。

## 备选方案

| 方案 | 优点 | 否决原因 |
|---|---|---|
| 直接部署 NetBox 作为 CMDB，本项目只做监控 | 立刻获得成熟 DCIM/IPAM/插件生态 | 两套用户体系与前端、数据割裂；设施监控与告警闭环无法复用；运维成本翻倍 |
| Fork django-idcops / idc_assest 继续二次开发 | 领域模型现成 | Django 技术栈与现有 FastAPI 资产不兼容，等于重写；项目维护活跃度低 |
| 引入蓝鲸 bk-CMDB | 动态建模最完整 | Go/Python/Node + MongoDB/ZK 重型生态，单机 Docker Compose 部署不现实 |
| 一次性大重构为微服务 + 统一 CMDB | 架构最「正确」 | 与 60+ 已验收页面冲突，风险集中且无法灰度；团队规模不支持 |

## 后果

### 正面
- 每个阶段可独立上线/回滚，不阻塞现有功能；对比分析得出的能力短板逐项补齐。
- 关系层为后续自动发现、IPAM 绑定、GraphQL、租户隔离提供统一锚点。
- 文档/CI/E2E 先行，为后续三个阶段提供安全网。

### 负面 / 需承担的成本
- 字符串 CI 标识无外键约束，数据质量靠应用层校验 + 后续一致性巡检（需补 `check_ci_orphans.py`）。
- 四阶段跨度长，需在每阶段结束跑完整验收并同步 `CHANGELOG.md`，否则文档会漂移。
- 新增 8+ 张表与 8 个 Alembic 修订，迁移链变长；升级存量环境必须按序 `alembic upgrade head`。
- 插件化后导航有「静态清单 + 动态清单」两个来源，必须靠 `check_nav_routes.py` 与离线兜底保证不退化为死链。

### 后续动作
- 每个阶段结束更新本 ADR 的「状态」与 `IMPLEMENTATION_PLAN.md` 的进度勾选。
- P2 完成后复评：CI 标识是否需要升级为正式的 `ci` 主表 + 外键。
