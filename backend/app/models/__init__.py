"""(模型注册 (供 Alembic autogenerate / Base.metadata.create_all 收集 metadata)。

核心数据模型按参考文件重构:
- 阿里云数据中心弱电课程: Equipment 统一设备台账(domain/category 业务单元分类)
- deploy/sql/004_schema_design.md: IDC / Room / Equipment / Cabinet / Server / PointData / Alarm
"""
from app.db.session import Base  # noqa: F401
from app.models.alarm import AlarmEvent  # noqa: F401
from app.models.alarm_state import (  # noqa: F401
    AlarmRule,
    AlarmActiveState,
    AlarmSuppressedDevice,
)
from app.models.cabinet import Cabinet  # noqa: F401
from app.models.equipment import Equipment  # noqa: F401
from app.models.external import ExternalDevice, MetricRaw, MetricDef  # noqa: F401
from app.models.capacity_energy import CapacityEnergyHistory  # noqa: F401
from app.models.idc import IDC  # noqa: F401
from app.models.knowledge import KnowledgeItem  # noqa: F401
from app.models.drill import DrillPlan  # noqa: F401
from app.models.drill_record import DrillRecord  # noqa: F401
from app.models.maintenance import MaintenanceRecord  # noqa: F401
from app.models.risk import RiskItem  # noqa: F401
from app.models.inspection import InspectionRoute, InspectionFinding, InspectionRobot  # noqa: F401
from app.models.point_data import PointData  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.server import Server  # noqa: F401
from app.models.shift import ShiftSchedule, ShiftHandover  # noqa: F401
from app.models.ticket import Ticket  # noqa: F401
from app.models.user import User, Role, user_role  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.assistant_feedback import AssistantFeedback  # noqa: F401
from app.models.alarm_feedback import AlarmFeedback  # noqa: F401
from app.models.energy_advice import EnergyAdviceAdopt  # noqa: F401

__all__ = [
    "Base",
    "IDC",
    "Room",
    "Equipment",
    "Cabinet",
    "Server",
    "PointData",
    "AlarmEvent",
    "Ticket",
    "KnowledgeItem",
    "DrillPlan",
    "DrillRecord",
    "MaintenanceRecord",
    "RiskItem",
    "InspectionRoute",
    "InspectionFinding",
    "InspectionRobot",
    "ShiftSchedule",
    "ShiftHandover",
    "ExternalDevice",
    "MetricDef",
    "MetricRaw",
    "User",
    "Role",
    "user_role",
    "AuditLog",
    "AssistantFeedback",
    "AlarmFeedback",
    "EnergyAdviceAdopt",
    "AlarmRule",
    "AlarmActiveState",
    "AlarmSuppressedDevice",
]
