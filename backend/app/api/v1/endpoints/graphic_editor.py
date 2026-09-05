"""统一图形编辑入口端点。

- 图形场景配置: /api/ops/graphic-config/{kind} (GET/PUT/DELETE)
  为冷源工艺流程 / 制冷链路 / 温度云图 / 10KV·0.4KV 一次系统图 / 配电链路 /
  柴发并机 / 储油示意 / 电池组拓扑 / 门禁平面 / 周界示意 / 消防平面 等图形页
  提供"节点增删改 + 参数配置"的持久化覆盖层。
- 加油记录: /api/ops/refuel-records (GET/POST/PUT/DELETE)
  替换 PowerFuel.vue 里前端生成的假数据, 变成可增删改的真实记录。

权限: 读接口登录即可; 写接口限定 admin / operator。
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user, require_role
from app.crud import graphic_editor as ge_crud
from app.db.session import SessionLocal
from app.schemas.graphic_editor import (
    GraphicConfigIn,
    GraphicConfigOut,
    RefuelCreate,
    RefuelUpdate,
)

router = APIRouter(tags=["graphic-config"])
refuel_router = APIRouter(tags=["refuel-records"])

_rw = [Depends(require_role("admin", "operator"))]

_EMPTY_SCENE = {"nodes": [], "edges": [], "params": {}, "removed": []}


def _username(user) -> str:
    return getattr(user, "username", None) or "system"


# ------------------------------------------------------------------ #
# 图形场景配置
# ------------------------------------------------------------------ #
@router.get("/graphic-config", summary="列出已保存的图形配置", response_model=list[GraphicConfigOut])
def list_graphic_config(_user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return ge_crud.list_configs(db)
    finally:
        db.close()


@router.get(
    "/graphic-config/{kind}",
    summary="读取某图形的场景配置 (无配置时返回空场景)",
    response_model=GraphicConfigOut,
)
def get_graphic_config(kind: str, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        cfg = ge_crud.get_config(db, kind)
        if cfg is None:
            return {
                "kind": kind,
                "title": "",
                "payload": _EMPTY_SCENE,
                "updatedBy": "system",
                "updatedAt": None,
            }
        return cfg
    finally:
        db.close()


@router.put(
    "/graphic-config/{kind}",
    summary="保存某图形的场景配置 (节点/连线/参数)",
    response_model=GraphicConfigOut,
    dependencies=_rw,
)
def save_graphic_config(kind: str, body: GraphicConfigIn, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return ge_crud.save_config(
            db, kind, body.title, body.payload.model_dump(), _username(user)
        )
    finally:
        db.close()


@router.delete("/graphic-config/{kind}", summary="删除某图形的场景配置 (回到默认渲染)", dependencies=_rw)
def delete_graphic_config(kind: str, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"deleted": ge_crud.delete_config(db, kind)}
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 加油记录
# ------------------------------------------------------------------ #
@refuel_router.get("/refuel-records", summary="加油记录列表")
def list_refuel_records(limit: int = 200, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"items": ge_crud.list_refuels(db, limit)}
    finally:
        db.close()


@refuel_router.post("/refuel-records", summary="新增加油记录", dependencies=_rw)
def create_refuel_record(body: RefuelCreate, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = body.model_dump()
        if ge_crud.get_refuel_by_no(db, data["no"]):
            raise HTTPException(status_code=409, detail=f"记录编号 {data['no']} 已存在")
        return ge_crud.create_refuel(db, data, _username(user))
    finally:
        db.close()


@refuel_router.put("/refuel-records/{rid}", summary="修改加油记录", dependencies=_rw)
def update_refuel_record(rid: int, body: RefuelUpdate, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        obj = ge_crud.update_refuel(db, rid, body.model_dump(exclude_unset=True), _username(user))
        if obj is None:
            raise HTTPException(status_code=404, detail="加油记录不存在")
        return obj
    finally:
        db.close()


@refuel_router.delete("/refuel-records/{rid}", summary="删除加油记录", dependencies=_rw)
def delete_refuel_record(rid: int, _user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        if not ge_crud.delete_refuel(db, rid):
            raise HTTPException(status_code=404, detail="加油记录不存在")
        return {"deleted": True}
    finally:
        db.close()
