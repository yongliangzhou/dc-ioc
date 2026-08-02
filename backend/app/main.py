"""FastAPI 应用入口 — 仅负责装配, 生命周期/种子/KPI 广播见 app.core.lifespan。"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import ws
from app.api.v1.router import api_router
from app.core.audit import AuditMiddleware
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging_config import setup_logging
from app.core.monitoring import setup_monitoring
from app.core.secret_check import check_secrets_on_startup

# ---- 结构化日志 ----
setup_logging()
logger = logging.getLogger("main")

# ---- 密钥检查 (生产环境) ----
try:
    check_secrets_on_startup(
        settings.APP_ENV,
        settings.SECRET_KEY or "",
        admin_pwd="admin123",
        postgres_password=settings.POSTGRES_PASSWORD,
        external_collector_token=settings.EXTERNAL_COLLECTOR_TOKEN,
    )
except RuntimeError as e:
    logger.critical("密钥安全检查失败, 应用终止: %s", e)
    raise


app = FastAPI(
    title=settings.APP_NAME,
    version="0.6.0",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# ---- 监控 (Prometheus) ----
setup_monitoring(app)
logger.info("Prometheus 监控已挂载: /metrics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 操作审计 (记录所有 CRUD 写操作)
app.add_middleware(AuditMiddleware)

# 全部业务域 API 统一挂载于 /api
app.include_router(api_router, prefix="/api")

# 上传文件静态访问 (/uploads/<date>/<file>) — 目录不存在时跳过, 不影响启动
_upload_root = os.path.join(os.path.dirname(__file__), "..", "uploads")
if os.path.isdir(_upload_root):
    app.mount("/uploads", StaticFiles(directory=_upload_root), name="uploads")

# 实时遥测 WebSocket
app.include_router(ws.router)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "0.6.0",
        "debug": settings.APP_DEBUG,
    }


@app.get("/ready", tags=["system"])
def ready():
    """Kubernetes 就绪探针: 检查数据库和 Redis 可达性。"""
    checks = {"database": "unknown", "redis": "unknown"}
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("select 1"))
        db.close()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_uri)
        r.ping()
        r.close()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
