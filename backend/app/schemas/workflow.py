"""运维工作流 Pydantic Schema (D5)。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkflowNodeIn(BaseModel):
    approver: str
    status: str = "pending"
    comment: Optional[str] = None
    at: Optional[str] = None


class WorkflowCreate(BaseModel):
    type: str
    title: str
    description: str = ""
    priority: str = "P3"
    owner: str = ""
    applicant: Optional[str] = None
    sla_hours: Optional[int] = None
    risk_level: Optional[str] = None
    approval: Optional[list] = None


class WorkflowUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    applicant: Optional[str] = None
    sla_hours: Optional[int] = None
    risk_level: Optional[str] = None
    approval: Optional[list] = None
    knowledge_links: Optional[list] = None


class WorkflowApprove(BaseModel):
    node_index: int
    result: str                       # approved / rejected
    comment: Optional[str] = None
    operator: Optional[str] = None


class WorkflowLogIn(BaseModel):
    text: str
    operator: Optional[str] = None


class WorkflowLinkIn(BaseModel):
    kb_id: str
    operator: Optional[str] = None
