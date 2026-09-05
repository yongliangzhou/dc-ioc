"""统一告警触达中心两表 (production migration)。

生产库由本修订补齐；开发/测试库由 lifespan 逐表 create_all 兜底建表
（NotificationChannel / NotificationRecord 均注册于 app.models）。

- notification_channel : 通知通道配置 (类型/URL/最低级别/静默窗口/启停)。
- notification_record  : 每次触达尝试留痕 (sent/failed/muted/dedup)，
  附 dedup 复合索引 (alarm_id, channel_id, created_at) 供去重判定。

全部 IF NOT EXISTS，与 lifespan create_all 幂等共存；
downgrade 对称 DROP TABLE IF EXISTS（索引随表删除）。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0012_notification"
down_revision: Union[str, None] = "0011_graphic_editor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHANNEL_DDL = """
CREATE TABLE IF NOT EXISTS notification_channel (
    id           BIGSERIAL      NOT NULL,
    type         VARCHAR(32)    NOT NULL,
    name         VARCHAR(64)    NOT NULL,
    url          TEXT           NULL,
    min_level    VARCHAR(8)     NOT NULL DEFAULT 'crit',
    quiet_start  VARCHAR(5)     NULL,
    quiet_end    VARCHAR(5)     NULL,
    enabled      BOOLEAN        NOT NULL DEFAULT TRUE,
    updated_by   VARCHAR(64)    NULL DEFAULT 'system',
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT pk_notification_channel PRIMARY KEY (id)
)
"""

_RECORD_DDL = """
CREATE TABLE IF NOT EXISTS notification_record (
    id           BIGSERIAL      NOT NULL,
    alarm_id     VARCHAR(64)    NULL,
    channel_id   BIGINT         NOT NULL,
    channel_name VARCHAR(64)    NULL,
    level        VARCHAR(8)     NOT NULL,
    title        VARCHAR(255)   NOT NULL,
    status       VARCHAR(16)    NOT NULL DEFAULT 'sent',
    error        TEXT           NULL,
    retry_count  INTEGER        NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT pk_notification_record PRIMARY KEY (id)
)
"""

_RECORD_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_notification_record_alarm_id ON notification_record (alarm_id)",
    "CREATE INDEX IF NOT EXISTS ix_notification_record_channel_id ON notification_record (channel_id)",
    # 去重判定复合索引 (与模型 __table_args__ 一致)
    "CREATE INDEX IF NOT EXISTS ix_notification_record_dedup "
    "ON notification_record (alarm_id, channel_id, created_at)",
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(_CHANNEL_DDL))
    bind.execute(text(_RECORD_DDL))
    for ddl in _RECORD_INDEXES:
        bind.execute(text(ddl))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS notification_record"))
    bind.execute(text("DROP TABLE IF EXISTS notification_channel"))
