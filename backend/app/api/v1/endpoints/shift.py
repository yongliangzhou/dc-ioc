"""值班排班接口 (2.3)。"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import shift as shift_crud
from app.models.user import User
from app.schemas.shift import ShiftCreate, ShiftOut, ShiftUpdate

router = APIRouter()


def _date_range(start: str | None, end: str | None):
    today = datetime.now().strftime("%Y-%m-%d")
    if not start:
        start = today
    if not end:
        end = (datetime.strptime(start, "%Y-%m-%d") + timedelta(days=13)).strftime("%Y-%m-%d")
    return start, end


@router.get("", response_model=list[ShiftOut], summary="值班排班列表")
def list_shifts(
    start: str | None = Query(default=None, description="YYYY-MM-DD"),
    end: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    s, e = _date_range(start, end)
    return shift_crud.list_items(db, start=s, end=e)


@router.get("/{item_id}", response_model=ShiftOut, summary="排班详情")
def get_shift(item_id: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    item = shift_crud.get(db, item_id)
    if not item:
        raise HTTPException(404, "排班记录不存在")
    return item


@router.post("", response_model=ShiftOut, status_code=201, summary="新建排班")
def create_shift(
    req: ShiftCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    return shift_crud.create(db, data=req.model_dump())


@router.put("/{item_id}", response_model=ShiftOut, summary="更新排班")
def update_shift(
    item_id: int,
    req: ShiftUpdate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    item = shift_crud.update(db, item_id, data=data)
    if not item:
        raise HTTPException(404, "排班记录不存在")
    return item


@router.delete("/{item_id}", status_code=204, summary="删除排班")
def delete_shift(
    item_id: int,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    if not shift_crud.delete(db, item_id):
        raise HTTPException(404, "排班记录不存在")
