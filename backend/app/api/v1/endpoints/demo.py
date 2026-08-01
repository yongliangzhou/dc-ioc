"""v2 演示数据路由 (新版实现, 与旧版占位解耦) —— 统一数据流向。

设计目标:
- 本模块为 v2 数据通道的「演示 / 兜底」端点: 即使外部采集器未在线、数据库未就绪,
  前端「v2 数据演示」页也能拿到结构化数据, 不再出现空白页。
- 使用 dc_aggregator 聚合层，与业务端点共享同一数据流。
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import dc_aggregator as agg

router = APIRouter()


# ------------------------------------------------------------------ v2 总览
@router.get("/overview", summary="v2 驾驶舱总览(演示/兜底)")
def demo_overview() -> dict:
    return agg.dashboard_overview()


# ------------------------------------------------------------------ v2 设备列表
class DemoDeviceItem(BaseModel):
    device_id: str
    name: str
    model: str
    ip: str
    protocol: str
    online: bool
    last_seen: str | None = None
    metric_count: int = 0


class DemoDeviceList(BaseModel):
    total: int
    online: int
    offline: int
    total_metrics: int
    items: list[DemoDeviceItem]


@router.get("/devices", response_model=DemoDeviceList, summary="v2 演示设备列表(兜底)")
def demo_devices(limit: int = 30) -> DemoDeviceList:
    """从 external_devices 查询真实设备，无数据时生成兜底列表。"""
    from app.crud import external as ext_crud
    from app.db.session import SessionLocal

    try:
        db = SessionLocal()
        items, total, online, offline = ext_crud.list_devices(db, skip=0, limit=limit)
        total_metrics = ext_crud.total_metric_count(db)
        db.close()
        if total > 0:
            return DemoDeviceList(
                total=total,
                online=online,
                offline=offline,
                total_metrics=total_metrics,
                items=[DemoDeviceItem(
                    device_id=i.device_id,
                    name=i.name or i.device_id,
                    model=i.model,
                    ip=i.ip,
                    protocol=i.protocol or "—",
                    online=i.online,
                    last_seen=i.last_seen,
                    metric_count=i.metric_count,
                ) for i in items],
            )
    except Exception:
        pass

    # 兜底：生成演示设备
    rng = random.Random(7)
    cats = [
        ("CHILLER", "冷水机组", "Carrier-19XR", "modbus"),
        ("CRAC", "精密空调", "Emerson-DX", "snmp"),
        ("UPS", "UPS 电源", "Vertiv-Liebert", "snmp"),
    ]
    now = datetime.now(timezone.utc)
    fallback_items: list[DemoDeviceItem] = []
    for i in range(1, limit + 1):
        cat, name, model, proto = cats[(i - 1) % len(cats)]
        online = rng.random() > 0.1
        fallback_items.append(
            DemoDeviceItem(
                device_id=f"DEMO-{cat}-{i:02d}",
                name=f"{name}-{i:02d}",
                model=model,
                ip=f"10.40.0.{i}",
                protocol=proto,
                online=online,
                last_seen=now.isoformat() if online else None,
                metric_count=rng.randint(120, 5000),
            )
        )
    return DemoDeviceList(
        total=len(fallback_items),
        online=sum(1 for d in fallback_items if d.online),
        offline=sum(1 for d in fallback_items if not d.online),
        total_metrics=sum(d.metric_count for d in fallback_items),
        items=fallback_items,
    )
