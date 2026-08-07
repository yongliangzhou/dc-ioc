"""知识库/处置预案 Schema (2.3)。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemberIn(BaseModel):
    name: str
    role: str = ""
    phone: str = ""


class KnowledgeCreate(BaseModel):
    title: str
    category: str = ""
    domain: str = ""
    type: str = "sop"
    tags: list[str] = Field(default_factory=list)
    relatedCategories: list[str] = Field(default_factory=list)
    relatedDomains: list[str] = Field(default_factory=list)
    relatedMetrics: list[str] = Field(default_factory=list)
    summary: str = ""
    content: str = ""
    steps: list[str] = Field(default_factory=list)
    owner: str = ""
    hot: bool = False
    code: Optional[str] = None
    # 导入切分自动生成的内容默认进入待审核
    reviewStatus: Optional[str] = "pending"


class KnowledgeReviewIn(BaseModel):
    """人工审核：通过 / 驳回 + 意见。"""
    status: str  # approved / rejected
    note: str = ""
    reviewer: str = ""


class KnowledgeUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[list[str]] = None
    relatedCategories: Optional[list[str]] = None
    relatedDomains: Optional[list[str]] = None
    relatedMetrics: Optional[list[str]] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    steps: Optional[list[str]] = None
    owner: Optional[str] = None
    hot: Optional[bool] = None
    reviewStatus: Optional[str] = None
    reviewNote: Optional[str] = None


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    title: str
    category: str = ""
    domain: str = ""
    type: str = "sop"
    tags: list[str] = Field(default_factory=list)
    relatedCategories: list[str] = Field(default_factory=list)
    relatedDomains: list[str] = Field(default_factory=list)
    relatedMetrics: list[str] = Field(default_factory=list)
    summary: str = ""
    content: str = ""
    steps: list[str] = Field(default_factory=list)
    owner: str = ""
    hot: bool = False
    version: int = 1
    reviewStatus: str = "approved"
    reviewer: str = ""
    reviewedAt: Any = None
    reviewNote: str = ""
    createdAt: Any = None
    updatedAt: Any = None


class KnowledgeListOut(BaseModel):
    total: int
    items: list[KnowledgeOut]
    stats: dict


class KnowledgeImportOut(BaseModel):
    """一键导入运维指导书(按章节切分)的返回: 入库条目 + 切分统计。"""
    items: list[KnowledgeOut] = Field(default_factory=list)
    created: int = 0
    skipped: int = 0
    total: int = 0
    detectedDomains: list[str] = Field(default_factory=list)
    detectedCategories: list[str] = Field(default_factory=list)
    note: str = ""
