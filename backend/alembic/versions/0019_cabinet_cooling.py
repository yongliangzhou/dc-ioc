"""阶段 1 · 机柜制冷能力字段（docs/design/06_ROADMAP.md §7 决策 1）。

用户确认机柜「制冷方式 / 额定制冷容量 kW」要在契约中存在。
新增两列，使用 IF NOT EXISTS 保证幂等；downgrade 对称。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0019_cabinet_cooling"
down_revision: Union[str, None] = "0018_tenant_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPGRADE = [
    "ALTER TABLE cabinet ADD COLUMN IF NOT EXISTS cooling_capability VARCHAR(16) DEFAULT '风冷'",
    "ALTER TABLE cabinet ADD COLUMN IF NOT EXISTS cooling_capacity_kw NUMERIC(8, 2) DEFAULT 0",
]
DOWNGRADE = [
    "ALTER TABLE cabinet DROP COLUMN IF EXISTS cooling_capacity_kw",
    "ALTER TABLE cabinet DROP COLUMN IF EXISTS cooling_capability",
]


def upgrade() -> None:
    bind = op.get_bind()
    for ddl in UPGRADE:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    for ddl in DOWNGRADE:
        bind.execute(text(ddl))
