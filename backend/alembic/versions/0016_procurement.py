"""阶段三 · 采购合同 / 盘点任务 (production migration)。"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0016_procurement"
down_revision: Union[str, None] = "0015_discovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DDL = [
    """CREATE TABLE IF NOT EXISTS purchase_order (
        id SERIAL PRIMARY KEY, order_no VARCHAR(64) NOT NULL UNIQUE,
        vendor VARCHAR(128) DEFAULT '', category VARCHAR(64) DEFAULT '',
        quantity INTEGER DEFAULT 1, amount DOUBLE PRECISION DEFAULT 0,
        purchase_date VARCHAR(16) DEFAULT '', warranty_until VARCHAR(16) DEFAULT '',
        contract_no VARCHAR(64) DEFAULT '', status VARCHAR(16) DEFAULT 'active',
        note TEXT DEFAULT '', tenant_id INTEGER NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS stocktake_task (
        id SERIAL PRIMARY KEY, name VARCHAR(128) NOT NULL, scope VARCHAR(128) DEFAULT '',
        status VARCHAR(16) DEFAULT 'open', created_by VARCHAR(64) DEFAULT 'system',
        started_at VARCHAR(32) DEFAULT '', finished_at VARCHAR(32) DEFAULT '',
        tenant_id INTEGER NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS stocktake_item (
        id SERIAL PRIMARY KEY, task_id INTEGER NOT NULL, asset_ci VARCHAR(128) NOT NULL,
        expected_location VARCHAR(128) DEFAULT '', result VARCHAR(16) DEFAULT 'matched',
        confirmed_by VARCHAR(64) DEFAULT '', confirmed_at VARCHAR(32) DEFAULT '',
        tenant_id INTEGER NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_purchase_warranty ON purchase_order (warranty_until)",
    "CREATE INDEX IF NOT EXISTS ix_stocktake_item_task_ci ON stocktake_item (task_id, asset_ci)",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in DDL:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("stocktake_item", "stocktake_task", "purchase_order"):
        bind.execute(text(f"DROP TABLE IF EXISTS {table}"))
