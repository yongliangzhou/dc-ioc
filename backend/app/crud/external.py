"""外部设备接入 CRUD — 数据库持久化 (含内存兜底)。

设计要点:
- 与 app.schemas.external 的 Pydantic 契约对齐: 入参为 DeviceRegisterRequest / MetricPoint。
- 所有函数接收 `db: Session | None`: 传入真实会话走 ORM; 传 None 走内存兜底
  (后端未接数据库 / 联调阶段), 保证端点契约不变、前端始终有数据可展示。
- 视图模型统一为 schemas.external.ExternalDeviceView / MetricRecordView,
  DB 路径与内存路径返回完全一致的结构, 前端无需区分。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.external import ExternalDevice, MetricRaw
# [P2-8] 摄取指标 (计数 / 延迟). monitoring 不反向依赖本模块, 可安全导入。
from app.core import monitoring
from app.schemas.external import (
    DeviceRegisterRequest,
    DeviceUpdateRequest,
    ExternalDeviceView,
    MetricPoint,
    MetricQuality,
    MetricRecordView,
)

logger = logging.getLogger("external.crud")

# ---- 内存兜底存储 ----
_MEM_DEV: dict[str, dict] = {}          # device_id -> ExternalDeviceView 字典
_MEM_METRIC_CNT: dict[str, int] = {}    # device_id -> 累计测点数
_MEM_RECENT: dict[str, list[dict]] = {}  # device_id -> 最近测点环形缓冲 (供无 DB 时 recent_metrics)
_RECENT_CAP = 100
_MEM_MAX_METRICS = 200_000

# 实时缓存: 设备最新测点 (供 realtime 端点 / WS 实时推送, 避免每 push 查库)
_LATEST: dict[str, dict] = {}            # device_id -> {metric_name: {value,unit,quality,ts}}
_HISTORY: dict[tuple, list] = {}         # (device_id, metric_name) -> 历史环形缓冲
_HIST_CAP = 3000                         # 每测点最大保留点数

# 视为「在线」的阈值: 最近一次上报距现在 <= 该秒数
ONLINE_THRESHOLD_SEC = 5 * 60


def _quality_to_str(q: object) -> str:
    if isinstance(q, MetricQuality):
        return q.value
    return str(q) if q is not None else "good"


def _to_dt(value: str) -> datetime:
    """解析测点时间戳: ISO8601 (含 Z / 时区偏移) 或 Unix 秒。"""
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.fromtimestamp(float(s), tz=timezone.utc)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_device(
    db: Optional[Session], req: DeviceRegisterRequest
) -> tuple[ExternalDevice | None, str]:
    """注册 / 更新设备。返回 (ORM 对象 或 None(内存), 注册状态)。"""
    if db is None:
        existing = _MEM_DEV.get(req.device_id)
        if existing is None:
            status = "registered"
        else:
            status = (
                "updated"
                if (existing.get("ip") != req.ip or existing.get("sn") != req.sn or existing.get("model") != req.model)
                else "duplicate"
            )
        now = _now_iso()
        rec = existing or {
            "device_id": req.device_id,
            "registered_at": now,
            "last_seen": None,
        }
        rec.update(
            device_id=req.device_id,
            ip=req.ip,
            sn=req.sn,
            model=req.model,
            name=req.name,
            vendor=req.vendor,
            domain=req.domain,
            category=req.category,
            location=req.location,
            protocol=req.protocol,
            tags=list(req.tags or []),
            description=req.description,
            extra=dict(req.extra or {}),
        )
        _MEM_DEV[req.device_id] = rec
        return None, status

    obj = (
        db.query(ExternalDevice)
        .filter(ExternalDevice.device_id == req.device_id)
        .first()
    )
    status = "registered"
    if obj is not None:
        status = (
            "updated"
            if (obj.ip != req.ip or obj.sn != req.sn or obj.model != req.model)
            else "duplicate"
        )
    if obj is None:
        obj = ExternalDevice()
        db.add(obj)
    obj.device_id = req.device_id
    obj.ip = req.ip
    obj.sn = req.sn
    obj.model = req.model
    obj.name = req.name
    obj.vendor = req.vendor
    obj.domain = req.domain
    obj.category = req.category
    obj.location = req.location
    obj.protocol = req.protocol
    obj.tags = list(req.tags or [])
    obj.description = req.description
    obj.extra = dict(req.extra or {})
    db.flush()
    return obj, status


def update_device(
    db: Optional[Session], device_id: str, req: DeviceUpdateRequest
) -> tuple[Optional[ExternalDevice], bool]:
    """更新设备信息。返回 (ORM对象或None, 是否找到并更新)。"""
    if db is None:
        existing = _MEM_DEV.get(device_id)
        if existing is None:
            return None, False
        upd = req.model_dump(exclude_none=True, exclude_unset=True)
        for key, value in upd.items():
            existing[key] = value
        return None, True

    obj = db.query(ExternalDevice).filter(ExternalDevice.device_id == device_id).first()
    if obj is None:
        return None, False
    upd = req.model_dump(exclude_none=True, exclude_unset=True)
    for key, value in upd.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    db.flush()
    return obj, True


def delete_device(db: Optional[Session], device_id: str) -> bool:
    """删除设备及其测点数据。返回是否找到并删除。"""
    if db is None:
        existed = _MEM_DEV.pop(device_id, None) is not None
        _MEM_METRIC_CNT.pop(device_id, None)
        _MEM_RECENT.pop(device_id, None)
        return existed

    obj = db.query(ExternalDevice).filter(ExternalDevice.device_id == device_id).first()
    if obj is None:
        return False
    db.query(MetricRaw).filter(MetricRaw.device_id == device_id).delete()
    db.delete(obj)
    db.flush()
    return True


def bulk_insert_metrics(db: Optional[Session], points: list[MetricPoint]) -> int:
    """批量落库测点 (或内存缓冲), 同步刷新设备 last_seen 与测点计数。返回成功条数。"""
    if not points:
        return 0

    if db is None:
        for p in points:
            _MEM_METRIC_CNT[p.device_id] = _MEM_METRIC_CNT.get(p.device_id, 0) + 1
            rec = _MEM_DEV.get(p.device_id)
            if rec is not None:
                rec["last_seen"] = _now_iso()
            # 写入最近测点环形缓冲 (供无 DB 时 recent_metrics 查询)
            buf = _MEM_RECENT.setdefault(p.device_id, [])
            buf.append({
                "device_id": p.device_id,
                "ts": _to_dt(p.timestamp).isoformat() if p.timestamp else None,
                "metric_name": p.metric_name,
                "value": float(p.value),
                "quality": _quality_to_str(p.quality),
                "unit": p.unit,
                "received_at": _now_iso(),
            })
            if len(buf) > _RECENT_CAP:
                del buf[: len(buf) - _RECENT_CAP]
            ts_iso = _to_dt(p.timestamp).isoformat() if p.timestamp else _now_iso()
            _cache_point(p.device_id, p.metric_name, float(p.value),
                         _quality_to_str(p.quality), p.unit, ts_iso)
        if sum(_MEM_METRIC_CNT.values()) > _MEM_MAX_METRICS:
            logger.warning("内存测点缓冲超过上限, 仅保留计数统计")
        # [P2-8] 摄取计数 (无 DB 模式也统计, rate() 得摄取 QPS)
        monitoring.external_points_ingested.inc(len(points))
        return len(points)

    rows = []
    last_seen: dict[str, datetime] = {}
    for p in points:
        ts = _to_dt(p.timestamp)
        rows.append({
            "device_id": p.device_id,
            "ts": ts,
            "metric_name": p.metric_name,
            "value": float(p.value),
            "quality": _quality_to_str(p.quality),
            "unit": p.unit,
            "tags": dict(p.tags or {}),
        })
        if p.device_id not in last_seen or ts > last_seen[p.device_id]:
            last_seen[p.device_id] = ts
        # 内存缓存始终按最新报值更新 (即便该 (device,metric,ts) 已落库, 覆盖即可)
        _cache_point(p.device_id, p.metric_name, float(p.value),
                     _quality_to_str(p.quality), p.unit, ts.isoformat())

    import time

    _t0 = time.perf_counter()
    try:
        # [P1-4 FIX] 幂等去重: 以 (device_id, metric_name, ts) 唯一键兜底,
        # 即便上游 (Kafka at-least-once / 采集器重发) 重投也不产生重复落库。
        dialect = "postgresql"
        try:
            bind = db.get_bind()
            if bind is not None:
                dialect = bind.dialect.name
        except Exception:  # noqa: BLE001
            pass

        if dialect == "postgresql":
            stmt = pg_insert(MetricRaw).values(rows)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["device_id", "metric_name", "ts"]
            )
            # RETURNING id 仅返回实际插入的行; 被唯一键跳过的重复行不返回 -> 得到真实插入数
            result = db.execute(stmt.returning(MetricRaw.id))
            saved = len(result.fetchall())
            db.flush()
        else:
            # 非 Postgres (如本地 sqlite 自测) 退化为普通批量插入
            db.add_all([MetricRaw(**r) for r in rows])
            db.flush()
            saved = len(rows)

        # 更新设备最近活跃时间 (内存计数 + 落库)
        for device_id, ts in last_seen.items():
            db.query(ExternalDevice).filter(
                ExternalDevice.device_id == device_id
            ).update({ExternalDevice.last_seen: ts})
        # [P2-8] 摄取计数 (按接收条数, rate() 得摄取 QPS) + 写入延迟分布
        monitoring.external_points_ingested.inc(len(rows))
        monitoring.external_ingest_latency.observe(time.perf_counter() - _t0)
        return saved
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("批量写入 MetricRaw 失败: %s", e)
        return 0


def list_devices(
    db: Optional[Session],
    *,
    domain: Optional[str] = None,
    protocol: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    with_metric_count: bool = True,
) -> tuple[list[ExternalDeviceView], int, int, int]:
    """返回 (设备视图列表, 总数, 在线数, 离线数)。

    with_metric_count=False 时跳过对 metric_raw 的 group_by 统计 (该查询在大数据量下极慢),
    仅在聚合注入等内部场景使用; 外部设备列表接口默认 True。
    """
    if db is None:
        items = [ExternalDeviceView(**v) for v in _MEM_DEV.values()]
        return _filter_and_count(items, domain, protocol, skip, limit, with_metric_count)

    q = db.query(ExternalDevice)
    if domain:
        q = q.filter(ExternalDevice.domain == domain)
    if protocol:
        q = q.filter(ExternalDevice.protocol == protocol)
    total = q.count()
    rows = q.order_by(ExternalDevice.id.desc()).offset(skip).limit(limit).all()

    ids = [r.device_id for r in rows]
    cnt_map = {}
    if ids and with_metric_count:
        cnt_q = (
            db.query(MetricRaw.device_id, func.count().label("c"))
            .filter(MetricRaw.device_id.in_(ids))
            .group_by(MetricRaw.device_id)
        )
        cnt_map = {d: c for d, c in cnt_q.all()}

    items: list[ExternalDeviceView] = []
    online = offline = 0
    now = datetime.now(timezone.utc)
    for r in rows:
        seen = r.last_seen
        is_online = (
            seen is not None
            and (now - seen).total_seconds() <= ONLINE_THRESHOLD_SEC
        )
        items.append(
            ExternalDeviceView(
                device_id=r.device_id,
                ip=r.ip,
                sn=r.sn,
                model=r.model,
                name=r.name,
                vendor=r.vendor,
                domain=r.domain,
                category=r.category,
                location=r.location,
                protocol=r.protocol,
                tags=list(r.tags or []),
                description=r.description,
                extra=dict(r.extra or {}),
                registered_at=r.created_at.isoformat() if r.created_at else None,
                last_seen=r.last_seen.isoformat() if r.last_seen else None,
                metric_count=cnt_map.get(r.device_id, 0),
                online=is_online,
            )
        )
        if is_online:
            online += 1
        else:
            offline += 1
    return items, total, online, offline


def get_device_by_id(db: Optional[Session], device_id_int: int):
    """按整数主键 id 取 ExternalDevice ORM 行 (供台账详情/指标映射, B2)。无 DB 时返回 None。"""
    if db is None:
        return None
    return db.query(ExternalDevice).filter(ExternalDevice.id == device_id_int).first()


def _filter_and_count(
    items: list[ExternalDeviceView],
    domain: Optional[str],
    protocol: Optional[str],
    skip: int,
    limit: int,
    with_metric_count: bool = True,
):
    if domain:
        items = [i for i in items if i.domain == domain]
    if protocol:
        items = [i for i in items if i.protocol == protocol]
    now = datetime.now(timezone.utc)
    online = offline = 0
    for i in items:
        if i.last_seen:
            try:
                seen = datetime.fromisoformat(i.last_seen)
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=timezone.utc)
                is_online = (now - seen).total_seconds() <= ONLINE_THRESHOLD_SEC
            except ValueError:
                is_online = False
        else:
            is_online = False
        i.online = is_online
        if is_online:
            online += 1
        else:
            offline += 1
        if with_metric_count:
            i.metric_count = _MEM_METRIC_CNT.get(i.device_id, 0)
    total = len(items)
    page = items[skip : skip + limit]
    return page, total, online, offline


def recent_metrics(
    db: Optional[Session], device_id: str, limit: int = 50
) -> list[MetricRecordView]:
    """某设备最近测点 (按接收时间倒序)。"""
    if db is None:
        buf = _MEM_RECENT.get(device_id, [])
        items = sorted(buf, key=lambda r: r.get("received_at") or "", reverse=True)[:limit]
        return [MetricRecordView(**r) for r in items]
    rows = (
        db.query(MetricRaw)
        .filter(MetricRaw.device_id == device_id)
        .order_by(MetricRaw.received_at.desc())
        .limit(limit)
        .all()
    )
    return [
        MetricRecordView(
            device_id=r.device_id,
            ts=r.ts.isoformat() if r.ts else None,
            metric_name=r.metric_name,
            value=r.value,
            quality=r.quality,
            unit=r.unit,
            received_at=r.received_at.isoformat() if r.received_at else None,
        )
        for r in rows
    ]


def total_metric_count(db: Optional[Session]) -> int:
    if db is None:
        return sum(_MEM_METRIC_CNT.values())
    return db.query(func.count(MetricRaw.id)).scalar() or 0


def delete_old_metrics(db: Session, older_than: datetime, batch_size: int = 50000) -> int:
    """按存储引擎分层清理 ts 早于 older_than 的过期测点 (P0-1 修复)。

    分派依据 metric_agg._detect(db)["mode"]:
      - timescale: 走 drop_chunks 整块丢弃超期 chunk (级联连续聚合), 避免逐行
        DELETE 的索引维护开销; drop_chunks 为独立事务, 内部自行 commit。
      - plain / none: 分批 DELETE, [P0-1 FIX] 每批 commit 一次 (消除原实现只
        flush() 不 commit() 导致的长事务锁表风险); 全部批次完成后 refresh_views
        使物化视图与保留窗口重新对齐 (原实现依赖下次 refresh 周期 -> 窗口错位,
        历史查询会读到已被 retention 删除的区间)。

    由 lifespan 的 metric_retention_loop 周期调用。
    """
    if db is None:
        return 0
    try:
        from app.services import metric_agg
        mode = metric_agg._detect(db).get("mode")
    except Exception:  # noqa: BLE001
        mode = "plain"

    # [P2-8] 保留清理单次调用耗时分布
    import time as _time

    _t0 = _time.perf_counter()
    if mode == "timescale":
        deleted = _delete_old_metrics_timescale(db, older_than)
    else:
        deleted = _delete_old_metrics_plain(db, older_than, batch_size)
    monitoring.metric_retention_duration.observe(_time.perf_counter() - _t0)
    return deleted


def _delete_old_metrics_timescale(db: Session, older_than: datetime) -> int:
    """TimescaleDB: drop_chunks 整块丢弃超期 chunk, 级联清理连续聚合。

    返回被丢弃的 chunk 数; drop_chunks 失败则回退分批 DELETE。
    """
    try:
        # [P2-8] 保留清理删除条数 (drop_chunks 只返回 chunk 数, 先预估实际行数用于指标)
        row_count = db.execute(
            text("SELECT count(*) FROM metric_raws WHERE ts < :cutoff"),
            {"cutoff": older_than},
        ).scalar() or 0
        rows = db.execute(
            text(
                "SELECT drop_chunks(relation => 'metric_raws', "
                "older_than => :cutoff, cascade_to_materializations => true)"
            ),
            {"cutoff": older_than},
        ).fetchall()
        db.commit()
        dropped = len(rows)
        # [P2-8] 累计保留清理删除的测点行数
        monitoring.metric_retention_deleted.inc(row_count)
        logger.info(
            "[metric_retention] TimescaleDB drop_chunks 早于 %s, 丢弃 chunk %d 块 (约 %d 行)",
            older_than, dropped, row_count,
        )
        return dropped
    except Exception as e:  # noqa: BLE001
        logger.warning("[metric_retention] drop_chunks 失败, 回退分批 DELETE: %s", e)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return _delete_old_metrics_plain(db, older_than, 50000)


def _delete_old_metrics_plain(db: Session, older_than: datetime, batch_size: int) -> int:
    """普通 PostgreSQL: 分批 DELETE, 每批独立提交; 完成后刷新物化视图。

    [P0-1 FIX] 原实现只 flush() 不 commit(), 所有批次处于同一长事务 -> 锁表风险,
    现每批单独 commit。plain 物化视图需在删除后 REFRESH 以与保留窗口对齐。
    """
    total = 0
    while True:
        res = db.execute(
            text(
                "DELETE FROM metric_raws WHERE id IN ("
                "SELECT id FROM metric_raws WHERE ts < :cutoff LIMIT :batch)"
            ),
            {"cutoff": older_than, "batch": batch_size},
        )
        n = res.rowcount or 0
        db.commit()  # [P0-1 FIX] 每批提交, 避免长事务锁表
        total += n
        if n < batch_size:
            break
    # 删除完成后刷新物化视图, 使聚合与保留窗口重新对齐 (解决窗口错位)
    try:
        from app.services import metric_agg
        metric_agg.refresh_views(db)
    except Exception as e:  # noqa: BLE001
        logger.warning("[metric_retention] 物化视图刷新失败 (删除已完成): %s", e)
    # [P2-8] 累计保留清理删除的测点行数
    monitoring.metric_retention_deleted.inc(total)
    return total


# ---- 实时缓存与历史查询 (物模型驱动可视化) ----
def _cache_point(device_id: str, metric_name: str, value: float, quality: str, unit, ts_iso: str) -> None:
    """写入实时缓存与历史环形缓冲 (无论是否落库均维护, 保证无 DB 时趋势可用)。"""
    _LATEST.setdefault(device_id, {})[metric_name] = {
        "value": value, "unit": unit, "quality": quality, "ts": ts_iso,
    }
    key = (device_id, metric_name)
    buf = _HISTORY.setdefault(key, [])
    buf.append({"ts": ts_iso, "value": value, "quality": quality})
    if len(buf) > _HIST_CAP:
        del buf[: len(buf) - _HIST_CAP]


def _downsample(points: list, limit: int) -> list:
    """等间隔降采样到 limit 个点。"""
    if not points or len(points) <= limit:
        return points
    step = len(points) / limit
    return [points[int(i * step)] for i in range(limit)]


def latest_metrics(device_id: str) -> dict:
    """返回设备最新测点缓存 {metric_name: {value,unit,quality,ts}}。"""
    return dict(_LATEST.get(device_id, {}))


def is_online(device_id: str, threshold_sec: int = ONLINE_THRESHOLD_SEC) -> bool:
    """依据实时缓存最近时间戳判定在线。"""
    latest = _LATEST.get(device_id)
    if not latest:
        return False
    try:
        last = max(_to_dt(v["ts"]) for v in latest.values() if v.get("ts"))
    except Exception:
        return False
    return (datetime.now(timezone.utc) - last).total_seconds() <= threshold_sec


def query_history(
    db: Optional[Session],
    device_id: str,
    metrics: list[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 500,
) -> tuple[dict, dict]:
    """查询某设备历史测点, 返回 (series, unit_map)。

    - db 为 None: 从内存环形缓冲取 (开发/无 DB 联调场景)
    - db 可用 + 长跨度: 优先命中预聚合视图 (TimescaleDB 连续聚合 / 普通物化视图),
      避免全量扫描 metric_raws; 短跨度或聚合不可用时回退原始表
    """
    unit_map: dict[str, str] = {}
    start_dt = _to_dt(start) if start else None
    end_dt = _to_dt(end) if end else None

    if db is None:
        series: dict[str, list] = {}
        for m in metrics:
            buf = _HISTORY.get((device_id, m), [])
            pts = buf
            if start_dt or end_dt:
                pts = [
                    p for p in buf
                    if (start_dt is None or _to_dt(p["ts"]) >= start_dt)
                    and (end_dt is None or _to_dt(p["ts"]) <= end_dt)
                ]
            series[m] = _downsample(pts, limit)
            lc = _LATEST.get(device_id, {}).get(m)
            if lc and lc.get("unit"):
                unit_map[m] = lc["unit"]
        return series, unit_map

    # 长跨度查询优先走预聚合视图 (行数少 1~2 个数量级)
    try:
        from app.services import metric_agg
        agg_result = metric_agg.query_history_agg(db, device_id, metrics, start_dt, end_dt, limit)
        if agg_result is not None and agg_result[0]:
            return agg_result
    except Exception:  # noqa: BLE001
        pass  # 聚合路径异常不影响原始表兜底

    q = db.query(MetricRaw).filter(MetricRaw.device_id == device_id)
    if metrics:
        q = q.filter(MetricRaw.metric_name.in_(metrics))
    if start_dt:
        q = q.filter(MetricRaw.ts >= start_dt)
    if end_dt:
        q = q.filter(MetricRaw.ts <= end_dt)
    rows = q.order_by(MetricRaw.ts.asc()).limit(20000).all()

    grouped: dict[str, list] = {}
    for r in rows:
        if r.metric_name not in unit_map:
            unit_map[r.metric_name] = r.unit or ""
        grouped.setdefault(r.metric_name, []).append({
            "ts": r.ts.isoformat() if r.ts else None,
            "value": r.value,
            "quality": r.quality,
        })
    for m in list(grouped.keys()):
        grouped[m] = _downsample(grouped[m], limit)
    return grouped, unit_map
