"""[Q-03] 认证限流门禁测试。

手写限流基于 Redis 计数器 (rds.incr), 超阈值抛 429。
测试 mock rds 为可用 fake 并让计数超阈, 验证返回 429。
"""
import pytest
from fastapi.testclient import TestClient

from app.core import ratelimit
from app.main import app as real_app

# RATE_LIMIT_PER_MINUTE=60, 计数超过即触发 429
_OVER_LIMIT = 61


class _FakeRedis:
    """incr 永远返回超过阈值, 触发限流。"""

    def incr(self, key: str, amount: int = 1) -> int:  # noqa: ARG002
        return _OVER_LIMIT

    def expire(self, key: str, ttl: int) -> None:  # noqa: ARG002
        return None

    def get(self, key: str):
        return None


@pytest.fixture
def client():
    from app.cache import redis_client
    from app.core import config as cfg

    # 测试环境可能关闭了限流, 这里强制开启以验证 429 行为
    saved_enabled = cfg.settings.RATE_LIMIT_ENABLED
    saved_rds_src = redis_client.rds
    saved_rds_rt = ratelimit.rds
    cfg.settings.RATE_LIMIT_ENABLED = True
    fake = _FakeRedis()
    redis_client.rds = fake
    ratelimit.rds = fake
    real_app.debug = False
    try:
        with TestClient(real_app, raise_server_exceptions=False) as c:
            yield c
    finally:
        cfg.settings.RATE_LIMIT_ENABLED = saved_enabled
        redis_client.rds = saved_rds_src
        ratelimit.rds = saved_rds_rt


def test_login_rate_limited_returns_429(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 429
    # 全局异常处理器将 429 包装为 {code, message}
    body = resp.json()
    assert body.get("code") == 429
    assert "登录" in body.get("message", "")


def test_ratelimit_disabled_when_redis_none():
    """rds 为 None 时限流降级放行 (不抛 429)。"""
    saved = ratelimit.rds
    ratelimit.rds = None
    try:
        # 直接调用依赖, 应静默 return 而非抛 429
        class _Req:
            headers = {}
            client = None

        ratelimit.login_rate_limit(_Req())  # 不应抛异常
    finally:
        ratelimit.rds = saved
