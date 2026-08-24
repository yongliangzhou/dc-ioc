"""测点历史聚合查询服务 (TimescaleDB 连续聚合 / 普通物化视图 双路径)。

目标: 长时间跨度的历史趋势查询不再全量扫描 metric_raws 原始表, 而是命中
预聚合视图, 行数减少 1~2 个数量级。

三级路径 (启动时探测一次, 结果缓存):
  1. TimescaleDB 已启用且 005 脚本建好连续聚合 -> 直接查 metric_raws_5min / metric_raws_1h
     (刷新由 add_continuous_aggregate_policy 托管, 应用无需刷新)
  2. 普通 PostgreSQL -> 自动创建物化视图 metric_agg_5min / metric_agg_1h
     (epoch 取整分桶), 由后台循环周期 REFRESH MATERIALIZED VIEW CONCURRENTLY
  3. 其它方言 (SQLite 等) / 探测失败 -> 返回 None, 调用方回退原始表查询

选择策略 (query_history 调用):
  跨度 > 48h  -> 1h 桶
  跨度 > 3h   -> 5min 桶
  其余 / 未给定跨度 -> 原始表 (保持最高精度)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("metric_agg")

# 探测结果缓存: None=未探测; dict(mode, view_5min, view_1h)
_CAP: Optional[dict] = None

_PLAIN_5MIN = "metric_agg_5min"
_PLAIN_1H = "metric_agg_1h"

_CREATE_PLAIN_5MIN = f"""
CREATE MATERIALIZED VIEW IF NOT EXISTS {_PLAIN_5MIN} AS
SELECT to_timestamp(floor(extract(epoch FROM ts) / 300) * 300) AS bucket,
       device_id, metric_name,
       avg(value)  AS avg_value,
       max(value)  AS max_value,
       min(value)  AS min_value,
       count(*)    AS samples,
       max(unit)   AS unit
FROM metric_raws
GROUP BY 1, 2, 3
"""

_CREATE_PLAIN_1H = f"""
CREATE MATERIALIZED VIEW IF NOT EXISTS {_PLAIN_1H} AS
SELECT to_timestamp(floor(extract(epoch FROM ts) / 3600) * 3600) AS bucket,
       device_id, metric_name,
       avg(value)  AS avg_value,
       max(value)  AS max_value,
       min(value)  AS min_value,
       count(*)    AS samples,
       max(unit)   AS unit
FROM metric_raws
GROUP BY 1, 2, 3
"""


def _detect(db: Session) -> dict:
    """探测可用的聚合路径 (幂等, 失败降级 none)。"""
    global _CAP
    if _CAP is not None:
        return _CAP

    cap = {"mode": "none", "view_5min": None, "view_1h": None}
    try:
        if db.get_bind().dialect.name != "postgresql":
            _CAP = cap
            return cap

        # 路径 1: TimescaleDB 连续聚合 (005 脚本)
        has_cagg = db.execute(text(
            "SELECT count(*) FROM pg_matviews WHERE matviewname IN ('metric_raws_5min','metric_raws_1h')"
        )).scalar() or 0
        if has_cagg >= 2:
            cap = {"mode": "timescale", "view_5min": "metric_raws_5min", "view_1h": "metric_raws_1h"}
            _CAP = cap
            logger.info("[metric_agg] 使用 TimescaleDB 连续聚合视图")
            return cap

        # 路径 2: 普通物化视图 (不存在则创建; CONCURRENTLY 刷新需唯一索引)
        db.execute(text(_CREATE_PLAIN_5MIN))
        db.execute(text(_CREATE_PLAIN_1H))
        db.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{_PLAIN_5MIN} "
            f"ON {_PLAIN_5MIN} (device_id, metric_name, bucket)"
        ))
        db.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{_PLAIN_1H} "
            f"ON {_PLAIN_1H} (device_id, metric_name, bucket)"
        ))
        db.commit()
        cap = {"mode": "plain", "view_5min": _PLAIN_5MIN, "view_1h": _PLAIN_1H}
        _CAP = cap
        logger.info("[metric_agg] 已就绪普通物化视图 %s / %s", _PLAIN_5MIN, _PLAIN_1H)
        return cap
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.warning("[metric_agg] 聚合视图不可用, 回退原始表: %s", e)
        _CAP = cap
        return cap


def pick_bucket(start_dt: Optional[datetime], end_dt: Optional[datetime]) -> Optional[str]:
    """按查询跨度选择聚合粒度; 返回 '1h' / '5min' / None(用原始表)。"""
    if start_dt is None:
        return None
    end = end_dt or datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    span = end - start_dt
    if span > timedelta(hours=48):
        return "1h"
    if span > timedelta(hours=3):
        return "5min"
    return None


def query_history_agg(
    db: Session,
    device_id: str,
    metrics: list[str],
    start_dt: Optional[datetime],
    end_dt: Optional[datetime],
    limit: int = 500,
) -> Optional[tuple[dict, dict]]:
    """走聚合视图查询历史; 不适用/失败返回 None (调用方回退原始表)。"""
    bucket = pick_bucket(start_dt, end_dt)
    if bucket is None:
        return None
    cap = _detect(db)
    if cap["mode"] == "none":
        return None
    view = cap["view_1h"] if bucket == "1h" else cap["view_5min"]

    try:
        sql = (
            "SELECT bucket, metric_name, avg_value, max_value, min_value, samples"  # noqa: S608
            + (", unit" if cap["mode"] == "plain" else "")
            + f" FROM {view} WHERE device_id = :dev"
        )
        params: dict = {"dev": device_id}
        if metrics:
            sql += " AND metric_name = ANY(:names)"
            params["names"] = metrics
        if start_dt is not None:
            sql += " AND bucket >= :start"
            params["start"] = start_dt
        if end_dt is not None:
            sql += " AND bucket <= :end"
            params["end"] = end_dt
        sql += " ORDER BY bucket ASC"

        rows = db.execute(text(sql), params).mappings().all()
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.warning("[metric_agg] 聚合查询失败回退原始表: %s", e)
        return None

    series: dict[str, list] = {}
    unit_map: dict[str, str] = {}
    for r in rows:
        m = r["metric_name"]
        if m not in unit_map and r.get("unit"):
            unit_map[m] = r["unit"]
        series.setdefault(m, []).append({
            "ts": r["bucket"].isoformat() if r["bucket"] else None,
            "value": round(float(r["avg_value"]), 4) if r["avg_value"] is not None else None,
            "quality": "agg",
            "max": round(float(r["max_value"]), 4) if r["max_value"] is not None else None,
            "min": round(float(r["min_value"]), 4) if r["min_value"] is not None else None,
            "samples": int(r["samples"] or 0),
        })

    # 等间隔降采样到 limit
    for m, pts in series.items():
        if len(pts) > limit:
            step = len(pts) / limit
            series[m] = [pts[int(i * step)] for i in range(limit)]
    return series, unit_map


def refresh_views(db: Session) -> bool:
    """刷新普通物化视图 (TimescaleDB 路径由策略自动刷新, 无需处理)。"""
    cap = _detect(db)
    if cap["mode"] != "plain":
        return False
    try:
        # CONCURRENTLY 不能在事务块内: 使用 autocommit 连接
        engine = db.get_bind()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {_PLAIN_5MIN}"))  # sql-guard-ignore
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {_PLAIN_1H}"))  # sql-guard-ignore
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[metric_agg] 物化视图刷新失败: %s", e)
        return False


async def agg_refresh_loop(interval_sec: int = 300):
    """后台循环: 周期刷新普通物化视图 (仅 plain 模式生效)。"""
    from app.db.session import SessionLocal

    # 首次延迟, 等种子数据/采集器就绪
    await asyncio.sleep(30)
    while True:
        try:
            db = SessionLocal()
            try:
                ok = await asyncio.to_thread(refresh_views, db)
                if ok:
                    logger.debug("[metric_agg] 物化视图已刷新")
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            logger.warning("[metric_agg] 刷新循环异常: %s", e)
        await asyncio.sleep(interval_sec)
