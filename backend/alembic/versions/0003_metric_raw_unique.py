"""metric_raws idempotent unique constraint (P1-4)

Revision ID: 0003_metric_raw_unique
Revises: 0002_external_device_metric
Create Date: 2026-07-30

说明:
- 为 metric_raws 增加 (device_id, metric_name, ts) 唯一约束,
  配合后端 bulk_insert_metrics 的 ON CONFLICT DO NOTHING,
  实现 Kafka at-least-once 重投的测点幂等去重 (P1-4)。
- 大表请用 deploy/sql/007_metric_raw_unique.sql 的 CONCURRENTLY 版本零锁建索引。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_metric_raw_unique"
down_revision: Union[str, None] = "0002_external_device_metric"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # 1) 清理历史重复行 (同 device_id/metric_name/ts 仅保留 id 最大一条)
    bind.execute(
        sa.text(
            """
            DELETE FROM metric_raws a
            USING metric_raws b
            WHERE a.device_id = b.device_id
              AND a.metric_name = b.metric_name
              AND a.ts = b.ts
              AND a.id < b.id
            """
        )
    )
    # 2) 增加唯一约束 (普通建索引会短暂锁表; 大表见 deploy/sql/007)
    #    用 IF NOT EXISTS 防止与 create_all 已建索引冲突。
    bind.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_metric_raw_device_name_ts "
            "ON metric_raws (device_id, metric_name, ts)"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DROP INDEX IF EXISTS uq_metric_raw_device_name_ts")
    )
