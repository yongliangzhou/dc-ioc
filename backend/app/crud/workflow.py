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


def stats(db: Session) -> dict:
    """流程统计聚合：KPI + 分布 + 近 12 周趋势。

    口径与前端 WorkflowCenter 保持一致，但判定下推到服务端（UTC），
    避免前端本地时钟/时区差异导致 SLA 超时率与平均时长统计漂移：
      - SLA 超时: 未关闭/未驳回 且 (now - created_at) > sla_hours
      - 平均解决时长: 已关闭流程 (updated_at - created_at) 均值(小时)
      - 趋势: 近 12 个自然周（周一起算, UTC），统计每周创建数 / 关闭数
    """
    rows = db.query(WorkflowItem).all()
    now = datetime.datetime.now(datetime.timezone.utc)
    total = len(rows)

    def _parse(val: Optional[str]) -> Optional[datetime.datetime]:
        if not val:
            return None
        try:
            d = datetime.datetime.strptime(str(val)[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        return d.replace(tzinfo=datetime.timezone.utc)

    by_type: dict = {}
    by_status: dict = {}
    by_priority: dict = {}
    open_cnt = 0
    breached = 0
    month_created = 0
    month_closed = 0
    durations: list = []

    for w in rows:
        wtype = w.type or "unknown"
        wstatus = w.status or "unknown"
        wpri = w.priority or "P3"
        by_type[wtype] = by_type.get(wtype, 0) + 1
        by_status[wstatus] = by_status.get(wstatus, 0) + 1
        by_priority[wpri] = by_priority.get(wpri, 0) + 1

        created = _parse(w.created_at)
        updated = _parse(w.updated_at)
        sla = w.sla_hours or 24

        if wstatus not in ("closed", "rejected"):
            open_cnt += 1
            if created and (now - created).total_seconds() / 3600.0 > sla:
                breached += 1
        if created and created.year == now.year and created.month == now.month:
            month_created += 1
        if wstatus == "closed":
            if updated and updated.year == now.year and updated.month == now.month:
                month_closed += 1
            if created and updated:
                durations.append((updated - created).total_seconds() / 3600.0)

    avg_resolve = round(sum(durations) / len(durations), 1) if durations else 0.0
    breach_rate = round(breached / total * 100, 1) if total else 0.0

    # ---- 近 12 周趋势 ----
    weeks = 12
    this_monday = (now - datetime.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    starts = [this_monday - datetime.timedelta(weeks=weeks - 1 - i) for i in range(weeks)]
    created_series = [0] * weeks
    closed_series = [0] * weeks
    for w in rows:
        created = _parse(w.created_at)
        updated = _parse(w.updated_at)
        for i in range(weeks):
            lo, hi = starts[i], starts[i] + datetime.timedelta(days=7)
            if created and lo <= created < hi:
                created_series[i] += 1
            if (w.status or "") == "closed" and updated and lo <= updated < hi:
                closed_series[i] += 1

    trend = [
        {"week": s.strftime("%m-%d"), "created": created_series[i], "closed": closed_series[i]}
        for i, s in enumerate(starts)
    ]

    return {
        "total": total,
        "open": open_cnt,
        "monthCreated": month_created,
        "monthClosed": month_closed,
        "avgResolve": avg_resolve,
        "breachRate": breach_rate,
        "byType": by_type,
        "byStatus": by_status,
        "byPriority": by_priority,
        "trend": trend,
    }


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
