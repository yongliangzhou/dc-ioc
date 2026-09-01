-- ============================================================================
-- 8.5 ③ 敏感表行级审计 (行级审计视图/触发器, 设计文档第八章 8.5)
-- 作用: 对 users / roles / tenant 三张敏感表的 INSERT/UPDATE/DELETE 做行级审计,
--       记录变更前后脱敏行(JSONB)与操作人, 供安全追溯。
-- 生产库直接用 `alembic upgrade head` 即可(见 backend/alembic/versions/0009_row_audit.py);
-- 此处保留等价 SQL 供人工复核或脱离 Alembic 直接执行。
-- 注意: 触发器函数对 users.password_hash 等密钥字段脱敏, 不写入审计日志。
-- ============================================================================

CREATE TABLE IF NOT EXISTS row_audit (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    table_name TEXT NOT NULL,
    row_id TEXT,
    action CHAR(1) NOT NULL,            -- I / U / D
    old_val JSONB,
    new_val JSONB,
    changed_by TEXT,
    app_name TEXT
);

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

DROP TRIGGER IF EXISTS trg_users_audit ON users;
CREATE TRIGGER trg_users_audit AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

DROP TRIGGER IF EXISTS trg_roles_audit ON roles;
CREATE TRIGGER trg_roles_audit AFTER INSERT OR UPDATE OR DELETE ON roles
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

DROP TRIGGER IF EXISTS trg_tenant_audit ON tenant;
CREATE TRIGGER trg_tenant_audit AFTER INSERT OR UPDATE OR DELETE ON tenant
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();
