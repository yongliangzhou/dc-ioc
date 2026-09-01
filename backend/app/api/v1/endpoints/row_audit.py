"""行级变更审计查询端点 (row_audit 可视化)。

权限: 仅 admin / operator 可查询 (RBAC 全局 + 本路由依赖)。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, require_role
from app.crud.row_audit import get_row_audit_logs, get_row_audit_stats
from app.db.session import SessionLocal

router = APIRouter(tags=["row-audit"])

_rw = [Depends(require_role("admin", "operator"))]


@router.get("", summary="查询行级变更审计 (分页/过滤)", dependencies=_rw)
def list_row_audit(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    table_name: Optional[str] = Query(None, description="表名过滤 (users/roles/tenant)"),
    action: Optional[str] = Query(None, description="变更类型过滤 I/U/D"),
    changed_by: Optional[str] = Query(None, description="操作人过滤 (模糊)"),
    start: Optional[datetime] = Query(None, description="起始时间 (ISO8601)"),
    end: Optional[datetime] = Query(None, description="结束时间 (ISO8601)"),
    _user=Depends(get_current_user),
):
    db = SessionLocal()
    try:
        return get_row_audit_logs(
            db,
            skip=(page - 1) * page_size,
            limit=page_size,
            table_name=table_name,
            action=action,
            changed_by=changed_by,
            start=start,
            end=end,
        )
    finally:
        db.close()


@router.get("/stats", summary="行级变更审计统计 (按表/按类型)", dependencies=_rw)
def row_audit_stats(_user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return get_row_audit_stats(db)
    finally:
        db.close()
