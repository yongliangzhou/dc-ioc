"""数据中心 (IDC) CRUD + 跨中心聚合 (phase: datacenter)。

- list/get/create/update/delete: 基础生命周期, 写操作保证 is_current 唯一。
- set_current: 清空其它中心的 is_current, 仅置目标为 True。
- compare: 复用 external_devices (按 idc_id 归属) + 告警引擎, 聚合各中心
  电力/制冷/机柜/设备/在线/告警指标, 供前端并排对比。
- unified_alarms: 将活跃告警按 device_id -> external_devices.idc_id 映射,
  汇总成统一告警视图 (含各中心告警数)。
返回 camelCase dict 供前端直接使用。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.external import ExternalDevice
from app.models.idc import IDC


def _to_dict(c: IDC) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "region": c.region,
        "address": c.address,
        "powerCapacityMw": c.power_capacity_mw,
        "coolingCapacityMw": c.cooling_capacity_mw,
        "rackCapacity": c.rack_capacity,
        "rooms": c.rooms,
        "status": c.status,
        "capacityKw": c.capacity_kw,
        "description": c.description,
        "isCurrent": c.is_current,
        "createdAt": c.created_at.isoformat() if c.created_at else "",
        "updatedAt": c.updated_at.isoformat() if c.updated_at else "",
    }


def list_idcs(db: Session, region: str = "", status: str = "",
              limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(IDC)
    if region:
        q = q.filter(IDC.region == region)
    if status:
        q = q.filter(IDC.status == status)
    q = q.order_by(IDC.id.asc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(c) for c in rows]


def get(db: Session, cid: int) -> Optional[dict]:
    c = db.query(IDC).filter(IDC.id == cid).first()
    return _to_dict(c) if c else None


def get_by_code(db: Session, code: str) -> Optional[dict]:
    c = db.query(IDC).filter(IDC.code == code).first()
    return _to_dict(c) if c else None


def get_current(db: Session) -> Optional[dict]:
    c = db.query(IDC).filter(IDC.is_current.is_(True)).order_by(IDC.id.asc()).first()
    return _to_dict(c) if c else (get(db, db.query(func.min(IDC.id)).scalar() or 0))


def create(db: Session, data: dict) -> dict:
    if get_by_code(db, data["code"]):
        raise ValueError(f"数据中心编码 '{data['code']}' 已存在")
    c = IDC(**data)
    db.add(c)
    db.flush()
    # 首个中心自动设为当前
    if not db.query(IDC).filter(IDC.is_current.is_(True)).first():
        c.is_current = True
    db.commit()
    db.refresh(c)
    return _to_dict(c)


def update(db: Session, cid: int, data: dict) -> Optional[dict]:
    c = db.query(IDC).filter(IDC.id == cid).first()
    if not c:
        return None
    code = data.get("code")
    if code and code != c.code and get_by_code(db, code):
        raise ValueError(f"数据中心编码 '{code}' 已存在")
    for k, v in data.items():
        if v is not None and hasattr(c, k):
            setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _to_dict(c)


def delete(db: Session, cid: int) -> bool:
    c = db.query(IDC).filter(IDC.id == cid).first()
    if not c:
        return False
    was_current = c.is_current
    db.delete(c)
    db.commit()
    # 若删掉的是当前中心, 自动把剩余最小 id 的中心设为当前
    if was_current:
        nxt = db.query(IDC).order_by(IDC.id.asc()).first()
        if nxt:
            nxt.is_current = True
            db.commit()
    return True


def set_current(db: Session, cid: int) -> Optional[dict]:
    c = db.query(IDC).filter(IDC.id == cid).first()
    if not c:
        return None
    db.query(IDC).update({IDC.is_current: False})
    c.is_current = True
    db.commit()
    db.refresh(c)
    return _to_dict(c)


def _device_stats_by_idc(db: Session) -> dict[int, dict]:
    """按 idc_id 聚合设备数与在线数 (last_seen 15 分钟内视为在线)。"""
    devs = (
        db.query(ExternalDevice.idc_id, ExternalDevice.last_seen)
        .filter(ExternalDevice.idc_id.isnot(None))
        .all()
    )
    stats: dict[int, dict] = {}
    cutoff = datetime.now().timestamp() - 15 * 60
    for idc_id, last_seen in devs:
        s = stats.setdefault(idc_id, {"device_count": 0, "online_count": 0})
        s["device_count"] += 1
        if last_seen is not None:
            ts = last_seen.timestamp() if hasattr(last_seen, "timestamp") else 0
            if ts >= cutoff:
                s["online_count"] += 1
    return stats


def compare(db: Session) -> dict:
    """跨中心对比: 聚合各中心电力/制冷/机柜/设备/在线/告警指标。"""
    from app.services import alarm_engine

    centers = db.query(IDC).order_by(IDC.id.asc()).all()
    dev_stats = _device_stats_by_idc(db)

    # 告警按 device_id -> idc_id 映射
    alarm_by_idc: dict[int, int] = {}
    dev_to_idc: dict[str, int] = {}
    devs = db.query(ExternalDevice.device_id, ExternalDevice.idc_id).filter(
        ExternalDevice.idc_id.isnot(None)
    ).all()
    for device_id, idc_id in devs:
        dev_to_idc[device_id] = idc_id
    for a in alarm_engine.get_active_alarms():
        did = a.get("device_id")
        idc_id = dev_to_idc.get(did) if did else None
        if idc_id is not None:
            alarm_by_idc[idc_id] = alarm_by_idc.get(idc_id, 0) + 1

    cur = get_current(db)
    out = []
    for c in centers:
        s = dev_stats.get(c.id, {"device_count": 0, "online_count": 0})
        # 机柜已用: 粗略以机柜容量与设备数无关, 这里以设备数/容量估算占位
        rack_used = min(c.rack_capacity, s["device_count"]) if c.rack_capacity else 0
        out.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "region": c.region,
            "status": c.status,
            "powerCapacityMw": c.power_capacity_mw,
            "coolingCapacityMw": c.cooling_capacity_mw,
            "rackCapacity": c.rack_capacity,
            "rackUsed": rack_used,
            "deviceCount": s["device_count"],
            "onlineCount": s["online_count"],
            "activeAlarmCount": alarm_by_idc.get(c.id, 0),
        })
    return {"centers": out, "currentIdcId": cur["id"] if cur else None}


def unified_alarms(db: Session) -> dict:
    """统一告警汇总: 活跃告警映射回归属数据中心。"""
    from app.services import alarm_engine

    dev_to_idc: dict[str, dict] = {}
    devs = db.query(
        ExternalDevice.device_id, ExternalDevice.idc_id,
        IDC.name, IDC.code,
    ).join(IDC, IDC.id == ExternalDevice.idc_id, isouter=True).filter(
        ExternalDevice.idc_id.isnot(None)
    ).all()
    for device_id, idc_id, idc_name, idc_code in devs:
        dev_to_idc[device_id] = {
            "idc_id": idc_id,
            "idc_name": idc_name,
            "idc_code": idc_code,
        }

    items = []
    by_idc: dict[int, int] = {}
    for a in alarm_engine.get_active_alarms():
        did = a.get("device_id")
        meta = dev_to_idc.get(did) if did else None
        if meta:
            idc_id = meta["idc_id"]
            by_idc[idc_id] = by_idc.get(idc_id, 0) + 1
            items.append({
                "idcId": idc_id,
                "idcName": meta["idc_name"],
                "idcCode": meta["idc_code"],
                "alarmId": a.get("alarm_id"),
                "deviceId": did,
                "category": a.get("category"),
                "metricName": a.get("metric_name"),
                "level": a.get("level", "warn"),
                "value": a.get("value"),
                "unit": a.get("unit"),
                "desc": a.get("desc") or f"{did} 告警",
                "state": a.get("ack_state", "待确认"),
                "ts": a.get("ts"),
            })
    # 无归属 idc 的告警也保留 (idcId=0) 以便前端提示
    by_idc[0] = sum(1 for a in alarm_engine.get_active_alarms()
                    if a.get("device_id") not in dev_to_idc)
    return {"total": len(items), "items": items, "byIdc": by_idc}
