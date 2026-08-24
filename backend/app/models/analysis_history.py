"""影响分析报告历史 (故障影响分析深化: 存档 + 会签)。"""
from __future__ import annotations

import datetime
import json

from sqlalchemy import Column, Integer, String, Text, Boolean, JSON

from app.db.session import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), default="")
    fault_ids = Column(JSON, default=list)          # 故障源 id 列表
    severity = Column(String(32), default="low")     # low/high/critical
    summary = Column(JSON, default=dict)             # 评估摘要
    businesses = Column(JSON, default=list)          # 受影响业务域
    mitigations = Column(JSON, default=list)         # 缓解措施清单
    signers = Column(JSON, default=list)             # 会签人列表
    pushed = Column(Boolean, default=False)          # 是否已按严重级别推送
    created_by = Column(String(64), default="")
    created_at = Column(String(32), default=lambda: datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "faultIds": self.fault_ids if isinstance(self.fault_ids, list) else json.loads(self.fault_ids or "[]"),
            "severity": self.severity,
            "summary": self.summary if isinstance(self.summary, dict) else json.loads(self.summary or "{}"),
            "businesses": self.businesses if isinstance(self.businesses, list) else json.loads(self.businesses or "[]"),
            "mitigations": self.mitigations if isinstance(self.mitigations, list) else json.loads(self.mitigations or "[]"),
            "signers": self.signers if isinstance(self.signers, list) else json.loads(self.signers or "[]"),
            "pushed": bool(self.pushed),
            "createdBy": self.created_by,
            "createdAt": self.created_at,
        }
