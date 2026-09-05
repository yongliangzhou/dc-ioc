"""统一图形编辑入口两表 + 列漂移补齐 (production migration)。

生产库由本修订补齐；开发/测试库由 lifespan 逐表 create_all 兜底建表
（graphic_config / refuel_record 均注册于 app.models，会被 create_all 自动建出）。

内容：
1. graphic_config      —— 统一图形编辑入口的场景覆盖层存储 (kind 主键 + JSONB payload)。
2. refuel_record       —— 储油系统加油/补油记录 (no 业务唯一键)，含唯一索引 ix_refuel_record_no。
3. 列漂移补齐（幂等，仅当表已存在时执行）：
   - knowledge_item.review_status/reviewer/reviewed_at/review_note
   - inspection_route.name/description
   这 6 列在开发库靠 lifespan._ensure_missing_columns 自愈补齐，但生产迁移链
   0001~0010 均未覆盖（create_all 只补缺失表、不改已有表结构），故在此补上，
   与 _ensure_missing_columns 的列定义保持一致。

全部使用 IF NOT EXISTS / DO 块守卫，可与 lifespan create_all 幂等共存
（create_all checkfirst=True 只判表名，故唯一索引单独用 IF NOT EXISTS 补齐）。

downgrade: 对称 DROP TABLE IF EXISTS（索引随表删除）；补列的漂移修复不回滚
（与 0007/0008 惯例一致——有数据丢失风险的回退不做，删列会丢业务数据）。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0011_graphic_editor"
down_revision: Union[str, None] = "0010_timeseries_hypertable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 与 app/models/graphic_config.py 列定义一致 (kind 业务主键 + JSONB payload)
_GRAPHIC_CONFIG_DDL = """
CREATE TABLE IF NOT EXISTS graphic_config (
    kind        VARCHAR(64)    NOT NULL,
    title       VARCHAR(128)   NULL,
    payload     JSONB          NULL,
    updated_by  VARCHAR(64)    NULL DEFAULT 'system',
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT pk_graphic_config PRIMARY KEY (kind)
)
"""

# 与 app/models/refuel_record.py 列定义一致 (no 业务唯一键 + 前后液位百分比)
_REFUEL_RECORD_DDL = """
CREATE TABLE IF NOT EXISTS refuel_record (
    id          BIGSERIAL      NOT NULL,
    no          VARCHAR(64)    NOT NULL,
    date        VARCHAR(32)    NOT NULL,
    tank        VARCHAR(64)    NULL DEFAULT '',
    amount      DOUBLE PRECISION NULL DEFAULT 0,
    before_pct  DOUBLE PRECISION NULL,
    after_pct   DOUBLE PRECISION NULL,
    vendor      VARCHAR(128)   NULL DEFAULT '',
    grade       VARCHAR(64)    NULL DEFAULT '',
    qc          VARCHAR(32)    NULL DEFAULT '',
    operator    VARCHAR(64)    NULL DEFAULT '',
    status      VARCHAR(32)    NOT NULL DEFAULT '已完成',
    note        TEXT           NULL,
    created_by  VARCHAR(64)    NULL DEFAULT 'system',
    updated_by  VARCHAR(64)    NULL DEFAULT 'system',
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT pk_refuel_record PRIMARY KEY (id)
)
"""

# create_all 的 Column(unique=True, index=True) 会生成唯一索引 ix_refuel_record_no；
# 若表由本迁移先建（表内已带 uq 约束），该索引补建与约束语义重复但无害，
# 统一用 IF NOT EXISTS 保证"表已存在但索引缺失"的旧库也能补上。
_REFUEL_NO_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS ix_refuel_record_no ON refuel_record (no)
"""

# 列漂移补齐：仅当目标表存在时执行（生产老库可能已由早期 create_all 建表）。
# 列定义与 lifespan._ensure_missing_columns 的 specs 逐项一致 (L41-50)。
_COLUMN_DRIFT_FIXES = [
    (
        "knowledge_item",
        [
            ("review_status", "VARCHAR(16) DEFAULT 'approved'"),
            ("reviewer", "VARCHAR(64) DEFAULT ''"),
            ("reviewed_at", "VARCHAR(32) DEFAULT ''"),
            ("review_note", "TEXT DEFAULT ''"),
        ],
    ),
    (
        "inspection_route",
        [
            ("name", "VARCHAR(128) DEFAULT ''"),
            ("description", "TEXT DEFAULT ''"),
        ],
    ),
]


def _column_fix_sql(table: str, col: str, ddl: str) -> str:
    return (
        f"DO $$ BEGIN "
        f"IF to_regclass('{table}') IS NOT NULL "
        f"AND NOT EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{col}') "
        f"THEN ALTER TABLE {table} ADD COLUMN {col} {ddl}; END IF; END $$;"
    )


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(_GRAPHIC_CONFIG_DDL))
    bind.execute(text(_REFUEL_RECORD_DDL))
    bind.execute(text(_REFUEL_NO_INDEX_DDL))
    for table, cols in _COLUMN_DRIFT_FIXES:
        for col, ddl in cols:
            bind.execute(text(_column_fix_sql(table, col, ddl)))


def downgrade() -> None:
    # 漂移补列不回滚（删列丢业务数据，与 0007/0008 惯例一致）；
    # 两张表为本修订新建，对称删除。
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS refuel_record"))
    bind.execute(text("DROP TABLE IF EXISTS graphic_config"))
