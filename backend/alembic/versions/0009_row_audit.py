"""敏感表行级审计 (数据库设计文档 第八章 8.5 ③: 扩展性-审计与追踪)

为敏感表 users/roles/tenant 建立行级变更审计: row_audit 表 + audit_row_change()
触发器函数 + 三表 AFTER INSERT/UPDATE/DELETE 触发器, 记录变更前后脱敏行(JSONB)
与操作人(取自 GUC app.audit_user, 回退 current_user)。

开发/测试库由 app.core.lifespan._ensure_row_audit 自愈创建(无需手动执行);
生产库经本修订补齐。downgrade 删除触发器/函数/表。

触发器函数对 users 表的 password_hash 等密钥字段做脱敏(从 JSONB 载荷中剔除),
避免口令哈希进入审计日志。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0009_row_audit"
down_revision: Union[str, None] = "0008_fk_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS row_audit (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    table_name TEXT NOT NULL,
    row_id TEXT,
    action CHAR(1) NOT NULL,
    old_val JSONB,
    new_val JSONB,
    changed_by TEXT,
    app_name TEXT
)
"""

_FUNC_DDL = """
CREATE OR REPLACE FUNCTION audit_row_change() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    who TEXT := COALESCE(NULLIF(current_setting('app.audit_user', true), ''), current_user);
    an  TEXT := current_setting('application_name', true);
    oldj JSONB := to_jsonb(OLD);
    newj JSONB := to_jsonb(NEW);
BEGIN
    oldj := oldj - 'password_hash' - 'password' - 'hashed_password' - 'secret' - 'token';
    newj := newj - 'password_hash' - 'password' - 'hashed_password' - 'secret' - 'token';
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO row_audit(table_name, row_id, action, old_val, new_val, changed_by, app_name)
            VALUES (TG_TABLE_NAME, NEW.id::text, 'I', NULL, newj, who, an);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO row_audit(table_name, row_id, action, old_val, new_val, changed_by, app_name)
            VALUES (TG_TABLE_NAME, NEW.id::text, 'U', oldj, newj, who, an);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO row_audit(table_name, row_id, action, old_val, new_val, changed_by, app_name)
            VALUES (TG_TABLE_NAME, OLD.id::text, 'D', oldj, NULL, who, an);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
"""

_AUDIT_TABLES = ("users", "roles", "tenant")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(_TABLE_DDL))
    bind.execute(text(_FUNC_DDL))
    for t in _AUDIT_TABLES:
        bind.execute(text(f"DROP TRIGGER IF EXISTS trg_{t}_audit ON {t}"))
        bind.execute(text(
            f"CREATE TRIGGER trg_{t}_audit AFTER INSERT OR UPDATE OR DELETE ON {t} "
            f"FOR EACH ROW EXECUTE FUNCTION audit_row_change()"
        ))


def downgrade() -> None:
    bind = op.get_bind()
    for t in _AUDIT_TABLES:
        bind.execute(text(f"DROP TRIGGER IF EXISTS trg_{t}_audit ON {t}"))
    bind.execute(text("DROP FUNCTION IF EXISTS audit_row_change()"))
    bind.execute(text("DROP TABLE IF EXISTS row_audit"))
