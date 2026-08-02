-- =============================================================================
-- 5.7.1 / 5.7.2 时序性能优化 (TimescaleDB 超表 / 压缩 / 连续聚合)
-- -----------------------------------------------------------------------------
-- 目标: 解决 point_data / realtime_metrics / external_metrics 大表查询性能:
--   1. 将时序表转为 TimescaleDB hypertable (按时间分区)
--   2. 启用列存压缩, 降低存储并加速范围扫描
--   3. 建立连续聚合视图 (materialized view), 加速历史趋势/大盘统计
-- 执行: PostgreSQL + TimescaleDB 环境; 首次部署执行一次 (幂等)。
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. 创建超表 (hypertable)
--    分区键为 ts (DateTime, 已是主键之一)
-- ---------------------------------------------------------------------------
SELECT create_hypertable('point_data', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('realtime_metrics', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('external_metrics', 'ts', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 2. 压缩策略 (columnar compression)
--    超过 7 天的 chunks 自动压缩 (时序数据顺序写, 压缩率高)
-- ---------------------------------------------------------------------------
ALTER TABLE point_data SET (timescaledb.compress, timescaledb.compress_segmentby = 'target_type,target_id,metric');
ALTER TABLE realtime_metrics SET (timescaledb.compress, timescaledb.compress_segmentby = 'equipment_id,metric');
ALTER TABLE external_metrics SET (timescaledb.compress, timescaledb.compress_segmentby = 'device_id,metric');

SELECT add_compression_policy('point_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('realtime_metrics', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('external_metrics', INTERVAL '7 days', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 3. 连续聚合视图 (加速历史趋势/大盘统计)
--    每分钟聚合: 按 target_type/target_id/metric 取 avg/min/max/count
--    后台定时刷新, 前端 history 查询直接读聚合而非原始 chunk
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS point_data_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    target_type,
    target_id,
    metric,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value,
    count(*)   AS sample_count
FROM point_data
GROUP BY bucket, target_type, target_id, metric;

-- 连续聚合自动刷新策略: 每 1 分钟刷新最近 1 小时
SELECT add_continuous_aggregate_policy('point_data_1m',
    start_offset => INTERVAL '1 hour',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 4. 数据保留策略 (可选, 按需开启)
--    原始时序保留 90 天, 超期自动 drop chunks (聚合视图不受影响)
-- ---------------------------------------------------------------------------
-- SELECT add_retention_policy('point_data', INTERVAL '90 days', if_not_exists => TRUE);
-- SELECT add_retention_policy('realtime_metrics', INTERVAL '90 days', if_not_exists => TRUE);
-- SELECT add_retention_policy('external_metrics', INTERVAL '90 days', if_not_exists => TRUE);

-- =============================================================================
-- 验证:
--   -- 查看 chunks / 压缩率
--   SELECT * FROM chunk_compression_stats('point_data');
--   -- 历史趋势改查聚合视图 (性能数量级提升)
--   SELECT * FROM point_data_1m
--   WHERE target_type='server' AND target_id=1 AND metric='cpu_usage'
--     AND bucket > now() - INTERVAL '24 hours';
-- =============================================================================
