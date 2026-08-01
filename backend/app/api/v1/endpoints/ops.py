"""智能运营 + 运维作业域 API: 孪生/容量/告警/电量/工单/巡检/维保/演练/排班/风险/知识。
统一数据流向: 运营数据当前使用生成器，后续接入真实运营系统后替换。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import dc_aggregator as agg
from app.services import capacity_forecast, energy_advice, equipment_health

router = APIRouter()


class TwinSimulateRequest(BaseModel):
    """推演仿真请求: 指定场景做故障注入; 可显式指定受影响设备, 否则按场景默认 domain 注入。"""
    scenario: str = "全停演练"  # 市电失电 | 冷源故障 | 全停演练
    affectedIds: list[int] | None = None
    params: dict | None = None


@router.get("/twin", summary="数字孪生 (Raptor)")
def twin():
    return agg.twin()


@router.get("/twin/graph", summary="数字孪生层级图(园区-包间-设备, 数据驱动)")
def twin_graph():
    return agg.twin_graph()


@router.post("/twin/simulate", summary="数字孪生推演仿真(故障注入/what-if)")
def twin_simulate(req: TwinSimulateRequest):
    return agg.twin_simulate(req.dict())


@router.get("/twin/scenarios", summary="推演场景库(数据驱动, 含波及预览)")
def twin_scenarios():
    return agg.twin_scenarios()


@router.get("/twin/ark", summary="方舟闭环(真实功率/PUE 测算节能收益)")
def twin_ark():
    return agg.twin_ark()


@router.get("/topology/graph", summary="链路拓扑图(供电/制冷节点与边)")
def topology_graph():
    return agg.topology_graph()


# ---- build-graph-apis: /twin/topology 数据底座组 (图数据 + 推演接口) ----
@router.get("/twin/topology", summary="孪生拓扑数据底座(合并孪生层级图+链路拓扑图+汇总)")
def twin_topology():
    return agg.twin_topology()


@router.get("/twin/topology/metrics", summary="链路节点实时测点映射(真实测点驱动能流速度/温度)")
def twin_topology_metrics():
    return agg.topology_metrics()


@router.get("/twin/topology/scenarios", summary="推演场景库(数据驱动, 含波及预览)")
def twin_topology_scenarios():
    return agg.twin_scenarios()


@router.get("/twin/topology/ark", summary="方舟闭环(真实功率/PUE 测算节能收益)")
def twin_topology_ark():
    return agg.twin_ark()


@router.post("/twin/topology/simulate", summary="数字孪生推演仿真(故障注入/what-if)")
def twin_topology_simulate(req: TwinSimulateRequest):
    return agg.twin_simulate(req.dict())


@router.get("/capacity", summary="容量管理 + 容量预测 (阶段三 B)")
def capacity(db: Session = Depends(get_db)):
    base = agg.capacity()
    fd = capacity_forecast.forecast_capacity(base)
    base["forecastDetail"] = fd
    base["forecast"] = fd["headline"]  # 用真实预测结论替换原写死文案
    return base


@router.get("/alarms", summary="告警中心 (收敛/趋势/活跃/ SLA)")
def alarms():
    return agg.alarms()


@router.get("/energy", summary="电量预测与节能 + 能效优化建议 (阶段三 C)")
def energy(db: Session = Depends(get_db)):
    base = agg.energy()
    advice = energy_advice.build_energy_advice(db)
    base["advice"] = advice
    base["breakdown"] = advice["breakdown"]  # 用真实/兜底计算覆盖演示值
    return base


@router.get("/equipment-health", summary="设备健康评分 (阶段三 D/E)")
def equipment_health_():
    return equipment_health.build_equipment_health()


@router.get("/maintain", summary="维保管理")
def maintain(db: Session = Depends(get_db)):
    return agg.maintain_plan(db)

