"""AI 运维助手（知识库检索问答）请求/响应模型。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AssistantContext(BaseModel):
    """前端可携带的现场上下文，用于提升检索与回答的相关性。"""

    system: Optional[str] = Field(None, description="当前系统/页面标题，如 冷源/消防主机")
    domain: Optional[str] = Field(None, description="业务域标识，如 hvac_source/security_fire")
    metric: Optional[str] = Field(None, description="相关测点，如 supply_temp")
    alarm: Optional[str] = Field(None, description="当前告警文本/代码")
    page: Optional[str] = Field(None, description="前端路由，如 /ops/twin")
    # [B6] 实时态势上下文: 前端可携带当前设备编号, 后端据此注入该设备实时测点与活跃告警
    device_id: Optional[str] = Field(None, description="当前设备编号, 用于注入实时测点态势")


class AssistantAskReq(BaseModel):
    question: str = Field(..., min_length=1, description="运维人员描述的现场情况/问题")
    context: Optional[AssistantContext] = None


class AssistantRef(BaseModel):
    code: str
    title: str
    type: str


class SituationAlarm(BaseModel):
    device_id: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    level: Optional[str] = None
    ts: Optional[float] = None
    rule_id: Optional[str] = None


class SituationMetric(BaseModel):
    metric: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    ts: Optional[float] = None


class AssistantSituation(BaseModel):
    """[B6] 注入到问答中的实时态势上下文 (活跃告警 + 设备实时测点)。"""
    active_alarm_count: int = 0
    active_alarms: List[SituationAlarm] = Field(default_factory=list)
    device_metrics: Optional[List[SituationMetric]] = None


class AssistantAskResp(BaseModel):
    question: str
    answer: str
    steps: List[str] = Field(default_factory=list, description="建议处置步骤（去重后）")
    refs: List[AssistantRef] = Field(default_factory=list, description="命中的知识库条目")
    model: str = Field(..., description="回答引擎，如 rag-grounded / llm:gpt-4o-mini")
    grounded: bool = Field(True, description="是否基于知识库检索（False 表示走大模型自由生成）")
    noMatch: bool = Field(False, description="知识库是否未检索到相关条目")
    # [B6] 注入的实时态势上下文 (供前端展示/复用)
    situation: Optional[AssistantSituation] = None
    # [B] 大模型接入诊断：当配置了 LLM 但调用失败回退时，给出可读失败原因
    llm_error: Optional[str] = Field(
        None,
        description="大模型调用失败原因（如 Key 失效/网络不通/模型不存在）；成功或未配置时为 None",
    )


class AssistantStatusResp(BaseModel):
    """大模型接入状态自查（运维调试用，GET /ops/assistant/status）。"""
    configured: bool = Field(..., description="是否配置了 LLM_API_KEY")
    base_url: str = Field(..., description="大模型 API Base URL")
    model: str = Field(..., description="配置的大模型 id")
    reachable: bool = Field(..., description="能否连通端点并通过 Key 校验")
    http_status: Optional[int] = Field(None, description="探测得到的 HTTP 状态码（401/403/404/200 等）")
    latency: Optional[float] = Field(None, description="探测耗时（秒）")
    model_available: Optional[bool] = Field(None, description="所配置模型 id 是否在端点模型列表中")
    detail: str = Field(..., description="可读诊断说明")
