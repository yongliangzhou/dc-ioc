"""统一设备台账模型 — 按参考课程文件的业务单元建模。

domain / category 取值对照 (阿里云数据中心弱电课程):
- hvac_source  暖通冷源: chiller冷水机组 / cooling_tower冷却塔 / chw_pump冷冻泵 / cw_pump冷却泵
                sec_pump二次泵 / hex板式换热器 / storage_tank蓄冷罐 / valve电动阀门 / dosing加药旁流
- hvac_terminal暖通末端: crac精密空调 / fau新风机组 / humidifier恒湿一体机 / leak_detector漏水检测
- power_hv     10KV中压: hv_incomer进线柜 / hv_isolator隔离柜 / hv_breaker断路器柜 / hv_pt PT柜
                hv_metering计量柜 / hv_feeder馈线柜 / bus_tie母联柜(备自投)
- power_lv     0.4KV低压: transformer变压器 / ups UPS / hvdc高压直流 / ats自动切换 / lv_feeder馈线
- power_genset 柴发并机: genset柴油发电机 / parallel_ctrl并机控制柜 / earthing_res接地电阻柜
- power_fuel   燃油系统: fuel_tank油罐 / day_tank日用油箱 / fuel_pump供回油泵 / shutoff_valve紧急切断阀
- power_batt   电池监控: battery_group电池组 / ta_module TA采集 / tc_module TC采集 / converge收敛模块
- sec_cctv     视频监控: camera枪机球机 / nvr录像主机 / matrix控制矩阵
- sec_acs      门禁:     door_ctrl门禁主机 / reader读卡器 / face_terminal人脸终端
- sec_ids      防入侵:   fence电子围栏 / vibration_fiber振动光纤 / ir_detector红外
- sec_fire     消防:     smoke_detector感烟 / heat_detector感温 / vesda极早期 / gas_panel气灭盘
                manual_call手报 / sounder声光 / qiefei_module切非模块 / emergency_light应急照明
"""
from sqlalchemy import String, Float, Integer, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class Equipment(Base, TimestampMixin):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    idc_id: Mapped[int] = mapped_column(ForeignKey("idc.id", ondelete="CASCADE"), nullable=False)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("room.id", ondelete="SET NULL"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="设备编码 CH-01/DG-01/CRAC-08")
    name: Mapped[str] = mapped_column(String(128), default="")
    domain: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="业务域(见模块注释)")
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="设备类别")
    vendor: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    # 运行状态: 运行/待机/备用/检修/维保/故障/合闸/分闸/浮充...
    status: Mapped[str] = mapped_column(String(16), default="运行", index=True)
    load_pct: Mapped[float] = mapped_column(Float, default=0, comment="负载率%")
    run_hours: Mapped[int] = mapped_column(Integer, default=0)
    redundancy: Mapped[str] = mapped_column(String(16), default="", comment="N+1/2N/主备")
    # 异构参数 (COP/频率/液位/SOC/电压等按类别存放, 与参考文件各业务单元测点对应)
    attrs: Mapped[dict] = mapped_column(JSON, default=dict, comment="类别专属参数")

    __table_args__ = (
        Index("uq_equipment_idc_code", "idc_id", "code", unique=True),
        Index("ix_equipment_domain_cat", "domain", "category"),
        Index("ix_equipment_room", "room_id"),
        {"comment": "统一设备台账(按课程业务单元)"},
    )
