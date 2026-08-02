"""5.3.2 种子脚本(二): 演示数据 (仅非生产环境)。

灌入轻量演示数据, 便于本地/演示环境快速看到拓扑与知识库:
  - 1 个 IDC -> 2 机房 -> 若干机柜/服务器
  - 2 台设备 (暖通/电力)
  - 3 条知识库处置预案

运行: python seed_demo.py [--force]
  --force: 清空已有演示数据后重建
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.equipment import Equipment
from app.models.idc import Idc, Room, Cabinet, Server
from app.models.knowledge import KnowledgeItem

DEMO_IDC_NAME = "演示数据中心 A"


def _seed_idc(db):
    existing = db.execute(select(Idc).where(Idc.name == DEMO_IDC_NAME)).scalar_one_or_none()
    if existing:
        return existing
    idc = Idc(name=DEMO_IDC_NAME, location="上海", status="running", capacity_kw=2000)
    db.add(idc)
    db.commit()
    db.refresh(idc)

    rooms = []
    for i, rname in enumerate(["主机房 1", "动力机房"], start=1):
        room = Room(idc_id=idc.id, name=rname, purpose="IT" if i == 1 else "动力", area_m2=300)
        db.add(room)
        rooms.append(room)
    db.commit()
    for r in rooms:
        for c in range(1, 4):
            cab = Cabinet(room_id=r.id, code=f"{r.name[:2]}-C{c:02d}", status="on", u_height=42)
            db.add(cab)
            db.commit()
            db.refresh(cab)
            srv = Server(
                cabinet_id=cab.id,
                hostname=f"srv-{r.id}-{c:02d}",
                asset_no=f"AS{r.id}{c:03d}",
                status="running",
                ip=f"10.0.{r.id}.{c}",
            )
            db.add(srv)
    db.commit()
    return idc


def _seed_equipment(db):
    if db.execute(select(Equipment).where(Equipment.name == "演示冷水机组")).scalar_one_or_none():
        return
    eqs = [
        Equipment(name="演示冷水机组", category="hvac", model="CVHF-500", location="动力机房", status="running"),
        Equipment(name="演示 UPS", category="power", model="UPS-200k", location="动力机房", status="running"),
    ]
    db.add_all(eqs)
    db.commit()


def _seed_knowledge(db):
    if db.execute(select(KnowledgeItem).where(KnowledgeItem.code == "KB-9001")).scalar_one_or_none():
        return
    items = [
        KnowledgeItem(
            code="KB-9001", title="冷水机组高压报警处置", category="暖通空调", domain="hvac_source",
            type="manual", tags="冷水机组,高压", related_domains="hvac_source",
            summary="冷水机组高压报警的标准处置流程。", hot=1, version=1,
            content="1.检查冷却水流量;2.确认冷凝器脏堵;3.复位机组。",
            steps="['检查流量','确认脏堵','复位']",
        ),
        KnowledgeItem(
            code="KB-9002", title="UPS 旁路切换预案", category="供配电", domain="power_dist",
            type="manual", tags="UPS,旁路", related_domains="power_dist",
            summary="UPS 旁路切换操作步骤与风险点。", hot=1, version=1,
            content="1.确认负载;2.切旁路;3.观察电压。",
            steps="['确认负载','切旁路','观察电压']",
        ),
        KnowledgeItem(
            code="KB-9003", title="机房温湿度异常排查", category="环境", domain="env",
            type="manual", tags="温湿度", related_domains="env",
            summary="机房温湿度越限的排查清单。", hot=0, version=1,
            content="1.查空调;2.查气流;3.查传感器。",
            steps="['查空调','查气流','查传感器']",
        ),
    ]
    db.add_all(items)
    db.commit()


def seed(force: bool = False):
    db = SessionLocal()
    try:
        if force:
            db.query(Server).delete()
            db.query(Cabinet).delete()
            db.query(Room).delete()
            db.query(Idc).where(Idc.name == DEMO_IDC_NAME).delete()
            db.query(Equipment).where(Equipment.name.like("演示%")).delete()
            db.query(KnowledgeItem).where(KnowledgeItem.code.like("KB-900%")).delete()
            db.commit()
            print("force: cleared previous demo data")
        _seed_idc(db)
        _seed_equipment(db)
        _seed_knowledge(db)
        print("seed_demo done.")
    finally:
        db.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    seed(force=force)
