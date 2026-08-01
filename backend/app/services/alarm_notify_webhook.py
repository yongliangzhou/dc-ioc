"""告警 Webhook 通知 (预留通道: 钉钉 / 邮件 / 微信)。

[P2-7] 告警通知渠道接通: 在 alarm_engine._notify 的注册机制上, 增加一个 Webhook 通道。
- 默认关闭: 仅当在 settings 中配置了对应 URL 才启用, 否则该通道静默跳过 (不影响告警落库与 WS 实时刷新)。
- 命中阈值的告警会异步 (守护线程, 不阻塞告警链路) POST 到各已配置的 Webhook。
- 无需额外第三方依赖: 使用标准库 urllib 发送。

启用方式 (config / 环境变量):
    ALARM_WEBHOOK_DINGTALK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
    ALARM_WEBHOOK_EMAIL_URL=https://hooks.example.com/email
    ALARM_WEBHOOK_WECHAT_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
"""
import json
import logging
import threading
import urllib.request

from app.core.config import settings

logger = logging.getLogger("alarm.webhook")

# 各通道定义: url 运行时从 settings 注入; fmt 决定 payload 形态
_CHANNELS: dict[str, dict] = {
    "dingtalk": {"url": None, "fmt": "dingtalk"},
    "email": {"url": None, "fmt": "generic"},
    "wechat": {"url": None, "fmt": "wechat"},
}


def _load_channels() -> None:
    _CHANNELS["dingtalk"]["url"] = settings.ALARM_WEBHOOK_DINGTALK_URL or None
    _CHANNELS["email"]["url"] = settings.ALARM_WEBHOOK_EMAIL_URL or None
    _CHANNELS["wechat"]["url"] = settings.ALARM_WEBHOOK_WECHAT_URL or None


def _build_payload(channel: str, alarm: dict) -> dict:
    """按通道构造 Webhook payload。"""
    level = (alarm.get("level") or "warn").upper()
    device = alarm.get("device_id", "?")
    metric = alarm.get("metric_name", "?")
    value = alarm.get("value")
    unit = alarm.get("unit", "")
    ts = alarm.get("ts", "")

    if channel == "dingtalk":
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "DC-IOC 告警",
                "text": (
                    f"#### {level} 告警\n"
                    f"> **设备**: {device}\n\n"
                    f"> **测点**: {metric}\n\n"
                    f"> **值**: {value}{unit}\n\n"
                    f"> **规则**: {alarm.get('rule_id', '-')}\n\n"
                    f"> **时间**: {ts}\n"
                ),
            },
        }
    if channel == "wechat":
        return {
            "msgtype": "text",
            "text": {
                "content": f"[DC-IOC 告警] {level} {device} {metric}={value}{unit} (规则 {alarm.get('rule_id', '-')})",
            },
        }
    # 通用 JSON (邮件网关 / 自定义接收端)
    return {"alarm": alarm, "channel": channel}


def _post(url: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 400:
                logger.warning("告警 Webhook 推送失败 (%s): HTTP %s", url, resp.status)
    except Exception as e:  # noqa: BLE001
        logger.debug("告警 Webhook 推送异常: %s", e)


def notify_webhook(alarm: dict) -> None:
    """告警事件 -> 各已配置 Webhook 通道 (异步线程, 不阻塞告警链路)。"""
    for name, cfg in _CHANNELS.items():
        url = cfg.get("url")
        if not url:
            continue
        payload = _build_payload(name, alarm)
        try:
            t = threading.Thread(target=_post, args=(url, payload), daemon=True)
            t.start()
        except Exception as e:  # noqa: BLE001
            logger.debug("告警 Webhook 线程启动失败: %s", e)


def register_webhook_notifier() -> None:
    """注册 Webhook 通知处理器 (由 lifespan 调用, 仅注册一次)。"""
    _load_channels()
    enabled = [n for n, c in _CHANNELS.items() if c.get("url")]
    if enabled:
        from app.services import alarm_engine

        alarm_engine.register_notify_handler("webhook", notify_webhook)
        logger.info("告警 Webhook 通知已注册, 启用通道: %s", ", ".join(enabled))
    else:
        logger.info("告警 Webhook 通知未启用 (未配置 ALARM_WEBHOOK_*_URL)")
