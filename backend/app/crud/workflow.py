"""运维工作流 CRUD + 状态流转 (D5 后端化)。

状态机 (对齐前端 WorkflowCenter):
  - new      -> 有审批节点则 approval, 否则 progress
  - progress -> closed
  - approval -> 全部 approved 则 progress; 任一 rejected 则 rejected
  - closed   -> reopen 回到 progress
"""
from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.workflow import WorkflowItem


_TYPE_PREFIX = {"incident": "INC", "problem": "PRB", "change": "CHG", "risk": "RSK"}
_DEFAULT_APPROVAL = {
    "incident": [{"approver": "一线主管", "status": "pending"}],
    "problem": [{"approver": "技术专家", "status": "pending"}],
    "change": [{"approver": "变更委员会", "status": "pending"}, {"approver": "运维经理", "status": "pending"}],
    "risk": [{"approver": "安全负责人", "status": "pending"}],
}
_SLA_BY_PRIORITY = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _to_dict(w: WorkflowItem) -> dict:
    return {
        "id": w.id,
        "type": w.type,
        "title": w.title,
        "description": w.description,
        "priority": w.priority,
        "status": w.status,
        "owner": w.owner,
        "applicant": w.applicant,
        "createdAt": w.created_at,
        "updatedAt": w.updated_at,
        "slaHours": w.sla_hours,
        "riskLevel": w.risk_level,
        "approval": w.approval or [],
        "logs": w.logs or [],
        "knowledgeLinks": w.knowledge_links or [],
    }


def _gen_id(db: Session, wtype: str) -> str:
    prefix = _TYPE_PREFIX.get(wtype, "WF")
    cnt = db.query(WorkflowItem).filter(WorkflowItem.id.like(f"{prefix}-%")).count() + 1
    return f"{prefix}-2026-{cnt:04d}"


def _approval_for(wtype: str) -> list:
    now = _now()
    out = []
    for n in _DEFAULT_APPROVAL.get(wtype, _DEFAULT_APPROVAL["incident"]):
        item = dict(n)
        item["at"] = now if n.get("status") != "pending" else None
        out.append(item)
    return out


def list_items(db: Session, *, wtype: str = "", status: str = "", kw: str = "") -> list[dict]:
    q = db.query(WorkflowItem)
    if wtype:
        q = q.filter(WorkflowItem.type == wtype)
    if status:
        q = q.filter(WorkflowItem.status == status)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            WorkflowItem.title.ilike(like)
            | WorkflowItem.owner.ilike(like)
            | WorkflowItem.id.ilike(like)
        )
    rows = q.order_by(WorkflowItem.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, wid: str) -> Optional[WorkflowItem]:
    return db.query(WorkflowItem).filter(WorkflowItem.id == wid).first()


def get_dict(db: Session, wid: str) -> Optional[dict]:
    obj = get(db, wid)
    return _to_dict(obj) if obj else None


def create(db: Session, data: dict, operator: str) -> dict:
    wtype = data.get("type", "incident")
    now = _now()
    approval = data.get("approval") or _approval_for(wtype)
    sla = data.get("sla_hours") or _SLA_BY_PRIORITY.get(data.get("priority", "P3"), 24)
    item = WorkflowItem(
        id=_gen_id(db, wtype),
        type=wtype,
        title=data.get("title", ""),
        description=data.get("description", ""),
        priority=data.get("priority", "P3"),
        status="new",
        owner=data.get("owner", "") or operator,
        applicant=data.get("applicant") or operator,
        sla_hours=sla,
        risk_level=data.get("risk_level"),
        approval=approval,
        logs=[{"user": operator, "text": "创建", "at": now}],
        knowledge_links=[],
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)


def update(db: Session, wid: str, data: dict) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    for k, v in data.items():
        if v is None:
            continue
        if k == "knowledgeLinks":
            k = "knowledge_links"
        if hasattr(obj, k):
            setattr(obj, k, v)
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def delete(db: Session, wid: str) -> bool:
    obj = get(db, wid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def _append_log(obj: WorkflowItem, operator: str, text: str) -> None:
    logs = list(obj.logs or [])
    logs.append({"user": operator, "text": text, "at": _now()})
    obj.logs = logs


def advance(db: Session, wid: str, operator: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    if obj.status == "new":
        obj.status = "approval" if obj.approval else "progress"
    elif obj.status == "progress":
        obj.status = "closed"
    else:
        return _to_dict(obj)
    obj.updated_at = _now()
    _append_log(obj, operator, f"推进至 {obj.status}")
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def close_workflow(db: Session, wid: str, operator: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    obj.status = "closed"
    obj.updated_at = _now()
    _append_log(obj, operator, "关闭")
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def reopen(db: Session, wid: str, operator: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    obj.status = "progress"
    obj.updated_at = _now()
    _append_log(obj, operator, "重新打开")
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def approve_node(
    db: Session,
    wid: str,
    node_index: int,
    result: str,
    comment: Optional[str],
    operator: str,
) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    approval = list(obj.approval or [])
    if node_index < 0 or node_index >= len(approval):
        raise ValueError("审批节点序号越界")
    node = dict(approval[node_index])
    if node.get("status") != "pending":
        raise ValueError("该审批节点已处理, 不可重复审批")
    node["status"] = result
    node["comment"] = comment
    node["at"] = _now()
    approval[node_index] = node
    obj.approval = approval
    obj.updated_at = _now()
    _append_log(obj, operator, f"审批节点 {node_index + 1}: {result}")
    if result == "rejected":
        obj.status = "rejected"
    elif all(n.get("status") == "approved" for n in approval):
        obj.status = "progress"
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def add_log(db: Session, wid: str, text: str, operator: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    obj.updated_at = _now()
    _append_log(obj, operator, text)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def link_kb(db: Session, wid: str, kb_id: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    links = list(obj.knowledge_links or [])
    if kb_id not in links:
        links.append(kb_id)
    obj.knowledge_links = links
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def unlink_kb(db: Session, wid: str, kb_id: str) -> Optional[dict]:
    obj = get(db, wid)
    if not obj:
        return None
    obj.knowledge_links = [x for x in (obj.knowledge_links or []) if x != kb_id]
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)
