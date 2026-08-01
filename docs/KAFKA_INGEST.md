# 外部设备接入 · Kafka 接入路径（端到端演示）

阶段 3 · 1.5 可选项。本平台「外部设备接入」支持 **同一数据契约、双通道（HTTP + Kafka）收敛**：

- HTTP 通道：`POST /api/external/device/register`、`POST /api/external/metrics/upload`
- Kafka 通道：消费 topic `dc_ioc_external_ingest`，消息为「信封」
  - `{"type": "register", "payload": {<DeviceRegisterRequest 字段>}}`
  - `{"type": "metrics",  "payload": [ {<MetricPoint 字段>}, ... ]}`

> 两条通道复用 `app/schemas/external.py` 的 Pydantic 契约反序列化，采集器团队无需关心落地方式。

## 数据流

```
Mock 采集器 (backend 进程内)
   │  register / metrics 信封
   ▼
Kafka topic: dc_ioc_external_ingest
   │  AIOKafkaConsumer 拉取
   ▼
kafka_consumer._handle_message  (复用 external 契约校验)
   │  upsert_device / bulk_insert_metrics
   ▼
PostgreSQL  ──► 前端「采集器接入 / 设备遥测」页、孪生/能效/容量等模块
```

非法消息写入 DLQ topic `dc_ioc_external_ingest_dlq`（不阻塞主消费流）。

## 一键启用（开发环境）

`deploy/docker-compose.dev.yml` 已内置单节点 Kafka（apache/kafka 官方镜像，KRaft 模式，无需 Zookeeper），
并为 `backend` 注入了 `EXTERNAL_KAFKA_BOOTSTRAP_SERVERS=kafka:9092`。

```bash
# 在 docker-compose 根目录（含 docker-compose.yml）执行
docker compose -f docker-compose.yml -f deploy/docker-compose.dev.yml up -d kafka backend
```

- 未配置 `EXTERNAL_KAFKA_BOOTSTRAP_SERVERS` 时：消费端不启动，Mock 仍走 HTTP，系统照常运行。
- 配置后：Mock 自动改走 Kafka 信封发送；若 broker 不可达 / 未装 `aiokafka`，自动回退 HTTP。

## 验证演示是否走通 Kafka

1. 看 backend 日志：
   - `MockCollector Kafka producer 已连接: kafka:9092`（说明发送走 Kafka）
   - `Kafka 消费端协程已启动: topic=dc_ioc_external_ingest`
   - `Kafka 写入测点 N 条`（说明消费端落库）
2. 前端 `运维作业 → 采集器接入`：设备数与测点持续增长（Mock 设备 id 形如 `MOCK-CHILLER-01`）。
3. 可选，进 Kafka 容器检查 topic：
   ```bash
   docker exec -it dc-ioc-platform-kafka-1 kafka-topics.sh \
     --bootstrap-server localhost:9092 --list
   # 应看到 dc_ioc_external_ingest / dc_ioc_external_ingest_dlq（自动创建）
   ```

## 生产接入

真实采集器按相同契约推送即可，业务端点零改动：

```bash
# HTTP 方式
curl -X POST http://<host>:8000/api/external/metrics/upload \
  -H "X-Collector-Token: <token>" \
  -d '[{"device_id":"CHL-A01","timestamp":"2026-07-25T00:00:00Z",
        "metric_name":"supply_temp","value":7.4,"quality":"good","unit":"℃"}]'

# 或经 Kafka 生产同结构信封（推荐，解耦 + 削峰 + 可重放）
```

生产环境建议显式 `EXTERNAL_MOCK_COLLECTOR_ENABLED=false` 关闭 Mock，由真实采集器推送。
