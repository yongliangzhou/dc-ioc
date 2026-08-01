-- ============================================================================
-- 认证体系种子数据: 默认角色 + 管理员账号
-- 用法: psql -d dc_ioc -f 006_seed_auth.sql
-- ============================================================================

-- ---- 用户表 ----
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(64)  NOT NULL DEFAULT '',
    email           VARCHAR(128),
    phone           VARCHAR(32),
    department      VARCHAR(64)  NOT NULL DEFAULT '',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN      NOT NULL DEFAULT FALSE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---- 角色表 ----
CREATE TABLE IF NOT EXISTS roles (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32)  NOT NULL UNIQUE,
    label           VARCHAR(32)  NOT NULL DEFAULT '',
    permissions     VARCHAR(1024),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---- 用户-角色关联表 ----
CREATE TABLE IF NOT EXISTS user_role (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ---- 种子数据 ----
INSERT INTO roles (name, label, permissions) VALUES
    ('admin',    '超级管理员', '["*"]'),
    ('operator', '运维操作员', '["dashboard:read","equipment:read","equipment:write","alarm:read","alarm:write","hvac:read","power:read","security:read","ops:read","ops:write"]'),
    ('viewer',   '只读用户',   '["dashboard:read","equipment:read","alarm:read","hvac:read","power:read","security:read","ops:read"]')
ON CONFLICT (name) DO UPDATE SET permissions = EXCLUDED.permissions;

-- 默认管理员: admin / admin123
-- bcrypt hash for 'admin123' (compatible with bcrypt==4.0.1):
-- $2b$12$ZRjkpIpyMBHSNpCT8Sr43e81IUgJUxoEltYy6/Zzc7sHXe9UhNgA.
-- (生产环境请立即修改密码)
INSERT INTO users (username, password_hash, display_name, is_superuser, is_active) VALUES
    ('admin', '$2b$12$ZRjkpIpyMBHSNpCT8Sr43e81IUgJUxoEltYy6/Zzc7sHXe9UhNgA.', '系统管理员', TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- 分配 admin 角色给 admin 用户
INSERT INTO user_role (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT DO NOTHING;
