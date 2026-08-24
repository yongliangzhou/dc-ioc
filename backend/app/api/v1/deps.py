"""v1 依赖注入入口: 重新导出认证/DB 依赖, 供 endpoints 统一导入。

(server.py 等端点统一从 app.api.v1.deps 导入 get_db / get_current_user,
此处转发至 app.core.deps 的真实实现, 避免重复定义。)
"""
from app.core.deps import get_db, get_current_user, get_optional_user  # noqa: F401

__all__ = ["get_db", "get_current_user", "get_optional_user"]
