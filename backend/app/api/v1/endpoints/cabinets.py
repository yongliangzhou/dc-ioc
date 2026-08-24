"""机柜 API (Mock): 分页列表 + 单机柜时序指标。
统一数据流向: 机柜属于非物理采集设备，暂保留 mock_data 生成器。
"""
from fastapi import APIRouter, HTTPException, Query

from app.schemas.dashboard import CabinetItem, CabinetMetrics, Paginated
from app.services import mock_data

router = APIRouter()


@router.get("", response_model=Paginated[CabinetItem], summary="机柜分页列表")
def list_cabinets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=2000),
    room: str | None = Query(None, description="按机房筛选, 如 R01"),
):
    total, items = mock_data.list_cabinets(page=page, size=size, room=room)
    return Paginated[CabinetItem](total=total, page=page, size=size, items=items)


@router.get("/{cabinet_id}/metrics", response_model=CabinetMetrics, summary="机柜近1小时温湿度/功耗曲线")
def get_cabinet_metrics(
    cabinet_id: int,
    minutes: int = Query(60, ge=5, le=720, description="回看分钟数"),
    step_sec: int = Query(60, ge=10, le=600, description="采样间隔秒"),
):
    data = mock_data.cabinet_metrics(cabinet_id, minutes=minutes, step_sec=step_sec)
    if data is None:
        raise HTTPException(status_code=404, detail="cabinet not found")
    return data
