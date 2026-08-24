"""Alembic 运行环境 — 读取应用配置的连接串, 收集全部模型 metadata。

用法 (在 backend/ 目录):
  alembic revision --autogenerate -m "msg"   # 生成迁移
  alembic upgrade head                        # 应用迁移
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings

# 导入全部模型, 确保 Base.metadata 收集到所有表
import app.models  # noqa: F401

config = context.config
# 用应用运行时连接串覆盖 ini 中的占位 url
config.set_main_option("sqlalchemy.url", settings.sqlalchemy_uri)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = app.models.Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"}, compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
