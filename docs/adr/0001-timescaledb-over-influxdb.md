# ADR-0001: 时序存储选择 TimescaleDB 而非 InfluxDB

- 状态: 已接受
- 日期: 2026-07-23
- 决策者: 平台架构

## 背景

平台同时存在两类数据：①设备台账、工单、告警、用户等强关系型业务数据；②采集器高频上报的测点时序数据（`metric_raws`）。需要一个既能承载时序写入/压缩/保留策略，又不引入第二套数据库运维体系的方案。约束：单机 Docker Compose 可跑、团队以 SQL 为主、需要和业务表做 JOIN（如「某机柜下所有设备的近 1h 温度」）。

## 决策

采用 **PostgreSQL 16 + TimescaleDB 扩展**，业务表与时序超表同库：

- `metric_raws` 建为 hypertable，按时间分区；
- 7 天后启用列式压缩、90 天保留策略、5min/1h 连续聚合；
- 高频查询依赖复合索引（见 `backend/deploy/sql/013_timeseries_optimization.sql`）；
- 业务表保持普通 SQLAlchemy ORM 模型，跨「设备 → 测点」查询用原生 SQL JOIN。

## 备选方案

| 方案 | 优点 | 否决原因 |
|---|---|---|
| InfluxDB + PostgreSQL 双库 | 时序写入吞吐高、Prometheus 生态成熟 | 两套备份/监控/连接池；业务表与测点无法 JOIN，跨库一致性需应用层拼装 |
| PostgreSQL 普通分区表 | 无扩展依赖 | 需手写分区维护、压缩与连续聚合，工作量大于收益 |
| ClickHouse | 分析型查询极快 | 对事务型业务数据不友好，运维复杂度高 |
| MongoDB 时间序列集合 | 模式灵活 | 与既有 SQLAlchemy 关系模型割裂，团队熟悉度低 |

## 后果

### 正面
- 单一数据库：备份 (`pg_dump`)、迁移 (Alembic)、监控、连接池统一。
- 时序与业务数据可 JOIN；SQL 技能复用。
- 压缩/保留/连续聚合由扩展声明式管理。

### 负面 / 需承担的成本
- 部署镜像必须是 `timescale/timescaledb` 或安装扩展的 PG，`deploy/sql/init.sql` 有前置依赖。
- 超表不能直接作为 Alembic autogenerate 的普通表处理，需要专用 SQL 脚本（`003` / `005` / `013`）。
- SQLite 单测无法覆盖 PG 方言类型（JSONB / hypertable），测试中需用 `pre_ddl` 或泛型类型规避（见 `tests/conftest.py`）。

### 后续动作
- 压测 `tests/load/locustfile.py` 覆盖写入端点，观察压缩窗口前后的写入延迟。
- 若未来测点数超单机承载，再评估分层（保留 PG 业务库，仅把原始测点外置）。
