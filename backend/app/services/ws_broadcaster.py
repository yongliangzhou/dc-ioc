"""WebSocket 广播管理器 — 向所有连接的客户端推送实时数据。

推送内容:
- telemetry: KPI 快照 (PUE/负载/温度等驾驶舱指标)
- alarm: 新告警通知
- device_status: 设备在线状态变更
- device_metrics: 某设备实时测点 (仅推送给订阅该设备的客户端)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import WebSocket

logger = logging.getLogger("ws_broadcaster")

# 连接池: {client_id: WebSocket}
_connections: dict[str, WebSocket] = {}
_counter = 0

# 按设备订阅关系: device_id -> {client_id}
_device_subs: dict[str, set] = {}

# 后台事件循环引用 (用于从同步上下文安全推送)
_loop = None

# 告警引擎通知处理器已注册标志
_notify_registered = False


def register(client: WebSocket) -> str:
    """注册新连接，返回 client_id。"""
    global _counter, _loop
    _counter += 1
    cid = f"ws-{_counter}"
    _connections[cid] = client
    try:
        _loop = asyncio.get_event_loop()
    except Exception:
        _loop = None
    logger.info("WS 客户端连接: %s (当前 %d 个连接)", cid, len(_connections))
    return cid


def unregister(client_id: str):
    """注销连接。"""
    _connections.pop(client_id, None)
    for subs in _device_subs.values():
        subs.discard(client_id)
    logger.info("WS 客户端断开: %s (剩余 %d 个连接)", client_id, len(_connections))


def subscribe(client_id: str, device_id: str):
    """客户端订阅某设备的实时测点推送。"""
    _device_subs.setdefault(device_id, set()).add(client_id)


def unsubscribe(client_id: str, device_id: Optional[str] = None):
    """取消订阅 (指定 device_id 或该客户端全部订阅)。"""
    if device_id:
        _device_subs.get(device_id, set()).discard(client_id)
    else:
        for subs in _device_subs.values():
            subs.discard(client_id)


async def _send_raw(ws: WebSocket, data: str):
    await ws.send_text(data)


def publish_device_metrics(device_id: str, message: dict):
    """向订阅了该设备的 WS 客户端推送实时测点 (可从同步上下文调用)。"""
    subs = _device_subs.get(device_id)
    if not subs:
        return
    if _loop is None:
        return
    data = json.dumps(message, ensure_ascii=False)
    for cid in list(subs):
        ws = _connections.get(cid)
        if ws is None:
            subs.discard(cid)
            continue
        fut = asyncio.run_coroutine_threadsafe(_send_raw(ws, data), _loop)
        try:
            fut.result(timeout=2)
        except Exception:
            subs.discard(cid)


async def broadcast(message: dict):
    """向所有在线客户端广播 JSON 消息。"""
    if not _connections:
        return
    data = json.dumps(message, ensure_ascii=False)
    tasks = []
    for cid, ws in list(_connections.items()):
        try:
            tasks.append(ws.send_text(data))
        except Exception:
            _connections.pop(cid, None)
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.debug("WS 广播异常: %s", r)


async def broadcast_telemetry(kpi_snapshot: dict):
    """推送实时 KPI 遥测数据。"""
    await broadcast({"type": "telemetry", "data": kpi_snapshot, "ts": _now_iso()})


async def broadcast_alarm(alarm: dict):
    """推送新告警。"""
    await broadcast({"type": "alarm", "data": alarm, "ts": _now_iso()})


async def broadcast_device_status(device_id: str, online: bool):
    """推送设备状态变更。"""
    await broadcast({"type": "device_status", "device_id": device_id, "online": online, "ts": _now_iso()})


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---- 告警引擎集成 ----
def _alarm_ws_notify(alarm: dict):
    """告警引擎通知 → WS 广播。"""
    asyncio.create_task(broadcast_alarm(alarm))


def setup_alarm_notify():
    """将 WS 广播注册为告警引擎的通知处理器 (仅注册一次)。"""
    global _notify_registered
    if _notify_registered:
        return
    from app.services import alarm_engine
    alarm_engine.register_notify_handler("ws_broadcast", _alarm_ws_notify)
    _notify_registered = True
    logger.info("WS 告警通知处理器已注册")