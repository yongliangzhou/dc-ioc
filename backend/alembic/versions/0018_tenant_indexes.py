"""阶段四 · 多租户复合索引 (production migration)。

所有阶段二/三新增表已含可空 tenant_id; 本修订补齐 (tenant_id, created_at/id)
复合索引, 供 ORM 全局过滤走索引。全部 IF NOT EXISTS, downgrade 对称。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0018_tenant_indexes"
down_revision: Union[str, None] = "0017_custom_field"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_ci_relation_tenant_created ON ci_relation (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_ip_vlan_tenant_created ON ip_vlan (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_ip_subnet_tenant_created ON ip_subnet (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_ip_address_tenant_created ON ip_address (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_discovery_tenant_status ON discovery_candidate (tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_purchase_tenant_created ON purchase_order (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_stocktake_task_tenant_created ON stocktake_task (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_stocktake_item_tenant_task ON stocktake_item (tenant_id, task_id)",
    "CREATE INDEX IF NOT EXISTS ix_custom_field_tenant_created ON custom_field_def (tenant_id, created_at)",
]
DROP = [
    "DROP INDEX IF EXISTS ix_ci_relation_tenant_created",
    "DROP INDEX IF EXISTS ix_ip_vlan_tenant_created",
    "DROP INDEX IF EXISTS ix_ip_subnet_tenant_created",
    "DROP INDEX IF EXISTS ix_ip_address_tenant_created",
    "DROP INDEX IF EXISTS ix_discovery_tenant_status",
    "DROP INDEX IF EXISTS ix_purchase_tenant_created",
    "DROP INDEX IF EXISTS ix_stocktake_task_tenant_created",
    "DROP INDEX IF EXISTS ix_stocktake_item_tenant_task",
    "DROP INDEX IF EXISTS ix_custom_field_tenant_created",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in INDEXES:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for ddl in DROP:
        bind.execute(text(ddl))
