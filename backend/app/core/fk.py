"""数据库设计文档 第八章 8.3 — 外键约束补全 (阶段一, 单一事实源)。

对现有"逻辑关联"补 DB 外键并设级联/置空, 提升引用一致性:
- external_devices.idc_id          -> idc.id                 (SET NULL, 弱 FK)
- alarm_event.device_id           -> external_devices.device_id (SET NULL, 自然键 FK)
- alarm_event.rule_id             -> alarm_rule.rule_id     (SET NULL)
- alarm_feedback.alarm_id         -> alarm_event.id         (CASCADE)
- ticket.source_alarm_id          -> alarm_event.id         (SET NULL)
- metric_defs.device_id           -> external_devices.device_id (CASCADE)
- metric_raws.device_id           -> external_devices.device_id (CASCADE)
- maintenance_record.plan_id(新增) -> maintenance_plan.id   (SET NULL, 同时保留 plan_code 冗余)

说明: 设备关联采用 external_devices.device_id 自然键 (unique) 做 FK, 属低风险;
文档另建议改引 external_devices.id 内部 id, 那需新增 BIGINT 列 + 改写采集/告警代码,
留作后续可选增强, 不在阶段一强一致低风险范围内。

drill_record.plan_id -> drill_plan.id 已在 8.2 阶段建好 (FK_BIGINT_SPECS), 阶段一无需重复。
阶段二 (采集高写入链路) 的 point_data 维持无 FK, 由应用层保障。

开发库自愈见 app.core.lifespan._ensure_fk_constraints; 生产路径见
alembic/versions/0008_fk_constraints.py。两者均消费本模块常量。
"""

# (child_table, child_col, parent_table, parent_col, ondelete)
FK_CONSTRAINTS: list[tuple[str, str, str, str, "str | None"]] = [
    ("external_devices", "idc_id", "idc", "id", "SET NULL"),
    ("alarm_event", "device_id", "external_devices", "device_id", "SET NULL"),
    ("alarm_event", "rule_id", "alarm_rule", "rule_id", "SET NULL"),
    ("alarm_feedback", "alarm_id", "alarm_event", "id", "CASCADE"),
    ("ticket", "source_alarm_id", "alarm_event", "id", "SET NULL"),
    ("metric_defs", "device_id", "external_devices", "device_id", "CASCADE"),
    ("metric_raws", "device_id", "external_devices", "device_id", "CASCADE"),
    ("maintenance_record", "plan_id", "maintenance_plan", "id", "SET NULL"),
]

# external_devices.idc_id 在 8.2 中刻意保留 Integer, 阶段一统一改为 BIGINT 再建 FK。
IDC_ID_BIGINT_TABLE = "external_devices"
IDC_ID_COLUMN = "idc_id"

# 子表空字符串需先置 NULL, 否则 FK 约束会拒绝 '' (非空但不命中父表)。
EMPTY_NULL_CLEANUP: list[tuple[str, str]] = [
    ("alarm_event", "device_id"),
    ("alarm_event", "rule_id"),
    ("alarm_feedback", "alarm_id"),
    ("ticket", "source_alarm_id"),
]

# maintenance_record 新增 plan_id 列并从 plan_code 迁移 (plan_code 保留为冗余列)。
PLAN_ID_TABLE = "maintenance_record"
PLAN_ID_COLUMN = "plan_id"
PLAN_CODE_COLUMN = "plan_code"


def fk_constraint_name(child_table: str, child_col: str) -> str:
    return f"{child_table}_{child_col}_fkey"


def ondelete_clause(ondelete: "str | None") -> str:
    return f" ON DELETE {ondelete}" if ondelete else ""
