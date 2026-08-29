"""运维工作流 API (D5 后端化: 流程数据服务端化, 审批权限改为基于角色)。

  - getWorkflows       -> GET    /api/ops/workflows
  - createWorkflow     -> POST   /api/ops/workflows
  - getWorkflow        -> GET    /api/ops/workflows/{id}
  - updateWorkflow     -> PUT    /api/ops/workflows/{id}
  - deleteWorkflow     -> DELETE /api/ops/workflows/{id}
  - advanceWorkflow    -> POST   /api/ops/workflows/{id}/advance
  - closeWorkflow      -> POST   /api/ops/workflows/{id}/close
  - reopenWorkflow     -> POST   /api/ops/workflows/{id}/reopen
  - approveNode        -> POST   /api/ops/workflows/{id}/approve
  - addWorkflowLog     -> POST   /api/ops/workflows/{id}/logs
  - linkKnowledge      -> POST   /api/ops/workflows/{id}/link
  - unlinkKnowledge    -> DELETE /api/ops/workflows/{id}/link/{kbId}
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import workflow as crud
from app.models.user import User
from app.schemas.workflow import (
    WorkflowApprove,
    WorkflowCreate,
    WorkflowLinkIn,
    WorkflowLogIn,
    WorkflowUpdate,
)

logger = logging.getLogger("ops.workflow")

router = APIRouter(prefix="/ops/workflows", tags=["workflows"])


def _can_approve(user: User, approver: str) -> bool:
    """审批权限: 超管放行; 否则要求当前用户拥有与节点审批角色同名的角色。"""
    if user.is_superuser:
        return True
    names = {r.name for r in (user.roles or [])}
    return approver in names


@router.get("", response_model=dict)
def list_workflows(
    wtype: str = "",
    status: str = "",
    kw: str = "",
    db: Session = Depends(get_db),
):
    items = crud.list_items(db, wtype=wtype, status=status, kw=kw)
    return {"items": items}


@router.post(
    "",
    response_model=dict,
    status_code=201,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    return crud.create(db, payload.model_dump(exclude_none=True), operator=_u.username)


@router.get("/{wid}", response_model=dict)
def get_workflow(wid: str, db: Session = Depends(get_db)):
    obj = crud.get_dict(db, wid)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.put(
    "/{wid}",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def update_workflow(wid: str, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    obj = crud.update(db, wid, payload.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.delete(
    "/{wid}",
    status_code=204,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def delete_workflow(wid: str, db: Session = Depends(get_db)):
    if not crud.delete(db, wid):
        raise HTTPException(status_code=404, detail="流程不存在")


@router.post(
    "/{wid}/advance",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def advance_workflow(
    wid: str,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    obj = crud.advance(db, wid, operator=_u.username)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.post(
    "/{wid}/close",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def close_wf(
    wid: str,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    obj = crud.close_workflow(db, wid, operator=_u.username)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.post(
    "/{wid}/reopen",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def reopen_wf(
    wid: str,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    obj = crud.reopen(db, wid, operator=_u.username)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.post("/{wid}/approve", response_model=dict)
def approve_workflow(
    wid: str,
    payload: WorkflowApprove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = crud.get(db, wid)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    if payload.node_index < 0 or payload.node_index >= len(obj.approval or []):
        raise HTTPException(status_code=400, detail="审批节点序号越界")
    node = (obj.approval or [])[payload.node_index]
    if not _can_approve(user, node.get("approver", "")):
        raise HTTPException(status_code=403, detail="当前用户无该节点审批权限")
    if payload.result not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="result 仅支持 approved / rejected")
    try:
        return crud.approve_node(
            db, wid, payload.node_index, payload.result, payload.comment, operator=user.username
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/{wid}/logs",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def add_log(
    wid: str,
    payload: WorkflowLogIn,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=422, detail="日志内容不能为空")
    obj = crud.add_log(db, wid, payload.text, operator=_u.username)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.post(
    "/{wid}/link",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def link_kb(
    wid: str,
    payload: WorkflowLinkIn,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    obj = crud.link_kb(db, wid, payload.kb_id)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj


@router.delete(
    "/{wid}/link/{kb_id}",
    response_model=dict,
    dependencies=[Depends(require_role("admin", "operator"))],
)
def unlink_kb(
    wid: str,
    kb_id: str,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    obj = crud.unlink_kb(db, wid, kb_id)
    if not obj:
        raise HTTPException(status_code=404, detail="流程不存在")
    return obj
