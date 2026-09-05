"""统一图形编辑入口 Pydantic Schema (图形场景配置 + 加油记录)。"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GraphicNode(BaseModel):
    """图形节点 (覆盖层条目: 与页面节点按 id 对齐)。"""

    id: str
    label: str = ""
    type: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    status: str = ""
    params: Dict[str, str] = Field(default_factory=dict)


class GraphicEdge(BaseModel):
    """图形连线 (from → to)。"""

    id: str = ""
    source: str = ""
    target: str = ""
    label: str = ""


class GraphicScene(BaseModel):
    """一份图形场景覆盖层。

    nodes 中 id 与页面数据一致的条目 = 覆盖(改名/改坐标/改状态/改参数);
    id 在页面数据里不存在 = 用户新增的节点; removed 中的 id = 用户删除的节点。
    params = 页面级参数配置 (如温度云图阈值、储油罐额定容量等)。
    """

    nodes: List[GraphicNode] = Field(default_factory=list)
    edges: List[GraphicEdge] = Field(default_factory=list)
    params: Dict[str, str] = Field(default_factory=dict)
    removed: List[str] = Field(default_factory=list)


class GraphicConfigIn(BaseModel):
    title: Optional[str] = None
    payload: GraphicScene


class GraphicConfigOut(BaseModel):
    kind: str
    title: str = ""
    payload: GraphicScene
    updatedBy: str = "system"
    updatedAt: Optional[str] = None


class RefuelCreate(BaseModel):
    no: str
    date: str
    tank: str = ""
    amount: float = 0
    before: Optional[float] = None
    after: Optional[float] = None
    vendor: str = ""
    grade: str = ""
    qc: str = ""
    operator: str = ""
    status: str = "已完成"
    note: str = ""


class RefuelUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    no: Optional[str] = None
    date: Optional[str] = None
    tank: Optional[str] = None
    amount: Optional[float] = None
    before: Optional[float] = None
    after: Optional[float] = None
    vendor: Optional[str] = None
    grade: Optional[str] = None
    qc: Optional[str] = None
    operator: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
