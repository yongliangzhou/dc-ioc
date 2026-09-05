"""登录端点速率限制 (基于 Redis, 失败降级放行)。

用于防御 /api/auth/login 的暴力破解: 每个客户端 IP 在 60s 窗口内最多
RATE_LIMIT_PER_MINUTE 次登录尝试。Redis 不可用时自动降级为放行, 不阻断登录主流程。
"""
import logging

from fastapi import HTTPException, Request, status

from app.cache.redis_client import rds
from app.core.config import settings

logger = logging.getLogger(__name__)


def _client_key(request: Request) -> str:
    """取客户端真实 IP (经反代时优先 X-Forwarded-For)。"""
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def login_rate_limit(request: Request) -> None:
    """登录限流依赖: 超出阈值抛出 429。"""
    if not settings.RATE_LIMIT_ENABLED:
        return
    key = f"ratelimit:login:{_client_key(request)}"
    limit = settings.RATE_LIMIT_PER_MINUTE
    try:
        count = rds.incr(key)
        if count == 1:
            rds.expire(key, 60)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登录尝试过于频繁, 请稍后再试",
            )
    except HTTPException:
        raise
    except Exception as e:
        # Redis 不可用 -> 降级放行 (基础防护失效, 但登录不阻断)
        logger.debug("登录限流 Redis 不可用, 降级放行: %s", e)
