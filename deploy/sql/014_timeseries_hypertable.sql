-- ============================================================================
-- 8.6 时序大表专项: point_data / metric_raws 转为 TimescaleDB hypertable
-- 前提: 已安装 TimescaleDB 扩展 (docker 镜像 timescale/timescaledb)
-- 用法: psql -d <db> -f 014_timeseries_hypertable.sql
-- 幂等: 所有建表/策略均带 IF NOT EXISTS / if_not_exists, 可重复执行。
-- 说明: 设计文档 8.6。开发/测试库由 app.core.lifespan._ensure_hypertables 自愈,
--       生产库由 Alembic 0010 执行; 本脚本为独立/可复核的 SQL 参考实现。
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- 0. metric_raws 复合主键 (id, ts): TimescaleDB 要求分区列(ts)必须包含在
--    主键/所有唯一索引中。原 metric_raws 主键仅为 id, 需补 ts 进主键。
--    (唯一索引 uq_metric_raw_device_name_ts 已含 ts, 满足约束)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_index i JOIN pg_attribute a
            ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey)
        WHERE i.indrelid='metric_raws'::regclass
          AND i.indisprimary AND a.attname='ts'
    ) THEN
        ALTER TABLE metric_raws DROP CONSTRAINT metric_raws_pkey;
        ALTER TABLE metric_raws ADD PRIMARY KEY (id, ts);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. 建超表 (按 ts 分区)
-- ---------------------------------------------------------------------------
SELECT create_hypertable('point_data', 'ts',
       chunk_time_interval => INTERVAL '7 days',
       if_not_exists => TRUE, migrate_data => TRUE);

SELECT create_hypertable('metric_raws', 'ts',
       chunk_time_interval => INTERVAL '1 day',
       if_not_exists => TRUE, migrate_data => TRUE);

-- ---------------------------------------------------------------------------
-- 2. 列存压缩 (顺序写时序, 压缩率高)
-- ---------------------------------------------------------------------------
ALTER TABLE point_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'target_type, target_id, metric',
    timescaledb.compress_orderby = 'ts DESC'
);
SELECT add_compression_policy('point_data', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE metric_raws SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id, metric_name',
    timescaledb.compress_orderby = 'ts DESC'
);
SELECT add_compression_policy('metric_raws', INTERVAL '7 days', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 3. 数据保留策略 (原始时序保留, 聚合视图不受影响)
-- ---------------------------------------------------------------------------
SELECT add_retention_policy('point_data', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('metric_raws', INTERVAL '90 days', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 4. 连续聚合视图 (加速看板/趋势查询, 直接读聚合而非原始 chunk)
-- ---------------------------------------------------------------------------
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
       schedule_interval => INTERVAL '5 minutes',
       if_not_exists => TRUE);

CREATE MATERIALIZED VIEW IF NOT EXISTS metric_raws_5min
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', ts) AS bucket,
       device_id, metric_name,
       avg(value) AS avg_value,
       max(value) AS max_value,
       min(value) AS min_value,
       count(*)   AS samples
FROM metric_raws
GROUP BY bucket, device_id, metric_name;

SELECT add_continuous_aggregate_policy('metric_raws_5min',
       start_offset => INTERVAL '1 hour',
       end_offset   => INTERVAL '5 minutes',
       schedule_interval => INTERVAL '5 minutes',
       if_not_exists => TRUE);

-- ============================================================================
-- 验证:
--   SELECT hypertable_name, num_chunks FROM timescaledb_information.hypertables;
--   SELECT * FROM chunk_compression_stats('metric_raws');
--   SELECT * FROM point_data_5min
--     WHERE target_type='server' AND target_id=1 AND metric='cpu_usage'
--       AND bucket > now() - INTERVAL '24 hours';
-- ============================================================================
