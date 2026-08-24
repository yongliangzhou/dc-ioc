"""5.8.2 日志/审计告警联动。

将「关键审计动作」与「系统级错误」桥接到既有告警 Webhook 通道
(app.services.alarm_notify_webhook)，实现统一告警出口:

  - 关键审计动作 (用户删除 / 角色权限变更 / 登录失败 / 批量删除) -> 安全告警
  - 系统 ERROR 级日志 -> 通过日志 handler 触发运维告警

仅在已配置 ALARM_WEBHOOK_*_URL 时生效 (与告警通知同开关)，否则静默。
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("audit.alert")

# 触发安全告警的审计动作 + 资源组合
_SENSITIVE = {
    ("delete", "users"),
    ("create", "roles"),
    ("update", "roles"),
    ("delete", "roles"),
}


def emit_security_alert(
    action: str,
    resource: str,
    detail: Optional[str] = None,
    username: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """由审计逻辑调用: 关键操作 -> 统一告警通道。"""
    try:
        from app.services.alarm_notify_webhook import notify_webhook
    except Exception:  # noqa: BLE001
        return  # webhook 未启用或导入失败, 静默
    alarm = {
        "level": "warn",
        "category": "security_audit",
        "device_id": username or "system",
        "metric_name": f"{resource}.{action}",
        "value": 1,
        "unit": "",
        "rule_id": "audit-bridge",
        "ts": "",
        "detail": detail or "",
        "src_ip": ip or "",
    }
    notify_webhook(alarm)


def should_alert(action: str, resource: str) -> bool:
    return (action, resource) in _SENSITIVE


class AlertLogHandler(logging.Handler):
    """日志 Handler: ERROR 级系统日志 -> 告警通道 (去重/限流由 webhook 侧兜底)。"""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        if record.name.startswith("uvicorn.access"):
            return  # 访问日志不告警
        try:
            from app.services.alarm_notify_webhook import notify_webhook
        except Exception:  # noqa: BLE001
            return
        alarm = {
            "level": "error",
            "category": "system_log",
            "device_id": "backend",
            "metric_name": record.name,
            "value": 1,
            "unit": "",
            "rule_id": "log-bridge",
            "ts": "",
            "detail": self.format(record)[:1000],
            "src_ip": "",
        }
        notify_webhook(alarm)
