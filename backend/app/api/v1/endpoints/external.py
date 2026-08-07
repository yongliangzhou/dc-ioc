"""外部设备接入 API — 标准数据契约接收端 (采集器对接入口)。

提供两个稳定端点, 采集器团队只需按 API_CONTRACT.md 推送 JSON 即可:
  - POST /api/external/device/register   设备注册
  - POST /api/external/metrics/upload     实时测点上报 (单点 / 批量)

并提供只读查询端点 (供前端「采集器接入 / 设备注册状态」页):
  - GET  /api/external/devices            已注册设备列表 + 注册状态
  - GET  /api/external/devices/{id}/metrics 某设备最近测点

持久化: 优先落库 (app.models.external), 数据库不可用时自动回退到内存兜底,
契约保持不变 (详见 app.crud.external)。Kafka 消费侧复用同一套 Pydantic 契约。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, require_role
from app.crud import external as ext_crud
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.external import (
    DeviceActionResponse,
    DeviceListResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceUpdateRequest,
    MetricPoint,
    MetricRecordView,
    MetricHistoryResponse,
    MetricRealtimeResponse,
    MetricRealtimePoint,
    MetricUploadResponse,
    RejectedItem,
    ThingModelDef,
    ThingModelMetricDef,
)
from app.services.external_ingest import ingest_metrics

logger = logging.getLogger("external")

router = APIRouter()


def verify_collector_token(
    x_collector_token: Optional[str] = Header(None, alias="X-Collector-Token"),
) -> bool:
    """外部采集器 Token 校验 (X-Collector-Token 头), 仅用于写端点。

    未配置 EXTERNAL_COLLECTOR_TOKEN 时: 开发/联调环境放行, 其余环境强制 401。
    生产环境必须配置且匹配, 否则拒绝。
    """
    expected = settings.EXTERNAL_COLLECTOR_TOKEN
    is_dev = settings.APP_ENV in ("dev", "development", "local")
    if not expected:
        if is_dev:
            return True
        raise HTTPException(status_code=401, detail="collector token required")
    if x_collector_token != expected:
        raise HTTPException(status_code=401, detail="invalid collector token")
    return True


def _get_db() -> Optional[Session]:
    """尽量返回数据库会话; 连接不可用时返回 None (由 CRUD 走内存兜底)。"""
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("select 1"))
        return db
    except Exception as e:  # noqa: BLE001
        logger.warning("数据库不可用, 启用内存兜底存储: %s", e)
        return None


@router.post("/device/register", response_model=DeviceRegisterResponse, summary="外部设备注册")
def device_register(
    payload: DeviceRegisterRequest,
    _: bool = Depends(verify_collector_token),
):
    """注册一台外部设备 (采集器首次发现或配置变更时调用)。"""
    db = _get_db()
    try:
        _, status = ext_crud.upsert_device(db, payload)
    finally:
        if db is not None:
            db.commit()
            db.close()
    msg = (
        "设备注册成功"
        if status == "registered"
        else ("设备已存在 (信息已更新)" if status == "updated" else "设备已存在")
    )
    return DeviceRegisterResponse(
        device_id=payload.device_id, status=status,
        received_at=ext_crud._now_iso(), message=msg,
        # [P1-6] 下发上报周期 / stale 阈值, 与 WS connected 保持一致
        report_interval_s=settings.DEVICE_REPORT_INTERVAL_S,
        stale_threshold_ms=settings.stale_threshold_ms,
    )


@router.put("/devices/{device_id}", response_model=DeviceActionResponse, summary="更新设备信息")
def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    _: bool = Depends(verify_collector_token),
):
    """编辑已注册设备的信息 (可只传需要修改的字段)。"""
    db = _get_db()
    try:
        _, found = ext_crud.update_device(db, device_id, payload)
    finally:
        if db is not None:
            db.commit()
            db.close()
    if not found:
        raise HTTPException(status_code=404, detail=f"设备 {device_id} 不存在")
    return DeviceActionResponse(
        device_id=device_id, action="updated",
        received_at=ext_crud._now_iso(), message="设备信息已更新"
    )


@router.delete("/devices/{device_id}", response_model=DeviceActionResponse, summary="删除设备")
def delete_device(
    device_id: str,
    _: bool = Depends(verify_collector_token),
):
    """删除设备及其所有测点数据。"""
    db = _get_db()
    try:
        found = ext_crud.delete_device(db, device_id)
    finally:
        if db is not None:
            db.commit()
            db.close()
    if not found:
        raise HTTPException(status_code=404, detail=f"设备 {device_id} 不存在")
    return DeviceActionResponse(
        device_id=device_id, action="deleted",
        received_at=ext_crud._now_iso(), message="设备及测点数据已删除"
    )


@router.get("/thing-models", response_model=list[ThingModelDef], summary="物模型列表 (传感器/测点模板)")
def list_thing_models(_user: User = Depends(get_current_user)):
    """返回所有设备类别的测点模板 (从 Mock 采集器定义提取)。采集器和前端共用此契约。"""
    from app.collectors.mock_collector import _CATEGORY_METRICS

    # 类别中文名 + 业务域 + 协议 / 测点中文说明: 统一来自配置化物模型 (app.collectors.thing_models)。
    # 支持通过 settings.THING_MODELS_FILE 指定 JSON 覆盖文件, 无需改代码即可新增类别 / 测点说明。
    from app.collectors import thing_models
    _CATEGORY_LABEL = thing_models.CATEGORY_META
    _METRIC_LABEL = thing_models.METRIC_LABELS

    result: list[ThingModelDef] = []
    for cat, metrics in _CATEGORY_METRICS.items():
        label_info = _CATEGORY_LABEL.get(cat, (cat, "", ""))
        result.append(ThingModelDef(
            category=cat,
            category_label=label_info[0],
            domain=label_info[1],
            protocol=label_info[2],
            metrics=[
                ThingModelMetricDef(
                    metric_name=m[0],
                    unit=m[1],
                    description=_METRIC_LABEL.get(m[0], m[0]),
                )
                for m in metrics
            ],
        ))
    return result


@router.post("/metrics/upload", response_model=MetricUploadResponse, summary="实时测点上报 (单点/批量)")
def metrics_upload(
    payload: list[dict[str, Any]],
    _: bool = Depends(verify_collector_token),
):
    """批量 (或单点) 上报实时测点。

    请求体为数组: [{device_id, timestamp, metric_name, value, quality}, ...]。
    支持「单点」= 仅含 1 个元素的数组。逐条校验, 任一条异常不影响其余;
    响应中返回 accepted / rejected 计数与逐条失败原因。
    """
    total = len(payload)
    accepted_points: list[MetricPoint] = []
    rejected: list[RejectedItem] = []

    for idx, item in enumerate(payload):
        try:
            point = MetricPoint.model_validate(item)
        except ValidationError as e:
            rejected.append(RejectedItem(
                index=idx,
                device_id=(item.get("device_id") if isinstance(item, dict) else None),
                reason=str(e).splitlines()[0],
            ))
            continue
        accepted_points.append(point)

    # ---- 统一摄取: 落库 + 告警评估 + 实时 WS 推送 (HTTP / Kafka 双通道共用) ----
    saved = ingest_metrics(accepted_points)

    return MetricUploadResponse(
        total=total,
        accepted=saved,
        rejected=len(rejected),
        rejected_items=rejected,
        received_at=ext_crud._now_iso(),
        message=f"已接收 {saved}/{total} 条测点" + (f", {len(rejected)} 条被拒绝" if rejected else ""),
    )


@router.get("/devices", response_model=DeviceListResponse, summary="已注册设备列表 + 注册状态")
def list_devices(
    domain: Optional[str] = None,
    protocol: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    _user: User = Depends(get_current_user),
):
    """供前端「采集器接入 / 设备注册状态」页: 列出设备并标注在线/离线与测点数。"""
    db = _get_db()
    try:
        items, total, online, offline = ext_crud.list_devices(
            db, domain=domain, protocol=protocol, skip=skip, limit=limit
        )
        total_metrics = ext_crud.total_metric_count(db)
    finally:
        if db is not None:
            db.close()
    return DeviceListResponse(
        total=total, online=online, offline=offline,
        total_metrics=total_metrics, items=items
    )


@router.get(
    "/devices/{device_id}/metrics",
    response_model=list[MetricRecordView],
    summary="某设备最近测点",
)
def device_metrics(device_id: str, limit: int = 50, _user: User = Depends(get_current_user)):
    """返回指定设备最近 limit 条测点 (按接收时间倒序), 用于明细查看。"""
    db = _get_db()
    try:
        rows = ext_crud.recent_metrics(db, device_id, limit=limit)
    finally:
        if db is not None:
            db.close()
    return rows


@router.get("/devices/{device_id}/metrics/realtime", response_model=MetricRealtimeResponse, summary="某设备实时测点快照")
def device_metrics_realtime(device_id: str, _user: User = Depends(get_current_user)):
    """返回设备最新测点 (来自实时缓存), 含在线状态, 供初始加载 / WS 订阅前拉取。"""
    latest = ext_crud.latest_metrics(device_id)
    points = [
        MetricRealtimePoint(
            metric_name=k,
            value=v["value"],
            unit=v.get("unit"),
            quality=v.get("quality", "good"),
        )
        for k, v in latest.items()
    ]
    ts = max((v["ts"] for v in latest.values() if v.get("ts")), default=None)
    return MetricRealtimeResponse(
        device_id=device_id,
        ts=ts,
        online=ext_crud.is_online(device_id),
        points=points,
    )


# ===== 测点定义 CRUD (前端「测点增删改查」) =====
@router.get("/devices/{device_id}/metric-defs", summary="某设备测点定义列表")
def list_metric_defs(device_id: str, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    if db is None:
        return []
    return ext_crud.list_metric_defs(db, device_id)


@router.post("/devices/{device_id}/metric-defs", summary="新增测点定义",
             dependencies=[Depends(require_role("admin", "operator"))])
def create_metric_def(device_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    name = (payload.get("metricName") or "").strip()
    if not name:
        raise HTTPException(422, "metricName 为必填")
    data = {
        "device_id": device_id,
        "metric_name": name,
        "label": payload.get("label", ""),
        "unit": payload.get("unit", ""),
        "data_type": payload.get("dataType", "float"),
        "description": payload.get("description", ""),
        "enabled": payload.get("enabled", True),
    }
    return ext_crud.create_metric_def(db, data=data)


@router.put("/devices/{device_id}/metric-defs/{mid}", summary="更新测点定义",
            dependencies=[Depends(require_role("admin", "operator"))])
def update_metric_def(device_id: str, mid: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    data = {k: v for k, v in payload.items() if v is not None}
    row = ext_crud.update_metric_def(db, mid, data=data)
    if not row:
        raise HTTPException(404, "测点定义不存在")
    return row


@router.delete("/devices/{device_id}/metric-defs/{mid}", status_code=204, summary="删除测点定义",
               dependencies=[Depends(require_role("admin", "operator"))])
def delete_metric_def(device_id: str, mid: int, db: Session = Depends(get_db)):
    if not ext_crud.delete_metric_def(db, mid):
        raise HTTPException(404, "测点定义不存在")


@router.get("/devices/{device_id}/metrics/history", response_model=MetricHistoryResponse, summary="某设备历史测点 (趋势)")
def device_metrics_history(
    device_id: str,
    metrics: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 500,
    _user: User = Depends(get_current_user),
):
    """查询历史测点序列 (供趋势图)。metrics 为逗号分隔的测点名; 不传则取设备全部已知测点。"""
    if metrics:
        metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    else:
        metric_list = list(ext_crud.latest_metrics(device_id).keys())
    db = _get_db()
    try:
        series, unit = ext_crud.query_history(db, device_id, metric_list, start, end, limit)
    finally:
        if db is not None:
            db.close()
    return MetricHistoryResponse(device_id=device_id, unit=unit, series=series)
