"""启动时密钥安全检查 — 防止默认凭据上线生产。

Phase 3 生产化: 在生产环境 (APP_ENV=prod/staging) 启动时校验:
- SECRET_KEY 不能为默认值
- admin 密码不能为 admin123
- EXTERNAL_COLLECTOR_TOKEN 不能为空
"""
from __future__ import annotations

import logging

logger = logging.getLogger("secret_check")


# 默认值黑名单 (在代码中硬编码, 不依赖环境变量)
_DEFAULT_SECRETS = {
    "SECRET_KEY": {"change-me", "changeme", "secret", "dev-secret"},
    "POSTGRES_PASSWORD": {"dcpass", "postgres", "password", "123456", ""},
    "REDIS_PASSWORD": set(),  # 允许空 (开发环境)
}

# admin 默认密码
_DEFAULT_ADMIN_PASSWORDS = {"admin123", "admin", "password", "123456", "admin888"}


def check_secrets_on_startup(
    app_env: str,
    secret_key: str,
    admin_pwd: str = "admin123",
    postgres_password: str = "",
    external_collector_token: str | None = None,
):
    """启动时密钥检查。

    在开发环境仅打印警告; 在生产/预发环境直接抛出 RuntimeError 阻止启动。
    """
    is_prod = app_env in ("prod", "production", "staging")
    errors: list[str] = []

    # 1. SECRET_KEY
    sk = secret_key or ""
    sk_lower = sk.lower()
    if not sk or any(bad in sk_lower for bad in _DEFAULT_SECRETS["SECRET_KEY"]) or len(sk) < 16:
        msg = (
            f"SECRET_KEY 不安全 (当前长度: {len(sk)})。"
            " 请通过环境变量设置至少 32 字符的强随机密钥 (如 openssl rand -hex 32)。"
        )
        if is_prod:
            errors.append(msg)
        else:
            logger.warning("⚠ %s", msg)

    # 2. 管理员密码
    if (admin_pwd or "").lower() in _DEFAULT_ADMIN_PASSWORDS:
        msg = "admin 账户使用默认密码, 请立即修改。"
        if is_prod:
            errors.append(msg)
        else:
            logger.warning("⚠ %s", msg)

    # 3. POSTGRES 密码弱口令
    if (postgres_password or "") in _DEFAULT_SECRETS["POSTGRES_PASSWORD"]:
        msg = "POSTGRES_PASSWORD 使用默认/弱口令, 存在数据库被入侵风险, 请立即修改。"
        if is_prod:
            errors.append(msg)
        else:
            logger.warning("⚠ %s", msg)

    # 4. 生产环境强制采集器 Token (外部设备接入鉴权)
    if is_prod and not external_collector_token:
        errors.append(
            "生产环境必须配置 EXTERNAL_COLLECTOR_TOKEN, "
            "否则外部设备接入端点 (/api/external) 将无鉴权。"
        )

    if errors:
        err_detail = "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
        raise RuntimeError(
            f"生产环境密钥安全检查失败 ({len(errors)} 项):\n{err_detail}\n"
            "请确保通过环境变量注入安全的配置后重新启动。"
        )

    if is_prod:
        logger.info("生产环境密钥安全检查通过 (SECRET_KEY 长度: %d)", len(sk))
    else:
        logger.info("开发环境密钥检查完成 (安全警告已打印; 不会阻止启动)")
