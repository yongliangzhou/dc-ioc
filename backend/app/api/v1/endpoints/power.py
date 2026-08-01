"""电力域 API: 10KV 中压 / 0.4KV 低压 / 柴发 / 燃油 / 电池。
统一数据流向: 优先从真实采集链路聚合，无数据时回退生成器。
"""
from fastapi import APIRouter

from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("/hv", summary="10KV 中压配电")
def hv():
    return agg.hv()


@router.get("/lv", summary="0.4KV 低压配电")
def lv():
    return agg.lv()


@router.get("/genset", summary="柴发并机系统")
def genset():
    return agg.genset()


@router.get("/fuel", summary="燃油监控")
def fuel():
    return agg.fuel()


@router.get("/battery", summary="电池监控")
def battery():
    return agg.battery()
