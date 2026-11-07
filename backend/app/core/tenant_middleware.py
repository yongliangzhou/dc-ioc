"""阶段四 · 请求级租户上下文中间件 (P4-3)。

从 JWT payload 读取 `tenant_id` claim 作为权威来源; 未携带 claim 时:
- dev/test 环境允许 `X-Tenant-Id` 头用于联调;
- 其它环境一律 None (不过滤), 由既有 RBAC 负责鉴权。

JWT 签名/过期校验由 `deps.get_current_user` 独立完成, 此处只解码 payload
用于设置数据过滤上下文, 不会据此放行任何请求。
"""
from __future__ import annotations

import base64
import json
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.tenant_context import reset_current_tenant, set_current_tenant

logger = logging.getLogger(__name__)


def _jwt_tenant(request: Request) -> int | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    parts = header.split(".")
    if len(parts) < 2:
        return None
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        value = payload.get("tenant_id")
        return int(value) if value is not None else None
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        logger.debug("JWT tenant_id 解析失败, 忽略: %s", exc)
        return None


def _tenant_from_request(request: Request) -> int | None:
    claim = _jwt_tenant(request)
    if claim is not None:
        return claim  # 请求头不能覆盖 token claim (防越权)
    if os.getenv("APP_ENV", "dev") in ("dev", "test"):
        raw = request.headers.get("X-Tenant-Id")
        if raw and raw.isdigit():
            return int(raw)
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = set_current_tenant(_tenant_from_request(request))
        try:
            return await call_next(request)
        finally:
            reset_current_tenant(token)
