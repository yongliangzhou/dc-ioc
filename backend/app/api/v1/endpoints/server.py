"""物理服务器 / U 位识别 API。

路由挂载: /api/servers 与 /api/cabinets/{id}/u-position* (在 router.py 注册)。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.core.deps import get_current_user
from app.crud import server as server_crud
from app.schemas.server import (
    RecognizeResp,
    ServerCreate,
    ServerOut,
    ServerUpdate,
    UPositionView,
)
from app.services import mock_data

router = APIRouter()
# U 位立面 / 识别接口挂在 /api/cabinets 前缀下, 与机柜资源对齐。
cabinet_router = APIRouter()


def _cabinet_meta(cabinet_id: int):
    cab = next((c for c in mock_data.CABINETS if c.id == cabinet_id), None)
    if cab is None:
        return None
    return cab


def _to_out(s: dict) -> ServerOut:
    d = dict(s)
    d["u_height"] = int(s["u_end"]) - int(s["u_start"]) + 1
    return ServerOut.model_validate(d)


def _server_out_db(obj) -> ServerOut:
    d = {
        "id": obj.id,
        "cabinet_id": obj.cabinet_id,
        "asset_no": obj.asset_no,
        "hostname": obj.hostname,
        "ip": obj.ip,
        "brand": obj.brand,
        "model": obj.model,
        "u_start": obj.u_start,
        "u_end": obj.u_end,
        "u_height": obj.u_end - obj.u_start + 1,
        "cpu_model": obj.cpu_model,
        "cpu_count": obj.cpu_count,
        "cpu_cores": obj.cpu_cores,
        "memory_gb": obj.memory_gb,
        "disk_desc": obj.disk_desc,
        "business": obj.business,
        "status": obj.status,
        "source": "rfid",
    }
    return ServerOut.model_validate(d)


@router.get("", response_model=list[ServerOut], summary="机柜内服务器列表 (RFID/资产标签实测)")
def list_servers(
    cabinet_id: int = Query(..., description="机柜 id"),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    meta = _cabinet_meta(cabinet_id)
    u_total = meta.u_total if meta else 42
    rows = server_crud.list_by_cabinet(db, cabinet_id, u_total)
    return [_to_out(r) for r in rows]


@router.get("/{server_id}", response_model=ServerOut, summary="服务器详情")
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    obj = server_crud.get(db, server_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="server not found")
    return _server_out_db(obj)


@router.post("", response_model=ServerOut, status_code=201, summary="登记服务器 (人工/RFID 录入)")
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    obj = server_crud.create(db, payload.model_dump())
    return _server_out_db(obj)


@router.put("/{server_id}", response_model=ServerOut, summary="更新服务器 U 位/配置")
def update_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    obj = server_crud.update(db, server_id, payload.model_dump(exclude_unset=True))
    if obj is None:
        raise HTTPException(status_code=404, detail="server not found")
    return _server_out_db(obj)


@router.delete("/{server_id}", summary="下架/删除服务器")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    if not server_crud.delete(db, server_id):
        raise HTTPException(status_code=404, detail="server not found")
    return {"ok": True}


@cabinet_router.get(
    "/{cabinet_id}/u-position",
    response_model=UPositionView,
    summary="机柜 U 位立面图 (含识别冲突)",
)
def cabinet_u_position(
    cabinet_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    meta = _cabinet_meta(cabinet_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="cabinet not found")
    return server_crud.u_position(
        db, cabinet_id, u_total=meta.u_total, code=meta.code, room=meta.room, row=meta.row
    )


@cabinet_router.post(
    "/{cabinet_id}/u-position/recognize",
    response_model=RecognizeResp,
    summary="触发 U 位多源识别 (电子工单 + RFID 融合)",
)
def recognize_u_position(
    cabinet_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    meta = _cabinet_meta(cabinet_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="cabinet not found")
    return server_crud.recognize(
        db, cabinet_id, u_total=meta.u_total, code=meta.code, room=meta.room
    )
