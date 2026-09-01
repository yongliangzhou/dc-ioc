"""枚举字典化 -> CHECK 约束 (数据库设计文档 第八章 8.4)

为低基数枚举列补齐 DB CHECK 约束, 防止脏值写入。约束值集以 app.core.enums
为单一事实源 (与开发库实际取值对齐, 不破坏历史行)。

生产库经本修订补齐约束 (开发/测试库由 app.core.lifespan._ensure_check_constraints
自愈, 无需手动执行)。downgrade 删除这些约束。

约束采用 DO 块幂等创建 (已存在则跳过); 若目标表已有不满足约束的数据,
ADD CONSTRAINT 会校验失败并中断迁移 —— 需先清洗脏数据再升级。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.core.enums import CHECK_SPECS, constraint_name, check_condition

revision: str = "0006_ck_constraints"
down_revision: Union[str, None] = "0005_audit_softdelete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    for table, column, _values, _is_text in CHECK_SPECS:
        cname = constraint_name(table, column)
        cond = check_condition(table, column)
        ddl = (
            "DO $$\n"
            "BEGIN\n"
            f"  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{cname}') THEN\n"
            f"    ALTER TABLE {table} ADD CONSTRAINT {cname} CHECK ({cond});\n"
            "  END IF;\n"
            "END\n"
            "$$;"
        )
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for table, column, _values, _is_text in CHECK_SPECS:
        cname = constraint_name(table, column)
        bind.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {cname}"))
