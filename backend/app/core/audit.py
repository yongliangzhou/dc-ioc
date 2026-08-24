"""操作审计中间件 — 记录所有写操作 (POST/PUT/PATCH/DELETE) 与关键读操作到 audit_logs。

设计要点:
  - 通过解析 Authorization Bearer token 的 `sub` 得到操作人, 无需额外 DB 查询
  - Request.body() 在 Starlette 中带缓存, 多次读取安全; 仅对写方法读取并截断脱敏
  - 不拦截 /health /metrics /docs /openapi /ws / 静态资源 与 GET/OPTIONS
  - 落库失败不影响主流程 (单独 try/except)
"""
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_token
from app.db.session import SessionLocal

logger = logging.getLogger("audit")

# 不审计的路径前缀
_SKIP_PREFIXES = ("/health", "/ready", "/metrics", "/docs", "/openapi.json", "/ws", "/redoc")
_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
# 关键读操作也纳入审计
_READ_AUDIT_PATHS = ("/api/audit-logs",)
_DETAIL_MAX = 2000


def _infer_resource_action(path: str, method: str):
    """从路径与方法推断资源类型与动作。"""
    seg = [s for s in path.split("/") if s]
    resource = seg[1] if len(seg) > 1 else seg[0] if seg else ""
    if method == "POST":
        action = "create"
    elif method in ("PUT", "PATCH"):
        action = "update"
    elif method == "DELETE":
        action = "delete"
    else:
        action = "read"
    if "login" in path or path.endswith("/auth/token"):
        action = "login"
        resource = "auth"
    return resource, action


def _principal(request: Request) -> Optional[str]:
    """从 Bearer token 解析操作人 sub; 无/失效则返回 None。"""
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("sub")


def record_audit(
    method: str,
    path: str,
    status_code: int,
    username: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    query: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """写一条审计记录 (独立会话, 失败静默)。供中间件与程序化调用。"""
    try:
        resource, action = _infer_resource_action(path, method)
        db = SessionLocal()
        try:
            from app.models.audit_log import AuditLog
            from datetime import datetime
            db.add(AuditLog(
                ts=datetime.utcnow(),
                method=method,
                path=path[:255],
                query=query,
                status_code=status_code,
                username=username,
                ip=ip,
                user_agent=user_agent,
                resource=resource,
                action=action,
                detail=detail[:_DETAIL_MAX] if detail else None,
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:  # 审计失败绝不能影响业务
        logger.warning("审计记录写入失败: %s", e)


def get_audit_logs(
    db,
    skip: int = 0,
    limit: int = 50,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    username: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """分页 + 过滤查询审计日志 (按时间倒序)。"""
    from sqlalchemy import select, func, or_
    from app.models.audit_log import AuditLog

    stmt = select(AuditLog)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if username:
        stmt = stmt.where(AuditLog.username == username)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(AuditLog.path.ilike(like), AuditLog.detail.ilike(like), AuditLog.username.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(AuditLog.ts.desc()).offset(skip).limit(limit)
    ).all()
    return {
        "items": [r.to_dict() for r in rows],
        "total": total or 0,
        "page": skip // limit + 1 if limit else 1,
        "page_size": limit,
    }


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 跳过非审计路径与非关注方法
        if path.startswith(_SKIP_PREFIXES):
            return await call_next(request)
        if method not in _MUTATING and path not in _READ_AUDIT_PATHS:
            return await call_next(request)

        # 读取请求体 (Starlette 缓存, 安全); 仅写方法 + 截断
        detail = None
        if method in _MUTATING:
            try:
                body = await request.body()
                if body:
                    try:
                        detail = body.decode("utf-8", "ignore")
                    except Exception:
                        detail = "<binary>"
            except Exception:
                detail = None

        username = _principal(request)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        query = str(request.url.query) if request.url.query else None

        response = await call_next(request)

        # 4xx/5xx 也记录 (便于事后追溯失败操作)
        record_audit(
            method=method,
            path=path,
            status_code=response.status_code,
            username=username,
            ip=ip,
            user_agent=ua,
            query=query,
            detail=detail,
        )

        # 5.8.2 日志/审计告警联动: 关键操作触发安全告警
        if response.status_code < 400:
            resource, action = _infer_resource_action(path, method)
            try:
                from app.core.alert_bridge import emit_security_alert, should_alert

                if should_alert(action, resource):
                    emit_security_alert(
                        action=action, resource=resource,
                        detail=detail, username=username, ip=ip,
                    )
            except Exception:  # noqa: BLE001
                pass  # 告警失败不影响主流程

        return response
