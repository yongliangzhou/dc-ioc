"""行级变更审计查询端点 (row_audit 可视化)。

权限: 仅 admin / operator 可查询 (RBAC 全局 + 本路由依赖)。

表缺失降级: row_audit 表与触发器由 Alembic 0009 创建 (lifespan 不再自愈该对象)。
未执行 `alembic upgrade head` 的环境该表不存在, 直接查询会 500 导致整页加载失败;
此处捕获后返回空集 + unavailable 标记与提示, 由前端展示引导文案。
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, require_role
from app.crud.row_audit import get_row_audit_logs, get_row_audit_stats
from app.db.session import SessionLocal

logger = logging.getLogger("api.row_audit")

router = APIRouter(tags=["row-audit"])

_rw = [Depends(require_role("admin", "operator"))]

_MISSING_HINT = "row_audit 表不存在: 请执行 alembic upgrade head 建表并创建审计触发器"


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
    except Exception as e:  # noqa: BLE001
        logger.warning("行级审计查询失败 (表可能未创建): %s", e)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "unavailable": True,
            "hint": _MISSING_HINT,
        }
    finally:
        db.close()


@router.get("/stats", summary="行级变更审计统计 (按表/按类型)", dependencies=_rw)
def row_audit_stats(_user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return get_row_audit_stats(db)
    except Exception as e:  # noqa: BLE001
        logger.warning("行级审计统计失败 (表可能未创建): %s", e)
        return {
            "total": 0,
            "by_table": [],
            "by_action": [],
            "unavailable": True,
            "hint": _MISSING_HINT,
        }
    finally:
        db.close()
