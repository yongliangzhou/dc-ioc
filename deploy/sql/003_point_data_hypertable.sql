-- ============================================================================
-- 时序优化: 将 point_data 转换为 TimescaleDB Hypertable (强烈推荐)
-- 前提: 已安装 TimescaleDB 扩展
-- 用法: psql -d dc_ioc -f 003_point_data_hypertable.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. 转为 hypertable, 按 ts 分区 (7 天一个 chunk, 可调)
SELECT create_hypertable('point_data', 'ts',
       chunk_time_interval => INTERVAL '7 days',
       if_not_exists => TRUE,
       migrate_data => TRUE);

-- 2. 开启原生压缩 (默认 30 天前的数据压缩)
ALTER TABLE point_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'target_type, target_id, metric',
    timescaledb.compress_orderby = 'ts DESC'
);
SELECT add_compression_policy('point_data', INTERVAL '30 days');

-- 3. 数据保留策略: 仅保留 1 年原始数据 (按需调整)
SELECT add_retention_policy('point_data', INTERVAL '1 year');

-- 4. 连续聚合: 预计算 5 分钟均值 (大幅降低看板查询成本)
CREATE MATERIALIZED VIEW IF NOT EXISTS point_data_5min
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', ts) AS bucket,
       target_type, target_id, metric,
       avg(value) AS avg_value,
       max(value) AS max_value,
       min(value) AS min_value,
       count(*)   AS samples
FROM point_data
GROUP BY bucket, target_type, target_id, metric;

SELECT add_continuous_aggregate_policy('point_data_5min',
       start_offset => INTERVAL '1 hour',
       end_offset   => INTERVAL '5 minutes',
       schedule_interval => INTERVAL '5 minutes');
