"""统一告警触达中心 · 服务层。

在 alarm_engine 的 notify_handler 注册机制上增加 "notification-center" 处理器,
作为 ws_broadcaster (WS 实时) 与 alarm_notify_webhook (env 预留通道) 之外的
第三个投递通道 —— 也是唯一"可配置、可留痕"的通道:

    级别路由 (通道 minLevel) → 静默窗口 (quietStart/quietEnd) →
    去重 (同 alarm_id+channel 10 分钟) → 投递 (失败退避重试 ≤2 次) →
    落库 notification_record (sent/failed/muted/dedup)

投递复用 alarm_notify_webhook 的 payload 构造器与 urllib 发送 (无第三方依赖),
全程守护线程异步, 不阻塞告警主链路。
"""
import json
import logging
import threading
import urllib.request
from datetime import datetime

from app.services.alarm_notify_webhook import _build_payload

logger = logging.getLogger("alarm.notification")

DEDUP_WINDOW_MIN = 10   # 同 alarm_id + 同通道 去重窗口 (分钟)
RETRY_MAX = 2           # 失败重试次数上限
_POST_TIMEOUT = 5

_REGISTERED = False


# ------------------------------------------------------------------ #
# 静默窗口
# ------------------------------------------------------------------ #
def _in_quiet_window(channel: dict, now: datetime | None = None) -> bool:
    """quietStart/quietEnd 形如 "22:00"; 支持 跨零点 (22:00-07:00)。"""
    qs, qe = channel.get("quietStart"), channel.get("quietEnd")
    if not qs or not qe:
        return False
    try:
        h1, m1 = qs.split(":")
        h2, m2 = qe.split(":")
        start = int(h1) * 60 + int(m1)
        end = int(h2) * 60 + int(m2)
    except (ValueError, AttributeError):
        return False
    now = now or datetime.now()
    cur = now.hour * 60 + now.minute
    if start <= end:
        return start <= cur < end
    return cur >= start or cur < end  # 跨零点


# ------------------------------------------------------------------ #
# 通道执行 (单通道, 带重试)
# ------------------------------------------------------------------ #
def _post_once(url: str, payload: dict) -> tuple[bool, str]:
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=_POST_TIMEOUT) as resp:
            if resp.status >= 400:
                return False, f"HTTP {resp.status}"
        return True, ""
    except Exception as e:  # noqa: BLE001  # 网络异常按失败处理, 由重试/落库兜底
        return False, str(e)


def deliver(channel: dict, alarm: dict) -> tuple[str, str, int]:
    """向单通道投递告警, 失败退避重试。返回 (status, error, retry_count)。"""
    url = channel.get("url") or ""
    if not url:
        return "failed", "通道未配置 URL", 0
    payload = _build_payload(channel.get("type") or "custom", alarm)
    last_err = ""
    for attempt in range(RETRY_MAX + 1):
        ok, err = _post_once(url, payload)
        if ok:
            return "sent", "", attempt
        last_err = err
        logger.debug("通知投递失败 (%s#%s, 第 %d 次): %s", channel.get("name"), url, attempt + 1, err)
    return "failed", last_err, RETRY_MAX


# ------------------------------------------------------------------ #
# 路由层 (级别路由 → 静默 → 去重 → 投递 → 落库)
# ------------------------------------------------------------------ #
def _alarm_title(alarm: dict) -> str:
    return (
        f"[{(alarm.get('level') or 'info').upper()}] "
        f"{alarm.get('device_id', '?')} {alarm.get('metric_name', '?')}"
        f"={alarm.get('value')}{alarm.get('unit', '')}"
    )


def dispatch_sync(alarm: dict) -> None:
    """同步执行全通道路由与投递 (自带会话管理; 供异步线程调用)。"""
    from app.crud import notification as notif_crud
    from app.db.session import SessionLocal

    level = (alarm.get("level") or "info").lower()
    alarm_id = alarm.get("alarm_id") or ""
    title = _alarm_title(alarm)

    db = SessionLocal()
    try:
        for ch in notif_crud.list_channels(db, enabled_only=True):
            # 1) 级别路由: 通道 minLevel 之上的才投递
            if not notif_crud.level_at_least(level, ch.get("minLevel") or "crit"):
                continue
            # 2) 静默窗口: 记 muted 留痕 (可追溯"为什么没收到")
            if _in_quiet_window(ch):
                notif_crud.create_record(db, {
                    "alarm_id": alarm_id, "channel_id": ch["id"],
                    "channel_name": ch.get("name"), "level": level,
                    "title": title, "status": "muted",
                })
                continue
            # 3) 去重: 同告警 + 同通道 窗口内只发一次
            if notif_crud.is_duplicated(db, alarm_id, ch["id"], DEDUP_WINDOW_MIN):
                notif_crud.create_record(db, {
                    "alarm_id": alarm_id, "channel_id": ch["id"],
                    "channel_name": ch.get("name"), "level": level,
                    "title": title, "status": "dedup",
                })
                continue
            # 4) 投递 + 落库
            status, err, retries = deliver(ch, alarm)
            if status != "sent":
                logger.warning("告警通知投递失败 (%s): %s", ch.get("name"), err)
            notif_crud.create_record(db, {
                "alarm_id": alarm_id, "channel_id": ch["id"],
                "channel_name": ch.get("name"), "level": level,
                "title": title, "status": status, "error": err,
                "retry_count": retries,
            })
    except Exception as e:  # noqa: BLE001  # 通知链路任何异常不影响告警主流程
        logger.debug("通知中心分发异常: %s", e)
    finally:
        db.close()


def notify_center_handler(alarm: dict) -> None:
    """alarm_engine notify_handler 入口: 守护线程异步执行, 不阻塞告警链路。"""
    try:
        threading.Thread(target=dispatch_sync, args=(alarm,), daemon=True).start()
    except Exception as e:  # noqa: BLE001
        logger.debug("通知中心线程启动失败: %s", e)


# ------------------------------------------------------------------ #
# 测试发送 (通知中心页 "测试" 按钮)
# ------------------------------------------------------------------ #
def test_channel(channel: dict, title: str, message: str) -> tuple[str, str]:
    """向单通道发送连通性测试。返回 (status, error)。"""
    synthetic = {
        "level": "info",
        "device_id": "TEST",
        "metric_name": "connectivity",
        "value": 0,
        "unit": "",
        "ts": datetime.now().isoformat(timespec="seconds"),
        "rule_id": "notification-test",
        "title": title,
        "message": message,
    }
    # 测试消息走通用 payload 附带 message, 钉钉/微信通道用其专用格式
    status, err, _ = deliver(channel, synthetic)
    return status, err


# ------------------------------------------------------------------ #
# 注册 (由 lifespan 调用, 仅一次)
# ------------------------------------------------------------------ #
def register_notification_center() -> None:
    """注册 'notification-center' handler。

    无论通道表是否有启用通道都注册 —— dispatch 每次实时查库,
    管理员在 UI 增开通道后即刻生效, 无需重启。
    """
    global _REGISTERED
    if _REGISTERED:
        return
    from app.services import alarm_engine

    alarm_engine.register_notify_handler("notification-center", notify_center_handler)
    _REGISTERED = True
    logger.info("统一告警触达中心 (notification-center) 已注册")
