"""操作审计日志模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class AuditLog(Base):
    """记录所有写操作 (CRUD: POST/PUT/PATCH/DELETE) 与关键读操作, 供审计追溯。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, comment="操作时间(UTC)")
    method = Column(String(8), nullable=False, comment="HTTP 方法")
    path = Column(String(255), nullable=False, comment="请求路径")
    query = Column(Text, nullable=True, comment="查询字符串")
    status_code = Column(Integer, nullable=False, comment="响应状态码")
    username = Column(String(64), nullable=True, comment="操作人 (token sub, 匿名为空)")
    ip = Column(String(64), nullable=True, comment="客户端 IP")
    user_agent = Column(Text, nullable=True, comment="User-Agent")
    resource = Column(String(64), nullable=True, comment="资源类型 (从路径推断)")
    action = Column(String(32), nullable=True, comment="动作 (create/update/delete/read/login)")
    detail = Column(Text, nullable=True, comment="请求体摘要 (已脱敏, 截断)")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts.isoformat() + "Z" if self.ts else None,
            "method": self.method,
            "path": self.path,
            "query": self.query,
            "status_code": self.status_code,
            "username": self.username,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "detail": self.detail,
        }
