"""CMDB 关系层端点 (阶段二)。

挂载: /api/ops/ci-relations
- GET    /                     关系列表 (按源 CI / 类型 / 关键字筛选)
- POST   /                     新建关系 (admin/operator)
- DELETE /{id}                 删除关系 (admin/operator)
- GET    /graph                关系图 nodes/edges
- GET    /impact/{ci_id}       影响扩散 (有向 BFS, fallback 标注)
- GET    /options              可选 CI 清单 (设备台账 / 机柜 / 外部设备并集)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user, require_role
from app.crud import ci_relation as ci_crud
from app.db.session import SessionLocal
from app.schemas.ci_relation import (
    CiGraphOut,
    CiImpactOut,
    CiOption,
    CiRelationCreate,
    CiRelationOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ci-relation"])
_rw = [Depends(require_role("admin", "operator"))]


def _username(user) -> str:
    return getattr(user, "username", None) or "system"


@router.get("", summary="CI 关系列表", response_model=list[CiRelationOut])
def list_relations(
    source_ci: str | None = Query(None),
    relation_type: str | None = Query(None),
    keyword: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _user=Depends(get_current_user),
):
    db = SessionLocal()
    try:
        return ci_crud.list_relations(db, source_ci, relation_type, keyword, limit, offset)
    finally:
        db.close()


@router.post("", summary="新建 CI 关系", response_model=CiRelationOut, dependencies=_rw)
def create_relation(body: CiRelationCreate, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        payload = body.model_dump()
        payload["created_by"] = _username(user)
        return ci_crud.create_relation(db, payload)
    except ci_crud.CiConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        db.close()


@router.delete("/{relation_id}", summary="删除 CI 关系", dependencies=_rw)
def delete_relation(relation_id: int, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        deleted = ci_crud.delete_relation(db, relation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="关系不存在")
        return {"deleted": True, "id": relation_id}
    finally:
        db.close()


@router.get("/graph", summary="CI 关系图", response_model=CiGraphOut)
def relation_graph(_user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return ci_crud.build_graph(db)
    finally:
        db.close()


@router.get("/options", summary="可选 CI 清单", response_model=list[CiOption])
def relation_options(limit: int = Query(100, ge=1, le=500), _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return ci_crud.list_options(db, limit)
    finally:
        db.close()


@router.get("/impact/{ci_id:path}", summary="沿真实关系的影响扩散", response_model=CiImpactOut)
def relation_impact(
    ci_id: str,
    depth: int = Query(3, ge=1, le=6),
    relation_type: str | None = Query(None),
    _user=Depends(get_current_user),
):
    db = SessionLocal()
    try:
        return ci_crud.impact(db, ci_id, depth, relation_type)
    finally:
        db.close()
