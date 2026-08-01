"""网络监控域 API (交换机端口流量 / Ping 延迟 / 带宽利用率 TopN)。"""
from fastapi import APIRouter, Request

from app.schemas.network import (
    BwUtilOverviewOut,
    NetworkOverviewOut,
    PingOverviewOut,
)
from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("/overview", response_model=NetworkOverviewOut, summary="网络全貌: 交换机 & 端口")
def network_overview(request: Request):
    return agg.network_overview()


@router.get("/ping", response_model=PingOverviewOut, summary="ICMP Ping 连通性/延迟")
def network_ping(request: Request):
    return agg.network_ping()


@router.get("/bandwidth", response_model=BwUtilOverviewOut, summary="带宽利用率 TopN")
def network_bandwidth(request: Request):
    return agg.network_bandwidth()
