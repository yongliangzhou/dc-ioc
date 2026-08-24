"""通用 DTO 基类: CamelCase 序列化 (对齐前端 TypeScript 类型)。

前端约定字段使用小驼峰 (camelCase), 而后端 ORM / Python 约定蛇形 (snake_case)。
通过 alias_generator 自动将蛇形字段名转为小驼峰输出, 同时允许按蛇形/驼峰双向校验输入。
"""
from pydantic import BaseModel, ConfigDict


def to_camel(s: str) -> str:
    """snake_case -> camelCase。"""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
