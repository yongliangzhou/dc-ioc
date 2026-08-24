"""告警历史 API: GET /api/alarm-history (分页/筛选/统计) + ack / resolve。

对齐前端:
  - getAlarmHistory -> GET /api/alarm-history
  - acknowledgeAlarm -> PATCH /api/alarm-history/{id}/ack
  - resolveAlarm     -> PATCH /api/alarm-history/{id}/resolve
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.crud import alarm as alarm_crud
from app.models.user import User
from app.schemas.alarm import AlarmActionRequest, AlarmEventOut, AlarmHistoryResponse

router = APIRouter(prefix="/alarm-history", tags=["alarm-history"])


@router.get("", response_model=AlarmHistoryResponse)
def list_history(
    sys: str | None = Query(None, description="系统过滤"),
    lv: str | None = Query(None, description="级别 crit/warn/info"),
    state: str | None = Query(None, description="状态 active/acknowledged/resolved/suppressed"),
    from_: str | None = Query(None, alias="from", description="触发时间下界 ISO"),
    to: str | None = Query(None, description="触发时间上界 ISO"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = alarm_crud.list_alarms(
        db, sys=sys, lv=lv, state=state, from_=from_, to=to, page=page, limit=limit
    )
    stats = alarm_crud.alarm_stats(db)
    return AlarmHistoryResponse(
        items=[AlarmEventOut.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
        stats=stats,
    )


@router.patch("/{alarm_id}/ack", response_model=AlarmEventOut)
def ack_alarm(
    alarm_id: str,
    req: AlarmActionRequest,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    a = alarm_crud.ack_alarm(db, alarm_id, req.by, req.note)
    if a is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    return a


@router.patch("/{alarm_id}/resolve", response_model=AlarmEventOut)
def resolve_alarm(
    alarm_id: str,
    req: AlarmActionRequest,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    a = alarm_crud.resolve_alarm(db, alarm_id, req.by, req.note)
    if a is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    return a
