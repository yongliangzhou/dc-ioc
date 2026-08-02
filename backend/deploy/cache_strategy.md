# 5.7.3 缓存策略（推广 / 失效 / 预热）

> 本文档定义后端响应缓存的统一策略，覆盖高频只读接口的缓存推广、写后失效与启动预热。

## 1. 缓存层概览

| 组件 | 位置 | 作用 |
| --- | --- | --- |
| `cache_json(ttl, key_prefix)` | `app/core/cache.py` | 端点响应 JSON 缓存装饰器（best-effort，Redis 不可用自动降级） |
| `invalidate_prefix(prefix)` | `app/core/cache.py` | 按前缀批量失效缓存键 |
| `rds` | `app/cache/redis_client.py` | Redis 连接池封装 |

缓存键格式：`cache:<key_prefix>:<md5(request.url.path + request.url.query)>`

> **重要修复**：`@cache_json` 现保留被装饰函数原始签名（`wrapper.__signature__`），确保 FastAPI 能正确注入 `Request` 参数，否则会导致 `Request` 注入失败（历史 bug）。

## 2. 已推广的缓存接口

| 接口 | TTL | key_prefix | 说明 |
| --- | --- | --- | --- |
| `GET /api/dashboard/overview` | 30s | `dashboard:overview` | 驾驶舱总览聚合 |
| `GET /api/dashboard/campuses` | 30s | `dashboard:campuses` | 多园区概览 |
| `GET /api/dashboard/campus-comparison` | 30s | `dashboard:campus-comparison` | 跨园区对比 |

> 推广原则：仅对**高频只读、允许秒级延迟**的聚合接口启用；写密集接口（工单/告警处置）不缓存，保证实时性。

## 3. 缓存失效（写后失效）

当数据发生变更，需主动失效关联缓存，避免脏读。约定：

```python
from app.core.cache import invalidate_prefix

# 工单/设备/知识库等业务写操作后:
invalidate_prefix("dashboard:overview")
invalidate_prefix("dashboard:campuses")
```

可在以下写路径旁调用（建议封装为 service 层钩子）：
- `app/crud/ticket.py` 的 `create_ticket` / `transition_ticket`
- `app/crud/knowledge.py` 的写操作
- `app/services/dc_aggregator.py` 依赖的统计源变更时

## 4. 缓存预热（启动/低峰）

预热用于降低冷启动后的首次请求延迟。提供脚本 `scripts/warm_cache.py`（可选，低峰期 cron 调用）：

```bash
# 预热驾驶舱缓存
python scripts/warm_cache.py
```

预热逻辑：依次请求 dashboard 三个聚合端点（带内部 token 或直接调用 `agg.*`），触发 `cache_json` 写入。

## 5. 监控

- 命中率：`redis-cli info stats` 关注 `keyspace_hits` / `keyspace_misses`。
- 内存：`used_memory` 超 60% 告警（见 `redis_backup.md`）。
- 降级：Redis 不可用时 `cache_json` 静默降级，仅记 warning，请求直连数据库。

## 6. 注意事项

- TTL 不宜过长（默认 30s），避免聚合数据严重滞后。
- 缓存体经 `orjson` 序列化（含 `default=str` 兜底），非 JSON 安全对象需自定义 `model_dump`。
- 生产环境确保 Redis 配置了 `maxmemory-policy allkeys-lru`（见 `redis_backup.md` §1）。
