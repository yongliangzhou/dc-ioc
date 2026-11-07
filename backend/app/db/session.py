"""SQLAlchemy 引擎与会话 (PostgreSQL)。

连接池参数从 Settings 读取, 支持按环境调优。
阶段四: 在 sessionmaker 上安装 `do_orm_execute` 行级租户过滤 hook,
仅对「含 tenant_id 列的模型」且「上下文非空」时生效, 存量模型零影响。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, with_loader_criteria

from app.core.config import settings
from app.core.tenant_context import get_current_tenant

engine = create_engine(
    settings.sqlalchemy_uri,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.DB_ECHO,
    connect_args={"connect_timeout": settings.DB_CONNECT_TIMEOUT},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def _tenant_orm_hook(execute_state) -> None:
    """ORM 全局过滤: 只处理纯 SELECT, 跳过列/关系懒加载, 避免破坏 ORM 内部结构。"""
    if not execute_state.is_select:
        return
    if execute_state.is_column_load or execute_state.is_relationship_load:
        return
    tenant_id = get_current_tenant()
    if tenant_id is None:
        return
    mappers = list(execute_state.all_mappers)
    if not mappers and execute_state.bind_mapper is not None:
        # Query.count() 等聚合语句的 all_mappers 为空, 但 bind_mapper 仍能定位实体,
        # 不补这一支会导致计数绕过租户隔离 (信息泄露)。
        mappers = [execute_state.bind_mapper]
    if not mappers:
        return
    # 混合了不含 tenant_id 的模型时整体跳过, 防止半过滤造成数据错乱
    if not all(hasattr(mp.class_, "tenant_id") for mp in mappers):
        return
    execute_state.statement = execute_state.statement.options(
        *[
            with_loader_criteria(
                mp.class_,
                mp.class_.tenant_id == tenant_id,
                include_aliases=True,
            )
            for mp in mappers
        ]
    )


def install_tenant_filter(session_factory) -> None:
    """幂等安装 hook (测试可对自建 SQLite sessionmaker 复用同一逻辑)。"""
    if not event.contains(session_factory, "do_orm_execute", _tenant_orm_hook):
        event.listen(session_factory, "do_orm_execute", _tenant_orm_hook)


install_tenant_filter(SessionLocal)


def get_db():
    """FastAPI 依赖注入: 请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
