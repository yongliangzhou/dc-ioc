"""运营 SLA / 统计指标接口 (2.4)。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import CamelModel
from app.services import metrics_service

router = APIRouter()


class TicketSlaOut(CamelModel):
    total: int
    open: int
    doing: int
    pending: int
    done: int
    avgResponseMin: float | None = None
    avgResolveMin: float | None = None
    slaTargetMin: int | None = None
    breach: int = 0
    onTimeRate: float | None = None


class AlarmSlaOut(CamelModel):
    total: int
    active: int
    acked: int
    resolved: int
    convergenceRate: float | None = None
    mttaMin: float | None = None
    mttrMin: float | None = None


class SlaMetricsOut(CamelModel):
    tickets: TicketSlaOut
    alarms: AlarmSlaOut
    generatedAt: str


@router.get("/sla", response_model=SlaMetricsOut, summary="运营 SLA 与统计指标")
def sla_metrics(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """工单响应/解决时长、SLA 按时率; 告警收敛率、MTTA/MTTR。"""
    return metrics_service.get_sla_metrics(db)
