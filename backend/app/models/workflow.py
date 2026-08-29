"""运维工作流(流程)模型 (D5 后端化: 流程数据由前端 localStorage 迁移至服务端)。

对应前端 WorkflowCenter 的 WorkflowItem:
  - approval / logs / knowledge_links 为嵌套结构, 用 JSON 列存储。
"""
from __future__ import annotations

import datetime

from sqlalchemy import JSON, Column, Integer, String, Text

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class WorkflowItem(Base):
    __tablename__ = "workflow_item"

    id = Column(String(32), primary_key=True)                 # INC-2026-0001
    type = Column(String(16), default="incident")              # incident/problem/change/risk
    title = Column(String(255), default="")
    description = Column(Text, default="")
    priority = Column(String(8), default="P3")                 # P1-P4
    status = Column(String(16), default="new")                 # new/progress/approval/rejected/closed
    owner = Column(String(64), default="")
    applicant = Column(String(64), default="")
    sla_hours = Column(Integer, default=24)
    risk_level = Column(String(16), default=None)              # high/medium/low (risk 类型)
    approval = Column(JSON, default=list)                      # [{approver,status,comment,at}]
    logs = Column(JSON, default=list)                          # [{user,text,at}]
    knowledge_links = Column(JSON, default=list)               # [kb_code]
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
