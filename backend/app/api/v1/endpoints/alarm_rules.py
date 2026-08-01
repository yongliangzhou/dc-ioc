"""告警规则统一管理 API — 规则配置由后端集中管理, 前端纯展示 + 启停。

Phase 2 增强:
- GET    /api/alarm-rules            规则列表 (AlarmRuleDef 格式)
- POST   /api/alarm-rules            创建规则
- PUT    /api/alarm-rules/{rule_id}  更新规则
- DELETE /api/alarm-rules/{rule_id}  删除规则
- PATCH  /api/alarm-rules/{id}/status   设置状态 (enabled|silenced)
- PATCH  /api/alarm-rules/{id}/silence  静默规则
- PATCH  /api/alarm-rules/{id}/toggle   启停翻转 (兼容旧版)

注: rule_id 形如 "chiller:supply_temp", 响应中 id 为后端分配的数字 ID。
"""
from fastapi import APIRouter, Depends, HTTPException, Body

from app.core.deps import require_role
from app.services import alarm_engine
from app.services.alarm_engine import (
    _rule_id_by_numeric,
    format_rules_for_frontend,
    _format_one_rule,
)

router = APIRouter()

# 写操作仅限管理员与运维操作员
_rw = [Depends(require_role("admin", "operator"))]


def _resolve_id(raw_id: str | int) -> str:
    """将前端传来的数字 ID 反解为后端 rule_id 字符串。若已是字符串则直接返回。"""
    sid = str(raw_id)
    # 尝试数字反查
    try:
        nid = int(raw_id)
        real = _rule_id_by_numeric(nid)
        if real:
            return real
    except (ValueError, TypeError):
        pass
    # 直接当 rule_id 使用 (兼容 "chiller:supply_temp" 格式)
    return sid


# ============ 规则 CRUD ============

@router.get("", summary="告警规则列表 (AlarmRuleDef 格式)")
def get_rules():
    raw = alarm_engine.list_rules()
    return format_rules_for_frontend(raw)


@router.post("", summary="创建告警规则", dependencies=_rw, status_code=201)
def create_rule(
    body: dict = Body(...),
):
    cat = (body.get("category") or "").strip()
    metric = (body.get("metric") or "").strip()
    if not cat or not metric:
        raise HTTPException(status_code=422, detail="category 与 metric 为必填项")
    result = alarm_engine.create_rule(
        category=cat,
        metric=metric,
        warn_lo=body.get("warnLo"),
        warn_hi=body.get("warnHi"),
        crit_lo=body.get("critLo"),
        crit_hi=body.get("critHi"),
        unit=body.get("unit", ""),
    )
    if result is None:
        raise HTTPException(status_code=500, detail="规则创建失败")
    return result


@router.put("/{rule_id}", summary="更新告警规则", dependencies=_rw)
def update_rule(
    rule_id: str | int,
    body: dict = Body(...),
):
    rid = _resolve_id(rule_id)
    result = alarm_engine.update_rule(
        rule_id=rid,
        category=body.get("category", ""),
        metric=body.get("metric", ""),
        warn_lo=body.get("warnLo"),
        warn_hi=body.get("warnHi"),
        crit_lo=body.get("critLo"),
        crit_hi=body.get("critHi"),
        unit=body.get("unit", ""),
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")
    return result


@router.delete("/{rule_id}", summary="删除告警规则", dependencies=_rw)
def delete_rule(rule_id: str | int):
    rid = _resolve_id(rule_id)
    ok = alarm_engine.delete_rule(rid)
    if not ok:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")
    return {"ok": True}


# ============ 规则状态管理 ============

@router.patch("/{rule_id}/toggle", summary="启停告警规则 (翻转)", dependencies=_rw)
def toggle_rule(rule_id: str | int):
    rid = _resolve_id(rule_id)
    result = alarm_engine.toggle_rule(rid)  # bool
    return _format_one_rule(rid, {"enabled": result, "silenced": False})


@router.patch("/{rule_id}/status", summary="设置规则状态 ({status: enabled|silenced})", dependencies=_rw)
def set_rule_status(rule_id: str | int, body: dict = Body(...)):
    status = (body or {}).get("status")
    if status not in ("enabled", "silenced"):
        raise HTTPException(status_code=422, detail="status 须为 enabled|silenced")
    rid = _resolve_id(rule_id)
    if status == "silenced":
        alarm_engine.silence_rule(rid)
    else:
        alarm_engine.set_rule_status(rid, status)
    return _format_one_rule(rid, {"silenced": status == "silenced", "enabled": status != "silenced"})


@router.patch("/{rule_id}/silence", summary="静默告警规则", dependencies=_rw)
def silence_rule(rule_id: str | int, body: dict = Body(default={})):
    rid = _resolve_id(rule_id)
    duration = (body or {}).get("durationMinutes", 0) or (body or {}).get("duration", 0)
    result = alarm_engine.silence_rule(rid, duration)
    if result is None:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")
    return result


# ============ 引擎状态 ============

@router.get("/state", summary="规则引擎运行状态")
def get_engine_state():
    return alarm_engine.engine_state()


# ============ 活动告警 (real-time linkage) ============

@router.get("/active", summary="活动联动告警列表")
def get_active():
    return {"alarms": alarm_engine.get_active_alarms()}


@router.post("/active/{alarm_id}/ack", summary="确认告警", dependencies=_rw)
def ack_alarm(alarm_id: str):
    if not alarm_engine.ack_alarm(alarm_id):
        raise HTTPException(status_code=404, detail=f"告警不存在: {alarm_id}")
    return {"ok": True, "id": alarm_id, "state": "已确认"}


@router.post("/active/{alarm_id}/resolve", summary="关闭告警", dependencies=_rw)
def resolve_alarm(alarm_id: str):
    alarm_engine.resolve_alarm(alarm_id)
    return {"ok": True, "id": alarm_id}
