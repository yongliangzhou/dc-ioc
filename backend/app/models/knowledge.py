"""知识库/处置预案模型 (2.3)。"""
from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.types import JSON

from app.db.session import Base


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_item"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, index=True, nullable=False)  # KB-0001
    title = Column(String(255), nullable=False)
    category = Column(String(64), index=True)            # 系统/专业, 如 暖通-冷源
    domain = Column(String(64), index=True)              # 业务域, 如 hvac_source (用于告警关联)
    type = Column(String(32), index=True, default="sop")  # sop/drawing/manual/emergency/case/training
    tags = Column(JSON, default=list)
    related_categories = Column(JSON, default=list)       # 关联告警系统 (告警 system 字段)
    related_domains = Column(JSON, default=list)           # 关联业务域 (告警 domain 字段)
    related_metrics = Column(JSON, default=list)          # 关联测点 (告警 metric_name 字段)
    summary = Column(Text)
    content = Column(Text)
    steps = Column(JSON, default=list)                    # 处置步骤 list[str]
    owner = Column(String(64), default="")
    hot = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    # 人工审核状态机: pending(待审核) / approved(已通过) / rejected(已驳回)
    # 导入切分自动生成的内容默认 pending, 审核通过后才正式入库可被检索。
    review_status = Column(String(16), default="approved")
    reviewer = Column(String(64), default="")
    reviewed_at = Column(String(32), default="")
    review_note = Column(Text, default="")
    created_at = Column(String(32), default=_now)
    updated_at = Column(String(32), default=_now, onupdate=_now)
