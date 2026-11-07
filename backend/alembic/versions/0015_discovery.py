"""阶段三 · 自动发现待确认区 (production migration)。"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0015_discovery"
down_revision: Union[str, None] = "0014_ipam"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DDL = [
    """CREATE TABLE IF NOT EXISTS discovery_candidate (
        id SERIAL PRIMARY KEY, ip VARCHAR(64) NOT NULL UNIQUE,
        hostname VARCHAR(128) DEFAULT '', mac VARCHAR(64) DEFAULT '',
        open_ports JSONB DEFAULT '[]'::jsonb, source VARCHAR(32) DEFAULT 'tcp-probe',
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        first_seen VARCHAR(32) DEFAULT '', last_seen VARCHAR(32) DEFAULT '',
        matched_ci VARCHAR(128) DEFAULT '', tenant_id INTEGER NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_discovery_status ON discovery_candidate (status, last_seen)",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in DDL:
        bind.execute(text(ddl))


def downgrade() -> None:
    op.get_bind().execute(text("DROP TABLE IF EXISTS discovery_candidate"))
