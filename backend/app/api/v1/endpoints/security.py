"""安防消防域 API: 视频监控 / 门禁 / 防入侵 / 消防。
统一数据流向: 优先从真实采集链路聚合，无数据时回退生成器。
"""
from fastapi import APIRouter

from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("/cctv", summary="视频监控")
def cctv():
    return agg.cctv()


@router.get("/acs", summary="门禁管理")
def acs():
    return agg.acs()


@router.get("/ids", summary="防入侵系统")
def ids():
    return agg.ids()


@router.get("/fire", summary="消防报警")
def fire():
    return agg.fire()
