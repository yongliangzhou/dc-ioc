# 外部设备接入 · 标准数据契约 (Data Contract)

> 采集器开发团队对接规范。后端已按本契约实现 **HTTP 接收端点** 与 **Kafka 消费端** 双通道，落库到 PostgreSQL（数据库不可用时自动内存兜底），并提供了前端「采集器接入 / 设备注册状态」运维页。
>
> **原则：先定死接口，采集器只需按本文件格式推数据即可，无需关心后端落地方式。**

---

## 1. 基础信息

| 项 | 值 |
| --- | --- |
| 契约版本 | v1 |
| Base URL | `/api` |
| 注册端点 | `POST /api/external/device/register` |
| 测点端点 | `POST /api/external/metrics/upload` |
| 查询端点 | `GET /api/external/devices` · `GET /api/external/devices/{device_id}/metrics` |
| 鉴权 (可选) | 请求头 `X-Collector-Token`，值等于后端配置 `EXTERNAL_COLLECTOR_TOKEN` 时放行；未配置则开发/联调阶段直接放行 |

---

## 2. 设备注册 `POST /api/external/device/register`

### 2.1 请求体字段

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `device_id` | string | ✅ | `^[A-Za-z0-9][A-Za-z0-9._:-]{1,63}$` | 采集侧稳定唯一标识（建议资产编号/序列号派生） |
| `ip` | string | ✅ | IPv4 / IPv6 / 主机名 | 管理或采集可达地址 |
| `sn` | string | ✅ | ≤128 | 设备出厂序列号 |
| `model` | string | ✅ | ≤128 | 设备型号 |
| `name` | string | | ≤128 | 展示名称 |
| `vendor` | string | | ≤64 | 厂商 |
| `domain` | string | | | 业务域，如 `hvac_source` / `hvac_terminal` / `power_hv` |
| `category` | string | | | 设备类别，如 `chiller` / `crac` / `ups` / `genset` |
| `location` | string | | ≤128 | 物理位置 / 包间，如 `R01` |
| `protocol` | string | | | 采集协议：`modbus` / `snmp` / `kafka` / … |
| `tags` | string[] | | | 自定义标签 |
| `description` | string | | ≤512 | 备注 |
| `extra` | object | | | 厂商 / 协议私有扩展字段 |

### 2.2 响应

```json
{ "device_id": "CHILLER-01", "status": "registered", "received_at": "2026-07-24T10:00:00+00:00", "message": "设备注册成功" }
```

`status` 取值：`registered`（首次） / `updated`（信息变更） / `duplicate`（已存在且一致）。

### 2.3 curl 示例

```bash
curl -X POST http://localhost:8000/api/external/device/register \
  -H "Content-Type: application/json" \
  -H "X-Collector-Token: <token>" \
  -d '{"device_id":"CHILLER-01","ip":"10.20.1.11","sn":"SN123456","model":"Carrier-19XR",
       "name":"1#冷水机组","vendor":"Carrier","domain":"hvac_source","category":"chiller",
       "location":"R01","protocol":"modbus","tags":["cooling"]}'
```

---

## 3. 实时测点上报 `POST /api/external/metrics/upload`

### 3.1 请求体

**数组**，支持单点（1 个元素）与批量（N 个元素）：

```json
[
  { "device_id": "CHILLER-01", "timestamp": "2026-07-24T10:00:00+08:00", "metric_name": "supply_temp", "value": 7.2, "quality": "good", "unit": "℃" },
  { "device_id": "CHILLER-01", "timestamp": 1753322400, "metric_name": "power_kw", "value": 320.5, "quality": "good", "unit": "kW" }
]
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `device_id` | string | ✅ | 2–64 | 设备唯一标识 |
| `timestamp` | string / number | ✅ | ISO8601 或 Unix 秒 | 测点采样时间（ISO8601 字符串，或 Unix 秒数字；含时区或 UTC 偏移，`Z` 视为 UTC） |
| `metric_name` | string | ✅ | 1–128，蛇形命名 | 如 `cpu_usage` / `inlet_temp` / `power_kw` |
| `value` | number | ✅ | float | 数值（遥信可用 0/1） |
| `quality` | enum | | `good`(默认) / `uncertain` / `bad` | 数据质量（对齐 OPC-UA / IEC 60870 语义） |
| `unit` | string | | ≤32 | 单位 `℃/kW/%/…`（可选，便于展示） |
| `tags` | object | | | 维度标签（可选） |

### 3.2 逐条校验与部分接受

后端对数组**逐条**用 `MetricPoint` 校验，任一条异常不影响其余；响应返回接受/拒绝计数与逐条失败原因：

```json
{
  "total": 2, "accepted": 1, "rejected": 1,
  "rejected_items": [{ "index": 1, "device_id": "CHILLER-01", "reason": "value: ... is not a valid float" }],
  "received_at": "2026-07-24T02:00:00+00:00",
  "message": "已接收 1/2 条测点, 1 条被拒绝"
}
```

### 3.3 数据质量码

| quality | 语义 | 典型场景 |
| --- | --- | --- |
| `good` | 正常、可信 | 采集成功 |
| `uncertain` | 可疑 | 抖动 / 插值 / 通信降级 |
| `bad` | 坏点 | 采集失败 / 超时 / 设备离线 |

### 3.4 curl 示例

```bash
curl -X POST http://localhost:8000/api/external/metrics/upload \
  -H "Content-Type: application/json" \
  -d '[{"device_id":"CHILLER-01","timestamp":"2026-07-24T10:00:00+08:00","metric_name":"supply_temp","value":7.2,"quality":"good","unit":"℃"}]'
```

---

## 4. 只读查询端点（前端运维页使用）

| 端点 | 说明 | 查询参数 |
| --- | --- | --- |
| `GET /api/external/devices` | 已注册设备列表 + 注册状态 | `domain` / `protocol` / `skip` / `limit` |
| `GET /api/external/devices/{device_id}/metrics` | 某设备最近测点（按接收时间倒序） | `limit`（默认 50） |

`GET /api/external/devices` 响应：

```json
{
  "total": 12, "online": 10, "offline": 2, "total_metrics": 184320,
  "items": [
    { "device_id": "CHILLER-01", "ip": "10.20.1.11", "model": "Carrier-19XR",
      "name": "1#冷水机组", "protocol": "modbus", "domain": "hvac_source",
      "last_seen": "2026-07-24T02:00:00+00:00", "metric_count": 15300, "online": true }
  ]
}
```

`online` 依据 `last_seen` 与当前时间差 ≤ 5 分钟判定。

---

## 5. Kafka 消费端（双通道，复用同一契约）

采集器也可通过 Kafka 推数据，后端消费端复用**完全相同的 Pydantic 契约**反序列化，做到「同一契约、双通道收敛」。

| 配置项（环境变量） | 默认值 | 说明 |
| --- | --- | --- |
| `EXTERNAL_KAFKA_BOOTSTRAP_SERVERS` | 空（不启动） | 配置后应用启动自动拉起消费协程 |
| `EXTERNAL_KAFKA_INGEST_TOPIC` | `dc_ioc_external_ingest` | 接入主题 |
| `EXTERNAL_KAFKA_DLQ_TOPIC` | `dc_ioc_external_ingest_dlq` | 死信主题（非法消息） |
| `EXTERNAL_KAFKA_GROUP_ID` | `dc_ioc_collector` | 消费者组 |

### 5.1 消息信封格式

每条消息为一个 JSON 信封，按 `type` 分发：

```jsonc
// 设备注册
{ "type": "register", "payload": { /* DeviceRegisterRequest 字段 */ } }

// 测点批量
{ "type": "metrics",  "payload": [ /* MetricPoint 字段 */, { /* ... */ } ] }
```

- 反序列化复用 `app.schemas.external.DeviceRegisterRequest` / `MetricPoint`，与 HTTP 端点零差异。
- 解析失败的消息写入 DLQ 主题，不阻塞主消费流。
- 未配置 `EXTERNAL_KAFKA_BOOTSTRAP_SERVERS` 或未安装 `aiokafka` 时不启动，HTTP 接入仍可用。

---

## 6. 持久化演进

| 层 | 实现 |
| --- | --- |
| ORM 模型 | `app/models/external.py` → `external_devices`（已注册设备）、`metric_raws`（原始测点时序） |
| 数据访问 | `app/crud/external.py`：`upsert_device` / `bulk_insert_metrics` / `list_devices` / `recent_metrics`，统一返回 `ExternalDeviceView` / `MetricRecordView` |
| 数据库迁移 | `alembic/versions/0002_external_device_metric.py`（`alembic.ini` + `alembic/env.py` 已就绪） |
| 内存兜底 | 数据库不可用时自动回退到进程内存储，契约与前端展示不变；重启后清空（仅开发/联调） |
| 应用启动 | `app/main.py` lifespan 中按配置拉起 Kafka 消费协程 |

> `metric_raws` 为高频写入表，生产环境建议改造为 TimescaleDB hypertable 或按时间分区（当前为通用关系表）。

### 6.1 应用迁移

```bash
cd backend
pip install -r requirements.txt          # 含 aiokafka
alembic upgrade head                      # 创建 external_devices / metric_raws
# 可选：设置环境变量后再启动
export EXTERNAL_KAFKA_BOOTSTRAP_SERVERS=broker1:9092
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 7. 实体类摘要

### 7.1 Pydantic（后端 `app/schemas/external.py`）

```python
class MetricQuality(str, Enum):
    GOOD = "good"; UNCERTAIN = "uncertain"; BAD = "bad"

class DeviceRegisterRequest(BaseModel):
    device_id: str                      # 正则约束
    ip: str                             # IPv4/IPv6/主机名
    sn: str; model: str
    name, vendor, domain, category, location, protocol: Optional[str]
    tags: list[str] = []; description: Optional[str]
    extra: dict = {}

class MetricPoint(BaseModel):
    device_id: str; timestamp: str      # ISO8601 或 Unix 秒
    metric_name: str; value: float
    quality: MetricQuality = MetricQuality.GOOD
    unit: Optional[str]; tags: dict = {}
```

### 7.2 TypeScript（前端 `src/types/index.ts`）

```ts
export type MetricQuality = "good" | "uncertain" | "bad";
export interface ExternalDevice { device_id: string; ip: string; sn: string; model: string;
  name?; vendor?; domain?; category?; location?; protocol?; tags?: string[]; description?; extra?; }
export interface MetricPoint { device_id: string; timestamp: string; metric_name: string;
  value: number; quality: MetricQuality; unit?; tags?; }
export interface ExternalDeviceView { device_id; ip; sn; model; name?; ...; last_seen?; metric_count: number; online: boolean; }
```
