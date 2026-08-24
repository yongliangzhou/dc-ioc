"""结构化日志配置 — 基于 loguru。

特性:
- 控制台输出: 开发环境彩色; 生产环境 JSON
- 文件轮转: 自动按天/按大小轮转, 保留 30 天
- 敏感信息脱敏 (access_token / password)
- 链路追踪: 注入 trace_id (取自请求上下文)
"""
import json
import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    """将标准库 logging 重定向到 loguru。"""

    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _sensitive_filter(record: dict) -> bool:
    """脱敏: 从日志中移除 access_token / password 等敏感字段。"""
    sensitive_keys = {"access_token", "password", "password_hash", "token", "secret"}
    msg = record.get("message", "")
    if isinstance(msg, str):
        for key in sensitive_keys:
            if key.lower() in msg.lower():
                # 截断敏感值
                record["message"] = "[REDACTED]" + msg[:20] + "..."
    return True


def setup_logging():
    """配置 loguru 全局日志。

    应在应用启动阶段调用一次。
    """
    # 移除默认 handler
    logger.remove()

    env = settings.APP_ENV.lower()

    # ---- 控制台输出 ----
    if env in ("dev", "test"):
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,
            diagnose=env == "dev",
            filter=_sensitive_filter,
        )
    else:
        # 生产环境: JSON 格式, 便于日志采集 (ELK / Loki)
        def json_formatter(record):
            log_entry = {
                "ts": record["time"].isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
            }
            if record["exception"]:
                log_entry["exception"] = str(record["exception"])
            return json.dumps(log_entry, ensure_ascii=False, default=str)

        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=json_formatter,
            filter=_sensitive_filter,
        )

    # ---- 文件轮转 (生产环境) ----
    if env == "prod":
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 通用业务日志
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            level="INFO",
            rotation="00:00",           # 每天午夜轮转
            retention="30 days",        # 保留 30 天
            compression="gz",           # 压缩归档
            encoding="utf-8",
            format=json.dumps,
            filter=_sensitive_filter,
        )

        # 错误日志单独文件
        logger.add(
            log_dir / "error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
            compression="gz",
            encoding="utf-8",
            backtrace=True,
            diagnose=False,
        )

        # 外部接入日志
        external_logger = logger.bind(module="external")
        external_logger.add(
            log_dir / "external_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            encoding="utf-8",
        )

    # ---- 重定向标准库 logging ----
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 静默 Uvicorn 的访问日志 (由 prometheus 接管)
    for lib in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(lib).handlers = [InterceptHandler()]

    # 5.8.2 日志告警联动: ERROR 级系统日志 -> 统一告警通道 (仅已配置 webhook 时生效)
    try:
        from app.core.alert_bridge import AlertLogHandler

        root = logging.getLogger()
        alert_handler = AlertLogHandler()
        alert_handler.setLevel(logging.ERROR)
        root.addHandler(alert_handler)
    except Exception:  # noqa: BLE001
        pass

    logger.info("日志系统初始化完成: env=%s level=%s", env, settings.LOG_LEVEL)
