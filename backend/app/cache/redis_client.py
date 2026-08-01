"""Redis 客户端 (连接池)。"""
import redis

from app.core.config import settings

_pool = redis.ConnectionPool.from_url(settings.redis_uri, decode_responses=True, max_connections=20)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


rds = get_redis()
