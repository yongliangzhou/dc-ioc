"""统一告警触达中心端点。

- GET    /api/ops/notifications/channels          通道列表 (登录即可)
- POST   /api/ops/notifications/channels          新建通道        (admin/operator)
- PUT    /api/ops/notifications/channels/{cid}    修改通道        (admin/operator)
- DELETE /api/ops/notifications/channels/{cid}    删除通道        (admin/operator)
- GET    /api/ops/notifications/records           发送记录 (分页/过滤, 登录即可)
- POST   /api/ops/notifications/test              测试发送        (admin/operator)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user, require_role
from app.crud import notification as notif_crud
from app.db.session import SessionLocal
from app.schemas.notification import ChannelCreate, ChannelOut, ChannelUpdate, RecordListResp, TestSendIn, TestSendResp
from app.services import notification_service

router = APIRouter(tags=["notifications"])

_rw = [Depends(require_role("admin", "operator"))]


def _username(user) -> str:
    return getattr(user, "username", None) or "system"


# ------------------------------------------------------------------ #
# 通道配置
# ------------------------------------------------------------------ #
@router.get("/notifications/channels", summary="通知通道列表", response_model=list[ChannelOut])
def list_channels(_user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return notif_crud.list_channels(db)
    finally:
        db.close()


@router.post("/notifications/channels", summary="新建通知通道", response_model=ChannelOut, dependencies=_rw)
def create_channel(body: ChannelCreate, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return notif_crud.create_channel(db, body.model_dump(), _username(user))
    finally:
        db.close()


@router.put("/notifications/channels/{cid}", summary="修改通知通道", response_model=ChannelOut, dependencies=_rw)
def update_channel(cid: int, body: ChannelUpdate, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        obj = notif_crud.update_channel(db, cid, body.model_dump(exclude_unset=True), _username(user))
        if obj is None:
            raise HTTPException(status_code=404, detail="通知通道不存在")
        return obj
    finally:
        db.close()


@router.delete("/notifications/channels/{cid}", summary="删除通知通道", dependencies=_rw)
def delete_channel(cid: int, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        if not notif_crud.delete_channel(db, cid):
            raise HTTPException(status_code=404, detail="通知通道不存在")
        return {"deleted": True}
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 发送记录
# ------------------------------------------------------------------ #
@router.get("/notifications/records", summary="发送记录 (分页/过滤)", response_model=RecordListResp)
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    level: Optional[str] = Query(None, description="crit/warn/info"),
    channel_id: Optional[int] = Query(None, alias="channelId"),
    status: Optional[str] = Query(None, description="sent/failed/muted/dedup"),
    _user=Depends(get_current_user),
):
    db = SessionLocal()
    try:
        return notif_crud.list_records(db, page=page, page_size=page_size, level=level,
                                       channel_id=channel_id, status=status)
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 测试发送
# ------------------------------------------------------------------ #
@router.post("/notifications/test", summary="通道连通性测试发送", response_model=TestSendResp, dependencies=_rw)
def test_send(body: TestSendIn, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        ch = notif_crud.get_channel(db, body.channelId)
        if ch is None:
            raise HTTPException(status_code=404, detail="通知通道不存在")
        if not ch.get("enabled"):
            raise HTTPException(status_code=400, detail="通道已停用, 请先启用后再测试")
        status, err = notification_service.test_channel(ch, body.title, body.message)
        # 测试发送同样留痕 (alarm_id 为空 → 不参与去重)
        notif_crud.create_record(db, {
            "alarm_id": None,
            "channel_id": ch["id"],
            "channel_name": ch.get("name"),
            "level": "info",
            "title": body.title,
            "status": status,
            "error": err,
        })
        return {"channelId": ch["id"], "status": status, "error": err}
    finally:
        db.close()
