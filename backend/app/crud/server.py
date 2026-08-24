"""物理服务器 / U 位识别 CRUD + 多源融合识别。

数据来源:
  - RFID / 资产标签实测: server 表 (DB 可用时) 或 mock_data.servers_for_cabinet (演示)
  - 电子工单 / 资产台账:   mock_data.ledger_for_cabinet (规划基准)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.server import Server
from app.schemas.server import RecognizeResp, UCell, UConflict, UPositionView
from app.services import mock_data


def _db_servers(db: Session, cabinet_id: int) -> Optional[list[dict]]:
    """优先读真实 server 表; 不可用时返回 None (调用方降级到 mock)。"""
    try:
        rows = db.execute(select(Server).where(Server.cabinet_id == cabinet_id)).scalars().all()
    except Exception:
        return None
    if not rows:
        return None
    return [
        {
            "id": s.id,
            "cabinet_id": s.cabinet_id,
            "asset_no": s.asset_no,
            "hostname": s.hostname,
            "ip": s.ip,
            "brand": s.brand,
            "model": s.model,
            "u_start": s.u_start,
            "u_end": s.u_end,
            "cpu_model": s.cpu_model,
            "cpu_count": s.cpu_count,
            "cpu_cores": s.cpu_cores,
            "memory_gb": s.memory_gb,
            "disk_desc": s.disk_desc,
            "business": s.business,
            "status": s.status,
            "source": "rfid",
        }
        for s in rows
    ]


def list_by_cabinet(db: Session, cabinet_id: int, u_total: int = 42) -> list[dict]:
    rows = _db_servers(db, cabinet_id)
    if rows is None:
        return mock_data.servers_for_cabinet(cabinet_id, u_total)
    return rows


def get(db: Session, server_id: int) -> Optional[Server]:
    return db.get(Server, server_id)


def create(db: Session, data: dict) -> Server:
    obj = Server(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, server_id: int, data: dict) -> Optional[Server]:
    obj = db.get(Server, server_id)
    if not obj:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, server_id: int) -> bool:
    obj = db.get(Server, server_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ----------------------------------------------------------------- 融合识别
def _cell(u: int) -> UCell:
    return UCell(u=u, status="empty", sources=[], device_refs=[], confidence=1.0, note="")


def build_cells(rfid: list[dict], ledger: list[dict], u_total: int) -> tuple[list[UCell], list[UConflict]]:
    """把 RFID 实测与工单台账对齐到 U 位立面, 产出 cells + conflicts。"""
    cells: list[UCell] = [_cell(u) for u in range(1, u_total + 1)]
    conflicts: list[UConflict] = []

    # RFID 实测落位
    for s in rfid:
        for u in range(s["u_start"], s["u_end"] + 1):
            if 1 <= u <= u_total:
                c = cells[u - 1]
                c.status = "occupied"
                c.sources.append("rfid")
                c.device_refs.append(s["id"])

    # 工单台账落位 + 交叉验证
    ledger_by_asset: dict[str, dict] = {}
    for s in ledger:
        ledger_by_asset.setdefault(s["asset_no"], s)
        for u in range(s["u_start"], s["u_end"] + 1):
            if 1 <= u <= u_total:
                c = cells[u - 1]
                if "ledger" not in c.sources:
                    c.sources.append("ledger")
                if s["id"] not in c.device_refs:
                    c.device_refs.append(s["id"])

    # 冲突 1: RFID 内部区间重叠
    occupied_ranges: list[tuple[int, int, str]] = []
    for s in rfid:
        for lo, hi, asset in occupied_ranges:
            if not (s["u_end"] < lo or s["u_start"] > hi):
                conflicts.append(
                    UConflict(
                        u=max(s["u_start"], lo),
                        type="range_overlap",
                        detail=f"RFID 实测区间重叠: {asset} 与 {s['asset_no']}",
                        asset_nos=[asset, s["asset_no"]],
                        severity="crit",
                    )
                )
        occupied_ranges.append((s["u_start"], s["u_end"], s["asset_no"]))

    # 冲突 2: 台账与实测不符 (同 asset_no 区间漂移)
    rfid_by_asset: dict[str, dict] = {s["asset_no"]: s for s in rfid}
    for asset, ls in ledger_by_asset.items():
        rs = rfid_by_asset.get(asset)
        if rs and (ls["u_start"] != rs["u_start"] or ls["u_end"] != rs["u_end"]):
            lo = max(ls["u_start"], rs["u_start"])
            hi = min(ls["u_end"], rs["u_end"])
            for u in range(max(1, lo), min(u_total, hi) + 1):
                cells[u - 1].status = "conflict"
            conflicts.append(
                UConflict(
                    u=ls["u_start"],
                    type="ledger_mismatch",
                    detail=(
                        f"台账规划 U{ls['u_start']}-{ls['u_end']} 与 RFID 实测 "
                        f"U{rs['u_start']}-{rs['u_end']} 不符: {asset}"
                    ),
                    asset_nos=[asset],
                    severity="warn",
                )
            )

    # 冲突 3: 台账多出的设备与现场已占 U 重叠
    rfid_set = {(u) for s in rfid for u in range(s["u_start"], s["u_end"] + 1)}
    for s in ledger:
        if s["asset_no"] not in rfid_by_asset:
            for u in range(s["u_start"], s["u_end"] + 1):
                if u in rfid_set and 1 <= u <= u_total:
                    cells[u - 1].status = "conflict"
                    conflicts.append(
                        UConflict(
                            u=u,
                            type="reservation_clash",
                            detail=f"台账登记设备 {s['asset_no']} 位于已占用 U{u}",
                            asset_nos=[s["asset_no"]],
                            severity="warn",
                        )
                    )

    # 置信度: 双源一致命中 -> 高; 仅单源 -> 中; 冲突 -> 低
    for c in cells:
        if c.status == "conflict":
            c.confidence = 0.4
        elif "rfid" in c.sources and "ledger" in c.sources:
            c.confidence = round(0.95, 2)
        elif c.status == "occupied":
            c.confidence = 0.8
        else:
            c.confidence = 1.0

    return cells, conflicts


def u_position(db: Session, cabinet_id: int, u_total: int = 42, code: str = "", room: str = "", row: str = "") -> UPositionView:
    rfid = list_by_cabinet(db, cabinet_id, u_total)
    ledger = mock_data.ledger_for_cabinet(cabinet_id, u_total)
    cells, conflicts = build_cells(rfid, ledger, u_total)
    occupied = sum(1 for c in cells if c.status in ("occupied", "conflict"))
    conflict_u = sum(1 for c in cells if c.status == "conflict")
    return UPositionView(
        cabinet_id=cabinet_id,
        code=code,
        room=room,
        row=row,
        u_total=u_total,
        cells=cells,
        conflicts=conflicts,
        occupied_u=occupied,
        empty_u=u_total - occupied,
        conflict_u=conflict_u,
        generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )


def recognize(db: Session, cabinet_id: int, u_total: int = 42, code: str = "", room: str = "") -> RecognizeResp:
    from datetime import datetime, timezone

    rfid = list_by_cabinet(db, cabinet_id, u_total)
    ledger = mock_data.ledger_for_cabinet(cabinet_id, u_total)
    cells, conflicts = build_cells(rfid, ledger, u_total)

    sources = [
        {
            "key": "ledger",
            "name": "电子工单 / 资产台账",
            "confidence": 0.92,
            "count": len(ledger),
        },
        {
            "key": "rfid",
            "name": "RFID / 资产标签",
            "confidence": 0.88,
            "count": len(rfid),
        },
    ]
    occupied = sum(1 for c in cells if c.status in ("occupied", "conflict"))
    conflict_u = sum(1 for c in cells if c.status == "conflict")
    conf_vals = [c.confidence for c in cells if c.status == "occupied"]
    avg_conf = round(sum(conf_vals) / len(conf_vals), 3) if conf_vals else 1.0

    return RecognizeResp(
        cabinet_id=cabinet_id,
        code=code,
        room=room,
        u_total=u_total,
        sources=sources,
        cells=cells,
        conflicts=conflicts,
        summary={
            "totalU": u_total,
            "occupied": occupied,
            "empty": u_total - occupied,
            "conflict": conflict_u,
            "avgConfidence": avg_conf,
            "ledgerCount": len(ledger),
            "rfidCount": len(rfid),
        },
        recognized_at=datetime.now(timezone.utc).isoformat(),
    )
