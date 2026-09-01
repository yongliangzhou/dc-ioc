"""数据库设计文档 第八章 8.2 — 主键与标识符策略 (单一事实源)。

内部关联表统一 `BIGINT` 自增主键, 引用这些 PK 的外键列也统一 `BIGINT`,
避免 INTEGER 自增上限风险。

业务单号表 (ticket / workflow_item / alarm_event) 的 String 主键改造
(额外保留内部 id BIGINT + 外键改引内部 id) 属于 8.3 外键阶段, 本模块不含。

开发库自愈见 app.core.lifespan._ensure_bigint_pk; 生产路径见
alembic/versions/0007_bigint_pk.py。两者均消费本模块常量, 保持单一事实源。
"""

# 需要把 PK (列名均为 id) 改为 BIGINT 的表 (以 __tablename__ 为准)。
PK_BIGINT_TABLES: list[str] = [
    # 资产拓扑树
    "idc", "room", "cabinet", "equipment", "server",
    # 物模型
    "thing_model", "thing_model_item",
    # 运维作业
    "drill_plan", "drill_record",
    "maintenance_plan", "maintenance_record",
    "risk_item", "tenant", "knowledge_item",
    "inspection_route", "inspection_finding", "inspection_robot",
    "shift_schedule", "shift_handover",
    # 用户/权限
    "users", "roles",
    # 采集接入 / 时序
    "external_devices", "metric_raws", "metric_defs",
    # 审计 / 反馈 / 日志
    "audit_logs", "assistant_feedback", "analysis_history", "alarm_feedback",
    "energy_advice_adopt", "control_log", "kpi_history",
]

# 外键列 (随 PK 一起改 BIGINT): (fk_table, fk_col, pk_table, pk_col, ondelete)
# ondelete 为 None 表示 NO ACTION。
FK_BIGINT_SPECS: list[tuple[str, str, str, str, "str | None"]] = [
    ("room", "idc_id", "idc", "id", "CASCADE"),
    ("cabinet", "idc_id", "idc", "id", "CASCADE"),
    ("equipment", "idc_id", "idc", "id", "CASCADE"),
    ("equipment", "room_id", "room", "id", "SET NULL"),
    ("server", "cabinet_id", "cabinet", "id", "CASCADE"),
    ("thing_model_item", "thing_model_id", "thing_model", "id", "CASCADE"),
    ("drill_record", "plan_id", "drill_plan", "id", None),
    ("user_role", "user_id", "users", "id", "CASCADE"),
    ("user_role", "role_id", "roles", "id", "CASCADE"),
]


def fk_constraint_name(fk_table: str, fk_col: str) -> str:
    """确定性外键约束名 (与 Postgres 默认命名约定一致)。"""
    return f"{fk_table}_{fk_col}_fkey"


def ondelete_clause(ondelete: "str | None") -> str:
    return f" ON DELETE {ondelete}" if ondelete else ""
