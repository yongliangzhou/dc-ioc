"""WebSocket 实时遥测推送 — 接入 ws_broadcaster 广播系统。

安全模型 (v2 — 首条握手消息认证):
- Token 不再通过 URL query 传递 (避免泄漏到访问日志 / 代理日志 / Referer)。
- 客户端连接后必须在 AUTH_TIMEOUT 秒内发送首条握手消息 {"type": "auth", "token": "<jwt>"}。
- 验签通过前连接 **不注册进广播池** (暂缓广播), 任何业务消息均被拒绝。
- 验签通过后回复 {"type": "auth_ok"}, 注册进广播池, 开始接收:
  - telemetry: 驾驶舱 KPI 快照 (5s 周期)
  - alarm: 新告警通知 (实时)
  - device_status: 设备在线状态变更
- 兼容: 仍接受 query ?token= / Authorization 头 (标记为已认证, 跳过握手等待),
  但前端已迁移为握手消息, query 方式仅作为过渡保留。
- 开发环境 (APP_ENV=dev/development/local) 允许匿名降级, 生产强制关闭 1008。
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import decode_token
from app.services import ws_broadcaster

logger = logging.getLogger("ws")

router = APIRouter()

# 首条握手消息超时 (秒)
AUTH_TIMEOUT_SEC = 10


def _is_dev() -> bool:
    return settings.APP_ENV in ("dev", "development", "local")


def _token_valid(token: str | None) -> bool:
    """校验 access token 是否有效。"""
    if not token:
        return False
    data = decode_token(token)
    return data is not None and data.get("type") == "access"


def _legacy_token(websocket: WebSocket) -> str | None:
    """过渡兼容: 从 query ?token= 或 Authorization 头提取 token (已弃用路径)。"""
    token = websocket.query_params.get("token")
    if token:
        return token
    auth = websocket.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return None


async def _handshake_auth(websocket: WebSocket) -> tuple[bool, dict | None]:
    """等待首条握手消息 {type:"auth", token} 并验签。

    返回 (authenticated, pending_msg):
    - authenticated: 是否通过认证
    - pending_msg: 若首条消息不是 auth (开发环境匿名场景), 返回该消息供后续处理
    """
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        logger.warning("WS 握手超时 (%ss 内未收到 auth 消息)", AUTH_TIMEOUT_SEC)
        return False, None
    except (WebSocketDisconnect, Exception):
        return False, None

    try:
        msg = json.loads(raw)
    except Exception:
        return False, None

    if isinstance(msg, dict) and (msg.get("type") == "auth" or msg.get("action") == "auth"):
        ok = _token_valid(str(msg.get("token") or ""))
        if not ok:
            logger.warning("WS 握手 token 验签失败")
        return ok, None

    # 首条消息不是 auth: 仅开发环境允许匿名 (消息暂存, 认证放行后继续处理)
    return False, msg if isinstance(msg, dict) else None


async def _handle_command(websocket: WebSocket, cid: str, msg: dict):
    """处理已认证客户端的业务指令: subscribe / unsubscribe。"""
    action = (msg or {}).get("action") or (msg or {}).get("type")
    if action == "subscribe":
        dev = msg.get("device_id")
        if dev:
            ws_broadcaster.subscribe(cid, dev)
            await websocket.send_json({"type": "subscribed", "device_id": dev})
    elif action == "unsubscribe":
        ws_broadcaster.unsubscribe(cid, msg.get("device_id"))


@router.websocket(settings.WS_PATH)
async def telemetry_ws(websocket: WebSocket):
    # 先 accept — 认证在应用层握手消息中完成 (Token 不再经 URL 传输)
    await websocket.accept()

    pending_msg: dict | None = None

    # 1) 过渡兼容: query/header 携带合法 token 则直接视为已认证
    authenticated = _token_valid(_legacy_token(websocket))

    # 2) 标准路径: 等待首条握手消息 {type:"auth", token}
    if not authenticated:
        authenticated, pending_msg = await _handshake_auth(websocket)

    # 3) 未认证: 开发环境匿名降级, 生产直接关闭
    if not authenticated:
        if _is_dev():
            logger.info("WS 匿名连接放行 (仅开发环境)")
            authenticated = True
        else:
            try:
                await websocket.send_json({"type": "auth_error", "message": "unauthorized"})
            except Exception:
                pass
            await websocket.close(code=1008, reason="unauthorized")
            return

    # === 验签通过后才注册进广播池 (此前任何广播都不会到达该连接) ===
    cid = ws_broadcaster.register(websocket)

    try:
        await websocket.send_json({"type": "auth_ok", "client_id": cid})
        await websocket.send_json({
            "type": "connected",
            "client_id": cid,
            "push_interval_s": settings.METRIC_PUSH_INTERVAL,
            # [P1-6] 下发采集器上报周期与 stale 阈值, 前端动态采纳 (替换硬编码 15s)
            "report_interval_s": settings.DEVICE_REPORT_INTERVAL_S,
            "stale_threshold_ms": settings.stale_threshold_ms,
            "message": "DC-IOC 实时遥测已连接",
        })
    except Exception:
        ws_broadcaster.unregister(cid)
        return

    try:
        # 开发环境匿名场景下暂存的首条业务消息, 认证放行后补处理
        if pending_msg is not None:
            await _handle_command(websocket, cid, pending_msg)

        # 接收客户端指令: subscribe / unsubscribe 设备实时通道
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug("WS 接收异常: %s", e)
                break
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            await _handle_command(websocket, cid, msg)
    except WebSocketDisconnect:
        pass
    finally:
        ws_broadcaster.unregister(cid)
