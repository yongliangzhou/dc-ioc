"""物模型 API (phase: thing-model)。

- GET    /api/thing-models        列表 (按 key/name/category/domain 过滤)
- GET    /api/thing-models/{id}   详情 (含 items)
- POST   /api/thing-models        新建 (含 items 批量写入)
- PUT    /api/thing-models/{id}   更新 (含 items 全量替换)
- DELETE /api/thing-models/{id}   删除 (级联 items)

读接口鉴权; 写接口要求 admin 角色。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import thing_model as tm_crud
from app.models.user import User
from app.schemas.thing_model import ThingModelCreate, ThingModelOut, ThingModelUpdate

router = APIRouter()


@router.get("", response_model=list[ThingModelOut], summary="物模型列表")
def list_thing_models(
    kw: str = Query("", description="按 modelKey/name 模糊搜索"),
    category: str = Query("", description="按设备类别过滤"),
    domain: str = Query("", description="按业务域过滤"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    """返回所有物模型模板 (含其 property/service/event 定义)。"""
    return tm_crud.list_models(db, kw=kw, category=category, domain=domain, limit=limit, offset=offset)


@router.get("/{mid}", response_model=ThingModelOut, summary="物模型详情")
def get_thing_model(mid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    row = tm_crud.get(db, mid)
    if not row:
        raise HTTPException(status_code=404, detail="物模型不存在")
    return row


@router.post("", response_model=ThingModelOut, status_code=201, summary="新建物模型")
def create_thing_model(
    payload: ThingModelCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    data = payload.model_dump()
    # 唯一 key 校验
    if tm_crud.get_by_key(db, data["model_key"]):
        raise HTTPException(status_code=409, detail=f"模型 key '{data['model_key']}' 已存在")
    return tm_crud.create(db, data)


@router.put("/{mid}", response_model=ThingModelOut, summary="更新物模型")
def update_thing_model(
    mid: int,
    payload: ThingModelUpdate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = tm_crud.update(db, mid, data)
    if not row:
        raise HTTPException(status_code=404, detail="物模型不存在")
    return row


@router.delete("/{mid}", status_code=204, summary="删除物模型")
def delete_thing_model(
    mid: int,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin")),
):
    if not tm_crud.delete(db, mid):
        raise HTTPException(status_code=404, detail="物模型不存在")
