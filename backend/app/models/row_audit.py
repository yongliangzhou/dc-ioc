"""行级变更审计模型 (数据库设计文档 第八章 8.5 ③: 扩展性-审计与追踪)。

row_audit 表由 app.core.lifespan._ensure_row_audit 自愈创建 (users/roles/tenant 三表
触发器的 audit_row_change() 写入), 此处仅做只读 ORM 映射, 供审计查询接口序列化。
表结构由 self-heal DDL / Alembic 0009 负责, 模型列类型与之保持一致 (TEXT / JSONB /
TIMESTAMPTZ / CHAR(1)), 避免 create_all 重建时类型漂移。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class RowAudit(Base):
    """记录敏感表行级变更 (I/U/D) 的脱敏前后镜像与操作人, 供审计追溯。"""

    __tablename__ = "row_audit"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    table_name = Column(Text, nullable=False)
    row_id = Column(Text, nullable=True)
    action = Column(String(1), nullable=False)  # 'I' / 'U' / 'D'
    old_val = Column(JSONB, nullable=True)
    new_val = Column(JSONB, nullable=True)
    changed_by = Column(Text, nullable=True)
    app_name = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts.isoformat() if self.ts else None,
            "table_name": self.table_name,
            "row_id": self.row_id,
            "action": (self.action or "").strip(),
            "old_val": self.old_val,
            "new_val": self.new_val,
            "changed_by": self.changed_by,
            "app_name": self.app_name,
        }
