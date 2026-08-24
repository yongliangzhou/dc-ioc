"""物理服务器 / U 位识别 DTO。

U 位识别采用「多源融合」模型:
  - RFID / 资产标签: server 表落地 (实时 U 位, 视为现场实测)
  - 电子工单 / 资产台账: 规划 U 位 (基准真值)
后端把两源对齐到机柜 U 位立面, 交叉验证并产出冲突与置信度。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import CamelModel


class ServerBase(CamelModel):
    cabinet_id: int = Field(..., description="所在机柜 id")
    asset_no: str = Field(..., max_length=64, description="资产编号 (唯一)")
    hostname: str = Field(default="", max_length=128)
    ip: str = Field(default="", max_length=45, description="管理 IP")
    brand: str = Field(default="", max_length=64, description="厂商")
    model: str = Field(default="", max_length=128, description="型号")
    u_start: int = Field(..., ge=1, description="起始 U 位 (含)")
    u_end: int = Field(..., ge=1, description="结束 U 位 (含)")
    cpu_model: str = Field(default="", max_length=128)
    cpu_count: int = Field(default=2, ge=0)
    cpu_cores: int = Field(default=0, ge=0)
    memory_gb: int = Field(default=0, ge=0)
    disk_desc: str = Field(default="", max_length=255)
    business: str = Field(default="", max_length=128)
    status: str = Field(default="在线", max_length=16, description="在线/离线/下架")


class ServerCreate(ServerBase):
    pass


class ServerUpdate(CamelModel):
    cabinet_id: Optional[int] = None
    asset_no: Optional[str] = Field(None, max_length=64)
    hostname: Optional[str] = Field(None, max_length=128)
    ip: Optional[str] = Field(None, max_length=45)
    brand: Optional[str] = Field(None, max_length=64)
    model: Optional[str] = Field(None, max_length=128)
    u_start: Optional[int] = Field(None, ge=1)
    u_end: Optional[int] = Field(None, ge=1)
    cpu_model: Optional[str] = Field(None, max_length=128)
    cpu_count: Optional[int] = Field(None, ge=0)
    cpu_cores: Optional[int] = Field(None, ge=0)
    memory_gb: Optional[int] = Field(None, ge=0)
    disk_desc: Optional[str] = Field(None, max_length=255)
    business: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = Field(None, max_length=16)


class ServerOut(ServerBase):
    id: int
    u_height: int = Field(..., description="占用 U 数 = u_end - u_start + 1")
    source: Literal["rfid", "ledger", "manual"] = Field(
        default="rfid", description="识别来源: 资产标签(RFID)实测 / 工单台账 / 人工录入"
    )


class UCell(CamelModel):
    """机柜立面单个 U 位 (1-based)。"""

    u: int = Field(..., description="U 位编号 (1=最下, 自下而上)")
    status: Literal["occupied", "empty", "conflict", "reserved"] = Field(
        default="empty", description="占用/空置/冲突/预留"
    )
    sources: list[str] = Field(default_factory=list, description="命中来源 server id 列表")
    device_refs: list[int] = Field(default_factory=list, description="占用该 U 的 server id")
    confidence: float = Field(default=1.0, ge=0, le=1, description="该 U 位识别置信度")
    note: str = Field(default="", description="备注 (如冲突说明)")


class UConflict(CamelModel):
    u: int = Field(..., description="冲突 U 位")
    type: Literal["range_overlap", "ledger_mismatch", "reservation_clash"] = Field(
        ..., description="区间重叠 / 台账不符 / 预留冲突"
    )
    detail: str = Field(..., description="冲突说明")
    asset_nos: list[str] = Field(default_factory=list, description="涉及资产编号")
    severity: Literal["warn", "crit"] = Field(default="warn")


class UPositionView(CamelModel):
    """机柜 U 位立面图 (含识别冲突)。"""

    cabinet_id: int
    code: str = Field(default="")
    room: str = Field(default="")
    row: str = Field(default="")
    u_total: int = Field(..., description="机柜总 U 数")
    cells: list[UCell] = Field(default_factory=list)
    conflicts: list[UConflict] = Field(default_factory=list)
    occupied_u: int = 0
    empty_u: int = 0
    conflict_u: int = 0
    generated_at: str = Field(default="")


class RecognizeSource(CamelModel):
    key: str = Field(..., description="来源 key: ledger / rfid")
    name: str = Field(..., description="来源名称")
    confidence: float = Field(..., ge=0, le=1, description="该来源整体置信度")
    count: int = Field(default=0, description="该来源命中设备数")


class RecognizeResp(CamelModel):
    """U 位多源识别结果。"""

    cabinet_id: int
    code: str = Field(default="")
    room: str = Field(default="")
    u_total: int = Field(..., description="机柜总 U 数")
    sources: list[RecognizeSource] = Field(default_factory=list)
    cells: list[UCell] = Field(default_factory=list)
    conflicts: list[UConflict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict, description="totalU/occupied/empty/conflict/avgConfidence")
    recognized_at: str = Field(default="")
