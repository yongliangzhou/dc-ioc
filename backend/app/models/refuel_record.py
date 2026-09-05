"""加油/补油记录 (储油系统示意图 · 加油记录模块)。

原来 PowerFuel.vue 的加油记录是前端 computed 里循环 12 次确定性生成的假数据,
无法新增/修改/删除。这里落库成真实记录, 供前端统一编辑入口 CRUD。
字段与前端 RefuelRecord 接口保持一致 (no/date/tank/amount/before/after/
vendor/grade/qc/operator/status), 避免前后端二次映射。
"""
from sqlalchemy import BigInteger, Column, DateTime, Float, String, Text, func

from app.db.session import Base


class RefuelRecord(Base):
    """柴发储油系统的加油(补油)记录。"""

    __tablename__ = "refuel_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    no = Column(String(64), nullable=False, unique=True, index=True)
    date = Column(String(32), nullable=False)
    tank = Column(String(64), nullable=False, default="")
    amount = Column(Float, nullable=False, default=0)
    before_pct = Column(Float, nullable=True)
    after_pct = Column(Float, nullable=True)
    vendor = Column(String(128), nullable=True)
    grade = Column(String(64), nullable=True)
    qc = Column(String(32), nullable=True)
    operator = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="已完成")
    note = Column(Text, nullable=True)
    created_by = Column(String(64), nullable=True, default="system")
    updated_by = Column(String(64), nullable=True, default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "no": self.no,
            "date": self.date,
            "tank": self.tank or "",
            "amount": self.amount or 0,
            "before": self.before_pct,
            "after": self.after_pct,
            "vendor": self.vendor or "",
            "grade": self.grade or "",
            "qc": self.qc or "",
            "operator": self.operator or "",
            "status": self.status or "",
            "note": self.note or "",
            "createdBy": self.created_by or "system",
            "updatedBy": self.updated_by or "system",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
