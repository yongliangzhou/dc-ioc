"""共享测点摄取逻辑 — HTTP 上传 与 Kafka 消费 两条通道共用。

职责收敛: 无论数据来自哪个通道, 都走「落库 + 告警评估 + 实时 WS 推送」的统一流程,
避免「Kafka 通道只落库、丢了告警与实时推送」的契约不一致 (修复: 双通道下半段断裂)。

设计:
- 设备类别映射按需查询: 仅对「本批测点涉及的设备」用单条 IN 查询 JOIN
  external_devices 取 category (参考 alarm_engine.sweep_recent_metrics), 不再
  list_devices(limit=10000) 全量加载, 也不维护 60s 模块级缓存 (P0-2 移除热路径缓存)。
- 内存兜底 (DB 不可用时 `_get_db()` 返回 None, 由 crud 走内存路径) 与真实会话
  路径对调用方透明。
- ingest_metrics 为同步阻塞函数 (含 DB 落库与类别查询); 异步通道必须放到
  executor 线程调用 (见 P0-2 修复), 不阻塞事件循环。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.crud import external as ext_crud
from app.db.session import SessionLocal
from app.schemas.external import MetricPoint

logger = logging.getLogger("external.ingest")


def _get_db() -> Optional[Session]:
    """尽量返回数据库会话; 连接不可用时返回 None (由 CRUD 走内存兜底)。"""
    try:
        db = SessionLocal()
        db.execute(text("select 1"))
        return db
    except Exception as e:  # noqa: BLE001
        logger.warning("数据库不可用, 启用内存兜底存储: %s", e)
        return None


def _device_category_map(points: List[MetricPoint], db: Optional[Session] = None) -> dict[str, str]:
    """返回本批测点涉及设备的 device_id -> category 映射。

    [P0-2 FIX] 改为单条 IN 查询直接查 external_devices 取本批设备类别
    (参考 alarm_engine.sweep_recent_metrics 的 JOIN 思路), 不再 list_devices(
    limit=10000) 全量加载成对象, 也不再维护 60s 模块级缓存 (移除热路径缓存),
    避免设备量上升后每次上报都扫描全表、拖垮摄取吞吐。
    """
    device_ids = {p.device_id for p in points if p.device_id}
    if not device_ids:
        return {}
    own = db is None
    target: Optional[Session] = db if db is not None else _get_db()
    if target is None:
        return {}
    try:
        rows = target.execute(
            text(
                "SELECT device_id, category FROM external_devices "
                "WHERE device_id IN :ids"
            ).bindparam("ids", expanding=True),
            {"ids": list(device_ids)},
        ).fetchall()
        # 仅保留带 category 的设备
        return {r[0]: r[1] for r in rows if r[1]}
    except Exception as e:  # noqa: BLE001
        logger.debug("类别映射查询失败: %s", e)
        return {}
    finally:
        if own and target is not None:
            target.close()


def _evaluate_alarms_for_points(points: List[MetricPoint], db: Optional[Session] = None) -> None:
    """对每条已接受的测点触发告警引擎评估 (按本批设备 JOIN 查 category)。"""
    if not points:
        return
    try:
        from app.services import alarm_engine

        cat_map = _device_category_map(points, db)
        for p in points:
            cat = cat_map.get(p.device_id, "")
            alarm_engine.evaluate(
                device_id=p.device_id,
                category=cat,
                metric_name=p.metric_name,
                value=float(p.value),
                unit=p.unit or "",
                quality=p.quality.value if hasattr(p.quality, "value") else str(p.quality),
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("告警引擎评估异常: %s", e)


def _publish_realtime(accepted: List[MetricPoint]) -> None:
    """将本轮测点推送给订阅了对应设备的 WS 客户端。

    直接使用本轮上报数据聚合推送 (不回查数据库), 兼容内存兜底 / 无 DB 联调场景,
    且保证推送的正是刚上报的实时值。
    """
    from app.services import ws_broadcaster

    by_device: dict[str, list[dict]] = {}
    ts = ext_crud._now_iso()
    for p in accepted:
        by_device.setdefault(p.device_id, []).append({
            "metric_name": p.metric_name,
            "value": p.value,
            "unit": getattr(p, "unit", None),
            "quality": getattr(p, "quality", "good"),
        })
    for did, points in by_device.items():
        ws_broadcaster.publish_device_metrics(did, {
            "type": "device_metrics",
            "device_id": did,
            "ts": ts,
            "points": points,
        })


def ingest_metrics(points: List[MetricPoint], db: Optional[Session] = None) -> int:
    """摄取一批测点: 落库 + 告警评估 + 实时 WS 推送。返回成功落库条数。

    - db 为 None: 内部按内存兜底逻辑取会话 (HTTP 端点场景, _get_db 在 DB 不可用时
      返回 None, crud 走内存路径), 会话由本函数负责 commit/close。
    - db 由调用方传入: 使用外部会话 (Kafka 消费侧已开启的会话), 本函数负责 commit,
      调用方负责 close, 便于调用方在更大事务内编排。

    [P0-2 FIX] 本函数为同步阻塞调用 (含 DB 落库与类别 JOIN 查询)。异步通道
    (Kafka 消费协程) 必须通过 run_in_executor / asyncio.to_thread 在独立线程中
    调用, 否则会阻塞事件循环; 告警评估复用落库会话, 在会话仍可用时执行。
    """
    if not points:
        return 0

    own_session = db is None
    session: Optional[Session] = db if db is not None else _get_db()
    try:
        saved = ext_crud.bulk_insert_metrics(session, points)
        if session is not None:
            session.commit()
        # 复用同一会话做告警评估 (会话未关闭前执行)
        _evaluate_alarms_for_points(points, session)
    finally:
        if own_session and session is not None:
            session.close()

    _publish_realtime(points)
    return saved
