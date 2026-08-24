"""租户 CRUD (阶段三 A · 资源运营-租户管理)。

前端以 camelCase 提交, 模型以 snake_case 存储, 故统一用 _to_snake 转换。
返回统一转成 camelCase dict 供前端直接使用。
资源用量明细与超阈值预警由 _derive_status 在返回时计算 (不持久化派生状态)。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tenant import Tenant

# 超阈值预警比例 (用量 / 配额 >= 该比例 视为预警)
WARN_RATIO = 0.8


def _to_snake(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def _derive_status(t: Tenant) -> str:
    """根据配额与用量派生健康状态: 超限 / 预警 / 正常。"""
    over = False
    warn = False
    # 机柜
    if t.quotaCabinets:
        r = (t.cabinets or 0) / t.quotaCabinets
        over = over or r >= 1
        warn = warn or r >= WARN_RATIO
    # 设备
    if t.quotaDevices:
        r = (t.usedDevices or 0) / t.quotaDevices
        over = over or r >= 1
        warn = warn or r >= WARN_RATIO
    # 功耗
    if t.quotaPowerKw:
        r = (t.usedPowerKw or 0) / t.quotaPowerKw
        over = over or r >= 1
        warn = warn or r >= WARN_RATIO
    # 带宽
    if t.quotaBandwidthMbps:
        r = (t.usedBandwidthMbps or 0) / t.quotaBandwidthMbps
        over = over or r >= 1
        warn = warn or r >= WARN_RATIO
    if over:
        return "over"
    if warn:
        return "warn"
    return "normal"


def _to_dict(r: Tenant) -> dict:
    return {
        "id": r.id, "name": r.name, "code": r.code, "contact": r.contact,
        "phone": r.phone, "industry": r.industry, "contractNo": r.contractNo,
        "validFrom": r.validFrom, "validTo": r.validTo, "status": r.status,
        "rent": r.rent, "cabinets": r.cabinets,
        "quotaCabinets": r.quotaCabinets, "quotaDevices": r.quotaDevices,
        "quotaPowerKw": r.quotaPowerKw, "quotaBandwidthMbps": r.quotaBandwidthMbps,
        "usedDevices": r.usedDevices, "usedPowerKw": r.usedPowerKw,
        "usedBandwidthMbps": r.usedBandwidthMbps, "uOccupied": r.uOccupied,
        "note": r.note,
        # 派生健康状态 (前端用于高亮告警)
        "health": _derive_status(r),
    }


def count(db: Session, kw: str = "", status: str = "") -> int:
    q = db.query(func.count(Tenant.id))
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            Tenant.name.ilike(like)
            | Tenant.code.ilike(like)
            | Tenant.contact.ilike(like)
        )
    if status:
        q = q.filter(Tenant.status == status)
    return q.scalar() or 0


def list_tenants(db: Session, kw: str = "", status: str = "",
                 limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.query(Tenant)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            Tenant.name.ilike(like)
            | Tenant.code.ilike(like)
            | Tenant.contact.ilike(like)
        )
    if status:
        q = q.filter(Tenant.status == status)
    q = q.order_by(Tenant.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def get(db: Session, tid: int) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.id == tid).first()


def create(db: Session, data: dict) -> dict:
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    cnt = db.query(func.count(Tenant.id)).scalar() or 0
    if not data.get("code"):
        data["code"] = f"TH-{cnt + 1:03d}"
    obj = Tenant(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def update(db: Session, tid: int, data: dict) -> Optional[dict]:
    obj = get(db, tid)
    if not obj:
        return None
    data = {k: v for k, v in _to_snake(data).items() if v is not None}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


def delete(db: Session, tid: int) -> bool:
    obj = get(db, tid)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def stats(db: Session) -> dict:
    """租户级统计汇总 (顶部统计卡真实聚合)。"""
    rows = db.query(Tenant).all()
    total = len(rows)
    active = sum(1 for r in rows if r.status == "active")
    total_cabinets = sum(r.cabinets or 0 for r in rows)
    total_power = round(sum(r.usedPowerKw or 0 for r in rows), 1)
    # 超阈值 / 预警租户数
    warn_count = 0
    over_count = 0
    for r in rows:
        h = _derive_status(r)
        if h == "over":
            over_count += 1
        elif h == "warn":
            warn_count += 1
    return {
        "total": total,
        "active": active,
        "totalCabinets": total_cabinets,
        "totalPowerKw": total_power,
        "warnCount": warn_count,
        "overCount": over_count,
    }
