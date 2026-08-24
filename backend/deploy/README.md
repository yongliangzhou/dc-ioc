# 5.3.3 数据库迁移与初始化策略

> 本文档说明 dc-ioc-platform 后端的数据库 schema 演进、初始化与数据恢复策略。

## 1. Schema 演进机制

后端采用 **"Alembic 可选 + 代码兜底"** 的混合策略：

| 机制 | 位置 | 作用 | 适用场景 |
| --- | --- | --- | --- |
| `Base.metadata.create_all` | `app/db/session.py`（lifespan 启动） | 自动按 ORM 模型建表，表不存在则创建 | 开发 / 首次部署 / 新增表 |
| Alembic 迁移链 | `alembic/versions/*.py` | 增量变更（加列、改类型、建索引） | 生产环境受控变更 |
| `deploy/sql/*.sql` | 部署脚本 | TimescaleDB 超表、压缩策略、索引、种子 | 时序优化 / 性能 |

> **关键约定**：`create_all` 只创建**不存在的表**，不会修改已存在的表结构。因此对已上线环境的列变更，必须走 Alembic 或手工 SQL。

## 2. 首次部署流程

```bash
# 1. 启动数据库(TimescaleDB)后, 应用首次启动会自动 create_all 建表
docker compose up -d db backend

# 2. 初始化时序超表与压缩策略(幂等, 仅首次需执行)
psql "$DATABASE_URL" -f deploy/sql/003_point_data_hypertable.sql
psql "$DATABASE_URL" -f deploy/sql/009_index_optimization.sql

# 3. 种子管理员 + 演示数据
python seed_admin.py            # 创建 admin / operator / viewer 三账号
python seed_demo.py             # 可选: 灌入拓扑/设备/知识库演示数据
```

## 3. 版本升级（生产）

1. **新增表**：由 `create_all` 自动完成，无需迁移。
2. **修改表结构**（加列/改类型）：
   - 在 `alembic/versions/` 新增一个 revision（down_revision 指向最新 head）。
   - 编写 `upgrade()` / `downgrade()`，仅做前向兼容变更（不删列、不改主键）。
   - 执行 `alembic upgrade head`。
3. **索引/超表类优化**：放入 `deploy/sql/` 并以 `IF NOT EXISTS` 保证幂等，随版本随附执行说明。

## 4. 回滚策略

- **表结构**：Alembic `downgrade` 可回退至任意历史版本；若未走 Alembic，需手工编写反向 SQL 并在测试库验证。
- **数据**：见备份文档 `backup.sh` + 5.6.1 定期全量/增量备份。回滚数据采用 `pg_restore`（全量）或 WAL 时间点恢复（PITR，需归档开启）。

## 5. 多环境一致性

| 环境 | Schema 来源 | 说明 |
| --- | --- | --- |
| 本地开发 | `create_all` 自动 | 快速迭代 |
| 测试 | `create_all` + 种子 | 每次重建 |
| 生产 | Alembic head | 受控、可审计 |

> 建议 CI 中加入 `alembic check`（若启用）或 `create_all` 与模型的一致性校验，避免 ORM 与迁移漂移。

## 6. 种子数据管理

- `seed_admin.py`：**幂等**，已存在同名用户则跳过（不覆盖密码）。
- `seed_demo.py`：演示数据，建议仅在非生产环境运行；带 `--force` 可清空重建演示集。
- 种子数据**不应**包含真实生产凭证；密码统一通过环境变量注入或安全默认值。
