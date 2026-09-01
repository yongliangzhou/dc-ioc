# DC-IOC 平台数据库设计文档（全量深化版）

> 适用范围：覆盖 `dc-ioc-platform` 后端 `app/models/` 下已注册的 **40 张业务/配置表**，按 7 大核心业务模块划分。
> 配套基线：资产核心（idc/cabinet/server/point_data）已在 `deploy/sql/004_schema_design.md` 详述，本文在其基础上补全其余模块并统一给出 ER 描述、数据字典、建表语句与深化设计。
> 约定：类型按 PostgreSQL 表述；`VARCHAR(n)` 对应 ORM `String(n)`，`TIMESTAMPTZ` 对应 `DateTime(timezone=True)`，`TIMESTAMP` 对应无时区 `DateTime`，`JSONB` 对应 `JSON`，`DOUBLE PRECISION` 对应 `Float`。

---

## 一、核心业务模块与实体总览

| 模块 | 关注点 | 实体（表） |
|---|---|---|
| **A. 资产拓扑 (Asset/Topology)** | 数据中心—包间—机柜—设备—服务器的物理与逻辑拓扑 | `idc`, `room`, `cabinet`, `equipment`, `server` |
| **B. 采集与时序 (Ingestion/TS)** | 外部设备注册、测点定义、原始/实时时序 | `external_devices`, `metric_defs`, `metric_raws`, `point_data` |
| **C. 身份与权限 (IAM)** | 用户、角色、多对多授权 | `users`, `roles`, `user_role` |
| **D. 运维作业 (Ops Workflow)** | 工单、流程、维保、风险、演练、巡检、值班 | `ticket`, `workflow_item`, `maintenance_plan`, `maintenance_record`, `risk_item`, `drill_plan`, `drill_record`, `inspection_route`, `inspection_finding`, `inspection_robot`, `shift_schedule`, `shift_handover` |
| **E. 告警与事件 (Alarm)** | 告警生命周期、规则、活跃态、抑制、处理反馈 | `alarm_event`, `alarm_rule`, `alarm_active_state`, `alarm_suppressed_device`, `alarm_feedback` |
| **F. 知识 / AI / 能效 (Intelligence)** | 知识库、AI 反馈、影响分析、节能采纳、容量能耗、KPI、快控、物模型 | `knowledge_item`, `assistant_feedback`, `analysis_history`, `energy_advice_adopt`, `capacity_energy_history`, `kpi_history`, `control_log`, `thing_model`, `thing_model_item` |
| **G. 租户与运营 (Tenant/Biz)** | 租户配额与用量 | `tenant` |
| **H. 审计 (Audit)** | 全量操作留痕 | `audit_logs` |

**总计 40 张表**（含 1 张多对多关联表 `user_role`、1 张 JSON/文本态表 `alarm_active_state`）。

---

## 二、设计原则与现状基线（重要）

梳理现有 `app/models` 后，识别出以下**已落地现状**与**待深化设计债**，本节结论贯穿全文并在第八章给出整改方案。

1. **审计字段三类并存（不一致）**
   - **类型一 `TimestampMixin`（规范）**：`idc / room / cabinet / equipment / server / external_devices / metric_defs` 使用 `created_at/updated_at` 为 `TIMESTAMPTZ`，`server_default=now()`。
   - **类型二 应用层 `DateTime`**：`users / alarm_rule / alarm_active_state / alarm_suppressed_device` 用 `DateTime` + `default=datetime.utcnow`（无 `server_default`，且部分为无时区）。
   - **类型三 字符串 UTC**：`workflow_item / maintenance_plan / maintenance_record / risk_item / drill_plan / drill_record / inspection_* / shift_* / tenant / knowledge_item / thing_model / thing_model_item / alarm_feedback / assistant_feedback / control_log / energy_advice_adopt / analysis_history` 用 **`VARCHAR(32)` 存 `"YYYY-MM-DD HH:MM:SS"`**（来自 `_now()`）。
   - **`created_by / updated_by` 几乎缺位**：仅 `ticket.created_by`、`analysis_history.created_by` 有；其余业务表无"创建人/更新人"列。
2. **无软删除机制**：全库**没有任何 `deleted_at / is_deleted` 列**，删除均为物理删除（硬删）。
3. **主键类型不统一**：`SERIAL INTEGER`（多数）、`VARCHAR` 业务单号（`alarm_event`=`uuid.hex`、`ticket`=`WO-...`、`workflow_item`=`INC-...`）、复合主键（`point_data`=`id BIGINT + ts`）、字符串主键（`alarm_rule`=`rule_id`、`alarm_active_state`=`key`、`alarm_suppressed_device`=`device_id`）。
4. **外键约束以"逻辑关联"为主**：仅资产拓扑树（`room/cabinet/equipment/server`）、`thing_model_item->thing_model`、`user_role` 建有真正 DB 级 `FOREIGN KEY` 与级联；其余跨表关联（如 `ticket.source_alarm_id`、`maintenance_record.plan_code`、`alarm_event.device_id`、`drill_record.plan_id` 已建 FK 但可空）多为**字符串编码，无 FK 约束**。
5. **时间类型混用**：`TIMESTAMPTZ` / `TIMESTAMP` / `VARCHAR(32)` 三者并存。
6. **反范式 JSON 合理但需治理**：`equipment.attrs`、`workflow_item.approval/logs/knowledge_links`、`tenant` 用量、`analysis_history.*`、`drill_plan.steps`(Text) 等用 JSON/Text 承载嵌套结构；高频检索字段未冗余为列。
7. **时序大表**：`point_data`、`metric_raws` 为高频写入大表，代码已注明建议 TimescaleDB hypertable / 分区（见 `003_point_data_hypertable.sql`、`005_metric_raws_hypertable.sql`）。

---

## 三、ER 图描述

### 3.1 资产拓扑树（强外键，级联删除）
```
idc (1) ──< (N) room          room.idc_id        FK → idc.id  ON DELETE CASCADE
idc (1) ──< (N) cabinet       cabinet.idc_id     FK → idc.id  ON DELETE CASCADE
idc (1) ──< (N) equipment     equipment.idc_id   FK → idc.id  ON DELETE CASCADE
room (1) ──< (N) equipment    equipment.room_id  FK → room.id ON DELETE SET NULL
cabinet (1) ──< (N) server    server.cabinet_id  FK → cabinet.id ON DELETE CASCADE
```
`point_data` 以 `(target_type, target_id)` **多态挂载** `idc / cabinet / server / env`，不强加外键（写入性能优先，应用层维护一致性）。

### 3.2 采集与时序
```
external_devices (1) ──< (N) metric_defs     metric_defs.device_id（逻辑，字符串）
external_devices (1) ──< (N) metric_raws      metric_raws.device_id（逻辑，字符串）
external_devices (1) ──< (N) alarm_event      alarm_event.device_id（逻辑，字符串）
```
说明：`external_devices.idc_id` 仅"软关联"数据中心（代码注释明确无 FK，避免迁移脆弱）。

### 3.3 身份与权限（多对多）
```
users (N) ──< user_role >── (N) roles        关联表 user_role(user_id, role_id)
```

### 3.4 运维作业
```
maintenance_plan (1) ──< (N) maintenance_record   maintenance_record.plan_code（逻辑编码）
drill_plan (1) ──< (N) drill_record               drill_record.plan_id FK → drill_plan.id（可空）
ticket (1) ──< (1) alarm_event                     ticket.source_alarm_id（逻辑，告警 id）
workflow_item / risk_item / inspection_* / shift_* 相互独立
```

### 3.5 告警与事件
```
alarm_rule (1) ──< (N) alarm_event        alarm_event.rule_id（逻辑编码）
alarm_event (1) ──< (N) alarm_feedback    alarm_feedback.alarm_id（逻辑编码）
alarm_suppressed_device (1) ──< (N) external_devices   device_id 抑制（逻辑）
alarm_active_state 为运行态快照（key=device_id:metric:level），无业务外键
```

### 3.6 知识 / AI / 能效 / 物模型
```
thing_model (1) ──< (N) thing_model_item   thing_model_item.thing_model_id FK → thing_model.id CASCADE
knowledge_item 独立（domain/category 与告警关联，逻辑）
assistant_feedback / analysis_history / energy_advice_adopt / capacity_energy_history / kpi_history / control_log 各自独立
```

### 3.7 全局 ASCII ER 总图
```
                          ┌─────────────┐
                          │     idc     │ (数据中心)
                          └──────┬──────┘
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
         ┌─────────┐       ┌──────────┐       ┌───────────┐
         │  room   │1    N │ cabinet  │1    N │ equipment │
         └────┬────┘       └────┬─────┘       └─────┬─────┘
              │room_id(SET NULL)  │1             N │
              │                  ▼                 │
              │            ┌─────────┐              │
              │            │ server  │ (cabinet_id)│
              │            └────┬────┘              │
              │                 │                  │
              └───── point_data(target_type/id) ────┘  (多态, 无FK)

   external_devices 1──N metric_defs / metric_raws / alarm_event (device_id 逻辑)

   users N──user_role──N roles

   maintenance_plan 1──N maintenance_record(plan_code)
   drill_plan 1──N drill_record(plan_id FK)
   ticket(source_alarm_id) ── alarm_event
   thing_model 1──N thing_model_item(FK)

   alarm_rule 1──N alarm_event(rule_id) ; alarm_feedback(alarm_id) ; alarm_suppressed_device
   knowledge_item / assistant_feedback / analysis_history / energy_advice_adopt /
   capacity_energy_history / kpi_history / control_log / tenant / audit_logs 各自独立
```

---

## 四、表间关系明细（外键矩阵）

### 4.1 现有 DB 级外键（真正约束）
| 子表 | 列 | 父表 | 级联 |
|---|---|---|---|
| `room` | `idc_id` | `idc.id` | CASCADE |
| `cabinet` | `idc_id` | `idc.id` | CASCADE |
| `equipment` | `idc_id` | `idc.id` | CASCADE |
| `equipment` | `room_id` | `room.id` | SET NULL |
| `server` | `cabinet_id` | `cabinet.id` | CASCADE |
| `thing_model_item` | `thing_model_id` | `thing_model.id` | CASCADE |
| `drill_record` | `plan_id` | `drill_plan.id` | （可空，无显式级联） |
| `user_role` | `user_id` / `role_id` | `users.id` / `roles.id` | CASCADE |

### 4.2 逻辑关联（无 FK 约束，建议深化补全）
| 子表 | 列 | 关联父 | 现状 |
|---|---|---|---|
| `external_devices` | `idc_id` | `idc.id` | 整数列，无 FK（注释有意省去） |
| `alarm_event` | `device_id` | `external_devices.device_id` | 字符串，无 FK |
| `alarm_event` | `rule_id` | `alarm_rule.rule_id` | 字符串，无 FK |
| `alarm_feedback` | `alarm_id` | `alarm_event.id` | 字符串，无 FK |
| `ticket` | `source_alarm_id` | `alarm_event.id` | 字符串，无 FK |
| `maintenance_record` | `plan_code` | `maintenance_plan.code` | 字符串，无 FK |
| `drill_record` | `plan_code` | `drill_plan.code` | 字符串，无 FK（与 plan_id 并存） |
| `metric_defs` / `metric_raws` | `device_id` | `external_devices.device_id` | 字符串，无 FK |

### 4.3 关系基数汇总
- **一对一**：无（无 1:1 表；`inspection_robot` 为单例配置表，非关联）。
- **一对多**：资产拓扑树、thing_model→item、maintenance_plan→record、drill_plan→record、alarm_rule→event、alarm_event→feedback、idc→external_devices（软）、users/roles 经 user_role。
- **多对多**：仅 `users ⇄ roles`（经 `user_role` 关联表）。
- **多态**：`point_data` 对 `idc/cabinet/server/env`。

## 五、数据字典（逐表）

> 列说明：`类型(长度)` / `可空` / `默认` / `约束` / 中文说明。约束标记：`PK` 主键、`U` 唯一、`IX` 索引、`FK→` 外键、`CK` 检查。

### 模块 A — 资产拓扑
#### A1 `idc` 数据中心
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | 自增主键 |
| code | VARCHAR(32) | 否 | — | U, IX | 站点编码 EC1-HZ |
| name | VARCHAR(128) | 否 | — | | 数据中心名称 |
| region | VARCHAR(64) | 否 | '' | IX | 地域/可用区 |
| address | VARCHAR(255) | 否 | '' | | 地址 |
| power_capacity_mw | NUMERIC(10,3) | 否 | 0 | | 电力容量 MW |
| cooling_capacity_mw | NUMERIC(10,3) | 否 | 0 | | 制冷容量 MW |
| rack_capacity | INTEGER | 否 | 0 | | 机柜总容量 |
| rooms | INTEGER | 否 | 0 | | 包间数量 |
| status | VARCHAR(16) | 否 | '运营' | IX | 运营/建设/下线 |
| capacity_kw | INTEGER | 否 | 0 | | 机柜额定功率 kW |
| description | VARCHAR(512) | 否 | '' | | 站点说明 |
| is_current | BOOLEAN | 否 | false | IX | 是否默认数据中心 |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计（TimestampMixin） |

#### A2 `room` 包间/功能间
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| idc_id | INTEGER | 否 | — | FK→idc.id CASCADE, IX | 所属数据中心 |
| code | VARCHAR(32) | 否 | — | | 包间编号 R01 |
| name | VARCHAR(64) | 否 | '' | | 名称 |
| kind | VARCHAR(32) | 否 | 'it_room' | IX | it_room/substation/battery_room/... |
| floor | VARCHAR(16) | 否 | '' | | 楼层 |
| rack_capacity | INTEGER | 否 | 0 | | 机柜容量 |
| cold_aisle_t / hot_aisle_t | DOUBLE PRECISION | 否 | 0 | | 冷/热通道均温 |
| rh | DOUBLE PRECISION | 否 | 0 | | 相对湿度 |
| pressure_pa | DOUBLE PRECISION | 否 | 0 | | 正压 Pa |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计 |
| 唯一约束 | | | | UQ(idc_id, code) | 同 IDC 内编码唯一 |

#### A3 `cabinet` 机柜
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| idc_id | INTEGER | 否 | — | FK→idc.id CASCADE, IX | 所属数据中心 |
| code | VARCHAR(32) | 否 | — | IX | 机柜编号 R01-A05 |
| room | VARCHAR(32) | 否 | '' | IX | 所在包间 |
| row | VARCHAR(16) | 否 | '' | | 机列 |
| u_total | INTEGER | 否 | 42 | | U 位总数 |
| u_used | INTEGER | 否 | 0 | | 已用 U 位 |
| rated_power_kw | NUMERIC(8,2) | 否 | 10.0 | | 额定功率 kW |
| current_power_kw | NUMERIC(8,2) | 否 | 0 | | 当前功率 kW |
| status | VARCHAR(16) | 否 | '在用' | IX | 在用/预留/停用 |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计 |
| 唯一/索引 | | | | UQ(idc_id, code); IX(idc_id, room) | |

#### A4 `equipment` 统一设备台账
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| idc_id | INTEGER | 否 | — | FK→idc.id CASCADE, IX | 所属数据中心 |
| room_id | INTEGER | 是 | NULL | FK→room.id SET NULL, IX | 所在包间 |
| code | VARCHAR(64) | 否 | — | | 设备编码 CH-01 |
| name | VARCHAR(128) | 否 | '' | | 名称 |
| domain | VARCHAR(32) | 否 | — | IX | 业务域 hvac_source/power_hv/... |
| category | VARCHAR(32) | 否 | — | IX | 设备类别 chiller/ups/... |
| vendor / model | VARCHAR(64)/(128) | 否 | '' | | 厂商/型号 |
| status | VARCHAR(16) | 否 | '运行' | IX | 运行/待机/检修/故障/... |
| load_pct | DOUBLE PRECISION | 否 | 0 | | 负载率 % |
| run_hours | INTEGER | 否 | 0 | | 运行小时 |
| redundancy | VARCHAR(16) | 否 | '' | | N+1/2N/主备 |
| attrs | JSONB | 否 | '{}' | | 类别专属参数（反范式扩展） |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计 |
| 唯一/索引 | | | | UQ(idc_id, code); IX(domain, category); IX(room_id) | |

#### A5 `server` 物理服务器
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| cabinet_id | INTEGER | 否 | — | FK→cabinet.id CASCADE | 所在机柜 |
| asset_no | VARCHAR(64) | 否 | — | U, IX | 资产编号 |
| hostname | VARCHAR(128) | 否 | '' | | 主机名 |
| ip | VARCHAR(45) | 否 | — | IX | 管理 IP（IPv4/IPv6） |
| brand / model | VARCHAR(64)/(128) | 否 | '' | | 厂商/型号 |
| u_start / u_end | INTEGER | 否 | — | CK(u_end>=u_start, u_start>=1) | U 位起止 |
| cpu_model | VARCHAR(128) | 否 | '' | | CPU 型号 |
| cpu_count / cpu_cores | INTEGER | 否 | 2 / 0 | | CPU 颗数/核数 |
| memory_gb | INTEGER | 否 | 0 | | 内存 GB |
| disk_desc | VARCHAR(255) | 否 | '' | | 磁盘描述 |
| business | VARCHAR(128) | 否 | '' | IX | 所属业务 |
| status | VARCHAR(16) | 否 | '在线' | IX | 在线/离线/下架 |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计 |
| 索引 | | | | IX(cabinet_id,u_start,u_end); IX(ip,status) | |

### 模块 B — 采集与时序
#### B1 `external_devices` 外部设备注册
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| device_id | VARCHAR(64) | 否 | — | U, IX | 采集侧唯一标识 |
| ip | VARCHAR(64) | 否 | — | | |
| sn | VARCHAR(128) | 否 | — | | 出厂序列号 |
| model | VARCHAR(128) | 否 | — | | |
| name / vendor / location | VARCHAR(128)/(64)/(128) | 是 | NULL | | |
| idc_id | INTEGER | 是 | NULL | IX | 归属数据中心（软关联，无 FK） |
| domain / category | VARCHAR(32) | 是 | NULL | IX | 业务域/类别 |
| protocol | VARCHAR(32) | 是 | NULL | | modbus/snmp/... |
| tags | JSONB | 否 | '[]' | | 标签 |
| description | VARCHAR(512) | 是 | NULL | | |
| extra | JSONB | 否 | '{}' | | 扩展 |
| last_seen | TIMESTAMPTZ | 是 | NULL | | 最近上报时间 |
| created_at / updated_at | TIMESTAMPTZ | 否 | now() | | 审计 |

#### B2 `metric_defs` 测点定义
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| device_id | VARCHAR(64) | 否 | — | IX | 设备 id（逻辑） |
| metric_name | VARCHAR(128) | 否 | — | IX | 测点名 |
| label | VARCHAR(128) | 是 | NULL | | 中文名 |
| unit | VARCHAR(32) | 是 | NULL | | 单位 |
| data_type | VARCHAR(16) | 否 | 'float' | | float/int/bool/string |
| description | VARCHAR(256) | 是 | NULL | | |
| enabled | BOOLEAN | 否 | true | | 是否启用 |
| created_at | TIMESTAMPTZ | 是 | now() | | 审计 |

#### B3 `metric_raws` 原始测点时序
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| device_id | VARCHAR(64) | 否 | — | IX | 设备 id |
| ts | TIMESTAMPTZ | 否 | — | IX | 采样时间 |
| metric_name | VARCHAR(128) | 否 | — | IX | 测点名 |
| value | DOUBLE PRECISION | 否 | — | | 数值 |
| quality | VARCHAR(16) | 否 | 'good' | | good/uncertain/bad |
| unit | VARCHAR(32) | 是 | NULL | | |
| tags | JSONB | 否 | '{}' | | |
| received_at | TIMESTAMPTZ | 否 | now() | | 平台接收时间 |
| 唯一/索引 | | | | UQ(device_id,metric_name,ts); IX(device_id,ts); IX(device_id,metric_name) | 幂等唯一键防重投 |

#### B4 `point_data` 实时测点（多态时序）
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | BIGINT | 否 | IDENTITY | PK(复合) | 自增 |
| ts | TIMESTAMPTZ | 否 | — | PK(复合) | 采集时间（分区键） |
| target_type | VARCHAR(16) | 否 | — | | idc/cabinet/server/env |
| target_id | BIGINT | 否 | — | | 对象 id |
| metric | VARCHAR(32) | 否 | — | | temperature/cpu_usage/power_kw/... |
| value | DOUBLE PRECISION | 否 | — | | 数值 |
| unit | VARCHAR(16) | 否 | '' | | 单位 |
| quality | SMALLINT | 否 | 100 | | 数据质量 0-100 |
| 索引 | | | | IX(target_type,target_id,metric,ts); IX(metric,ts); BRIN(ts) | 详见 004 文档 |

### 模块 C — 身份与权限
#### C1 `users`
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| username | VARCHAR(64) | 否 | — | U, IX | 登录名 |
| password_hash | VARCHAR(255) | 否 | — | | 密码哈希 |
| display_name | VARCHAR(64) | 否 | '' | | 显示名 |
| email / phone | VARCHAR(128)/(32) | 是 | NULL | | |
| department | VARCHAR(64) | 否 | '' | | 部门/班组 |
| is_active / is_superuser | BOOLEAN | 否 | true/false | | |
| last_login | TIMESTAMPTZ | 是 | NULL | | |
| created_at / updated_at | TIMESTAMP | 否 | utcnow | | 审计（无时区，建议改 TIMESTAMPTZ） |

#### C2 `roles`
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| name | VARCHAR(32) | 否 | — | U | admin/operator/viewer |
| label | VARCHAR(32) | 否 | '' | | 展示名 |
| permissions | VARCHAR(1024) | 是 | NULL | | JSON 权限串 |
| created_at | TIMESTAMP | 否 | utcnow | | 审计 |

#### C3 `user_role` 关联表
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| user_id | INTEGER | 否 | — | PK, FK→users.id CASCADE | |
| role_id | INTEGER | 否 | — | PK, FK→roles.id CASCADE | |

### 模块 D — 运维作业
#### D1 `ticket` 工单
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | VARCHAR(32) | 否 | — | PK | WO-YYMMDD-NNN |
| title | VARCHAR(256) | 否 | — | | 标题 |
| sys | VARCHAR(64) | 否 | '' | IX | 系统 |
| lv | VARCHAR(16) | 否 | 'info' | IX | 级别 |
| state | VARCHAR(32) | 否 | 'open' | IX | open/doing/pending/done |
| owner | VARCHAR(64) | 否 | '待分配' | | 责任人 |
| created | VARCHAR(32) | 否 | '' | | 创建时间（字符串） |
| created_by | VARCHAR(64) | 否 | 'system' | | 创建人 |
| updated_at | VARCHAR(32) | 否 | '' | | 更新时间（字符串） |
| sla | VARCHAR(32) | 否 | '' | | SLA |
| due_at | VARCHAR(32) | 是 | NULL | | 到期 |
| progress | INTEGER | 否 | 0 | | 进度 |
| source | VARCHAR(32) | 否 | 'manual' | | 来源 |
| source_alarm_id | VARCHAR(64) | 是 | NULL | IX | 关联告警（逻辑） |
| description | TEXT | 否 | '' | | 描述 |
| logs | JSONB | 否 | '[]' | | 流转日志 [{ts,operator,action,...}] |

#### D2 `workflow_item` 运维流程
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | VARCHAR(32) | 否 | — | PK | INC-2026-0001 |
| type | VARCHAR(16) | 否 | 'incident' | | incident/problem/change/risk |
| title | VARCHAR(255) | 否 | '' | | 标题 |
| description | TEXT | 否 | '' | | 描述 |
| priority | VARCHAR(8) | 否 | 'P3' | | P1-P4 |
| status | VARCHAR(16) | 否 | 'new' | | new/progress/approval/... |
| owner / applicant | VARCHAR(64) | 否 | '' | | 责任人/申请人 |
| sla_hours | INTEGER | 否 | 24 | | SLA 小时 |
| risk_level | VARCHAR(16) | 是 | NULL | | high/medium/low（risk 型） |
| approval / logs / knowledge_links | JSONB | 否 | '[]' | | 审批/日志/知识链接 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计（字符串，建议 TIMESTAMPTZ） |

#### D3 `maintenance_plan` 维保计划
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| code | VARCHAR(64) | 否 | '' | IX | 计划编号 PM-xxx |
| name | VARCHAR(128) | 否 | '' | | 科目 |
| equipment_code | VARCHAR(128) | 否 | '' | | 关联设备 |
| description | TEXT | 否 | '' | | 说明 |
| frequency | VARCHAR(32) | 否 | 'monthly' | | daily/weekly/... |
| next_due_date | VARCHAR(32) | 否 | '' | | 下次到期 |
| status | VARCHAR(32) | 否 | 'active' | | active/paused/done |
| owner | VARCHAR(64) | 否 | '' | | 责任人 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计（字符串） |

#### D4 `maintenance_record` 维保记录
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| plan_code | VARCHAR(64) | 否 | '' | IX | 关联计划（逻辑） |
| plan_name | VARCHAR(128) | 否 | '' | | 科目 |
| equipment_code | VARCHAR(128) | 否 | '' | | 关联设备 |
| maintained_by | VARCHAR(64) | 否 | '' | | 维保人 |
| started_at / completed_at | VARCHAR(32) | 否 | '' | | 起止 |
| status | VARCHAR(32) | 否 | '已完成' | | 已完成/未完成 |
| result | VARCHAR(32) | 否 | '—' | | 正常/异常 |
| action_description | TEXT | 否 | '' | | 处理说明 |
| notes | TEXT | 否 | '' | | 备注 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### D5 `risk_item` 风险项
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| code | VARCHAR(32) | 否 | '' | IX | R-xx |
| risk | TEXT | 否 | '' | | 风险描述 |
| cat | VARCHAR(64) | 否 | '' | | 类别 |
| prob / impact | INTEGER | 否 | 2 / 2 | | 概率/影响 1-4 |
| level | VARCHAR(16) | 否 | '中' | | 高/中/低 |
| ctrl | TEXT | 否 | '' | | 管控措施 |
| owner | VARCHAR(64) | 否 | '' | | 责任 |
| closed | INTEGER | 否 | 0 | | 0/1 关闭 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### D6 `drill_plan` 演练计划
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| code | VARCHAR(32) | 否 | '' | IX | DR-xx |
| name | VARCHAR(128) | 否 | '' | | 科目 |
| type | VARCHAR(32) | 否 | '电力' | | 电力/暖通/消防/安防 |
| date | VARCHAR(16) | 否 | '' | | 计划日期 |
| state | VARCHAR(32) | 否 | '计划中' | | 计划中/已编排/已完成 |
| result | VARCHAR(32) | 否 | '—' | | 通过/未通过 |
| note | TEXT | 否 | '' | | 备注 |
| level | VARCHAR(32) | 否 | '—' | | 一/二/三/四级 |
| scope | VARCHAR(128) | 否 | '' | | 范围 |
| duration | INTEGER | 否 | 0 | | 时长(分) |
| steps | TEXT | 否 | '[]' | | 步骤 JSON 串 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### D7 `drill_record` 演练记录
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| plan_id | INTEGER | 是 | NULL | FK→drill_plan.id, IX | 关联计划（可空 FK） |
| plan_code | VARCHAR(32) | 否 | '' | | 计划编号（逻辑） |
| plan_name | VARCHAR(128) | 否 | '' | | 科目 |
| executed_by | VARCHAR(64) | 否 | '' | | 执行人 |
| started_at / completed_at | VARCHAR(32) | 否 | '' | | 起止 |
| score | INTEGER | 是 | NULL | | 评分 0-100 |
| result | VARCHAR(32) | 否 | '—' | | 通过/未通过 |
| notes | TEXT | 否 | '' | | 备注 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### D8 `inspection_route` 巡检路线
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| code | VARCHAR(32) | 否 | '' | IX | 路线编码 |
| freq | VARCHAR(32) | 否 | '每日' | | 频次 |
| items | INTEGER | 否 | 0 | | 检查项数 |
| last / next | VARCHAR(32) | 否 | '' | | 上次/下次巡检 |
| state | VARCHAR(32) | 否 | '进行中' | | 进行中/已完成 |
| note | TEXT | 否 | '' | | 备注 |

#### D9 `inspection_finding` 巡检发现
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| route | VARCHAR(64) | 否 | '' | | 所属路线 |
| item | TEXT | 否 | '' | | 发现内容 |
| ts | VARCHAR(32) | 否 | '' | | 时间 |
| lv | VARCHAR(16) | 否 | 'info' | | crit/warn/info |
| action | TEXT | 否 | '' | | 处置动作 |

#### D10 `inspection_robot` 巡检机器人配置（单例）
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| units | INTEGER | 否 | 2 | | 机器人总数 |
| running | INTEGER | 否 | 2 | | 运行中 |
| coverage | INTEGER | 否 | 96 | | 覆盖率 % |

#### D11 `shift_schedule` 值班排班
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| date | VARCHAR(16) | 否 | — | IX | YYYY-MM-DD |
| shift | VARCHAR(16) | 否 | 'day' | IX | day/night |
| members | JSONB | 否 | '[]' | | 成员 [{name,role,phone}] |
| leader | VARCHAR(64) | 否 | '' | | 负责人 |
| note | TEXT | 否 | '' | | 备注 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### D12 `shift_handover` 交接班
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| shift_date | VARCHAR(16) | 否 | '' | IX | 班次日期 |
| shift_type | VARCHAR(16) | 否 | 'day' | | day/night |
| from_user / to_user | VARCHAR(64) | 否 | '' | | 交/接班人 |
| items | TEXT | 否 | '' | | 交接事项 JSON 串 |
| note | TEXT | 否 | '' | | 说明 |
| status | VARCHAR(16) | 否 | 'pending' | | pending/done |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

### 模块 E — 告警与事件
#### E1 `alarm_event` 告警事件
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | VARCHAR(64) | 否 | uuid.hex | PK | 告警 id |
| rule_id | VARCHAR(128) | 否 | '' | IX | 规则 id（逻辑） |
| rule_name | VARCHAR(128) | 否 | '' | | 规则名 |
| metric | VARCHAR(128) | 否 | '' | | 测点 |
| sys | VARCHAR(64) | 否 | '' | IX | 系统 |
| lv | VARCHAR(16) | 否 | 'info' | IX | 级别 |
| desc | VARCHAR(512) | 否 | '' | | 描述 |
| value / threshold | DOUBLE PRECISION | 是 | NULL | | 实测/阈值 |
| unit | VARCHAR(32) | 是 | NULL | | 单位 |
| state | VARCHAR(32) | 否 | 'active' | IX | active/acknowledged/resolved |
| triggered_at | TIMESTAMP | 否 | utcnow | | 触发时间 |
| acknowledged_at / acknowledged_by | TIMESTAMP / VARCHAR(64) | 是 | NULL | | 确认 |
| resolved_at / resolved_by | TIMESTAMP / VARCHAR(64) | 是 | NULL | | 解决 |
| note | TEXT | 是 | NULL | | 备注 |
| auto_resolved | BOOLEAN | 否 | false | | 自动恢复 |
| escalation_count | INTEGER | 否 | 0 | | 升级次数 |
| device_id | VARCHAR(64) | 是 | NULL | IX | 设备 id（逻辑） |
| category / domain | VARCHAR(64) | 是 | NULL | | 类别/域 |

#### E2 `alarm_rule` 告警规则
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| rule_id | VARCHAR(128) | 否 | — | PK | chiller:supply_temp |
| category / metric | VARCHAR(64) | 否 | '' | | 类别/测点 |
| warn_lo / warn_hi / crit_lo / crit_hi | DOUBLE PRECISION | 是 | NULL | | 阈值 |
| unit | VARCHAR(16) | 否 | '' | | 单位 |
| enabled / silenced | BOOLEAN | 否 | true/false | | 启停/抑制 |
| silence_until | TIMESTAMP | 是 | NULL | | 抑制到期 |
| created_at / updated_at | TIMESTAMP | 否 | utcnow | | 审计 |

#### E3 `alarm_active_state` 活跃告警态
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| key | VARCHAR(256) | 否 | — | PK | device_id:metric:level |
| device_id | VARCHAR(64) | 否 | '' | IX | 设备 |
| metric_name | VARCHAR(64) | 否 | '' | | 测点 |
| level | VARCHAR(16) | 否 | 'warn' | | 级别 |
| alarm_json | TEXT | 否 | '{}' | | 完整告警字典 |
| conv_ts / first_seen_ts | DOUBLE PRECISION | 否 | 0.0 | | 收敛/首见时间 |
| ack_state | VARCHAR(16) | 否 | '待确认' | | 确认态 |
| status | VARCHAR(16) | 否 | 'active' | | active/resolved |
| updated_at | TIMESTAMP | 否 | utcnow | | 审计 |

#### E4 `alarm_suppressed_device` 告警抑制设备
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| device_id | VARCHAR(64) | 否 | — | PK | 设备 id |
| reason | VARCHAR(128) | 否 | '' | | 抑制原因 |
| created_at | TIMESTAMP | 否 | utcnow | | 审计 |

#### E5 `alarm_feedback` 告警处理反馈
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| alarm_id | VARCHAR(64) | 否 | '' | IX | 告警 id（逻辑） |
| system | VARCHAR(64) | 否 | '' | | 系统 |
| result | VARCHAR(32) | 否 | '' | | 已修复/误报/转工单/观察 |
| note | TEXT | 否 | '' | | 根因/方案 |
| operator | VARCHAR(64) | 否 | '' | | 处理人 |
| created_at | VARCHAR(32) | 否 | _now() | | 审计（字符串） |

### 模块 F — 知识 / AI / 能效 / 物模型
#### F1 `knowledge_item` 知识库
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| code | VARCHAR(32) | 否 | — | U, IX | KB-0001 |
| title | VARCHAR(255) | 否 | — | | 标题 |
| category / domain | VARCHAR(64) | 否 | — | IX | 系统/业务域 |
| type | VARCHAR(32) | 否 | 'sop' | IX | sop/drawing/manual/... |
| tags / related_categories / related_domains / related_metrics | JSONB | 否 | '[]' | | 关联标签/域/测点 |
| summary / content | TEXT | 否 | — | | 摘要/正文 |
| steps | JSONB | 否 | '[]' | | 处置步骤 |
| owner | VARCHAR(64) | 否 | '' | | 责任人 |
| hot | BOOLEAN | 否 | false | | 热门 |
| version | INTEGER | 否 | 1 | | 版本 |
| review_status | VARCHAR(16) | 否 | 'approved' | | pending/approved/rejected |
| reviewer / reviewed_at / review_note | VARCHAR(64)/VARCHAR(32)/TEXT | 否 | '' | | 审核 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### F2 `assistant_feedback` AI 助手反馈
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| question / answer | TEXT | 否 | '' | | 提问/回答 |
| rating | VARCHAR(16) | 否 | '' | | up/down |
| correction / note | TEXT | 否 | '' | | 纠错/备注 |
| grounded | VARCHAR(8) | 否 | '' | | 是否命中知识库 |
| model | VARCHAR(64) | 否 | '' | | 模型 |
| user | VARCHAR(64) | 否 | '' | | 反馈人 |
| created_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### F3 `analysis_history` 影响分析报告
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| title | VARCHAR(128) | 否 | '' | | 标题 |
| fault_ids | JSONB | 否 | '[]' | | 故障源 id |
| severity | VARCHAR(32) | 否 | 'low' | | low/high/critical |
| summary | JSONB | 否 | '{}' | | 摘要 |
| businesses | JSONB | 否 | '[]' | | 受影响业务域 |
| mitigations | JSONB | 否 | '[]' | | 缓解措施 |
| signers | JSONB | 否 | '[]' | | 会签人 |
| pushed | BOOLEAN | 否 | false | | 是否已推送 |
| created_by | VARCHAR(64) | 否 | '' | | 创建人 |
| created_at | VARCHAR(32) | 否 | _now() | | 审计（字符串） |

#### F4 `energy_advice_adopt` 节能建议采纳
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| suggestion_id | VARCHAR(64) | 否 | '' | | 建议 id |
| title | VARCHAR(255) | 否 | '' | | 标题 |
| priority | VARCHAR(16) | 否 | '' | | 高/中/低 |
| saving_kw / saving_pct | DOUBLE PRECISION | 否 | 0.0 | | 估算节能 |
| detail / basis | TEXT | 否 | '' | | 详情/依据 |
| action | VARCHAR(16) | 否 | 'adopt' | | adopt/ignore |
| note | TEXT | 否 | '' | | 备注 |
| pue_current / pue_target | DOUBLE PRECISION | 否 | 0.0 | | PUE |
| user | VARCHAR(64) | 否 | '' | | 操作人 |
| created_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### F5 `capacity_energy_history` 容量能耗历史
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | BIGINT | 否 | IDENTITY | PK | |
| idc_code | VARCHAR(32) | 否 | 'DC1' | | 作用域 |
| metric_key | VARCHAR(64) | 否 | — | | 指标键 |
| bucket | TIMESTAMPTZ | 否 | — | | 日聚合桶 |
| value | DOUBLE PRECISION | 否 | — | | 值 |
| unit | VARCHAR(16) | 是 | NULL | | 单位 |
| source | VARCHAR(16) | 否 | 'real' | | real/generated |
| meta | JSONB | 是 | NULL | | 元数据 |
| created_at | TIMESTAMPTZ | 否 | now() | | 审计 |
| 唯一/索引 | | | | UQ(idc_code,metric_key,bucket); IX(metric_key,bucket) | |

#### F6 `kpi_history` KPI 滚动历史
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| ts | TIMESTAMPTZ | 否 | — | IX | 快照时间 |
| pue / wue | DOUBLE PRECISION | 否 | 0.0 | | PUE/WUE |
| it_load_mw / total_load_mw / cool_load_mw | DOUBLE PRECISION | 否 | 0.0 | | 负载 |
| online_rate / availability | DOUBLE PRECISION | 否 | 0.0 | | 在线率/可用性 |

#### F7 `control_log` 快控指令记录
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| chiller_id | VARCHAR(32) | 否 | '' | | 机组 id |
| action | VARCHAR(16) | 否 | '' | | start/stop/mode/temp |
| value | DOUBLE PRECISION | 否 | NULL | | 设定值 ℃ |
| operator | VARCHAR(64) | 否 | '' | | 操作人 |
| result | VARCHAR(16) | 否 | 'accepted' | | accepted/rejected |
| created_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### F8 `thing_model` 物模型
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| model_key | VARCHAR(64) | 否 | — | U, IX | 模型唯一 key |
| name | VARCHAR(128) | 否 | '' | | 中文名 |
| category / domain | VARCHAR(64) | 否 | '' | IX | 类别/业务域 |
| protocol | VARCHAR(32) | 否 | '' | | 协议 |
| vendor | VARCHAR(64) | 否 | '' | | 厂商 |
| description | TEXT | 否 | '' | | 说明 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

#### F9 `thing_model_item` 物模型子项
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| thing_model_id | INTEGER | 否 | — | FK→thing_model.id CASCADE, IX | 所属模型 |
| item_type | VARCHAR(16) | 否 | 'property' | IX | property/service/event |
| identifier | VARCHAR(64) | 否 | '' | | 标识符 |
| name | VARCHAR(128) | 否 | '' | | 中文名 |
| data_type | VARCHAR(32) | 否 | 'float' | | float/int/bool/enum/... |
| unit | VARCHAR(16) | 否 | '' | | 单位 |
| desc | TEXT | 否 | '' | | 说明 |
| extra | JSONB | 否 | '{}' | | 扩展 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

### 模块 G — 租户与运营
#### G1 `tenant` 租户
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK, IX | |
| name | VARCHAR(128) | 否 | '' | | 租户名称 |
| code | VARCHAR(32) | 否 | '' | IX | TH-xx |
| contact / phone | VARCHAR(64)/(32) | 否 | '' | | 联系人/电话 |
| industry | VARCHAR(64) | 否 | '' | | 行业 |
| contractNo | VARCHAR(64) | 否 | '' | | 合同编号 |
| validFrom / validTo | VARCHAR(16) | 否 | '' | | 合同起止 |
| status | VARCHAR(32) | 否 | 'active' | | active/pending/expired |
| rent | DOUBLE PRECISION | 否 | 0 | | 月租金 |
| cabinets | INTEGER | 否 | 0 | | 已承租机柜 |
| quotaCabinets / quotaDevices | INTEGER | 否 | 0 | | 机柜/设备配额 |
| quotaPowerKw | DOUBLE PRECISION | 否 | 0 | | 功耗配额 kW |
| quotaBandwidthMbps | INTEGER | 否 | 0 | | 带宽配额 Mbps |
| usedDevices / uOccupied | INTEGER | 否 | 0 | | 在用设备/已用 U |
| usedPowerKw | DOUBLE PRECISION | 否 | 0 | | 实时功耗 kW |
| usedBandwidthMbps | INTEGER | 否 | 0 | | 实时带宽 Mbps |
| note | TEXT | 否 | '' | | 备注 |
| created_at / updated_at | VARCHAR(32) | 否 | _now() | | 审计 |

### 模块 H — 审计
#### H1 `audit_logs` 操作审计
| 字段 | 类型 | 可空 | 默认 | 约束 | 说明 |
|---|---|---|---|---|---|
| id | INTEGER | 否 | IDENTITY | PK | |
| ts | TIMESTAMP | 否 | utcnow | | 操作时间 |
| method | VARCHAR(8) | 否 | — | | HTTP 方法 |
| path | VARCHAR(255) | 否 | — | | 请求路径 |
| query | TEXT | 是 | NULL | | 查询串 |
| status_code | INTEGER | 否 | — | | 响应码 |
| username | VARCHAR(64) | 是 | NULL | | 操作人 |
| ip | VARCHAR(64) | 是 | NULL | | 客户端 IP |
| user_agent | TEXT | 是 | NULL | | UA |
| resource | VARCHAR(64) | 是 | NULL | | 资源类型 |
| action | VARCHAR(32) | 是 | NULL | | create/update/delete/read |
| detail | TEXT | 是 | NULL | | 请求体摘要（脱敏） |

---

## 六、建表语句（标准 PostgreSQL DDL）

> 以下 DDL 忠实反映当前 ORM（列名/类型/约束一致），可直接用于新建库或对照核对。
> 资产核心 4 表（idc/cabinet/server/point_data）的索引与 hypertable 优化见 `deploy/sql/002_core_tables.sql`、`003_point_data_hypertable.sql`。

```sql
-- ============ 模块 A 资产拓扑 ============
CREATE TABLE idc (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,
  name VARCHAR(128) NOT NULL,
  region VARCHAR(64) NOT NULL DEFAULT '',
  address VARCHAR(255) NOT NULL DEFAULT '',
  power_capacity_mw NUMERIC(10,3) NOT NULL DEFAULT 0,
  cooling_capacity_mw NUMERIC(10,3) NOT NULL DEFAULT 0,
  rack_capacity INTEGER NOT NULL DEFAULT 0,
  rooms INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT '运营',
  capacity_kw INTEGER NOT NULL DEFAULT 0,
  description VARCHAR(512) NOT NULL DEFAULT '',
  is_current BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_idc_region ON idc(region);
CREATE INDEX ix_idc_status ON idc(status);
CREATE INDEX ix_idc_current ON idc(is_current);

CREATE TABLE room (
  id SERIAL PRIMARY KEY,
  idc_id INTEGER NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
  code VARCHAR(32) NOT NULL,
  name VARCHAR(64) NOT NULL DEFAULT '',
  kind VARCHAR(32) NOT NULL DEFAULT 'it_room',
  floor VARCHAR(16) NOT NULL DEFAULT '',
  rack_capacity INTEGER NOT NULL DEFAULT 0,
  cold_aisle_t DOUBLE PRECISION NOT NULL DEFAULT 0,
  hot_aisle_t DOUBLE PRECISION NOT NULL DEFAULT 0,
  rh DOUBLE PRECISION NOT NULL DEFAULT 0,
  pressure_pa DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_room_idc_code UNIQUE (idc_id, code)
);
CREATE INDEX ix_room_kind ON room(kind);

CREATE TABLE cabinet (
  id SERIAL PRIMARY KEY,
  idc_id INTEGER NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
  code VARCHAR(32) NOT NULL,
  room VARCHAR(32) NOT NULL DEFAULT '',
  row VARCHAR(16) NOT NULL DEFAULT '',
  u_total INTEGER NOT NULL DEFAULT 42,
  u_used INTEGER NOT NULL DEFAULT 0,
  rated_power_kw NUMERIC(8,2) NOT NULL DEFAULT 10.0,
  current_power_kw NUMERIC(8,2) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT '在用',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_cabinet_idc_code UNIQUE (idc_id, code)
);
CREATE INDEX ix_cabinet_idc_room ON cabinet(idc_id, room);
CREATE INDEX ix_cabinet_status ON cabinet(status);

CREATE TABLE equipment (
  id SERIAL PRIMARY KEY,
  idc_id INTEGER NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
  room_id INTEGER REFERENCES room(id) ON DELETE SET NULL,
  code VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL DEFAULT '',
  domain VARCHAR(32) NOT NULL,
  category VARCHAR(32) NOT NULL,
  vendor VARCHAR(64) NOT NULL DEFAULT '',
  model VARCHAR(128) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT '运行',
  load_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
  run_hours INTEGER NOT NULL DEFAULT 0,
  redundancy VARCHAR(16) NOT NULL DEFAULT '',
  attrs JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_equipment_idc_code UNIQUE (idc_id, code)
);
CREATE INDEX ix_equipment_domain_cat ON equipment(domain, category);
CREATE INDEX ix_equipment_room ON equipment(room_id);
CREATE INDEX ix_equipment_status ON equipment(status);

CREATE TABLE server (
  id SERIAL PRIMARY KEY,
  cabinet_id INTEGER NOT NULL REFERENCES cabinet(id) ON DELETE CASCADE,
  asset_no VARCHAR(64) NOT NULL UNIQUE,
  hostname VARCHAR(128) NOT NULL DEFAULT '',
  ip VARCHAR(45) NOT NULL,
  brand VARCHAR(64) NOT NULL DEFAULT '',
  model VARCHAR(128) NOT NULL DEFAULT '',
  u_start INTEGER NOT NULL,
  u_end INTEGER NOT NULL,
  cpu_model VARCHAR(128) NOT NULL DEFAULT '',
  cpu_count INTEGER NOT NULL DEFAULT 2,
  cpu_cores INTEGER NOT NULL DEFAULT 0,
  memory_gb INTEGER NOT NULL DEFAULT 0,
  disk_desc VARCHAR(255) NOT NULL DEFAULT '',
  business VARCHAR(128) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT '在线',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_server_u_range CHECK (u_end >= u_start),
  CONSTRAINT ck_server_u_start_pos CHECK (u_start >= 1)
);
CREATE INDEX ix_server_cabinet_u ON server(cabinet_id, u_start, u_end);
CREATE INDEX ix_server_ip_status ON server(ip, status);
CREATE INDEX ix_server_business ON server(business);

-- ============ 模块 B 采集与时序 ============
CREATE TABLE external_devices (
  id SERIAL PRIMARY KEY,
  device_id VARCHAR(64) NOT NULL UNIQUE,
  ip VARCHAR(64) NOT NULL,
  sn VARCHAR(128) NOT NULL,
  model VARCHAR(128) NOT NULL,
  name VARCHAR(128),
  vendor VARCHAR(64),
  location VARCHAR(128),
  idc_id INTEGER,                       -- 软关联, 无 FK (有意)
  domain VARCHAR(32),
  category VARCHAR(32),
  protocol VARCHAR(32),
  tags JSONB NOT NULL DEFAULT '[]',
  description VARCHAR(512),
  extra JSONB NOT NULL DEFAULT '{}',
  last_seen TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ext_device_idc ON external_devices(idc_id);
CREATE INDEX ix_ext_device_dom ON external_devices(domain);
CREATE INDEX ix_ext_device_cat ON external_devices(category);

CREATE TABLE metric_defs (
  id SERIAL PRIMARY KEY,
  device_id VARCHAR(64) NOT NULL,
  metric_name VARCHAR(128) NOT NULL,
  label VARCHAR(128),
  unit VARCHAR(32),
  data_type VARCHAR(16) NOT NULL DEFAULT 'float',
  description VARCHAR(256),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_metric_def_dev ON metric_defs(device_id);
CREATE INDEX ix_metric_def_name ON metric_defs(metric_name);

CREATE TABLE metric_raws (
  id SERIAL PRIMARY KEY,
  device_id VARCHAR(64) NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  metric_name VARCHAR(128) NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  quality VARCHAR(16) NOT NULL DEFAULT 'good',
  unit VARCHAR(32),
  tags JSONB NOT NULL DEFAULT '{}',
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_metric_raw_device_name_ts UNIQUE (device_id, metric_name, ts)
);
CREATE INDEX ix_metric_raw_device_ts ON metric_raws(device_id, ts);
CREATE INDEX ix_metric_raw_device_name ON metric_raws(device_id, metric_name);

CREATE TABLE point_data (
  id BIGSERIAL,
  ts TIMESTAMPTZ NOT NULL,
  target_type VARCHAR(16) NOT NULL,
  target_id BIGINT NOT NULL,
  metric VARCHAR(32) NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  unit VARCHAR(16) NOT NULL DEFAULT '',
  quality SMALLINT NOT NULL DEFAULT 100,
  PRIMARY KEY (id, ts)
);
CREATE INDEX ix_pd_target_metric_ts ON point_data(target_type, target_id, metric, ts);
CREATE INDEX ix_pd_metric_ts ON point_data(metric, ts);
CREATE INDEX ix_pd_ts_brin ON point_data USING brin(ts);

-- ============ 模块 C 身份与权限 ============
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(64) NOT NULL DEFAULT '',
  email VARCHAR(128),
  phone VARCHAR(32),
  department VARCHAR(64) NOT NULL DEFAULT '',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(32) NOT NULL UNIQUE,
  label VARCHAR(32) NOT NULL DEFAULT '',
  permissions VARCHAR(1024),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_role (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

-- ============ 模块 D 运维作业 ============
CREATE TABLE ticket (
  id VARCHAR(32) PRIMARY KEY,
  title VARCHAR(256) NOT NULL,
  sys VARCHAR(64) NOT NULL DEFAULT '',
  lv VARCHAR(16) NOT NULL DEFAULT 'info',
  state VARCHAR(32) NOT NULL DEFAULT 'open',
  owner VARCHAR(64) NOT NULL DEFAULT '待分配',
  created VARCHAR(32) NOT NULL DEFAULT '',
  created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  updated_at VARCHAR(32) NOT NULL DEFAULT '',
  sla VARCHAR(32) NOT NULL DEFAULT '',
  due_at VARCHAR(32),
  progress INTEGER NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'manual',
  source_alarm_id VARCHAR(64),
  description TEXT NOT NULL DEFAULT '',
  logs JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX ix_ticket_sys ON ticket(sys);
CREATE INDEX ix_ticket_lv ON ticket(lv);
CREATE INDEX ix_ticket_state ON ticket(state);
CREATE INDEX ix_ticket_alarm ON ticket(source_alarm_id);

CREATE TABLE workflow_item (
  id VARCHAR(32) PRIMARY KEY,
  type VARCHAR(16) NOT NULL DEFAULT 'incident',
  title VARCHAR(255) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  priority VARCHAR(8) NOT NULL DEFAULT 'P3',
  status VARCHAR(16) NOT NULL DEFAULT 'new',
  owner VARCHAR(64) NOT NULL DEFAULT '',
  applicant VARCHAR(64) NOT NULL DEFAULT '',
  sla_hours INTEGER NOT NULL DEFAULT 24,
  risk_level VARCHAR(16),
  approval JSONB NOT NULL DEFAULT '[]',
  logs JSONB NOT NULL DEFAULT '[]',
  knowledge_links JSONB NOT NULL DEFAULT '[]',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE TABLE maintenance_plan (
  id SERIAL PRIMARY KEY,
  code VARCHAR(64) NOT NULL DEFAULT '',
  name VARCHAR(128) NOT NULL DEFAULT '',
  equipment_code VARCHAR(128) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  frequency VARCHAR(32) NOT NULL DEFAULT 'monthly',
  next_due_date VARCHAR(32) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  owner VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_mplan_code ON maintenance_plan(code);
CREATE INDEX ix_mplan_status ON maintenance_plan(status);

CREATE TABLE maintenance_record (
  id SERIAL PRIMARY KEY,
  plan_code VARCHAR(64) NOT NULL DEFAULT '',
  plan_name VARCHAR(128) NOT NULL DEFAULT '',
  equipment_code VARCHAR(128) NOT NULL DEFAULT '',
  maintained_by VARCHAR(64) NOT NULL DEFAULT '',
  started_at VARCHAR(32) NOT NULL DEFAULT '',
  completed_at VARCHAR(32) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT '已完成',
  result VARCHAR(32) NOT NULL DEFAULT '—',
  action_description TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_mrec_plan ON maintenance_record(plan_code);

CREATE TABLE risk_item (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL DEFAULT '',
  risk TEXT NOT NULL DEFAULT '',
  cat VARCHAR(64) NOT NULL DEFAULT '',
  prob INTEGER NOT NULL DEFAULT 2,
  impact INTEGER NOT NULL DEFAULT 2,
  level VARCHAR(16) NOT NULL DEFAULT '中',
  ctrl TEXT NOT NULL DEFAULT '',
  owner VARCHAR(64) NOT NULL DEFAULT '',
  closed INTEGER NOT NULL DEFAULT 0,
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_risk_code ON risk_item(code);
CREATE INDEX ix_risk_level ON risk_item(level);

CREATE TABLE drill_plan (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL DEFAULT '',
  name VARCHAR(128) NOT NULL DEFAULT '',
  type VARCHAR(32) NOT NULL DEFAULT '电力',
  date VARCHAR(16) NOT NULL DEFAULT '',
  state VARCHAR(32) NOT NULL DEFAULT '计划中',
  result VARCHAR(32) NOT NULL DEFAULT '—',
  note TEXT NOT NULL DEFAULT '',
  level VARCHAR(32) NOT NULL DEFAULT '—',
  scope VARCHAR(128) NOT NULL DEFAULT '',
  duration INTEGER NOT NULL DEFAULT 0,
  steps TEXT NOT NULL DEFAULT '[]',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_drill_code ON drill_plan(code);
CREATE INDEX ix_drill_state ON drill_plan(state);

CREATE TABLE drill_record (
  id SERIAL PRIMARY KEY,
  plan_id INTEGER REFERENCES drill_plan(id),
  plan_code VARCHAR(32) NOT NULL DEFAULT '',
  plan_name VARCHAR(128) NOT NULL DEFAULT '',
  executed_by VARCHAR(64) NOT NULL DEFAULT '',
  started_at VARCHAR(32) NOT NULL DEFAULT '',
  completed_at VARCHAR(32) NOT NULL DEFAULT '',
  score INTEGER,
  result VARCHAR(32) NOT NULL DEFAULT '—',
  notes TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_drec_plan ON drill_record(plan_id);

CREATE TABLE inspection_route (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL DEFAULT '',
  freq VARCHAR(32) NOT NULL DEFAULT '每日',
  items INTEGER NOT NULL DEFAULT 0,
  last VARCHAR(32) NOT NULL DEFAULT '',
  next VARCHAR(32) NOT NULL DEFAULT '',
  state VARCHAR(32) NOT NULL DEFAULT '进行中',
  note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX ix_insp_route_code ON inspection_route(code);

CREATE TABLE inspection_finding (
  id SERIAL PRIMARY KEY,
  route VARCHAR(64) NOT NULL DEFAULT '',
  item TEXT NOT NULL DEFAULT '',
  ts VARCHAR(32) NOT NULL DEFAULT '',
  lv VARCHAR(16) NOT NULL DEFAULT 'info',
  action TEXT NOT NULL DEFAULT ''
);

CREATE TABLE inspection_robot (
  id SERIAL PRIMARY KEY,
  units INTEGER NOT NULL DEFAULT 2,
  running INTEGER NOT NULL DEFAULT 2,
  coverage INTEGER NOT NULL DEFAULT 96
);

CREATE TABLE shift_schedule (
  id SERIAL PRIMARY KEY,
  date VARCHAR(16) NOT NULL,
  shift VARCHAR(16) NOT NULL DEFAULT 'day',
  members JSONB NOT NULL DEFAULT '[]',
  leader VARCHAR(64) NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_shift_date ON shift_schedule(date);
CREATE INDEX ix_shift_type ON shift_schedule(shift);

CREATE TABLE shift_handover (
  id SERIAL PRIMARY KEY,
  shift_date VARCHAR(16) NOT NULL DEFAULT '',
  shift_type VARCHAR(16) NOT NULL DEFAULT 'day',
  from_user VARCHAR(64) NOT NULL DEFAULT '',
  to_user VARCHAR(64) NOT NULL DEFAULT '',
  items TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_handover_date ON shift_handover(shift_date);
```

-- ============ 模块 E 告警 ============
CREATE TABLE alarm_event (
  id VARCHAR(64) PRIMARY KEY DEFAULT md5(random()::text || clock_timestamp()::text),
  rule_id VARCHAR(128) NOT NULL DEFAULT '',
  rule_name VARCHAR(128) NOT NULL DEFAULT '',
  metric VARCHAR(128) NOT NULL DEFAULT '',
  sys VARCHAR(64) NOT NULL DEFAULT '',
  lv VARCHAR(16) NOT NULL DEFAULT 'info',
  desc VARCHAR(512) NOT NULL DEFAULT '',
  value DOUBLE PRECISION,
  threshold DOUBLE PRECISION,
  unit VARCHAR(32),
  state VARCHAR(32) NOT NULL DEFAULT 'active',
  triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  acknowledged_at TIMESTAMP,
  acknowledged_by VARCHAR(64),
  resolved_at TIMESTAMP,
  resolved_by VARCHAR(64),
  note TEXT,
  auto_resolved BOOLEAN NOT NULL DEFAULT FALSE,
  escalation_count INTEGER NOT NULL DEFAULT 0,
  device_id VARCHAR(64),
  category VARCHAR(64),
  domain VARCHAR(64)
);
CREATE INDEX ix_alarm_rule ON alarm_event(rule_id);
CREATE INDEX ix_alarm_sys ON alarm_event(sys);
CREATE INDEX ix_alarm_lv ON alarm_event(lv);
CREATE INDEX ix_alarm_state ON alarm_event(state);
CREATE INDEX ix_alarm_device ON alarm_event(device_id);

CREATE TABLE alarm_rule (
  rule_id VARCHAR(128) PRIMARY KEY,
  category VARCHAR(64) NOT NULL DEFAULT '',
  metric VARCHAR(64) NOT NULL DEFAULT '',
  warn_lo DOUBLE PRECISION,
  warn_hi DOUBLE PRECISION,
  crit_lo DOUBLE PRECISION,
  crit_hi DOUBLE PRECISION,
  unit VARCHAR(16) NOT NULL DEFAULT '',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  silenced BOOLEAN NOT NULL DEFAULT FALSE,
  silence_until TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alarm_active_state (
  key VARCHAR(256) PRIMARY KEY,
  device_id VARCHAR(64) NOT NULL DEFAULT '',
  metric_name VARCHAR(64) NOT NULL DEFAULT '',
  level VARCHAR(16) NOT NULL DEFAULT 'warn',
  alarm_json TEXT NOT NULL DEFAULT '{}',
  conv_ts DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  first_seen_ts DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  ack_state VARCHAR(16) NOT NULL DEFAULT '待确认',
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_aas_device ON alarm_active_state(device_id);

CREATE TABLE alarm_suppressed_device (
  device_id VARCHAR(64) PRIMARY KEY,
  reason VARCHAR(128) NOT NULL DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alarm_feedback (
  id SERIAL PRIMARY KEY,
  alarm_id VARCHAR(64) NOT NULL DEFAULT '',
  system VARCHAR(64) NOT NULL DEFAULT '',
  result VARCHAR(32) NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  operator VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_afb_alarm ON alarm_feedback(alarm_id);

-- ============ 模块 F 知识/AI/能效/物模型 ============
CREATE TABLE knowledge_item (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  category VARCHAR(64),
  domain VARCHAR(64),
  type VARCHAR(32) NOT NULL DEFAULT 'sop',
  tags JSONB NOT NULL DEFAULT '[]',
  related_categories JSONB NOT NULL DEFAULT '[]',
  related_domains JSONB NOT NULL DEFAULT '[]',
  related_metrics JSONB NOT NULL DEFAULT '[]',
  summary TEXT,
  content TEXT,
  steps JSONB NOT NULL DEFAULT '[]',
  owner VARCHAR(64) NOT NULL DEFAULT '',
  hot BOOLEAN NOT NULL DEFAULT FALSE,
  version INTEGER NOT NULL DEFAULT 1,
  review_status VARCHAR(16) NOT NULL DEFAULT 'approved',
  reviewer VARCHAR(64) NOT NULL DEFAULT '',
  reviewed_at VARCHAR(32) NOT NULL DEFAULT '',
  review_note TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_kb_cat ON knowledge_item(category);
CREATE INDEX ix_kb_dom ON knowledge_item(domain);
CREATE INDEX ix_kb_type ON knowledge_item(type);

CREATE TABLE assistant_feedback (
  id SERIAL PRIMARY KEY,
  question TEXT NOT NULL DEFAULT '',
  answer TEXT NOT NULL DEFAULT '',
  rating VARCHAR(16) NOT NULL DEFAULT '',
  correction TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  grounded VARCHAR(8) NOT NULL DEFAULT '',
  model VARCHAR(64) NOT NULL DEFAULT '',
  user VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE TABLE analysis_history (
  id SERIAL PRIMARY KEY,
  title VARCHAR(128) NOT NULL DEFAULT '',
  fault_ids JSONB NOT NULL DEFAULT '[]',
  severity VARCHAR(32) NOT NULL DEFAULT 'low',
  summary JSONB NOT NULL DEFAULT '{}',
  businesses JSONB NOT NULL DEFAULT '[]',
  mitigations JSONB NOT NULL DEFAULT '[]',
  signers JSONB NOT NULL DEFAULT '[]',
  pushed BOOLEAN NOT NULL DEFAULT FALSE,
  created_by VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE TABLE energy_advice_adopt (
  id SERIAL PRIMARY KEY,
  suggestion_id VARCHAR(64) NOT NULL DEFAULT '',
  title VARCHAR(255) NOT NULL DEFAULT '',
  priority VARCHAR(16) NOT NULL DEFAULT '',
  saving_kw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  saving_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  detail TEXT NOT NULL DEFAULT '',
  basis TEXT NOT NULL DEFAULT '',
  action VARCHAR(16) NOT NULL DEFAULT 'adopt',
  note TEXT NOT NULL DEFAULT '',
  pue_current DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  pue_target DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  user VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE TABLE capacity_energy_history (
  id BIGSERIAL PRIMARY KEY,
  idc_code VARCHAR(32) NOT NULL DEFAULT 'DC1',
  metric_key VARCHAR(64) NOT NULL,
  bucket TIMESTAMPTZ NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  unit VARCHAR(16),
  source VARCHAR(16) NOT NULL DEFAULT 'real',
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_ceh_scope_key_bucket UNIQUE (idc_code, metric_key, bucket)
);
CREATE INDEX ix_ceh_key_bucket ON capacity_energy_history(metric_key, bucket);

CREATE TABLE kpi_history (
  id SERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL,
  pue DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  wue DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  it_load_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  total_load_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  cool_load_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  online_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  availability DOUBLE PRECISION NOT NULL DEFAULT 0.0
);
CREATE INDEX ix_kpi_ts ON kpi_history(ts);

CREATE TABLE control_log (
  id SERIAL PRIMARY KEY,
  chiller_id VARCHAR(32) NOT NULL DEFAULT '',
  action VARCHAR(16) NOT NULL DEFAULT '',
  value DOUBLE PRECISION,
  operator VARCHAR(64) NOT NULL DEFAULT '',
  result VARCHAR(16) NOT NULL DEFAULT 'accepted',
  created_at VARCHAR(32) NOT NULL DEFAULT ''
);

CREATE TABLE thing_model (
  id SERIAL PRIMARY KEY,
  model_key VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL DEFAULT '',
  category VARCHAR(64) NOT NULL DEFAULT '',
  domain VARCHAR(64) NOT NULL DEFAULT '',
  protocol VARCHAR(32) NOT NULL DEFAULT '',
  vendor VARCHAR(64) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT '',
  CONSTRAINT uq_thing_model_key UNIQUE (model_key)
);
CREATE INDEX ix_tm_cat ON thing_model(category);
CREATE INDEX ix_tm_dom ON thing_model(domain);

CREATE TABLE thing_model_item (
  id SERIAL PRIMARY KEY,
  thing_model_id INTEGER NOT NULL REFERENCES thing_model(id) ON DELETE CASCADE,
  item_type VARCHAR(16) NOT NULL DEFAULT 'property',
  identifier VARCHAR(64) NOT NULL DEFAULT '',
  name VARCHAR(128) NOT NULL DEFAULT '',
  data_type VARCHAR(32) NOT NULL DEFAULT 'float',
  unit VARCHAR(16) NOT NULL DEFAULT '',
  desc TEXT NOT NULL DEFAULT '',
  extra JSONB NOT NULL DEFAULT '{}',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_tmi_model ON thing_model_item(thing_model_id);
CREATE INDEX ix_tmi_type ON thing_model_item(item_type);

-- ============ 模块 G 租户 ============
CREATE TABLE tenant (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL DEFAULT '',
  code VARCHAR(32) NOT NULL DEFAULT '',
  contact VARCHAR(64) NOT NULL DEFAULT '',
  phone VARCHAR(32) NOT NULL DEFAULT '',
  industry VARCHAR(64) NOT NULL DEFAULT '',
  contractNo VARCHAR(64) NOT NULL DEFAULT '',
  validFrom VARCHAR(16) NOT NULL DEFAULT '',
  validTo VARCHAR(16) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  rent DOUBLE PRECISION NOT NULL DEFAULT 0,
  cabinets INTEGER NOT NULL DEFAULT 0,
  quotaCabinets INTEGER NOT NULL DEFAULT 0,
  quotaDevices INTEGER NOT NULL DEFAULT 0,
  quotaPowerKw DOUBLE PRECISION NOT NULL DEFAULT 0,
  quotaBandwidthMbps INTEGER NOT NULL DEFAULT 0,
  usedDevices INTEGER NOT NULL DEFAULT 0,
  usedPowerKw DOUBLE PRECISION NOT NULL DEFAULT 0,
  usedBandwidthMbps INTEGER NOT NULL DEFAULT 0,
  uOccupied INTEGER NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  updated_at VARCHAR(32) NOT NULL DEFAULT ''
);
CREATE INDEX ix_tenant_code ON tenant(code);
CREATE INDEX ix_tenant_status ON tenant(status);

-- ============ 模块 H 审计 ============
CREATE TABLE audit_logs (
  id SERIAL PRIMARY KEY,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  method VARCHAR(8) NOT NULL,
  path VARCHAR(255) NOT NULL,
  query TEXT,
  status_code INTEGER NOT NULL,
  username VARCHAR(64),
  ip VARCHAR(64),
  user_agent TEXT,
  resource VARCHAR(64),
  action VARCHAR(32),
  detail TEXT
);
CREATE INDEX ix_audit_ts ON audit_logs(ts);
CREATE INDEX ix_audit_user ON audit_logs(username);
```

---

## 七、索引策略总览

| 表 | 关键索引 | 用途 |
|---|---|---|
| idc | U(code), IX(region,status,is_current) | 站点检索/默认站点 |
| room/cabinet/equipment | UQ(idc_id, code) 复合唯一 | 同 IDC 内编号唯一 + 反查 |
| cabinet | IX(idc_id, room) | 包间功率统计 |
| server | IX(cabinet_id,u_start,u_end), IX(ip,status) | U 位冲突检测/按 IP 查 |
| point_data | IX(target_type,target_id,metric,ts), IX(metric,ts), BRIN(ts) | 时序拉取/全网对比/归档（见 004） |
| metric_raws | UQ(device_id,metric_name,ts) 幂等, IX(device_id,ts) | 防重投/时序 |
| external_devices | IX(idc_id,domain,category) | 设备检索 |
| ticket | IX(sys,lv,state,source_alarm_id) | 工单看板/告警溯源 |
| workflow_item | PK(id) | 流程单号检索 |
| maintenance_plan/record | IX(code,status), IX(plan_code) | 计划/记录关联 |
| drill_plan/record | IX(code,state), IX(plan_id) | 演练检索 |
| alarm_event | IX(rule_id,sys,lv,state,device_id) | 告警查询/收敛 |
| alarm_active_state | PK(key), IX(device_id) | 活跃态去重 |
| knowledge_item | U(code), IX(category,domain,type) | 知识检索/告警关联 |
| thing_model | U(model_key), IX(category,domain) | 物模型检索 |
| tenant | IX(code,status) | 租户检索 |
| kpi_history / capacity_energy_history | IX(ts) / UQ(idc_code,metric_key,bucket) | 趋势/日聚合 |
| audit_logs | IX(ts,username) | 审计追溯 |

**通用原则**：等值过滤列放复合索引最左；排序列（ts）放右；高基数列（ip/device_id）前置；时序大表用 BRIN + 分区，避免过多 B-tree 写放大；JSON 列仅对必须检索的键建 **GIN 索引**（如 `equipment.attrs` 频繁按 `domain` 检索可改冗余列而非 GIN）。

---

## 八、深化设计建议（目标 Schema）

针对第二章识别的设计债，给出落地优先级。

### 8.1 统一审计与软删除基类（高优先级）
引入公共 Mixin，所有业务表继承，消除三类审计字段并存与"无创建人/更新人"问题：
```python
class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True, index=True)  # NULL=未删
```
- 将现有 `VARCHAR(32)` 字符串时间列（`workflow_item/maintenance/*/drill/*/inspection/*/shift/*/tenant/knowledge/thing_model/alarm_feedback/...`）**迁移为 TIMESTAMPTZ**（数据回填 + 列类型 ALTER）。
- `users/alarm_rule/alarm_active_state/alarm_suppressed_device/audit_logs` 的 `TIMESTAMP` 统一升级为 `TIMESTAMPTZ`。
- 软删除：对 `ticket/workflow_item/maintenance_*/risk_item/drill_*/inspection_*/knowledge_item/thing_model/tenant` 等**业务实体**加 `deleted_at`；查询层统一加 `WHERE deleted_at IS NULL`，并配合唯一约束时改为**部分唯一索引**（如 `CREATE UNIQUE INDEX ... ON ticket(code) WHERE deleted_at IS NULL`）。

### 8.2 主键与标识符策略（中优先级）
- 内部关联表（资产树、租户、知识等）统一 `BIGINT GENERATED ALWAYS AS IDENTITY`，避免 INTEGER 自增上限风险。
- 业务单号（`ticket`/`workflow_item`/`alarm_event`/`drill_plan`/`maintenance_plan`/`knowledge_item`/`tenant.code` 等）保留**有意义编码**作为业务键，但**额外保留内部 `id BIGINT` 主键**，外键统一引用内部 `id` 而非字符串编码（见 8.3）。
- `alarm_rule.rule_id` / `alarm_active_state.key` / `alarm_suppressed_device.device_id` 为复合业务键主键，保留，但建议 `alarm_active_state` 改为 `(device_id, metric_name, level)` 显式复合主键提升可读性。

### 8.3 外键约束补全（中优先级，分俩阶段）
- **阶段一（低风险、强一致）**：对现有"逻辑关联"补 DB 外键并设级联/置空：
  - `external_devices.idc_id` → `idc.id`（SET NULL，因原意软关联，可改为弱 FK）
  - `alarm_event.device_id` → `external_devices.device_id`（无标准 FK 目标，建议改为 `external_devices.id` 内部 id）
  - `alarm_event.rule_id` → `alarm_rule.rule_id`
  - `alarm_feedback.alarm_id` → `alarm_event.id`
  - `ticket.source_alarm_id` → `alarm_event.id`
  - `maintenance_record.plan_code` → 改为 `maintenance_plan.id` 外键（同时保留 code 冗余列）
  - `drill_record.plan_code` → 同 `drill_plan.id`（plan_id 已存在，建议弃用 plan_code 仅留 FK）
  - `metric_defs.device_id` / `metric_raws.device_id` → `external_devices.id`
- **阶段二（采集高写入链路）**：`point_data` 多态关联维持"无 FK"（写入性能优先），由应用层保障一致性；`metric_raws` 保留幂等唯一键即可。
- 注意：`external_devices` 由采集器注册、可能先于 `idc` 存在，弱 FK（SET NULL + 应用层补偿）更稳妥。

### 8.4 数据一致性 & 冗余控制（中优先级）
- **枚举字典化**：`equipment.domain/category`、`alarm_event.lv/state`、`ticket.state`、`drill_plan.type/state`、`thing_model_item.item_type` 等字符串枚举，建议落到配置表或 `CHECK` 约束，避免脏值；前端下拉与后端校验对齐（可复用 `i18n` 字典）。
- **冗余高频列**：`equipment.attrs` 中若 `load_pct/status` 已为列则不需冗余；但 `tenant.used*` 为衍生聚合值，写入时由触发器/定时任务更新并加 `CHECK(usedX <= quotaX)` 防越界（现有 `_derive_status` 已在应用层做，建议下推为 DB 约束或视图）。
- **JSON 治理**：`workflow_item.approval/logs`、`analysis_history.*`、`drill_plan.steps` 等嵌套结构保留 JSONB；但对需检索的字段（如 `analysis_history.severity`、`workflow_item.status`）已为独立列，正确。

### 8.5 扩展性设计（低优先级）
- **多园区/多租户**：`idc` 已支持多站点；`external_devices.idc_id`、`capacity_energy_history.idc_code` 已带作用域；新增园区无需改表结构。
- **测点/物模型扩展**：`thing_model_item.extra`（JSONB）承载 enum 值域/服务参数；`equipment.attrs` 承载类别专属参数，均无需 DDL 变更即可扩展新设备类型。
- **审计与追踪**：`audit_logs` 已全量记录写操作；建议对敏感表（`users/roles/tenant`）增加行级审计视图或触发器（可选）。
- **分库分表预留**：时序表 `point_data`/`metric_raws` 已设计为可按 `ts`/`idc_code` 分区；分析型 `capacity_energy_history`/`kpi_history` 为日/5 分钟粒度聚合，天然可水平拆分。

### 8.6 时序大表专项（已部分落地，持续）
- `point_data`：TimescaleDB hypertable（`003_point_data_hypertable.sql`），7 天 chunk + 列式压缩 + 连续聚合 `point_data_5min` + 1 年保留策略 + Redis 最新值缓存。
- `metric_raws`：幂等唯一键防重投（`007_metric_raw_unique.sql`），建议同样 hypertable（`005_metric_raws_hypertable.sql`）+ retention。
- 上述已在 `deploy/sql/` 提供脚本，Alembic/psql 执行即可。

---

## 九、建表执行顺序与依赖

```text
① 基础维度（无 FK 依赖）: idc, roles, users, user_role, alarm_rule, alarm_suppressed_device,
   thing_model, inspection_robot, knowledge_item, tenant
② 资产拓扑（依赖 idc/room/cabinet）: room→cabinet→equipment→server
③ 物模型子项（依赖 thing_model）: thing_model_item
④ 采集时序（依赖 idc 软关联）: external_devices, metric_defs, metric_raws, point_data
⑤ 运维作业（依赖 drill_plan）: maintenance_plan, maintenance_record, drill_plan, drill_record,
   ticket, workflow_item, risk_item, inspection_route, inspection_finding, shift_schedule, shift_handover
⑥ 告警（依赖 alarm_rule/external_devices）: alarm_event, alarm_active_state, alarm_feedback
⑦ 智能/能效: assistant_feedback, analysis_history, energy_advice_adopt, capacity_energy_history,
   kpi_history, control_log
⑧ 审计: audit_logs
```
> 说明：因资产树为强 FK 级联，建表顺序需先父后子；逻辑关联（字符串编码）无顺序约束。Alembic 可一次性 `upgrade head` 自动按依赖拓扑建表。

---

## 十、附录：枚举取值参考（供校验/字典表设计）

| 字段 | 取值 |
|---|---|
| idc.status | 运营 / 建设 / 下线 |
| room.kind | it_room / substation / battery_room / chiller_station / carrier_room / ups_room / noc |
| equipment.domain | hvac_source / hvac_terminal / power_hv / power_lv / power_genset / power_fuel / power_batt / sec_cctv / sec_acs / sec_ids / sec_fire |
| equipment.category | chiller / cooling_tower / crac / ups / transformer / genset / battery_group / camera / ...（见 `equipment.py` 模块注释） |
| alarm_event.lv | info / warn / crit |
| alarm_event.state | active / acknowledged / resolved / suppressed |
| ticket.state | open / doing / pending / done |
| workflow_item.type | incident / problem / change / risk |
| workflow_item.status | new / progress / approval / rejected / closed |
| maintenance_plan.frequency | daily / weekly / monthly / quarterly / yearly |
| drill_plan.type | 电力 / 暖通 / 消防 / 安防 |
| thing_model_item.item_type | property / service / event |
| tenant.status | active / pending / expired |

> 以上为当前代码中出现的主要取值；落地 8.4 的字典表/CHECK 时以本表为基线。



