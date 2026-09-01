"""外键约束补全 阶段一 (数据库设计文档 第八章 8.3)

对现有逻辑关联补 DB 外键并设级联/置空:
external_devices.idc_id->idc.id, alarm_event.device_id->external_devices.device_id,
alarm_event.rule_id->alarm_rule.rule_id, alarm_feedback.alarm_id->alarm_event.id,
ticket.source_alarm_id->alarm_event.id, metric_defs/metric_raws.device_id->
external_devices.device_id, maintenance_record.plan_id(新增)->maintenance_plan.id。
开发库由 app.core.lifespan._ensure_fk_constraints 自愈。

前置: external_devices.idc_id 先统一 BIGINT (FK 目标 idc.id 已是 BIGINT);
子表空字符串置 NULL; maintenance_record 新增 plan_id 列并从 plan_code 迁移。
幂等 (约束已存在则跳过)。若生产库存在脏数据 (子表孤儿值), ADD CONSTRAINT 会失败
(报错中断迁移, 需先清洗) — 与 8.4 CHECK 约束一致, 属预期强一致行为。

downgrade: 仅撤销本迁移新增的 8 个 FK 约束 + 删除 plan_id 列; idc_id 类型不回退
INTEGER (避免超范围丢数据), 空字符串置 NULL 不可逆但无害。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.core.fk import (
    FK_CONSTRAINTS, EMPTY_NULL_CLEANUP, IDC_ID_BIGINT_TABLE, IDC_ID_COLUMN,
    PLAN_ID_TABLE, PLAN_ID_COLUMN, PLAN_CODE_COLUMN, fk_constraint_name, ondelete_clause,
)

revision: str = "0008_fk_constraints"
down_revision: Union[str, None] = "0007_bigint_pk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _guard_bigint_ddl(table: str, column: str) -> str:
    return (
        "DO $$\nBEGIN\n"
        f"  IF EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}' AND data_type <> 'bigint') THEN\n"
        f"    ALTER TABLE {table} ALTER COLUMN {column} TYPE BIGINT;\n"
        "  END IF;\nEND $$;"
    )


def upgrade() -> None:
    bind = op.get_bind()
    # 1) idc_id 统一 BIGINT
    bind.execute(text(_guard_bigint_ddl(IDC_ID_BIGINT_TABLE, IDC_ID_COLUMN)))
    # 2) 子表空字符串置 NULL
    for table, column in EMPTY_NULL_CLEANUP:
        bind.execute(text(f"UPDATE {table} SET {column} = NULL WHERE {column} = ''"))
    # 3) maintenance_record.plan_id 列 + 迁移
    bind.execute(text(
        f"ALTER TABLE {PLAN_ID_TABLE} ADD COLUMN IF NOT EXISTS {PLAN_ID_COLUMN} BIGINT"
    ))
    bind.execute(text(
        f"UPDATE {PLAN_ID_TABLE} SET {PLAN_ID_COLUMN} = ("
        f"SELECT MIN(mp.id) FROM maintenance_plan mp "
        f"WHERE mp.code = {PLAN_ID_TABLE}.{PLAN_CODE_COLUMN}) "
        f"WHERE {PLAN_ID_COLUMN} IS NULL AND {PLAN_CODE_COLUMN} <> ''"
    ))
    # 4) 逐个建 FK 约束 (幂等)
    for child_table, child_col, parent_table, parent_col, ondelete in FK_CONSTRAINTS:
        cname = fk_constraint_name(child_table, child_col)
        ddl = (
            f"DO $$\nBEGIN\n"
            f"  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='{cname}') THEN\n"
            f"    ALTER TABLE {child_table} ADD CONSTRAINT {cname} "
            f"FOREIGN KEY ({child_col}) REFERENCES {parent_table}({parent_col})"
            f"{ondelete_clause(ondelete)};\n"
            f"  END IF;\nEND $$;"
        )
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for child_table, child_col, parent_table, parent_col, ondelete in FK_CONSTRAINTS:
        cname = fk_constraint_name(child_table, child_col)
        bind.execute(text(f"ALTER TABLE {child_table} DROP CONSTRAINT IF EXISTS {cname}"))
    bind.execute(text(f"ALTER TABLE {PLAN_ID_TABLE} DROP COLUMN IF EXISTS {PLAN_ID_COLUMN}"))
