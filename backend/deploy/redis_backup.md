# 5.6.2 Redis 持久化与备份策略

> 本文档说明后端缓存层 Redis 的持久化配置、备份与恢复方案，与 PostgreSQL 备份（`backup.sh`）互补。

## 1. 持久化配置（redis.conf 关键项）

| 配置项 | 推荐值 | 说明 |
| --- | --- | --- |
| `save 900 1` | 保留 | 15 分钟内至少 1 次写则落盘 RDB |
| `save 300 10` | 保留 | 5 分钟内 10 次写落盘 |
| `save 60 10000` | 保留 | 1 分钟内 1 万次写落盘 |
| `appendonly yes` | **开启** | AOF 持久化，崩溃后近乎零丢失 |
| `appendfsync everysec` | 推荐 | 每秒刷盘，兼顾性能与安全 |
| `auto-aof-rewrite-percentage 100` | 默认 | AOF 体积翻倍时自动重写 |
| `auto-aof-rewrite-min-size 64mb` | 默认 | 最小重写体积 |
| `maxmemory` | 按实例配置 | 建议不超过物理内存 60% |
| `maxmemory-policy allkeys-lru` | 推荐 | 缓存满时 LRU 淘汰（本平台缓存可丢弃） |

> 本平台 Redis 仅作**响应缓存**（`cache_json`）与限流计数，非持久业务数据。因此 `allkeys-lru` + `appendonly` 为最佳组合：**宕机后缓存可重建，不影响正确性**。

## 2. 备份方案

由于缓存可重建，**Redis 无需纳入每日冷备**，但建议：

1. **RDB 快照**：依赖 `save` 规则自动生成 `dump.rdb`，随主机磁盘快照（如云盘快照）一并保留。
2. **AOF 文件**：随主机备份保留，用于极端情况下的精确恢复。
3. **容器化部署**：`docker-compose.yml` 中将 `/data` 挂为命名卷（`redis-data`），避免容器重建丢快照。

### 可选：脚本化冷备（停写窗口极小）
```bash
#!/usr/bin/env bash
# redis_backup.sh — 在从节点执行 BGSAVE 后拷贝 dump.rdb
redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE
sleep 2
cp "$(redis-cli -h $REDIS_HOST config get dir | tail -1)/dump.rdb" \
    "$BACKUP_DIR/redis_$(date +%Y%m%d_%H%M%S).rdb"
```

## 3. 恢复

- **缓存重建优先**：直接重启 Redis（AOF/RDB 自动加载），丢失的仅为旧缓存，首次请求自动回源数据库重建——对业务**零影响**。
- **精确恢复**：停止 Redis → 替换 `dump.rdb`/`appendonly.aof` → 启动。

## 4. 监控与告警

- `redis-cli info memory` 关注 `used_memory` / `maxmemory` 占比，超过 80% 告警。
- `redis-cli info persistence` 关注 `aof_last_bgrewrite_status` / `rdb_last_bgsave_status` 异常告警。
- 与 5.8.2 日志告警联动：Redis 连接异常时 `cache_json` 自动降级（不缓存），仅记录 warning，不阻断主流程。

## 5. 容量与淘汰

- 缓存键前缀规范：`cache:<prefix>:<md5(path+query)>`（见 `app/core/cache.py`）。
- 单条缓存 TTL 默认 30s（dashboard），避免脏数据长期驻留。
- 写操作后通过 `invalidate_prefix(prefix)` 主动失效相关缓存（见 `cache_strategy.md`）。
