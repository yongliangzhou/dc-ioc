"""暖通域 API: 冷源系统 / 空调末端 / 液冷系统。
统一数据流向: 优先从真实采集链路聚合，无数据时回退生成器。
"""
from fastapi import APIRouter

from app.services import dc_aggregator as agg

router = APIRouter()


@router.get("/chiller-plant", summary="冷源系统 (冷水机组/冷却塔/水泵/板换/蓄冷罐)")
def chiller_plant():
    return agg.chiller_plant()


@router.get("/chiller-trends", summary="冷源趋势数据 (7类趋势图+1类柱状图)")
def chiller_trends():
    return agg.chiller_trends()


@router.get("/crac", summary="空调末端 (精密空调/新风/恒湿/包间环境)")
def crac():
    return agg.crac()


@router.get("/crac-trends", summary="空调末端趋势诊断 (7类趋势图)")
def crac_trends():
    return agg.crac_trends()


@router.get("/liquid-cooling", summary="液冷系统 (CDU/冷板/管路/漏液检测/热回收)")
def liquid_cooling():
    return agg.liquid_cooling()
