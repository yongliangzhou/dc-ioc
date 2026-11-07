"""CMDB 配置项关系 (阶段二 · ADR-0005)。

对标 NetBox / iTop / 蓝鲸 bk-CMDB: 让「设备台账」升级为「可表达连接与依赖的关系图谱」。

设计取舍:
- CI 标识用字符串 (`equipment:123` / `cabinet:A01` / `external:dev-9`), 不建跨表外键,
  以兼容现有设备台账 / 机柜 / 外部设备三套 ID 体系, 避免一次性重构。
- `tenant_id` 预留可空列, 阶段四由 ORM 全局过滤接管 (在此之前不做隔离)。
- 通用列类型 (Integer/String/Text/DateTime), 便于 SQLite 单测直接建表。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint, func

from app.db.session import Base


class CiRelation(Base):
    """一条有向 CI 关系: source_ci --[relation_type]--> target_ci。"""

    __tablename__ = "ci_relation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_ci = Column(String(128), nullable=False, index=True, comment="源 CI 标识")
    target_ci = Column(String(128), nullable=False, index=True, comment="目标 CI 标识")
    source_name = Column(String(128), default="", comment="源 CI 展示名 (冗余, 便于前端)")
    target_name = Column(String(128), default="", comment="目标 CI 展示名")
    relation_type = Column(String(32), nullable=False, default="connects_to",
                           comment="connects_to/powers/cools/depends_on/hosts")
    description = Column(Text, default="")
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    tenant_id = Column(Integer, nullable=True, index=True, comment="预留: 阶段四行级隔离")

    __table_args__ = (
        UniqueConstraint("source_ci", "target_ci", "relation_type", name="uq_ci_relation_edge"),
        Index("ix_ci_relation_pair", "source_ci", "target_ci"),
        Index("ix_ci_relation_tenant", "tenant_id", "created_at"),
    )

    def to_dict(self) -> dict:
        """白名单序列化 (禁止 SELECT * 直出, 避免列扩展破坏前端契约)。"""
        created = self.created_at
        if isinstance(created, datetime):
            created_s = created.isoformat()
        else:
            created_s = str(created) if created is not None else None
        return {
            "id": self.id,
            "source_ci": self.source_ci,
            "target_ci": self.target_ci,
            "source_name": self.source_name or "",
            "target_name": self.target_name or "",
            "relation_type": self.relation_type,
            "description": self.description or "",
            "created_by": self.created_by or "system",
            "created_at": created_s,
            "tenant_id": self.tenant_id,
        }
