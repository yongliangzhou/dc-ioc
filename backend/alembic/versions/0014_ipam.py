"""阶段三 · IPAM 三表 (production migration)。"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0014_ipam"
down_revision: Union[str, None] = "0013_ci_relation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DDL = [
    """CREATE TABLE IF NOT EXISTS ip_vlan (
        id SERIAL PRIMARY KEY, vlan_id INTEGER NOT NULL UNIQUE,
        name VARCHAR(128) DEFAULT '', site VARCHAR(64) DEFAULT '',
        description TEXT DEFAULT '', tenant_id INTEGER NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS ip_subnet (
        id SERIAL PRIMARY KEY, cidr VARCHAR(64) NOT NULL UNIQUE,
        vlan_id INTEGER NULL, gateway VARCHAR(64) DEFAULT '',
        description TEXT DEFAULT '', tenant_id INTEGER NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS ip_address (
        id SERIAL PRIMARY KEY, address VARCHAR(64) NOT NULL UNIQUE,
        subnet_id INTEGER NULL, status VARCHAR(16) NOT NULL DEFAULT 'allocated',
        device_ci VARCHAR(128) DEFAULT '', note TEXT DEFAULT '',
        tenant_id INTEGER NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "CREATE INDEX IF NOT EXISTS ix_ip_subnet_vlan ON ip_subnet (vlan_id)",
    "CREATE INDEX IF NOT EXISTS ix_ip_address_subnet ON ip_address (subnet_id)",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in DDL:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("ip_address", "ip_subnet", "ip_vlan"):
        bind.execute(text(f"DROP TABLE IF EXISTS {table}"))
