"""网络监控域 DTO。"""
from typing import List, Optional

from pydantic import BaseModel


# ---------- 核心网络监控 ----------
class SwitchPortOut(BaseModel):
    name: str          # e.g. "GE1/0/1"
    alias: str = ""    # 描述/用途
    status: str        # "up" / "down"
    speed_mbps: int    # 协商速率 Mbps
    in_bps: float      # 入流量 bps
    out_bps: float     # 出流量 bps
    in_util_pct: float  # 入利用率 %
    out_util_pct: float # 出利用率 %
    in_errors: int = 0
    out_errors: int = 0
    in_discards: int = 0


class SwitchOut(BaseModel):
    id: str            # e.g. "SW-CORE-01"
    name: str          # 设备名
    ip: str
    model: str         # 型号
    role: str          # core / agg / access / tor
    location: str      # 物理位置
    status: str        # "online" / "offline"
    cpu_pct: float
    mem_pct: float
    uptime_days: int
    total_ports: int
    up_ports: int
    down_ports: int
    ports: List[SwitchPortOut] = []


class NetworkOverviewOut(BaseModel):
    total_switches: int
    online_switches: int
    offline_switches: int
    total_ports: int
    up_ports: int
    down_ports: int
    overall_port_rate: float     # 端口在线率 %
    total_traffic_bps: float     # 全网总流量 bps
    avg_cpu_pct: float
    avg_mem_pct: float
    switches: List[SwitchOut] = []


class PingTargetOut(BaseModel):
    target: str          # IP 或主机名
    name: str            # 描述
    category: str        # "core" / "isp" / "peer" / "wan"
    rtt_min_ms: float
    rtt_avg_ms: float
    rtt_max_ms: float
    loss_pct: float      # 丢包率 %
    jitter_ms: float     # 抖动
    status: str           # "ok" / "lossy" / "down"


class PingOverviewOut(BaseModel):
    targets: List[PingTargetOut]
    avg_rtt_ms: float
    avg_loss_pct: float
    worst_rtt_target: str = ""


class BwUtilTopItem(BaseModel):
    rank: int
    name: str             # 端口/链路描述
    device: str           # 所属设备
    direction: str        # "in" / "out"
    util_pct: float       # 利用率 %
    traffic_bps: float    # 流量 bps
    capacity_mbps: int    # 端口速率 Mbps
    alert: bool = False   # >80% 高亮


class BwUtilOverviewOut(BaseModel):
    items: List[BwUtilTopItem]


# ---------- 多 DC 聚合 ----------
class DCCampus(BaseModel):
    id: str               # e.g. "ec1", "ec2"
    name: str             # e.g. "华东-杭州 EC1"
    short_name: str       # e.g. "EC1"
    region: str           # e.g. "华东"
    city: str             # e.g. "杭州"
    status: str           # "online" / "degraded" / "offline"
    total_devices: int
    online_devices: int
    online_rate: float
    pue: float
    wue: float = 0.0
    it_load_mw: float
    total_load_mw: float
    today_alarms: int
    availability: float = 99.999
    alerts_crit: int = 0
    alerts_warn: int = 0


class CampusComparison(BaseModel):
    metric: str           # "pue" / "online_rate" / "it_load_mw" / "total_load_mw" / "alarms"
    label: str            # 可读标签
    unit: str
    data: List[dict]      # [{"campus": "EC1", "value": 1.25}, ...]
    best: str             # 最优园区
    worst: str            # 最差园区
