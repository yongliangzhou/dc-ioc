"""CMDB 关系层 DTO (阶段二)。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

RelationType = Literal["connects_to", "powers", "cools", "depends_on", "hosts"]

RELATION_TYPES: tuple[str, ...] = (
    "connects_to", "powers", "cools", "depends_on", "hosts",
)


class CiRelationCreate(BaseModel):
    source_ci: str = Field(min_length=1, max_length=128, description="源 CI 标识, 如 equipment:12")
    target_ci: str = Field(min_length=1, max_length=128, description="目标 CI 标识")
    source_name: str = Field(default="", max_length=128)
    target_name: str = Field(default="", max_length=128)
    relation_type: RelationType = "connects_to"
    description: str = Field(default="", max_length=1024)
    tenant_id: int | None = None

    @model_validator(mode="after")
    def reject_self_loop(self) -> "CiRelationCreate":
        if self.source_ci.strip() == self.target_ci.strip():
            raise ValueError("CI 不能与自身建立关系 (自环不被允许)")
        return self


class CiRelationOut(BaseModel):
    id: int
    source_ci: str
    target_ci: str
    source_name: str = ""
    target_name: str = ""
    relation_type: str
    description: str = ""
    created_by: str = "system"
    created_at: str | None = None
    tenant_id: int | None = None


class CiOption(BaseModel):
    """可选 CI 下拉项 (来自设备台账 / 机柜 / 外部设备的并集)。"""

    ci: str
    name: str
    kind: str = ""


class CiGraphOut(BaseModel):
    """关系图 (前端绘制 SVG / 后续 GraphQL 复用)。"""

    nodes: list[dict]
    edges: list[dict]
    total: int
    topology_source: str = "real"


class CiImpactItem(BaseModel):
    ci: str
    name: str
    hop: int
    via: str
    path: list[str]


class CiImpactOut(BaseModel):
    """影响扩散结果: 有向 BFS, 有环保护, 深度上限 6。"""

    source_ci: str
    depth: int
    topology_source: str  # real | fallback
    impacted: list[CiImpactItem]
    total: int
    has_cycle: bool = False
