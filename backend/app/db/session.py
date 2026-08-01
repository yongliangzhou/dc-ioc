"""SQLAlchemy 引擎与会话 (PostgreSQL)。

连接池参数从 Settings 读取, 支持按环境调优。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

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


def get_db():
    """FastAPI 依赖注入: 请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
