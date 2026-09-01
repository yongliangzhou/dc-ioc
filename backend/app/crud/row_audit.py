"""行级变更审计查询 (row_audit 表, 由触发器写入, 此处只读查询)。

提供分页 + 过滤列表查询, 以及按表 / 按变更类型的聚合统计, 供前端可视化。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select


def get_row_audit_logs(
    db,
    skip: int = 0,
    limit: int = 50,
    table_name: Optional[str] = None,
    action: Optional[str] = None,
    changed_by: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    """分页 + 过滤查询行级审计 (按时间倒序)。"""
    from app.models.row_audit import RowAudit

    stmt = select(RowAudit)
    if table_name:
        stmt = stmt.where(RowAudit.table_name == table_name)
    if action:
        stmt = stmt.where(RowAudit.action == action)
    if changed_by:
        stmt = stmt.where(RowAudit.changed_by.ilike(f"%{changed_by}%"))
    if start is not None:
        stmt = stmt.where(RowAudit.ts >= start)
    if end is not None:
        stmt = stmt.where(RowAudit.ts <= end)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(RowAudit.ts.desc()).offset(skip).limit(limit)
    ).all()
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": skip // limit + 1 if limit else 1,
        "page_size": limit,
    }


def get_row_audit_stats(db):
    """聚合统计: 总条数 + 按表分布 + 按变更类型分布, 供可视化概览。"""
    from app.models.row_audit import RowAudit

    total = db.scalar(select(func.count()).select_from(RowAudit)) or 0
    by_table = db.execute(
        select(RowAudit.table_name, func.count().label("c"))
        .group_by(RowAudit.table_name)
        .order_by(func.count().desc())
    ).all()
    by_action = db.execute(
        select(RowAudit.action, func.count().label("c"))
        .group_by(RowAudit.action)
        .order_by(func.count().desc())
    ).all()
    return {
        "total": total,
        "by_table": [{"table_name": t, "count": c} for t, c in by_table],
        "by_action": [{"action": (a or "").strip(), "count": c} for a, c in by_action],
    }
