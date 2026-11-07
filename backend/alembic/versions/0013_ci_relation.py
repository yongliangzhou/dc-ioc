"""CMDB CI 关系表 (阶段二 · production migration)。

生产库由本修订补齐；开发/测试库由 lifespan 逐表 create_all 兜底建表
(CiRelation 已注册于 app.models)。

- ci_relation : 有向 CI 关系 (source_ci -> target_ci + relation_type)
- 预留 tenant_id 列供阶段四行级隔离使用 (本阶段不做过滤)

全部 IF NOT EXISTS，与 lifespan create_all 幂等共存；downgrade 对称。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0013_ci_relation"
down_revision: Union[str, None] = "0012_notification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ci_relation (
    id            SERIAL         NOT NULL,
    source_ci     VARCHAR(128)   NOT NULL,
    target_ci     VARCHAR(128)   NOT NULL,
    source_name   VARCHAR(128)   DEFAULT '',
    target_name   VARCHAR(128)   DEFAULT '',
    relation_type VARCHAR(32)    NOT NULL DEFAULT 'connects_to',
    description   TEXT           DEFAULT '',
    created_by    VARCHAR(64)    DEFAULT 'system',
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT now(),
    tenant_id     INTEGER        NULL,
    CONSTRAINT pk_ci_relation PRIMARY KEY (id),
    CONSTRAINT uq_ci_relation_edge UNIQUE (source_ci, target_ci, relation_type)
)
"""

_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS ix_ci_relation_source_ci ON ci_relation (source_ci)",
    "CREATE INDEX IF NOT EXISTS ix_ci_relation_target_ci ON ci_relation (target_ci)",
    "CREATE INDEX IF NOT EXISTS ix_ci_relation_pair ON ci_relation (source_ci, target_ci)",
    "CREATE INDEX IF NOT EXISTS ix_ci_relation_tenant ON ci_relation (tenant_id, created_at)",
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(_TABLE_DDL))
    for ddl in _INDEX_DDL:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS ci_relation"))
