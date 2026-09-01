"""主键 BIGINT 化 (数据库设计文档 第八章 8.2)

内部关联表 Integer 自增主键与外键列统一改为 BIGINT, 重建外键约束,
SERIAL 序列提升为 BIGINT。开发库由 app.core.lifespan._ensure_bigint_pk 自愈,
无需手动执行。downgrade 仅撤销外键约束 (列类型回退 BIGINT->INTEGER 有数据溢出风险, 不做)。

顺序: 先 drop 外键并改子列为 BIGINT, 再改主键列, 最后重建外键。幂等
(已为 bigint 跳过 / 约束已存在跳过)。存量数据不会超 INTEGER 范围, ALTER 安全。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.core.pk import (
    PK_BIGINT_TABLES, FK_BIGINT_SPECS, fk_constraint_name, ondelete_clause,
)

revision: str = "0007_bigint_pk"
down_revision: Union[str, None] = "0006_ck_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alter_ddl(table: str, column: str) -> str:
    return (
        "DO $$\nBEGIN\n"
        f"  IF EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}' AND data_type <> 'bigint') THEN\n"
        f"    ALTER TABLE {table} ALTER COLUMN {column} TYPE BIGINT;\n"
        "  END IF;\nEND $$;"
    )


def upgrade() -> None:
    bind = op.get_bind()
    # 阶段一: drop 外键 + 子列改 BIGINT
    for fk_table, fk_col, pk_table, pk_col, ondelete in FK_BIGINT_SPECS:
        con = bind.execute(
            text(
                "SELECT c.conname FROM pg_constraint c "
                "JOIN pg_class t ON c.conrelid = t.oid "
                "JOIN pg_class p ON c.confrelid = p.oid "
                "WHERE t.relname = :ft AND p.relname = :pt AND c.contype='f'"
            ),
            {"ft": fk_table, "pt": pk_table},
        ).fetchone()
        if con is not None:
            bind.execute(text(f"ALTER TABLE {fk_table} DROP CONSTRAINT IF EXISTS {con[0]}"))
        bind.execute(text(_alter_ddl(fk_table, fk_col)))
    # 阶段二: 主键列改 BIGINT
    for table in PK_BIGINT_TABLES:
        bind.execute(text(_alter_ddl(table, "id")))
    # 阶段三: 重建外键约束 (两侧均为 BIGINT), 幂等 (已存在则跳过)
    for fk_table, fk_col, pk_table, pk_col, ondelete in FK_BIGINT_SPECS:
        cname = fk_constraint_name(fk_table, fk_col)
        ddl = (
            f"DO $$\nBEGIN\n"
            f"  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='{cname}') THEN\n"
            f"    ALTER TABLE {fk_table} ADD CONSTRAINT {cname} "
            f"FOREIGN KEY ({fk_col}) REFERENCES {pk_table}({pk_col})"
            f"{ondelete_clause(ondelete)};\n"
            f"  END IF;\nEND $$;"
        )
        bind.execute(text(ddl))
    # 序列提升为 BIGINT
    for table in PK_BIGINT_TABLES:
        bind.execute(
            text(
                f"DO $$\nBEGIN\n"
                f"  IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename='{table}_id_seq') THEN\n"
                f"    ALTER SEQUENCE {table}_id_seq AS BIGINT;\n"
                f"  END IF;\nEND $$;"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    # 仅撤销外键约束; 列类型保持 BIGINT (回退 INTEGER 可能丢失超范围数据)。
    for fk_table, fk_col, pk_table, pk_col, ondelete in FK_BIGINT_SPECS:
        cname = fk_constraint_name(fk_table, fk_col)
        bind.execute(text(f"ALTER TABLE {fk_table} DROP CONSTRAINT IF EXISTS {cname}"))
