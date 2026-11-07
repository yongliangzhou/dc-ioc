"""阶段四 · 多租户上下文 (P4-3)。

- `ContextVar` 保证同步/异步请求间互不串扰。
- `get_current_tenant()` 返回 None 表示「不过滤」(脚本 / 种子 / 单测 / 管理端豁免)。
- `without_tenant_filter()` 供审计、跨租户运营分析显式豁免。

安全约定 (ADR-0003): `X-Tenant-Id` 请求头**不能**覆盖已登录 JWT 中的
`tenant_id` claim；仅 admin 在无 claim 时可通过中间件侧的显式策略跨租户。
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_current_tenant: ContextVar[int | None] = ContextVar("dc_ioc_current_tenant", default=None)
_exempt: ContextVar[bool] = ContextVar("dc_ioc_tenant_filter_exempt", default=False)


def set_current_tenant(tenant_id: int | None) -> Token:
    return _current_tenant.set(tenant_id)


def reset_current_tenant(token: Token) -> None:
    _current_tenant.reset(token)


def get_current_tenant() -> int | None:
    if _exempt.get():
        return None
    return _current_tenant.get()


@contextmanager
def tenant_scope(tenant_id: int | None) -> Iterator[None]:
    token = set_current_tenant(tenant_id)
    try:
        yield
    finally:
        reset_current_tenant(token)


@contextmanager
def without_tenant_filter() -> Iterator[None]:
    token = _exempt.set(True)
    try:
        yield
    finally:
        _exempt.reset(token)
