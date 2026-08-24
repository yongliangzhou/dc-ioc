"""Kafka 消费端 — 复用外部设备接入数据契约反序列化。

设计要点:
- 消费 topic (默认 dc_ioc_external_ingest) 中每条消息是一个「信封」:
    {"type": "register", "payload": {<DeviceRegisterRequest 字段>}}
    {"type": "metrics",  "payload": [ {<MetricPoint 字段>}, ... ]}
- 反序列化复用 app.schemas.external 的 Pydantic 契约 (与 HTTP 端点完全一致),
  做到「同一契约、双通道 (HTTP + Kafka)」收敛, 采集器团队无需关心落地方式。
- 非法/失败消息写入 DLQ topic (默认 ..._dlq), 由独立重投消费者重试, 不阻塞主消费流。

[P1-5 可靠性改造]
- 关闭 enable_auto_commit, 仅在处理成功后手动提交 offset (at-least-once):
  处理中崩溃/重启时未提交的 offset 会被 Kafka 重投, 避免消息静默丢失。
- DLQ producer 改为常驻单例, 不再每条消息新建/销毁 producer。
- 新增 DLQ 重投消费者, 读取 DLQ topic 并将失败消息重新注入主处理流程,
  带重投次数上限, 防止毒消息无限循环。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from aiokafka.structs import OffsetAndMetadata

from app.core.config import settings
from app.crud import external as ext_crud
from app.db.session import SessionLocal
from app.schemas.external import DeviceRegisterRequest, MetricPoint
from app.services.external_ingest import ingest_metrics

logger = logging.getLogger("external.kafka")

# DLQ 消息最大重投次数 (超过后判定为毒消息并丢弃, 仅记录)
DLQ_MAX_REDELIVER = 3

# 常驻 DLQ producer 单例 (避免每条失败消息都新建/销毁 producer)
_dlq_producer = None


async def _ensure_dlq_producer():
    """惰性创建常驻 DLQ producer (best-effort, broker 不可用时返回 None)。"""
    global _dlq_producer
    if _dlq_producer is not None:
        return _dlq_producer
    try:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )
        await producer.start()
        _dlq_producer = producer
    except Exception as e:  # noqa: BLE001
        logger.warning("DLQ producer 启动失败 (DLQ 暂不可用): %s", e)
        _dlq_producer = None
    return _dlq_producer


async def _stop_dlq_producer() -> None:
    global _dlq_producer
    if _dlq_producer is not None:
        try:
            await _dlq_producer.stop()
        except Exception as e:  # noqa: BLE001
            logger.warning("DLQ producer 关闭失败: %s", e)
        finally:
            _dlq_producer = None


async def maybe_start_consumer() -> Optional[asyncio.Task]:
    """若配置了 Kafka, 启动消费协程(主消费 + DLQ 重投); 否则返回 None。"""
    if not settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS:
        logger.info("未配置 EXTERNAL_KAFKA_BOOTSTRAP_SERVERS, 跳过 Kafka 消费端")
        return None
    try:
        from aiokafka import AIOKafkaConsumer  # noqa: F401
    except ImportError:
        logger.warning("未安装 aiokafka, 无法启动 Kafka 消费端 (HTTP 接入仍可用)")
        return None

    task = asyncio.create_task(_run_consumers(), name="external-kafka")
    logger.info(
        "Kafka 消费端协程已启动: topic=%s dlq=%s",
        settings.EXTERNAL_KAFKA_INGEST_TOPIC,
        settings.EXTERNAL_KAFKA_DLQ_TOPIC,
    )
    return task


async def _run_consumers() -> None:
    """同时驱动主消费循环与 DLQ 重投循环, 共享常驻 DLQ producer。"""
    try:
        await asyncio.gather(_consume_loop(), _dlq_redeliver_loop())
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("Kafka 消费协程异常退出: %s", e)
    finally:
        await _stop_dlq_producer()


async def _consume_loop() -> None:
    """主消费循环: 拉取 -> 按信封 type 分发 -> 复用契约反序列化 -> 落库。

    [P1-5 FIX] 关闭自动提交, 仅在处理成功后手动提交当前消息 offset。
    """
    from aiokafka import AIOKafkaConsumer

    consumer = AIOKafkaConsumer(
        settings.EXTERNAL_KAFKA_INGEST_TOPIC,
        bootstrap_servers=settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.EXTERNAL_KAFKA_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,  # [P1-5 FIX] 关闭自动提交
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await _handle_message(msg.value)
            except Exception as e:  # noqa: BLE001
                logger.exception("处理 Kafka 消息失败: %s", e)
                # 失败消息入 DLQ; 不提交本消息 offset -> 由 DLQ 重投消费者负责重试。
                # 若此处崩溃未提交, 重启后 Kafka 会重投未提交消息 (at-least-once)。
                await _send_to_dlq(msg.value, reason=str(e), attempt=0)
                continue
            # [P1-5 FIX] 处理成功 -> 手动提交本消息 offset (仅确认已成功处理的部分)
            await consumer.commit(
                {msg.topic_partition: OffsetAndMetadata(msg.offset + 1, "")}
            )
    finally:
        await consumer.stop()


async def _dlq_redeliver_loop() -> None:
    """DLQ 重投消费者: 读取 DLQ topic, 将失败消息重新注入主处理流程。

    [P1-5 FIX] 补上此前缺失的 DLQ 消费者, 避免失败消息无人处理而永久丢失。
    带重投次数上限 (DLQ_MAX_REDELIVER), 超过后判定为毒消息并丢弃。
    """
    from aiokafka import AIOKafkaConsumer

    consumer = AIOKafkaConsumer(
        settings.EXTERNAL_KAFKA_DLQ_TOPIC,
        bootstrap_servers=settings.EXTERNAL_KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.EXTERNAL_KAFKA_GROUP_ID + "_dlq_redeliver",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            envelope = msg.value if isinstance(msg.value, dict) else {}
            original = envelope.get("original")
            attempt = int(envelope.get("_redeliver_attempt", 0) or 0)

            if original is None:
                logger.warning("DLQ 收到无法识别的信封, 跳过: %s", envelope)
                await consumer.commit(
                    {msg.topic_partition: OffsetAndMetadata(msg.offset + 1, "")}
                )
                continue

            if attempt >= DLQ_MAX_REDELIVER:
                logger.error(
                    "DLQ 消息超过最大重投次数(%d), 丢弃: %s", DLQ_MAX_REDELIVER, original
                )
                await consumer.commit(
                    {msg.topic_partition: OffsetAndMetadata(msg.offset + 1, "")}
                )
                continue

            try:
                await _handle_message(original)
            except Exception as e:  # noqa: BLE001
                logger.warning("DLQ 重投仍失败 (第 %d 次): %s", attempt + 1, e)
                # 重新投回 DLQ, 递增重投计数; 提交本 DLQ offset 避免重复处理同一条
                await _send_to_dlq(
                    original,
                    reason=f"dlq-redeliver#{attempt + 1}: {e}",
                    attempt=attempt + 1,
                )
                await consumer.commit(
                    {msg.topic_partition: OffsetAndMetadata(msg.offset + 1, "")}
                )
                continue

            logger.info("DLQ 重投成功 (第 %d 次)", attempt + 1)
            await consumer.commit(
                {msg.topic_partition: OffsetAndMetadata(msg.offset + 1, "")}
            )
    finally:
        await consumer.stop()


async def _handle_message(envelope: dict) -> None:
    """解析信封并按 type 分发, 复用 Pydantic 契约完成校验与落库。"""
    if not isinstance(envelope, dict):
        raise ValueError("消息信封必须是 JSON 对象")

    mtype = envelope.get("type")
    payload = envelope.get("payload")
    if mtype is None or payload is None:
        raise ValueError("消息信封缺少 type 或 payload")

    db = None
    try:
        if mtype == "register":
            req = DeviceRegisterRequest.model_validate(payload)
            db = SessionLocal()
            ext_crud.upsert_device(db, req)
            db.commit()
            logger.info("Kafka 注册设备: %s", req.device_id)
        elif mtype == "metrics":
            if not isinstance(payload, list):
                raise ValueError("metrics 信封的 payload 必须是数组")
            points = [MetricPoint.model_validate(p) for p in payload]
            # [P0-2 FIX] ingest_metrics 内含同步 DB 落库与类别查询, 必须放到
            # executor 线程执行, 否则阻塞 Kafka 消费协程的事件循环; 设备量上升时
            # 吞吐塌方。ingest_metrics 内部自行获取会话, 无需调用方传入 db。
            loop = asyncio.get_running_loop()
            saved = await loop.run_in_executor(None, ingest_metrics, points)
            logger.info("Kafka 写入测点 %d 条", saved)
        else:
            raise ValueError(f"未知消息类型: {mtype}")
    finally:
        if db is not None:
            db.close()


async def _send_to_dlq(value: object, reason: str, attempt: int = 0) -> None:
    """将失败消息投递到 DLQ topic (best-effort, 失败仅记录)。

    [P1-5 FIX] 复用常驻 DLQ producer 单例, 不再每条消息新建/销毁 producer。
    """
    producer = await _ensure_dlq_producer()
    if producer is None:
        return
    try:
        await producer.send_and_wait(
            settings.EXTERNAL_KAFKA_DLQ_TOPIC,
            {"reason": reason, "original": value, "_redeliver_attempt": attempt},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("投递 DLQ 失败 (消息已丢弃): %s", e)
