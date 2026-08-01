"""外部设备接入数据契约 (Data Contract) — Pydantic 实体。

供采集器开发团队 (Modbus / SNMP / Kafka 等) 对接的标准结构:
  - 设备注册:  POST /api/external/device/register
  - 测点上报:  POST /api/external/metrics/upload  (单点 / 批量)

本文件仅为「契约定义」, 不依赖任何具体采集协议; 后端负责接收、校验与落地。
"""
from __future__ import annotations

import ipaddress
import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ------------------------------------------------------------------ 枚举
class MetricQuality(str, Enum):
    """测点数据质量 (对齐 OPC-UA / IEC 60870 质量码语义)。"""

    GOOD = "good"        # 正常、可信
    UNCERTAIN = "uncertain"  # 可疑 (抖动/插值/通信降级)
    BAD = "bad"          # 坏点 (采集失败/超时/设备离线)


# ------------------------------------------------------------------ 设备注册
class DeviceRegisterRequest(BaseModel):
    """设备注册请求体。

    必填核心字段 (契约硬约束): device_id / ip / sn / model。
    其余为可选扩展字段, 便于把外部设备映射到内部统一设备台账 (domain/category)。
    """

    device_id: str = Field(..., min_length=2, max_length=64,
                           pattern=r"^[A-Za-z0-9][A-Za-z0-9._:\-]{1,63}$",
                           description="设备唯一标识 (采集侧稳定 ID, 建议 资产编号/序列号派生)")
    ip: str = Field(..., min_length=1, max_length=64, description="管理/采集 IP 或可达主机名")
    sn: str = Field(..., min_length=1, max_length=128, description="设备出厂序列号")
    model: str = Field(..., min_length=1, max_length=128, description="设备型号")

    # ---- 可选扩展 (用于与内部统一设备台账 domain/category 对齐) ----
    name: Optional[str] = Field(None, max_length=128, description="展示名称")
    vendor: Optional[str] = Field(None, max_length=64, description="厂商")
    domain: Optional[str] = Field(None, description="业务域 hvac_source/hvac_terminal/power_hv/...")
    category: Optional[str] = Field(None, description="设备类别 chiller/crac/ups/genset/...")
    location: Optional[str] = Field(None, max_length=128, description="物理位置/包间 R01")
    protocol: Optional[str] = Field(None, description="采集协议 modbus/snmp/kafka/...")
    tags: list[str] = Field(default_factory=list, description="自定义标签")
    description: Optional[str] = Field(None, max_length=512)
    extra: dict[str, Any] = Field(default_factory=dict, description="厂商/协议私有扩展字段")

    @field_validator("ip")
    @classmethod
    def _check_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            if re.fullmatch(r"[A-Za-z0-9.\-]{1,253}", v):
                return v
            raise ValueError("ip 必须是合法的 IPv4/IPv6 地址或主机名")


class DeviceRegisterResponse(BaseModel):
    device_id: str
    status: str = Field(..., description="registered / duplicate / updated")
    received_at: str
    message: str
    # [P1-6] 随注册响应下发采集器上报周期 / 前端 stale 阈值, 采集器与前端据此联动
    report_interval_s: int | None = Field(
        None, description="采集器测点上报周期(s), 前端据此动态判定测点陈旧"
    )
    stale_threshold_ms: int | None = Field(
        None, description="前端判定单测点 stale 的阈值(ms)"
    )


# ------------------------------------------------------------------ 设备更新 (编辑/删除)
class DeviceUpdateRequest(BaseModel):
    """设备信息更新请求体 (所有字段可选, 仅更新传入的字段)。"""

    ip: Optional[str] = Field(None, min_length=1, max_length=64, description="管理/采集 IP 或可达主机名")
    sn: Optional[str] = Field(None, min_length=1, max_length=128, description="设备出厂序列号")
    model: Optional[str] = Field(None, min_length=1, max_length=128, description="设备型号")
    name: Optional[str] = Field(None, max_length=128, description="展示名称")
    vendor: Optional[str] = Field(None, max_length=64, description="厂商")
    domain: Optional[str] = Field(None, description="业务域")
    category: Optional[str] = Field(None, description="设备类别")
    location: Optional[str] = Field(None, max_length=128, description="物理位置")
    protocol: Optional[str] = Field(None, description="采集协议")
    tags: Optional[list[str]] = Field(None, description="自定义标签")
    description: Optional[str] = Field(None, max_length=512)
    extra: Optional[dict[str, Any]] = Field(None, description="厂商/协议私有扩展字段")

    @field_validator("ip")
    @classmethod
    def _check_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            if re.fullmatch(r"[A-Za-z0-9.\-]{1,253}", v):
                return v
            raise ValueError("ip 必须是合法的 IPv4/IPv6 地址或主机名")


class DeviceActionResponse(BaseModel):
    """设备操作通用响应 (更新/删除)。"""
    device_id: str
    action: str  # "updated" / "deleted"
    received_at: str
    message: str


# ------------------------------------------------------------------ 物模型 (传感器/测点模板)
class ThingModelMetricDef(BaseModel):
    """物模型中单个测点的定义。"""
    metric_name: str = Field(..., description="测点名称 (蛇形命名, 如 supply_temp)")
    unit: str = Field("", description="单位, 如 ℃ / kW / %")
    description: str = Field("", description="中文说明, 如 '送风温度'")


class ThingModelDef(BaseModel):
    """物模型: 某类设备的传感器/测点模板。"""
    category: str = Field(..., description="设备类别 key (chiller/crac/ups/...)")
    category_label: str = Field("", description="设备类别中文名")
    domain: str = Field("", description="所属业务域")
    protocol: str = Field("", description="推荐采集协议")
    metrics: list[ThingModelMetricDef] = Field(default_factory=list, description="该类别设备的传感器/测点列表")


# ------------------------------------------------------------------ 测点上报
class MetricPoint(BaseModel):
    """单条实时测点 (遥测/遥信)。

    字段 (契约硬约束): device_id / timestamp / metric_name / value / quality。
    """

    device_id: str = Field(..., min_length=2, max_length=64, description="设备唯一标识")
    timestamp: str | int | float = Field(..., description="测点时间戳, ISO8601 字符串 (如 2026-07-24T10:00:00+08:00) 或 Unix 秒 (数字)")
    metric_name: str = Field(..., min_length=1, max_length=128,
                             description="测点名 (蛇形命名, 如 cpu_usage / inlet_temp / power_kw)")
    value: float = Field(..., description="数值 (遥信可用 0/1 表示)")
    quality: MetricQuality = Field(MetricQuality.GOOD, description="数据质量 good/uncertain/bad")

    unit: Optional[str] = Field(None, max_length=32, description="单位 ℃/kW/%/... (可选, 便于展示)")
    tags: dict[str, Any] = Field(default_factory=dict, description="维度标签 (可选)")


class RejectedItem(BaseModel):
    index: int
    device_id: Optional[str] = None
    reason: str


class MetricUploadResponse(BaseModel):
    total: int
    accepted: int
    rejected: int
    rejected_items: list[RejectedItem] = Field(default_factory=list)
    received_at: str
    message: str


# ------------------------------------------------------------------ 视图(只读)响应
class ExternalDeviceView(BaseModel):
    """已注册设备视图 (供前端「采集器接入/设备注册状态」页展示)。"""

    device_id: str
    ip: str
    sn: str
    model: str
    name: Optional[str] = None
    vendor: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    protocol: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)
    registered_at: Optional[str] = None  # 首次注册时间 (ISO8601)
    last_seen: Optional[str] = None      # 最近一次测点上报时间
    metric_count: int = 0                # 累计测点数
    online: bool = False                 # 依据 last_seen 阈值判定在线/离线


class DeviceListResponse(BaseModel):
    """设备注册状态列表响应。"""

    total: int
    online: int
    offline: int
    total_metrics: int
    items: list[ExternalDeviceView] = Field(default_factory=list)


class MetricRecordView(BaseModel):
    """单条测点记录视图 (供前端展示某设备最近测点)。"""

    device_id: str
    ts: Optional[str] = None
    metric_name: str
    value: float
    quality: str = "good"
    unit: Optional[str] = None
    received_at: Optional[str] = None


# ------------------------------------------------------------------ 历史 / 实时查询 (物模型驱动可视化)
class MetricHistoryPoint(BaseModel):
    """历史序列中的单个采样点。"""

    ts: str = Field(..., description="采样时间 ISO8601")
    value: float
    quality: str = "good"


class MetricHistoryResponse(BaseModel):
    """某设备指定测点的历史序列 (供趋势图)。"""

    device_id: str
    unit: dict[str, str] = Field(default_factory=dict, description="metric_name -> 单位")
    series: dict[str, list[MetricHistoryPoint]] = Field(default_factory=dict, description="metric_name -> 采样点序列")


class MetricRealtimePoint(BaseModel):
    """设备实时测点 (单条)。"""

    metric_name: str
    value: float
    unit: Optional[str] = None
    quality: str = "good"


class MetricRealtimeResponse(BaseModel):
    """某设备实时测点快照 (供实时卡片 / WS 订阅推送)。"""

    device_id: str
    ts: Optional[str] = None
    online: bool = False
    points: list[MetricRealtimePoint] = Field(default_factory=list)
