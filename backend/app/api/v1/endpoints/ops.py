"""(Smart operations + O&M domain API: twin/capacity/alarms/energy/ticket/inspection/maintain/drill/shift/risk/knowledge.
Data flow: ops data currently uses generators; replace with real ops system later.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import dc_aggregator as agg
from app.services import capacity_forecast, energy_advice, equipment_health
from app.crud import maintenance as mrec
from app.schemas import maintenance as maintenance_schema
from app.core.deps import require_role

router = APIRouter()


class TwinSimulateRequest(BaseModel):
    """Twin simulation request: scenario fault injection; affected devices optional."""
    scenario: str = "全停演练"  # 市电失电 | 冷源故障 | 全停演练
    affectedIds: list[int] | None = None
    params: dict | None = None


@router.get("/twin", summary="Digital twin (Raptor)")
def twin():
    return agg.twin()


@router.get("/twin/graph", summary="Digital twin hierarchy graph")
def twin_graph():
    return agg.twin_graph()


@router.post("/twin/simulate", summary="Digital twin simulation (fault injection / what-if)")
def twin_simulate(req: TwinSimulateRequest):
    return agg.twin_simulate(req.dict())


@router.get("/twin/scenarios", summary="Simulation scenario library")
def twin_scenarios():
    return agg.twin_scenarios()


@router.get("/twin/ark", summary="Ark closed loop (real power / PUE saving)")
def twin_ark():
    return agg.twin_ark()


@router.get("/topology/graph", summary="Topology graph (power/cooling nodes and edges)")
def topology_graph():
    return agg.topology_graph()


# ---- build-graph-apis: /twin/topology data base group ----
@router.get("/twin/topology", summary="Twin topology data base")
def twin_topology():
    return agg.twin_topology()


@router.get("/twin/topology/metrics", summary="Topology node real-time metrics")
def twin_topology_metrics():
    return agg.topology_metrics()


@router.get("/twin/topology/scenarios", summary="Simulation scenario library")
def twin_topology_scenarios():
    return agg.twin_scenarios()


@router.get("/twin/topology/ark", summary="Ark closed loop")
def twin_topology_ark():
    return agg.twin_ark()


@router.post("/twin/topology/simulate", summary="Digital twin simulation (fault injection / what-if)")
def twin_topology_simulate(req: TwinSimulateRequest):
    return agg.twin_simulate(req.dict())


@router.get("/capacity", summary="Capacity management + forecast")
def capacity(db: Session = Depends(get_db)):
    base = agg.capacity()
    fd = capacity_forecast.forecast_capacity(base)
    base["forecastDetail"] = fd
    base["forecast"] = fd["headline"]
    return base


@router.get("/alarms", summary="Alarm center")
def alarms():
    return agg.alarms()


@router.get("/energy", summary="Energy forecast + saving advice")
def energy(db: Session = Depends(get_db)):
    base = agg.energy()
    advice = energy_advice.build_energy_advice(db)
    base["advice"] = advice
    base["breakdown"] = advice["breakdown"]
    return base


@router.get("/equipment-health", summary="Equipment health score")
def equipment_health_():
    return equipment_health.build_equipment_health()


@router.get("/maintain", summary="Maintenance management")
def maintain(db: Session = Depends(get_db)):
    return agg.maintain_plan(db)


@router.get("/maintain/records", summary="Maintenance records (real data)")
def list_maintenance_records(db: Session = Depends(get_db),
                             planCode: str = Query("", alias="planCode")):
    records = mrec.list_records(db, plan_code=planCode)
    return {"records": records, "total": mrec.count(db, plan_code=planCode)}


@router.post("/maintain/records", summary="Create maintenance record",
             dependencies=[Depends(require_role("admin", "operator"))])
def create_maintenance_record(payload: maintenance_schema.MaintenanceRecordCreate,
                               db: Session = Depends(get_db)):
    return mrec.create(db, payload.model_dump(exclude_none=True))


@router.get("/maintain/records/{rid}", summary="Maintenance record detail")
def get_maintenance_record(rid: int, db: Session = Depends(get_db)):
    obj = mrec.get(db, rid)
    if not obj:
        raise HTTPException(status_code=404, detail="维保记录不存在")
    return obj


@router.put("/maintain/records/{rid}", summary="Update maintenance record",
            dependencies=[Depends(require_role("admin", "operator"))])
def update_maintenance_record(rid: int, payload: maintenance_schema.MaintenanceRecordUpdate,
                              db: Session = Depends(get_db)):
    obj = mrec.update(db, rid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="维保记录不存在")
    return obj


@router.delete("/maintain/records/{rid}", summary="Delete maintenance record", status_code=204,
               dependencies=[Depends(require_role("admin", "operator"))])
def delete_maintenance_record(rid: int, db: Session = Depends(get_db)):
    if not mrec.delete(db, rid):
        raise HTTPException(status_code=404, detail="维保记录不存在")
