"""统一设备台账 API (按阿里云课程 domain/category 业务单元分类)。
统一数据流向: external_devices 为单一事实源 (B2), 无数据时回退生成器。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.business import EquipmentOut, EquipmentMetrics, EquipmentPage
from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("", response_model=EquipmentPage, summary="设备台账列表 (可按域/类别/包间/状态/关键字筛选 + 分页)")
def list_equipment(
    domain: Optional[str] = Query(None, description="业务域 hvac_source/hvac_terminal/power_hv/..."),
    category: Optional[str] = Query(None, description="设备类别 chiller/crac/ups/genset/..."),
    room: Optional[str] = Query(None, description="包间编码 R01"),
    status: Optional[str] = Query(None, description="运行状态"),
    kw: Optional[str] = Query(None, description="关键字: 编码/名称/厂商"),
    page: int = Query(1, ge=1, description="页码, 从 1 开始"),
    page_size: int = Query(50, ge=1, le=10000, description="每页条数 (列表分页上限; 全量选项拉取用较大值)"),
    db: Session = Depends(get_db),
):
    # B2: external_devices 为单一事实源, 分页/筛选在聚合层完成, 无数据回退生成器。
    data = agg.list_equipment(
        domain=domain, category=category, room=room, status=status,
        db=db, kw=kw, page=page, page_size=page_size,
    )
    return data


@router.get("/{equipment_id}", response_model=EquipmentOut, summary="设备详情")
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    eq = agg.get_equipment(equipment_id, db=db)
    if eq is None:
        raise HTTPException(status_code=404, detail="equipment not found")
    return eq


@router.get("/{equipment_id}/metrics", response_model=EquipmentMetrics, summary="设备近 N 分钟测点曲线")
def get_equipment_metrics(
    equipment_id: int,
    minutes: int = Query(60, ge=5, le=720),
    step_sec: int = Query(60, ge=10, le=600),
    metrics: Optional[List[str]] = Query(None, description="指定测点名, 默认按类别"),
    db: Session = Depends(get_db),
):
    data = agg.equipment_metrics(equipment_id, minutes=minutes, step_sec=step_sec, metrics=metrics, db=db)
    if data is None:
        raise HTTPException(status_code=404, detail="equipment not found")
    return data
