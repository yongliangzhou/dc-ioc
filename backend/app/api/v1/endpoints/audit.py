"""操作审计日志查询端点。

权限: 仅 admin / operator 可查询 (RBAC 全局 + 本路由依赖)。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, require_role
from app.core.audit import get_audit_logs
from app.db.session import SessionLocal

router = APIRouter(tags=["audit"])

_rw = [Depends(require_role("admin", "operator"))]


@router.get("", summary="查询操作审计日志 (分页/过滤)", dependencies=_rw)
def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    resource: Optional[str] = Query(None, description="资源类型过滤 (如 alarms/users)"),
    action: Optional[str] = Query(None, description="动作过滤 create/update/delete/read/login"),
    username: Optional[str] = Query(None, description="操作人过滤"),
    keyword: Optional[str] = Query(None, description="关键字 (路径/详情/操作人)"),
    _user=Depends(get_current_user),
):
    db = SessionLocal()
    try:
        return get_audit_logs(
            db,
            skip=(page - 1) * page_size,
            limit=page_size,
            resource=resource,
            action=action,
            username=username,
            keyword=keyword,
        )
    finally:
        db.close()
