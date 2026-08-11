"""应用配置: 统一从环境变量读取 (pydantic-settings)。"""
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# 开发环境未配置 SECRET_KEY 时自动生成的临时密钥 (模块级缓存, 重启失效)
_DEV_SECRET: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    APP_NAME: str = "DC-IOC Platform"
    APP_ENV: str = "dev"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str | None = None
    # JWT 签名密钥: 生产必须外部注入(通过环境变量); 开发环境未设置时自动生成临时密钥 (重启失效)
    @property
    def jwt_secret(self) -> str:
        if self.SECRET_KEY:
            return self.SECRET_KEY
        if self.APP_ENV in ("dev", "development", "local"):
            global _DEV_SECRET
            if _DEV_SECRET is None:
                _DEV_SECRET = secrets.token_hex(32)
            return _DEV_SECRET
        return ""
    LOG_LEVEL: str = "INFO"

    # 速率限制 (全局启用, 登录端点默认限流)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # PostgreSQL
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "dcuser"
    POSTGRES_PASSWORD: str = "dcpass"
    POSTGRES_DB: str = "dc_ioc"
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True
    DB_CONNECT_TIMEOUT: int = 3
    DB_ECHO: bool = False  # 生产必须关

    @property
    def sqlalchemy_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_CACHE_DB: int = 1
    REDIS_URL: str | None = None

    @property
    def redis_uri(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT / 认证
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Celery
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/3"

    # CORS (环境变量用逗号分隔字符串, 代码中用 cors_origin_list 属性取 List)
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # 实时推送
    WS_PATH: str = "/ws"
    METRIC_PUSH_INTERVAL: int = 3

    # [P1-6] 设备上报周期与前端的 stale 阈值联动: 后端在 WS connected / 设备注册响应
    # 下发 report_interval_s / stale_threshold_ms, 前端据此动态判定"测点陈旧",
    # 避免前端硬编码 15s 与采集器实际上报节奏脱节 (采集器改周期无需改前端)。
    DEVICE_REPORT_INTERVAL_S: int = 5  # 采集器测点上报周期 (与 mock_collector.PUSH_INTERVAL_SEC 对齐)
    REALTIME_STALE_MULTIPLIER: int = 3  # 超过该倍数周期未更新 => 测点断流/卡住

    @property
    def stale_threshold_ms(self) -> int:
        """前端判定单测点 stale 的阈值 (ms) = 上报周期 × 倍数。"""
        return self.DEVICE_REPORT_INTERVAL_S * self.REALTIME_STALE_MULTIPLIER * 1000

    # 外部设备接入 (采集器标准数据契约)
    # 配置后, 采集器须携带请求头 X-Collector-Token 方可调用 /api/external/*
    # 留空则开发/联调阶段放行
    EXTERNAL_COLLECTOR_TOKEN: str | None = None

    # 外部设备接入 · Kafka 消费端 (复用同一套 Pydantic 契约反序列化)
    # 配置 EXTERNAL_KAFKA_BOOTSTRAP_SERVERS 后, 应用启动会自动拉起消费协程;
    # 未配置则不启动 (端点 HTTP 接入仍可用)。
    EXTERNAL_KAFKA_BOOTSTRAP_SERVERS: str | None = None
    EXTERNAL_KAFKA_INGEST_TOPIC: str = "dc_ioc_external_ingest"
    EXTERNAL_KAFKA_DLQ_TOPIC: str = "dc_ioc_external_ingest_dlq"
    EXTERNAL_KAFKA_GROUP_ID: str = "dc_ioc_collector"

    # 外部设备接入 · Mock 采集器 (开发/联调用)
    # 作为内部 HTTP 客户端, 按契约 v1 向 /api/external/* 推数据, 不直接写库。
    # 生产环境务必设为 False。
    EXTERNAL_MOCK_COLLECTOR_ENABLED: bool = False
    EXTERNAL_MOCK_COLLECTOR_BASE_URL: str = "http://127.0.0.1:8000"

    # 外部设备接入 · 测点保留策略 (按存储引擎分层, 见 P0-1)
    # interval/days 决定清理周期与 TTL; batch_size 为 plain 模式分批 DELETE 单批行数。
    EXTERNAL_METRIC_RETENTION_DAYS: int = 30
    EXTERNAL_METRIC_RETENTION_INTERVAL_SEC: int = 6 * 60 * 60
    EXTERNAL_METRIC_RETENTION_BATCH_SIZE: int = 50000

    # [P2-7] 告警 Webhook 通知 (预留通道: 钉钉 / 邮件 / 微信)
    # 默认全空 => 该通道静默跳过 (不影响告警落库与 WS 实时刷新)。
    # 配置对应 URL 后, 命中阈值的告警会异步 POST 到该 Webhook (见 services/alarm_notify_webhook.py)。
    ALARM_WEBHOOK_DINGTALK_URL: str = ""
    ALARM_WEBHOOK_EMAIL_URL: str = ""
    ALARM_WEBHOOK_WECHAT_URL: str = ""

    # 物模型配置覆盖文件 (JSON): 用于在不改代码的情况下扩展 / 覆盖设备类别与测点说明
    # 格式见 deploy/thing_models.example.json; 留空则仅使用内置默认映射。
    THING_MODELS_FILE: str | None = None

    # [AI 助手] Dify RAG 检索层 (可选)
    # 配置 DIFY_API_KEY + DIFY_DATASET_ID 后, 知识库检索优先走 Dify Knowledge API (向量召回 top-k);
    # 失败/未配置时回退本地关键词打分。生成仍走现有 NIM 小模型 (LLM_*)。
    DIFY_API_KEY: str | None = None
    DIFY_BASE_URL: str = "http://localhost:5001/v1"  # Dify 控制台 API 地址, 结尾不带 /
    DIFY_DATASET_ID: str | None = None  # 知识库 ID (Dify 知识库设置页 "API 访问" 获取)
    # Dify 平台 API Tool 回调本项目后端时携带的 Bearer Token (与 Dify 侧配置一致)
    DIFY_TOOL_KEY: str | None = None
    DIFY_RETRIEVE_TOP_K: int = 5  # 向量检索召回数量


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
