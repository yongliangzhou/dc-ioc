"""驾驶舱总览 API (统一数据流向, 叠加 Redis 30s 响应缓存)。"""
from fastapi import APIRouter, Request

from app.core.cache import cache_json
from app.schemas.dashboard import (
    CampusesResponse,
    CampusComparisonResponse,
    DashboardOverview,
)
from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview, summary="驾驶舱总览")
@cache_json(ttl=30, key_prefix="dashboard:overview")
def get_overview(request: Request):
    return agg.dashboard_overview()


@router.get("/campuses", response_model=CampusesResponse, summary="多园区概览列表")
@cache_json(ttl=30, key_prefix="dashboard:campuses")
def get_campuses(request: Request):
    return agg.multi_campus_overview()


@router.get("/campus-comparison", response_model=CampusComparisonResponse, summary="跨园区 KPI 对比")
@cache_json(ttl=30, key_prefix="dashboard:campus-comparison")
def get_campus_comparison(request: Request):
    return agg.campus_comparison()
