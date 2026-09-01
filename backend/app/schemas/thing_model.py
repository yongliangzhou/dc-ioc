"""物模型 Pydantic Schema (phase: thing-model)。

接口契约与前端编辑器 (views/ops/ThingModelEditor.vue) 对齐:
- 属性 property / 服务 service / 事件 event 三要素, 前端以 camelCase 提交。
- extra 透传扩展信息 (enum 值域 / 服务入参等)。
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.schemas.common import CamelModel


# ------------------------------------------------------------------ 子项
class ThingModelItemBase(CamelModel):
    item_type: str = Field("property", description="property/service/event")
    identifier: str = Field(..., max_length=64, description="标识符 (蛇形命名)")
    name: str = Field("", max_length=128, description="中文名")
    data_type: str = Field("float", max_length=32, description="数据类型")
    unit: str = Field("", max_length=16, description="单位")
    desc: str = Field("", description="说明")
    extra: dict[str, Any] = Field(default_factory=dict, description="扩展信息 (enum 值域/服务入参等)")


class ThingModelItemCreate(ThingModelItemBase):
    pass


class ThingModelItemOut(ThingModelItemBase):
    id: int
    thing_model_id: int


# ------------------------------------------------------------------ 模型
class ThingModelCreate(CamelModel):
    model_key: str = Field(..., max_length=64, description="模型唯一 key (设备类别语义)")
    name: str = Field("", max_length=128, description="模型中文名")
    category: str = Field("", max_length=64, description="设备类别")
    domain: str = Field("", max_length=64, description="业务域")
    protocol: str = Field("", max_length=32, description="推荐采集协议")
    vendor: str = Field("", max_length=64, description="厂商")
    description: str = Field("", description="说明")
    items: list[ThingModelItemCreate] = Field(default_factory=list, description="属性/服务/事件定义")


class ThingModelUpdate(CamelModel):
    name: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None
    protocol: Optional[str] = None
    vendor: Optional[str] = None
    description: Optional[str] = None
    items: Optional[list[ThingModelItemCreate]] = None


class ThingModelOut(CamelModel):
    id: int
    model_key: str
    name: str
    category: str
    domain: str
    protocol: str
    vendor: str
    description: str
    items: list[ThingModelItemOut] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
