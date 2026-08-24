"""生成数据库数据字典 Markdown (仅反射 SQLAlchemy metadata, 不连库)。
输出: deploy/sql/010_data_dictionary.md
"""
import importlib
import os
from sqlalchemy import inspect as sa_inspect

# 触发所有模型注册
import app.models  # noqa
from app.db.session import Base

OUT = os.path.join(os.path.dirname(__file__), "deploy", "sql", "010_data_dictionary.md")
md = Base.metadata

lines = []
lines.append("# 数据库数据字典（自动生成补充）\n")
lines.append("> 生成方式：`python gen_dd.py`（反射 `app.models.Base.metadata`）。\n")
lines.append("> 本文件与 `004_schema_design.md`（核心表设计）互补，覆盖**全部业务表**的字段定义。\n")

tables = sorted(md.tables.values(), key=lambda t: t.name)
rel_lines = []

for t in tables:
    lines.append(f"\n## 表 `{t.name}`\n")
    cols = list(t.columns)
    lines.append("| 字段 | 类型 | 可空 | 默认 | 约束/说明 |")
    lines.append("|------|------|------|------|-----------|")
    for c in cols:
        ctype = str(c.type)
        nullable = "否" if not c.nullable else "是"
        default = ""
        if c.default is not None:
            try:
                if hasattr(c.default, "arg") and c.default.arg is not None:
                    default = repr(c.default.arg)
                elif c.default.is_scalar:
                    default = repr(c.default.arg)
                else:
                    # 服务端/Python 函数默认值 (如 utcnow)
                    default = "utcnow()/函数"
            except Exception:
                default = "有"
        cons = []
        if c.primary_key:
            cons.append("PK")
        for fk in c.foreign_keys:
            cons.append(f"FK→{fk.column.table.name}.{fk.column.name}")
        if c.unique:
            cons.append("UNIQUE")
        if c.index:
            cons.append("INDEX")
        if c.comment:
            cons.append(str(c.comment))
        lines.append(f"| {c.name} | {ctype} | {nullable} | {default} | {' '.join(cons)} |")
    # 表级约束
    pks = [c.name for c in cols if c.primary_key]
    if pks:
        lines.append(f"\n- 主键：{', '.join(pks)}")
    # 关系推理（外键）
    for c in cols:
        for fk in c.foreign_keys:
            rel_lines.append(f"- `{t.name}.{c.name}` → `{fk.column.table.name}.{fk.column.name}`")

lines.append("\n\n## 外键关系总览\n")
if rel_lines:
    lines.extend(rel_lines)
else:
    lines.append("(无外键约束，或已通过应用层维护关联)")

content = "\n".join(lines)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(content)
print(f"OK: 生成 {len(tables)} 张表 -> {OUT}")
