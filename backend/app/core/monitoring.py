"""Prometheus 指标导出 — 注入 FastAPI 应用。

提供:
- prometheus-fastapi-instrumentator: 自动收集 HTTP 请求指标
- rediness: Kubernetes 就绪探针
- 自定义业务指标 (WS 连接数、活跃告警数、设备在线数)
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import FastAPI, Response


# ======================================================================
#  自定义业务指标
# ======================================================================

# HTTP 请求 (除自动埋点外的手工版, 用于特定端点精确计数)
api_requests_total = Counter(
    "dc_ioc_api_requests_total",
    "API 请求总数",
    ["method", "endpoint", "status"],
)

# 活跃 WebSocket 连接数
ws_connections_active = Gauge(
    "dc_ioc_ws_connections_active",
    "当前 WebSocket 连接数",
)

# 活跃告警数
alarms_active = Gauge(
    "dc_ioc_alarms_active",
    "当前活跃告警数",
    ["severity"],
)

# 设备状态
devices_total = Gauge(
    "dc_ioc_devices_total",
    "设备总数及在线数",
    ["status"],  # total / online / offline / alarm
)

# 外部设备接入吞吐
external_points_ingested = Counter(
    "dc_ioc_external_points_ingested_total",
    "外部采集测点累计接收数 (用于 rate() 计算摄取 QPS)",
)

# 外部测点批量写入延迟 (摄取延迟分布)
external_ingest_latency = Histogram(
    "dc_ioc_external_ingest_latency_seconds",
    "外部测点批量写入耗时 (秒)",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

# 告警触发计数
alarms_triggered = Counter(
    "dc_ioc_alarms_triggered_total",
    "告警触发累计次数 (rate() 得告警触发率)",
    ["severity", "system"],
)

# 测点保留清理: 删除条数 / 耗时
metric_retention_deleted = Counter(
    "dc_ioc_metric_retention_deleted_total",
    "保留清理累计删除测点数",
)
metric_retention_duration = Histogram(
    "dc_ioc_metric_retention_duration_seconds",
    "保留清理单次批处理调用耗时 (秒)",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# KPI 快照 (Gauge, 每 5s 更新)
kpi_pue = Gauge("dc_ioc_kpi_pue", "实时 PUE")
kpi_wue = Gauge("dc_ioc_kpi_wue", "实时 WUE")
kpi_it_load_mw = Gauge("dc_ioc_kpi_it_load_mw", "IT 负载 (MW)")
kpi_total_load_mw = Gauge("dc_ioc_kpi_total_load_mw", "总负载 (MW)")
kpi_online_rate = Gauge("dc_ioc_kpi_online_rate", "设备在线率 (%)")

# API 延迟直方图
api_latency = Histogram(
    "dc_ioc_api_latency_seconds",
    "API 请求延迟 (秒)",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# ======================================================================
#  应用级注入
# ======================================================================

def setup_monitoring(app: FastAPI) -> Instrumentator:
    """在 FastAPI 应用上挂载 Prometheus 指标收集体及 /metrics 端点。

    返回值:
        Instrumentator 实例, 调用方可通过它访问 add_extra_handler 等方法。
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics"],
    )

    # 自动添加标准 HTTP 指标
    instrumentator.add(metrics.request_size())
    instrumentator.add(metrics.response_size())
    instrumentator.add(metrics.latency())
    instrumentator.add(metrics.requests())

    # 挂载: 当访问 /metrics 时触发指标生成并返回 prometheus 格式
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return instrumentator


def metrics_response() -> Response:
    """手工版 /metrics 响应 (用于额外注入自定义指标后统一返回)。"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
