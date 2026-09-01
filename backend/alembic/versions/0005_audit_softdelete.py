"""统一审计与软删除基类 (数据库设计文档 第八章 8.1)

为业务表补齐审计人 (created_by / updated_by) 与软删除 (deleted_at) 列:
  - 审计 Mixin: 所有业务实体继承 AuditMixin, 列默认 'system'
  - 软删除 Mixin: ticket / workflow_item / maintenance_* / risk_item / drill_* /
    inspection_* / knowledge_item / thing_model / tenant / shift_* 继承 SoftDeleteMixin

生产库经本修订补齐新列 (开发/测试库由 app.core.lifespan._ensure_missing_columns
自愈, 无需手动执行)。downgrade 删除这些列。

Revision ID: 0005_audit_softdelete
Revises: 0004_capacity_energy_history
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

from app.models import Base

revision: str = "0005_audit_softdelete"
down_revision: Union[str, None] = "0004_capacity_energy_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _targets() -> list[tuple[str, str]]:
    """枚举所有模型上由审计/软删除 Mixin 引入的列 (表, 列)。"""
    out: list[tuple[str, str]] = []
    for mapper in Base.registry.mappers:
        model = mapper.class_
        tbl = getattr(model, "__tablename__", None)
        if not tbl:
            continue
        for col in model.__table__.columns:
            if col.name in ("created_by", "updated_by", "deleted_at"):
                out.append((tbl, col.name))
    return out


def upgrade() -> None:
    bind = op.get_bind()
    for table, col in _targets():
        if col == "deleted_at":
            ddl = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ"
        else:
            ddl = (
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} "
                f"VARCHAR(64) NOT NULL DEFAULT 'system'"
            )
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for table, col in _targets():
        bind.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}"))
