"""Dify API Tool 回调端点（供 Dify 平台配置为「API Tool」回调本项目后端）。

用途：Dify 在对话编排中可调用的实时数据工具，让 AI 助手在问答时拿到最新告警 / 测点，
与知识库 RAG 检索形成「静态知识 + 动态态势」的闭环。

安全：所有端点仅暴露只读查询，且要求请求头携带
    Authorization: Bearer <DIFY_TOOL_KEY>
与 Dify 侧「API Tool」的鉴权配置一致。未配置 DIFY_TOOL_KEY 时端点返回 503，
提示运维在 .env 中配置。复用 alarm_engine / ext_crud 既有查询，避免重复实现。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import settings
from app.services import alarm_engine
from app.crud import external as ext_crud

logger = logging.getLogger("api.dify_tools")

router = APIRouter(prefix="/dify/tools", tags=["dify-tools"])


def _verify_tool_key(authorization: Optional[str] = Header(None)) -> None:
    """校验 Dify 回调鉴权 Bearer Token。"""
    if not settings.DIFY_TOOL_KEY:
        raise HTTPException(503, "Dify 工具未启用：请在 .env 配置 DIFY_TOOL_KEY")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "缺少 Authorization: Bearer <DIFY_TOOL_KEY>")
    token = authorization[len("Bearer ") :].strip()
    if token != settings.DIFY_TOOL_KEY:
        raise HTTPException(403, "DIFY_TOOL_KEY 校验失败")


@router.get("/alarms/active", summary="活跃告警（供 Dify API Tool 回调）")
def tool_active_alarms(_auth: None = Depends(_verify_tool_key)):
    """返回当前真实活跃告警（来自 alarm_engine 评估）。"""
    items = [
        {
            "device_id": a.get("device_id"),
            "metric": a.get("metric_name"),
            "value": a.get("value"),
            "level": a.get("level"),
            "rule_id": a.get("rule_id"),
            "ts": a.get("ts"),
        }
        for a in alarm_engine.get_active_alarms(limit=50)
    ]
    return {"total": len(items), "items": items}


@router.get("/metrics/realtime", summary="设备实时测点快照（供 Dify API Tool 回调）")
def tool_metrics_realtime(
    device_id: str,
    _auth: None = Depends(_verify_tool_key),
):
    """返回指定设备最新测点（来自实时缓存），含在线状态。"""
    if not device_id:
        raise HTTPException(422, "device_id 为必填")
    latest = ext_crud.latest_metrics(device_id)
    points = [
        {
            "metric_name": k,
            "value": v.get("value"),
            "unit": v.get("unit"),
            "quality": v.get("quality", "good"),
        }
        for k, v in latest.items()
    ]
    ts = max((v.get("ts") for v in latest.values() if v.get("ts")), default=None)
    return {
        "device_id": device_id,
        "ts": ts,
        "online": ext_crud.is_online(device_id),
        "points": points,
    }


@router.get("/devices", summary="已注册设备列表（供 Dify API Tool 回调）")
def tool_devices(
    domain: Optional[str] = None,
    limit: int = 200,
    _auth: None = Depends(_verify_tool_key),
):
    """返回已注册设备列表与在线/离线统计。"""
    items, total, online, offline = ext_crud.list_devices(
        None, domain=domain, limit=limit
    )
    return {
        "total": total,
        "online": online,
        "offline": offline,
        "items": [
            {
                "device_id": it.get("device_id") if isinstance(it, dict) else getattr(it, "device_id", None),
                "name": it.get("name") if isinstance(it, dict) else getattr(it, "name", None),
                "domain": it.get("domain") if isinstance(it, dict) else getattr(it, "domain", None),
                "online": it.get("online") if isinstance(it, dict) else getattr(it, "online", None),
            }
            for it in items
        ],
    }
