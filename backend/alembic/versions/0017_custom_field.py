"""阶段三 · 自定义字段定义表 + equipment 扩展列 (production migration)。

注意: equipment.custom_attributes 用 `ADD COLUMN IF NOT EXISTS`, 存量数据不受影响。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0017_custom_field"
down_revision: Union[str, None] = "0016_procurement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DDL = [
    """CREATE TABLE IF NOT EXISTS custom_field_def (
        id SERIAL PRIMARY KEY, key VARCHAR(64) NOT NULL UNIQUE,
        label_zh VARCHAR(128) NOT NULL, label_en VARCHAR(128) DEFAULT '',
        type VARCHAR(16) NOT NULL DEFAULT 'text', options JSONB DEFAULT '[]'::jsonb,
        required BOOLEAN DEFAULT FALSE, applies_to VARCHAR(64) DEFAULT '*',
        tenant_id INTEGER NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS custom_attributes JSONB DEFAULT '{}'::jsonb",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in DDL:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS custom_field_def"))
    bind.execute(text("ALTER TABLE equipment DROP COLUMN IF EXISTS custom_attributes"))
