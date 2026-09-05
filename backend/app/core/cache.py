"""Redis 响应缓存装饰器 (best-effort)。

用于高频只读接口 (如 /api/dashboard/overview) 的响应缓存, 显著降低
数据库/计算压力。Redis 不可用时自动降级为不缓存, 不影响主流程。
"""
import functools
import hashlib
import inspect
import json
import logging
from typing import Any

from fastapi import Request

from app.cache.redis_client import rds

logger = logging.getLogger(__name__)

try:
    import orjson  # 更快的 JSON 序列化

    def _dumps(obj: Any) -> str:
        return orjson.dumps(obj).decode("utf-8")

    def _loads(s: str) -> Any:
        return orjson.loads(s)
except Exception as e:  # pragma: no cover
    logger.debug("orjson 导入失败, 回退标准 json 序列化: %s", e)

    def _dumps(obj: Any) -> str:
        return json.dumps(obj, default=str, ensure_ascii=False)

    def _loads(s: str) -> Any:
        return json.loads(s)


def _to_serializable(obj: Any) -> Any:
    """Pydantic 模型转 dict, 其余原样返回。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def cache_json(ttl: int = 30, key_prefix: str = "dc-ioc"):
    """缓存端点 JSON 响应 ttl 秒; 缓存键包含 path + query。

    用法::

        @router.get("/overview", response_model=DashboardOverview)
        @cache_json(ttl=30, key_prefix="dashboard:overview")
        def get_overview(request: Request):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 取出 FastAPI 注入的 Request 以构造缓存键
            request: Request | None = kwargs.get("request")
            if request is None:
                for a in args:
                    if isinstance(a, Request):
                        request = a
                        break

            key = None
            if request is not None:
                raw = f"{key_prefix}:{request.url.path}:{request.url.query}"
                key = "cache:" + hashlib.md5(raw.encode("utf-8")).hexdigest()

            # 读缓存
            if key:
                try:
                    cached = rds.get(key)
                    if cached:
                        return _loads(cached)
                except Exception as e:
                    # Redis 不可用 -> 降级
                    logger.debug("读取 Redis 缓存失败, 降级直查: %s", e)

            result = func(*args, **kwargs)

            # 写缓存
            if key:
                try:
                    rds.set(key, _dumps(_to_serializable(result)), ex=ttl)
                except Exception as e:
                    logger.debug("写入 Redis 缓存失败, 本次不缓存: %s", e)

            return result

        # 关键修复: 保留被装饰函数的原始签名, 否则 FastAPI 无法注入 Request 参数
        wrapper.__signature__ = inspect.signature(func)
        return wrapper

    return decorator


def invalidate_prefix(prefix: str) -> int:
    """5.7.3 缓存失效: 删除匹配 prefix 的缓存键, 返回删除数量 (Redis 不可用返回 0)。"""
    try:
        keys = rds.keys(f"cache:{prefix}:*") if hasattr(rds, "keys") else []
    except Exception as e:
        logger.debug("查询缓存键失败, 按 0 处理: %s", e)
        return 0
    if not keys:
        return 0
    try:
        return rds.delete(*keys) if hasattr(rds, "delete") else 0
    except Exception as e:
        logger.debug("批量删除缓存键失败, 按 0 处理: %s", e)
        return 0
