"""运维预案(runbooks)接口: 别名挂载于 /api/runbooks。

前端告警详情页通过 `getRelatedRunbooks("/api/runbooks/related")` 拉取与告警
相关的处置预案。预案数据复用知识库(Knowledge, type=emergency/sop/case 等),
逻辑委托给 `app.crud.knowledge.related`, 返回结构与 /api/ops/knowledge/related
一致(list[KnowledgeOut]), 前端无需区分两者。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.crud import knowledge as kb_crud
from app.models.user import User
from app.schemas.knowledge import KnowledgeOut

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


@router.get("/related", response_model=list[KnowledgeOut], summary="按告警匹配运维预案")
def related_runbooks(
    system: str | None = Query(default=None, description="告警 system, 如 暖通-冷源"),
    domain: str | None = Query(default=None, description="告警 domain, 如 hvac_source"),
    metric: str | None = Query(default=None, description="告警 metric_name"),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    """告警详情页用于关联运维预案 (告警 -> 处置预案)。"""
    return kb_crud.related(db, system=system, domain=domain, metric=metric, limit=limit)
