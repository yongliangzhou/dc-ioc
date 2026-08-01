"""capacity_energy_history: 容量/能耗分析型长期时序表 (B4)

Revision ID: 0004_capacity_energy_history
Revises: 0003_metric_raw_unique
Create Date: 2026-07-30

说明:
- 与 metric_raws 解耦的独立表, 由每日 rollup 写入, 不受 P0-1 retention 清理影响,
  使容量/能耗历史长期留存 (不再依赖快照逆推)。
- 大表/已上线库也可用 deploy/sql/008_capacity_energy_history.sql 手动建表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_capacity_energy_history"
down_revision: Union[str, None] = "0003_metric_raw_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capacity_energy_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("idc_code", sa.String(length=32), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idc_code", "metric_key", "bucket", name="uq_ceh_scope_key_bucket"),
    )
    op.create_index("ix_ceh_key_bucket", "capacity_energy_history", ["metric_key", "bucket"])


def downgrade() -> None:
    op.drop_index("ix_ceh_key_bucket", table_name="capacity_energy_history")
    op.drop_table("capacity_energy_history")
