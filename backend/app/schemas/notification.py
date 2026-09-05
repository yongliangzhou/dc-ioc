"""统一告警触达中心 Pydantic Schema。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    type: str = Field(..., description="dingtalk/email/wechat/sms/custom")
    name: str
    url: str = ""
    minLevel: str = "crit"          # crit/warn/info
    quietStart: Optional[str] = None  # "22:00"
    quietEnd: Optional[str] = None    # "07:00"
    enabled: bool = True


class ChannelUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    minLevel: Optional[str] = None
    quietStart: Optional[str] = None
    quietEnd: Optional[str] = None
    enabled: Optional[bool] = None


class ChannelOut(BaseModel):
    id: int
    type: str
    name: str
    url: str = ""
    minLevel: str = "crit"
    quietStart: Optional[str] = None
    quietEnd: Optional[str] = None
    enabled: bool = True
    updatedBy: str = "system"
    updatedAt: Optional[str] = None


class RecordOut(BaseModel):
    id: int
    alarmId: Optional[str] = None
    channelId: int
    channelName: str = ""
    level: str
    title: str
    status: str = "sent"
    error: str = ""
    retryCount: int = 0
    createdAt: Optional[str] = None


class RecordListResp(BaseModel):
    items: list[RecordOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pageSize: int = 50


class TestSendIn(BaseModel):
    channelId: int
    title: str = "【测试】通知中心连通性测试"
    message: str = "这是一条来自统一告警触达中心的测试消息。"


class TestSendResp(BaseModel):
    channelId: int
    status: str              # sent / failed / muted
    error: str = ""
