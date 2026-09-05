"""pytest 共享设施: 不依赖真实 Postgres / Docker, 全部 SQLite 内存库 + FastAPI 依赖覆盖。

设计说明:
- backend 源码通过 sys.path 注入 (tests/ 位于仓库根, backend/ 为独立应用根)。
- app.db.session 在 import 时就会 create_engine(postgres URI), 但引擎是惰性连接的,
  只要测试中通过依赖覆盖 / monkeypatch 替换掉 SessionLocal / get_db, 全程不会真正连库。
- 鉴权: 端点的 require_role = RoleChecker 内部 Depends(get_current_user),
  因此只需在 app.dependency_overrides 覆盖 get_current_user 即可同时控制
  "登录态"与"角色" (FakeUser.roles / is_superuser)。
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.deps import get_current_user  # noqa: E402

__all__ = ["FakeRole", "FakeUser", "make_client", "make_sqlite_sessionmaker"]


class FakeRole:
    """最小 Role 形状 (RoleChecker 只读 role.name)。"""

    def __init__(self, name: str):
        self.name = name


class FakeUser:
    """最小 User 形状 (get_current_user / RoleChecker 所需字段)。"""

    def __init__(self, username: str = "tester", roles: tuple = ("admin",), is_superuser: bool = False):
        self.username = username
        self.is_active = True
        self.is_superuser = is_superuser
        self.roles = [FakeRole(r) for r in roles]


def make_client(routers, user: "FakeUser | None" = None, extra_overrides: dict | None = None) -> TestClient:
    """构建只挂目标路由的轻量 FastAPI 应用 (不触发 main.py lifespan/中间件)。

    routers: [(APIRouter, prefix), ...]
    """
    app = FastAPI()
    for router, prefix in routers:
        app.include_router(router, prefix=prefix)
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    for dep, fn in (extra_overrides or {}).items():
        app.dependency_overrides[dep] = fn
    return TestClient(app)


def make_sqlite_sessionmaker(*tables, pre_ddl: str = ""):
    """SQLite 内存库 session 工厂 (StaticPool 保证多连接共享同一内存库)。

    注意:
    - 含 PG 方言类型 (JSONB/BIGSERIAL) 的模型不能传进来, 只适用于纯
      String/Integer/Float/Text/BigInteger 模型 (如 refuel_record / tenant)。
    - SQLite 的自增主键要求 `INTEGER PRIMARY KEY`: BigInteger 主键 (BIGINT)
      不会成为 rowid 别名, INSERT 不带 id 会报 NOT NULL。此类表请通过
      pre_ddl 用 `INTEGER PRIMARY KEY AUTOINCREMENT` 建表 (传表对象仅作文档,
      checkfirst=True 会自动跳过已存在的表)。
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    if pre_ddl.strip():
        with engine.begin() as conn:
            for stmt in pre_ddl.split(";"):
                if stmt.strip():
                    conn.execute(text(stmt))
    for table in tables:
        table.create(bind=engine, checkfirst=True)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
