"""暖通域 API: 冷源系统 / 空调末端 / 液冷系统。
统一数据流向: 优先从真实采集链路聚合，无数据时回退生成器。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_db, require_role
from app.models.control_log import ControlLog
from app.models.user import User
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


class ChillerControlRequest(BaseModel):
    chiller_id: str                       # 对齐 ChillerGroupView.chiller.id
    action: str                           # start / stop / mode / temp
    value: Optional[float] = None         # temp 动作的下发设定值 (℃)


_ALLOWED_ACTIONS = {"start", "stop", "mode", "temp"}


@router.post(
    "/chiller-control",
    summary="下发冷机机组控制指令 (启停 / 模式 / 设定温度)",
    dependencies=[Depends(require_role("admin", "operator"))],
)
def chiller_control(
    payload: ChillerControlRequest,
    db=Depends(get_db),
    user: User = Depends(require_role("admin", "operator")),
):
    """D6 后端化: 快控按钮由前端占位 toast 改为服务端下发 + 留痕。
    当前真实执行器尚未接入，故以记录控制指令 (ControlLog) 的方式落地，并返回受理回执。
    """
    if payload.action not in _ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"不支持的控制动作: {payload.action}")

    plant = agg.chiller_plant()
    ids = {
        str(g.get("chiller", {}).get("id", ""))
        for g in (plant.get("chillerGroups") or [])
    }
    if payload.chiller_id not in ids:
        raise HTTPException(status_code=404, detail=f"机组 {payload.chiller_id} 不存在")

    if payload.action == "temp":
        if payload.value is None or not (5 <= payload.value <= 15):
            raise HTTPException(status_code=400, detail="设定温度需在 5~ 15℃ 之间")
    if payload.action == "mode":
        # 模式以 value 整数编码记录: 1=制冷模式 2=预冷模式 3=自然冷却
        if payload.value is None or int(payload.value) not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="运行模式编码无效 (1~3)")

    accepted_at = datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log = ControlLog(
        chiller_id=payload.chiller_id,
        action=payload.action,
        value=payload.value,
        operator=user.username,
        result="accepted",
        created_at=accepted_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "status": "accepted",
        "chiller_id": payload.chiller_id,
        "action": payload.action,
        "value": payload.value,
        "operator": user.username,
        "accepted_at": accepted_at,
        "log_id": log.id,
    }
