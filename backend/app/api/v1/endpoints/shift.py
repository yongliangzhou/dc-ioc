"""值班排班接口 (2.3)。"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import shift as shift_crud
from app.models.user import User
from app.schemas.shift import (
    ShiftCreate,
    ShiftOut,
    ShiftUpdate,
    HandoverCreate,
    HandoverOut,
    HandoverUpdate,
)

router = APIRouter()


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


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


# ===== 交接班记录 =====
@router.get("/handover", summary="交接班记录列表")
def list_handovers(
    shiftDate: str = Query(default="", alias="shiftDate"),
    status: str = Query(default="", alias="status"),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    return {
        "items": shift_crud.list_handovers(db, shift_date=shiftDate, status=status),
        "total": shift_crud.count_handover(db, shift_date=shiftDate, status=status),
    }


@router.post("/handover", response_model=HandoverOut, status_code=201, summary="新建交接班记录")
def create_handover(
    req: HandoverCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    data = req.model_dump()
    data = {_to_snake(k): v for k, v in data.items()}
    return shift_crud.create_handover(db, data=data)


@router.get("/handover/{hid}", response_model=HandoverOut, summary="交接班记录详情")
def get_handover(hid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    row = shift_crud.get_handover(db, hid)
    if not row:
        raise HTTPException(404, "交接班记录不存在")
    return row


@router.put("/handover/{hid}", response_model=HandoverOut, summary="更新交接班记录")
def update_handover(
    hid: int,
    req: HandoverUpdate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    data = {_to_snake(k): v for k, v in req.model_dump().items() if v is not None}
    row = shift_crud.update_handover(db, hid, data=data)
    if not row:
        raise HTTPException(404, "交接班记录不存在")
    return row


@router.delete("/handover/{hid}", status_code=204, summary="删除交接班记录")
def delete_handover(
    hid: int,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    if not shift_crud.delete_handover(db, hid):
        raise HTTPException(404, "交接班记录不存在")
