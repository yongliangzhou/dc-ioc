"""v1 API 路由聚合 (全部业务域统一挂载于 /api 前缀, 由 main 挂载)。"""
from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    alarms,
    alarm_history,
    alarm_rules,
    audit,
    auth,
    cabinets,
    dashboard,
    demo,
    domain,
    drill,
    equipment,
    external,
    hvac,
    inspection,
    knowledge,
    metrics,
    network,
    ops,
    power,
    risk,
    runbooks,
    security,
    shift,
    uploads,
    tickets,
    assistant,
)
from app.core.deps import get_current_user

api_router = APIRouter()

# 认证 (独立前缀, 不挂载 /v1)
api_router.include_router(auth.router, tags=["auth"])

# 业务域默认要求登录鉴权 (external 走独立 X-Collector-Token 鉴权, 不叠加此依赖)
_auth = [Depends(get_current_user)]

# 驾驶舱 / 机柜 (原有 Mock 契约)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"], dependencies=_auth)
api_router.include_router(cabinets.router, prefix="/cabinets", tags=["cabinets"], dependencies=_auth)

# 统一设备台账 (按阿里云课程 domain/category 分类)
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"], dependencies=_auth)

# 暖通 / 电力 / 安防消防 / 智能运营+运维作业
api_router.include_router(hvac.router, prefix="/hvac", tags=["hvac"], dependencies=_auth)
api_router.include_router(power.router, prefix="/power", tags=["power"], dependencies=_auth)
api_router.include_router(security.router, prefix="/security", tags=["security"], dependencies=_auth)
api_router.include_router(ops.router, prefix="/ops", tags=["ops"], dependencies=_auth)
api_router.include_router(alarms.router, prefix="/alarms", tags=["alarms"], dependencies=_auth)
api_router.include_router(alarm_rules.router, prefix="/alarm-rules", tags=["alarm-rules"], dependencies=_auth)
api_router.include_router(alarm_history.router, tags=["alarm-history"], dependencies=_auth)
api_router.include_router(tickets.router, tags=["tickets"], dependencies=_auth)
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"], dependencies=_auth)
api_router.include_router(knowledge.router, prefix="/ops/knowledge", tags=["knowledge"], dependencies=_auth)
api_router.include_router(shift.router, prefix="/ops/shift", tags=["shift"], dependencies=_auth)
api_router.include_router(audit.router, prefix="/audit-logs", tags=["audit"], dependencies=_auth)
api_router.include_router(drill.router, prefix="/ops/drill", tags=["drill"], dependencies=_auth)
api_router.include_router(risk.router, prefix="/ops/risk", tags=["risk"], dependencies=_auth)
# 运维预案 (runbooks): 告警关联处置预案, 复用知识库 related 逻辑
api_router.include_router(runbooks.router, tags=["runbooks"], dependencies=_auth)
api_router.include_router(inspection.router, prefix="/ops/inspection", tags=["inspection"], dependencies=_auth)
api_router.include_router(assistant.router, prefix="", tags=["assistant"], dependencies=_auth)

# 网络监控 (交换机端口流量 / Ping / 带宽)
api_router.include_router(network.router, prefix="/network", tags=["network"], dependencies=_auth)
api_router.include_router(domain.router, tags=["domain"], dependencies=_auth)

# 外部设备接入 (采集器标准数据契约: 注册 / 测点上报), 使用独立 X-Collector-Token 鉴权
api_router.include_router(external.router, prefix="/external", tags=["external"])
# 通用文件上传 (头像/附件/批量)
api_router.include_router(uploads.router, tags=["uploads"], dependencies=_auth)
# WebSocket 遥测在 main 中单独挂载于 /ws

# v2 演示 / 兜底数据路由 (新版实现, 与旧版占位解耦; 挂载于 /api/demo)
api_router.include_router(demo.router, prefix="/demo", tags=["demo-v2"], dependencies=_auth)
