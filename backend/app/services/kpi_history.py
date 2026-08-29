"""campus 级 KPI 时序服务: 周期快照写入 + 历史查询 + 首次回填。

数据来源是后端聚合出的运营 KPI (dashboard_overview 的返回值), 而非逐设备测点,
因此与 metric_raws 解耦, 可作为 overview 趋势曲线的真实时序底座。
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.models.kpi_history import KpiHistory
from app.services.dc_ioc_data import kpi as gen_kpi

logger = logging.getLogger("kpi_history")

SNAPSHOT_INTERVAL_SEC = 300  # 每 5 分钟一个快照
RETENTION_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_kpi_snapshot(overview: dict, interval_sec: int = SNAPSHOT_INTERVAL_SEC) -> bool:
    """写入一条 KPI 快照; 距上一条不足 interval_sec 则跳过 (幂等节流)。返回是否写入。"""
    db = SessionLocal()
    try:
        last = db.execute(
            select(KpiHistory.ts).order_by(KpiHistory.ts.desc()).limit(1)
        ).scalar_one_or_none()
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (_now() - last).total_seconds() < interval_sec:
                return False

        row = KpiHistory(
            ts=_now(),
            pue=float(overview.get("pue") or 0.0),
            wue=float(overview.get("wue") or 0.0),
            it_load_mw=float(overview.get("it_load_mw") or 0.0),
            total_load_mw=float(overview.get("total_load_mw") or 0.0),
            cool_load_mw=float(overview.get("cool_load_mw") or 0.0),
            online_rate=float(overview.get("online_rate") or 0.0),
            availability=float(overview.get("availability") or 0.0),
        )
        db.add(row)
        db.commit()

        # 轻量 retention: 仅保留近 RETENTION_DAYS 天
        cutoff = _now() - timedelta(days=RETENTION_DAYS)
        db.execute(text("DELETE FROM kpi_history WHERE ts < :cutoff"), {"cutoff": cutoff})
        db.commit()
        return True
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.debug("KPI 快照写入跳过 (DB 不可用?): %s", e)
        return False
    finally:
        db.close()


def get_kpi_trends(hours: int = 48, max_points: int = 60) -> list[dict]:
    """读取窗口内的 KPI 历史, 等间隔降采样到 max_points 返回。"""
    db = SessionLocal()
    try:
        start = _now() - timedelta(hours=hours)
        rows = (
            db.execute(
                select(KpiHistory)
                .where(KpiHistory.ts >= start)
                .order_by(KpiHistory.ts.asc())
            )
            .scalars()
            .all()
        )
        pts = [r.to_dict() for r in rows]
        if len(pts) > max_points:
            step = len(pts) / max_points
            pts = [pts[int(i * step)] for i in range(max_points)]
        return pts
    except Exception as e:  # noqa: BLE001
        logger.debug("KPI 历史读取失败: %s", e)
        return []
    finally:
        db.close()


def seed_kpi_history(hours: int = 48) -> int:
    """首次启动回填历史; 仅当表为空时写入, 幂等。返回写入条数。"""
    db = SessionLocal()
    try:
        cnt = db.execute(select(func.count()).select_from(KpiHistory)).scalar() or 0
        if cnt > 0:
            return 0
        base = gen_kpi()
        now = _now()
        rows = []
        for i in range(hours):
            ts = now - timedelta(hours=i)
            h = ts.hour
            # 午后负载偏高、凌晨偏低 (温和日内波动, 仍属后端生成, 非前端虚构)
            diurnal = 0.08 * math.sin((h - 14) / 24 * 2 * math.pi)
            rows.append(
                KpiHistory(
                    ts=ts,
                    pue=round(base["pue"] * (1 - 0.01 * diurnal), 3),
                    wue=round(base["wue"] * (1 + 0.015 * diurnal), 3),
                    it_load_mw=round(base["itLoad"] * (1 + diurnal), 2),
                    total_load_mw=round(base["totalLoad"] * (1 + diurnal), 2),
                    cool_load_mw=round(base["coolLoad"] * (1 + 0.5 * diurnal), 2),
                    online_rate=round(99.0 + 0.9 * (0.5 + 0.5 * math.sin(i / 6)), 2),
                    availability=round(99.99 + 0.005 * math.sin(i / 9), 4),
                )
            )
        db.add_all(rows)
        db.commit()
        logger.info("[kpi_history] 已回填 %d 小时 campus KPI 历史", hours)
        return len(rows)
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.debug("KPI 历史回填跳过: %s", e)
        return 0
    finally:
        db.close()
