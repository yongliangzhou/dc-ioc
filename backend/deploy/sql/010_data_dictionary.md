# 数据库数据字典（自动生成补充）

> 生成方式：`python gen_dd.py`（反射 `app.models.Base.metadata`）。

> 本文件与 `004_schema_design.md`（核心表设计）互补，覆盖**全部业务表**的字段定义。


## 表 `alarm_active_state`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| key | VARCHAR(256) | 否 |  | PK |
| device_id | VARCHAR(64) | 否 | '' | INDEX |
| metric_name | VARCHAR(64) | 否 | '' |  |
| level | VARCHAR(16) | 否 | 'warn' |  |
| alarm_json | TEXT | 否 | '{}' |  |
| conv_ts | FLOAT | 否 | 0.0 |  |
| first_seen_ts | FLOAT | 否 | 0.0 |  |
| ack_state | VARCHAR(16) | 否 | '待确认' |  |
| status | VARCHAR(16) | 否 | 'active' |  |
| updated_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76EF1FF60> |  |

- 主键：key

## 表 `alarm_event`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | VARCHAR(64) | 否 | <function AlarmEvent.<lambda> at 0x000001D76EEC77E0> | PK |
| rule_id | VARCHAR(128) | 否 | '' | INDEX |
| rule_name | VARCHAR(128) | 否 | '' |  |
| metric | VARCHAR(128) | 否 | '' |  |
| sys | VARCHAR(64) | 否 | '' | INDEX |
| lv | VARCHAR(16) | 否 | 'info' | INDEX |
| desc | VARCHAR(512) | 否 | '' |  |
| value | FLOAT | 是 |  |  |
| threshold | FLOAT | 是 |  |  |
| unit | VARCHAR(32) | 是 |  |  |
| state | VARCHAR(32) | 否 | 'active' | INDEX |
| triggered_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76EEC7880> |  |
| acknowledged_at | DATETIME | 是 |  |  |
| acknowledged_by | VARCHAR(64) | 是 |  |  |
| resolved_at | DATETIME | 是 |  |  |
| resolved_by | VARCHAR(64) | 是 |  |  |
| note | TEXT | 是 |  |  |
| auto_resolved | BOOLEAN | 否 | False |  |
| escalation_count | INTEGER | 否 | 0 |  |
| device_id | VARCHAR(64) | 是 |  | INDEX |
| category | VARCHAR(64) | 是 |  |  |
| domain | VARCHAR(64) | 是 |  |  |

- 主键：id

## 表 `alarm_rule`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| rule_id | VARCHAR(128) | 否 |  | PK |
| category | VARCHAR(64) | 否 | '' |  |
| metric | VARCHAR(64) | 否 | '' |  |
| warn_lo | FLOAT | 是 |  |  |
| warn_hi | FLOAT | 是 |  |  |
| crit_lo | FLOAT | 是 |  |  |
| crit_hi | FLOAT | 是 |  |  |
| unit | VARCHAR(16) | 否 | '' |  |
| enabled | BOOLEAN | 否 | True |  |
| silenced | BOOLEAN | 否 | False |  |
| silence_until | DATETIME | 是 |  |  |
| created_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76EF1EB60> |  |
| updated_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76EF1EC00> |  |

- 主键：rule_id

## 表 `alarm_suppressed_device`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| device_id | VARCHAR(64) | 否 |  | PK |
| reason | VARCHAR(128) | 否 | '' |  |
| created_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76EF50FE0> |  |

- 主键：device_id

## 表 `audit_logs`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| ts | DATETIME | 否 | <function datetime.utcnow at 0x000001D76F09E700> | 操作时间(UTC) |
| method | VARCHAR(8) | 否 |  | HTTP 方法 |
| path | VARCHAR(255) | 否 |  | 请求路径 |
| query | TEXT | 是 |  | 查询字符串 |
| status_code | INTEGER | 否 |  | 响应状态码 |
| username | VARCHAR(64) | 是 |  | 操作人 (token sub, 匿名为空) |
| ip | VARCHAR(64) | 是 |  | 客户端 IP |
| user_agent | TEXT | 是 |  | User-Agent |
| resource | VARCHAR(64) | 是 |  | 资源类型 (从路径推断) |
| action | VARCHAR(32) | 是 |  | 动作 (create/update/delete/read/login) |
| detail | TEXT | 是 |  | 请求体摘要 (已脱敏, 截断) |

- 主键：id

## 表 `cabinet`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| idc_id | INTEGER | 否 |  | FK→idc.id 所属数据中心 |
| code | VARCHAR(32) | 否 |  | INDEX 机柜编号 如 R01-A05 |
| room | VARCHAR(32) | 否 |  | INDEX 所在包间 |
| row | VARCHAR(16) | 否 | '' | 机列 |
| u_total | INTEGER | 否 | 42 | U位总数 |
| u_used | INTEGER | 否 | 0 | 已用U位 |
| rated_power_kw | NUMERIC(8, 2) | 否 | 10.0 | 额定功率 kW |
| current_power_kw | NUMERIC(8, 2) | 否 | 0 | 当前功率 kW |
| status | VARCHAR(16) | 否 | '在用' | INDEX 在用/预留/停用 |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `capacity_energy_history`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | BIGINT | 否 |  | PK |
| idc_code | VARCHAR(32) | 否 | 'DC1' |  |
| metric_key | VARCHAR(64) | 否 |  |  |
| bucket | DATETIME | 否 |  |  |
| value | FLOAT | 否 |  |  |
| unit | VARCHAR(16) | 是 |  |  |
| source | VARCHAR(16) | 否 | 'real' |  |
| meta | JSON | 是 |  |  |
| created_at | DATETIME | 是 | <function CapacityEnergyHistory.<lambda> at 0x000001D76EF8FF60> |  |

- 主键：id

## 表 `drill_plan`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| code | VARCHAR(32) | 是 | '' | INDEX |
| name | VARCHAR(128) | 是 | '' |  |
| type | VARCHAR(32) | 是 | '电力' |  |
| date | VARCHAR(16) | 是 | '' |  |
| state | VARCHAR(32) | 是 | '计划中' |  |
| result | VARCHAR(32) | 是 | '—' |  |
| note | TEXT | 是 | '' |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFE8900> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFE89A0> |  |

- 主键：id

## 表 `drill_record`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| plan_id | INTEGER | 是 |  | FK→drill_plan.id INDEX |
| plan_code | VARCHAR(32) | 是 | '' |  |
| plan_name | VARCHAR(128) | 是 | '' |  |
| executed_by | VARCHAR(64) | 是 | '' |  |
| started_at | VARCHAR(32) | 是 | '' |  |
| completed_at | VARCHAR(32) | 是 | '' |  |
| score | INTEGER | 是 |  |  |
| result | VARCHAR(32) | 是 | '—' |  |
| notes | TEXT | 是 | '' |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFE9EE0> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFE9F80> |  |

- 主键：id

## 表 `equipment`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| idc_id | INTEGER | 否 |  | FK→idc.id |
| room_id | INTEGER | 是 |  | FK→room.id |
| code | VARCHAR(64) | 否 |  | 设备编码 CH-01/DG-01/CRAC-08 |
| name | VARCHAR(128) | 否 | '' |  |
| domain | VARCHAR(32) | 否 |  | INDEX 业务域(见模块注释) |
| category | VARCHAR(32) | 否 |  | INDEX 设备类别 |
| vendor | VARCHAR(64) | 否 | '' |  |
| model | VARCHAR(128) | 否 | '' |  |
| status | VARCHAR(16) | 否 | '运行' | INDEX |
| load_pct | FLOAT | 否 | 0 | 负载率% |
| run_hours | INTEGER | 否 | 0 |  |
| redundancy | VARCHAR(16) | 否 | '' | N+1/2N/主备 |
| attrs | JSON | 否 | <function dict at 0x000001D76EF536A0> | 类别专属参数 |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `external_devices`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| device_id | VARCHAR(64) | 否 |  | UNIQUE INDEX 采集侧唯一标识 |
| ip | VARCHAR(64) | 否 |  |  |
| sn | VARCHAR(128) | 否 |  | 出厂序列号 |
| model | VARCHAR(128) | 否 |  |  |
| name | VARCHAR(128) | 是 |  |  |
| vendor | VARCHAR(64) | 是 |  |  |
| domain | VARCHAR(32) | 是 |  | INDEX |
| category | VARCHAR(32) | 是 |  | INDEX |
| location | VARCHAR(128) | 是 |  |  |
| protocol | VARCHAR(32) | 是 |  |  |
| tags | JSON | 否 | <function list at 0x000001D76EF8D080> |  |
| description | VARCHAR(512) | 是 |  |  |
| extra | JSON | 否 | <function dict at 0x000001D76EF8D120> |  |
| last_seen | DATETIME | 是 |  | 最近一次测点上报时间 |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `idc`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| code | VARCHAR(32) | 否 |  | UNIQUE INDEX 站点编码 如 EC1-HZ |
| name | VARCHAR(128) | 否 |  | 数据中心名称 |
| region | VARCHAR(64) | 否 |  | INDEX 地域/可用区 |
| address | VARCHAR(255) | 否 | '' | 地址 |
| power_capacity_mw | NUMERIC(10, 3) | 否 | 0 | 电力容量 MW |
| cooling_capacity_mw | NUMERIC(10, 3) | 否 | 0 | 制冷容量 MW |
| rack_capacity | INTEGER | 否 | 0 | 机柜总容量 |
| rooms | INTEGER | 否 | 0 | 包间数量 |
| status | VARCHAR(16) | 否 | '运营' | INDEX 运营/建设/下线 |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `inspection_finding`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| route | VARCHAR(64) | 是 | '' |  |
| item | TEXT | 是 | '' |  |
| ts | VARCHAR(32) | 是 | '' |  |
| lv | VARCHAR(16) | 是 | 'info' |  |
| action | TEXT | 是 | '' |  |

- 主键：id

## 表 `inspection_robot`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| units | INTEGER | 是 | 2 |  |
| running | INTEGER | 是 | 2 |  |
| coverage | INTEGER | 是 | 96 |  |

- 主键：id

## 表 `inspection_route`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| code | VARCHAR(32) | 是 | '' | INDEX |
| freq | VARCHAR(32) | 是 | '每日' |  |
| items | INTEGER | 是 | 0 |  |
| last | VARCHAR(32) | 是 | '' |  |
| next | VARCHAR(32) | 是 | '' |  |
| state | VARCHAR(32) | 是 | '进行中' |  |
| note | TEXT | 是 | '' |  |

- 主键：id

## 表 `knowledge_item`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| code | VARCHAR(32) | 否 |  | UNIQUE INDEX |
| title | VARCHAR(255) | 否 |  |  |
| category | VARCHAR(64) | 是 |  | INDEX |
| domain | VARCHAR(64) | 是 |  | INDEX |
| type | VARCHAR(32) | 是 | 'sop' | INDEX |
| tags | JSON | 是 | <function list at 0x000001D76EFC25C0> |  |
| related_categories | JSON | 是 | <function list at 0x000001D76EFC2660> |  |
| related_domains | JSON | 是 | <function list at 0x000001D76EFC2700> |  |
| related_metrics | JSON | 是 | <function list at 0x000001D76EFC27A0> |  |
| summary | TEXT | 是 |  |  |
| content | TEXT | 是 |  |  |
| steps | JSON | 是 | <function list at 0x000001D76EFC2840> |  |
| owner | VARCHAR(64) | 是 | '' |  |
| hot | BOOLEAN | 是 | False |  |
| version | INTEGER | 是 | 1 |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFC2A20> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFC2B60> |  |

- 主键：id

## 表 `maintenance_record`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| plan_code | VARCHAR(64) | 是 | '' | INDEX |
| plan_name | VARCHAR(128) | 是 | '' |  |
| equipment_code | VARCHAR(128) | 是 | '' |  |
| maintained_by | VARCHAR(64) | 是 | '' |  |
| started_at | VARCHAR(32) | 是 | '' |  |
| completed_at | VARCHAR(32) | 是 | '' |  |
| status | VARCHAR(32) | 是 | '已完成' |  |
| result | VARCHAR(32) | 是 | '—' |  |
| action_description | TEXT | 是 | '' |  |
| notes | TEXT | 是 | '' |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFEB560> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76EFEB600> |  |

- 主键：id

## 表 `metric_raws`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| device_id | VARCHAR(64) | 否 |  | INDEX |
| ts | DATETIME | 否 |  | INDEX 测点采样时间 |
| metric_name | VARCHAR(128) | 否 |  | INDEX |
| value | FLOAT | 否 |  |  |
| quality | VARCHAR(16) | 否 | 'good' | good/uncertain/bad |
| unit | VARCHAR(32) | 是 |  |  |
| tags | JSON | 否 | <function dict at 0x000001D76EF8E700> |  |
| received_at | DATETIME | 否 |  | 平台接收时间 |

- 主键：id

## 表 `point_data`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | BIGINT | 否 |  | PK |
| ts | DATETIME | 否 |  | PK 采集时间(分区键) |
| target_type | VARCHAR(16) | 否 |  | 对象类型: idc/cabinet/server/env |
| target_id | BIGINT | 否 |  | 对象ID |
| metric | VARCHAR(32) | 否 |  | 指标: temperature/humidity/cpu_usage/mem_usage/power_kw... |
| value | FLOAT | 否 |  | 数值 |
| unit | VARCHAR(16) | 否 | '' | 单位 |
| quality | SMALLINT | 否 | 100 | 数据质量 0-100 |

- 主键：id, ts

## 表 `risk_item`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| code | VARCHAR(32) | 是 | '' | INDEX |
| risk | TEXT | 是 | '' |  |
| cat | VARCHAR(64) | 是 | '' |  |
| prob | INTEGER | 是 | 2 |  |
| impact | INTEGER | 是 | 2 |  |
| level | VARCHAR(16) | 是 | '中' |  |
| ctrl | TEXT | 是 | '' |  |
| owner | VARCHAR(64) | 是 | '' |  |
| closed | INTEGER | 是 | 0 |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76F014B80> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76F014C20> |  |

- 主键：id

## 表 `roles`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| name | VARCHAR(32) | 否 |  | UNIQUE |
| label | VARCHAR(32) | 否 | '' |  |
| permissions | VARCHAR(1024) | 是 |  |  |
| created_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76F09D800> |  |

- 主键：id

## 表 `room`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| idc_id | INTEGER | 否 |  | FK→idc.id |
| code | VARCHAR(32) | 否 |  | 包间编号 R01 |
| name | VARCHAR(64) | 否 | '' |  |
| kind | VARCHAR(32) | 否 | 'it_room' | INDEX 房间类型 |
| floor | VARCHAR(16) | 否 | '' |  |
| rack_capacity | INTEGER | 否 | 0 |  |
| cold_aisle_t | FLOAT | 否 | 0 | 冷通道均温 |
| hot_aisle_t | FLOAT | 否 | 0 | 热通道均温 |
| rh | FLOAT | 否 | 0 | 相对湿度 |
| pressure_pa | FLOAT | 否 | 0 | 正压 Pa (参考: 5~10Pa) |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `server`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| cabinet_id | INTEGER | 否 |  | FK→cabinet.id 所在机柜 |
| asset_no | VARCHAR(64) | 否 |  | UNIQUE INDEX 资产编号 |
| hostname | VARCHAR(128) | 否 | '' |  |
| ip | VARCHAR(45) | 否 |  | INDEX 管理IP (IPv4/IPv6) |
| brand | VARCHAR(64) | 否 | '' | 厂商 |
| model | VARCHAR(128) | 否 | '' | 型号 |
| u_start | INTEGER | 否 |  | 起始U位 |
| u_end | INTEGER | 否 |  | 结束U位 |
| cpu_model | VARCHAR(128) | 否 | '' | CPU 型号 |
| cpu_count | INTEGER | 否 | 2 | CPU 颗数 |
| cpu_cores | INTEGER | 否 | 0 | 总核数 |
| memory_gb | INTEGER | 否 | 0 | 内存 GB |
| disk_desc | VARCHAR(255) | 否 | '' | 磁盘描述 |
| business | VARCHAR(128) | 否 | '' | INDEX 所属业务 |
| status | VARCHAR(16) | 否 | '在线' | INDEX 在线/离线/下架 |
| created_at | DATETIME | 否 |  |  |
| updated_at | DATETIME | 否 |  |  |

- 主键：id

## 表 `shift_schedule`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK INDEX |
| date | VARCHAR(16) | 否 |  | INDEX |
| shift | VARCHAR(16) | 是 | 'day' | INDEX |
| members | JSON | 是 | <function list at 0x000001D76F079080> |  |
| leader | VARCHAR(64) | 是 | '' |  |
| note | TEXT | 是 | '' |  |
| created_at | VARCHAR(32) | 是 | <function _now at 0x000001D76F079120> |  |
| updated_at | VARCHAR(32) | 是 | <function _now at 0x000001D76F0791C0> |  |

- 主键：id

## 表 `ticket`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | VARCHAR(32) | 否 |  | PK |
| title | VARCHAR(256) | 否 |  |  |
| sys | VARCHAR(64) | 否 | '' | INDEX |
| lv | VARCHAR(16) | 否 | 'info' | INDEX |
| state | VARCHAR(32) | 否 | 'open' | INDEX |
| owner | VARCHAR(64) | 否 | '待分配' |  |
| created | VARCHAR(32) | 否 | '' |  |
| created_by | VARCHAR(64) | 否 | 'system' |  |
| updated_at | VARCHAR(32) | 否 | '' |  |
| sla | VARCHAR(32) | 否 | '' |  |
| due_at | VARCHAR(32) | 是 |  |  |
| progress | INTEGER | 否 | 0 |  |
| source | VARCHAR(32) | 否 | 'manual' |  |
| source_alarm_id | VARCHAR(64) | 是 |  | INDEX |
| description | TEXT | 否 | '' |  |
| logs | JSON | 否 | <function list at 0x000001D76F07A480> |  |

- 主键：id

## 表 `user_role`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| user_id | INTEGER | 否 |  | PK FK→users.id |
| role_id | INTEGER | 否 |  | PK FK→roles.id |

- 主键：user_id, role_id

## 表 `users`

| 字段 | 类型 | 可空 | 默认 | 约束/说明 |
|------|------|------|------|-----------|
| id | INTEGER | 否 |  | PK |
| username | VARCHAR(64) | 否 |  | UNIQUE INDEX |
| password_hash | VARCHAR(255) | 否 |  |  |
| display_name | VARCHAR(64) | 否 | '' |  |
| email | VARCHAR(128) | 是 |  |  |
| phone | VARCHAR(32) | 是 |  |  |
| department | VARCHAR(64) | 否 | '' |  |
| is_active | BOOLEAN | 否 | True |  |
| is_superuser | BOOLEAN | 否 | False |  |
| last_login | DATETIME | 是 |  |  |
| created_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76F09C4A0> |  |
| updated_at | DATETIME | 否 | <function datetime.utcnow at 0x000001D76F09C540> |  |

- 主键：id


## 外键关系总览

- `cabinet.idc_id` → `idc.id`
- `drill_record.plan_id` → `drill_plan.id`
- `equipment.idc_id` → `idc.id`
- `equipment.room_id` → `room.id`
- `room.idc_id` → `idc.id`
- `server.cabinet_id` → `cabinet.id`
- `user_role.user_id` → `users.id`
- `user_role.role_id` → `roles.id`