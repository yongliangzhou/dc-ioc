"""告警中心 API (B1: 告警中心消费真实告警引擎)。

- GET /api/alarms/active  -> 返回 alarm_engine 评估产生的真实活跃告警
  (此前该端点被架空, 返回 generated 假告警; 现统一为真实引擎单一出口)
- POST /api/alarms/active/{id}/ack     -> 确认 (写穿 alarm_engine 状态机)
- POST /api/alarms/active/{id}/resolve -> 关单 (从活跃态移除, 触发关联工单联动)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.services import alarm_engine

logger = logging.getLogger("api.alarms")

# 写操作 (确认/关单) 仅限管理员与运维操作员
_rw = [Depends(require_role("admin", "operator"))]

router = APIRouter(prefix="", tags=["alarms"])

# category -> 中文系统名 (展示用)
_CATEGORY_SYS = {
    "chiller": "暖通空调",
    "crac": "暖通空调",
    "acunit": "暖通空调",
    "liquid": "液冷系统",
    "ups": "供配电",
    "pdudevice": "供配电",
    "hv": "供配电",
    "lv": "供配电",
    "genset": "供配电",
    "battery": "储能系统",
    "fuel": "燃油系统",
    "WaterSystem": "给排水",
}


def _active_alarm_view(a: dict) -> dict:
    """将引擎活跃告警 dict 转换为前端告警卡片所需展示字段。

    关键点: 保留 alarm_id 作为 id (与 ack/resolve 路由参数一致), 并补全
    system/desc/threshold 让 AlarmListPanel 展示更完整。
    """
    cat = a.get("category", "")
    metric = a.get("metric_name", "")
    value = a.get("value")
    unit = a.get("unit", "")
    level = a.get("level", "warn")
    sys = _CATEGORY_SYS.get(cat, cat)
    limit = alarm_engine.get_metric_limit(cat, metric)
    desc = f"{a.get('device_id', '')} · {metric} 越限（{value}{unit}）"
    return {
        "id": a.get("alarm_id"),
        "alarm_id": a.get("alarm_id"),
        "device_id": a.get("device_id"),
        "category": cat,
        "metric_name": metric,
        "level": level,
        "value": value,
        "unit": unit,
        "threshold": limit,
        "system": sys,
        "desc": desc,
        "ts": a.get("ts"),
        "ack_state": a.get("ack_state", "待确认"),
        "state": a.get("ack_state", "待确认"),
        "owner": a.get("owner") or "—",
    }


@router.get("/active")
def active_alarms():
    """真实活跃告警 (来自 alarm_engine 评估, 与采集器实时联动)。"""
    items = [_active_alarm_view(a) for a in alarm_engine.get_active_alarms()]
    return {"total": len(items), "items": items}


@router.post("/active/{alarm_id}/ack", dependencies=_rw)
def ack_alarm(alarm_id: str):
    """确认告警 -> 写穿引擎状态机 (待确认 -> 已确认)。"""
    ok = alarm_engine.ack_alarm(alarm_id)
    return {"ok": ok, "id": alarm_id, "state": "已确认"}


@router.post("/active/{alarm_id}/resolve", dependencies=_rw)
def resolve_alarm(alarm_id: str):
    """关单告警 -> 从活跃态移除 (联动工单关单时调用)。"""
    alarm_engine.resolve_alarm(alarm_id)
    return {"ok": True, "id": alarm_id}
