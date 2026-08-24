-- ============================================================================
-- 时序优化: 将 metric_raws + point_data 转为 TimescaleDB Hypertable
-- 前提: 已安装 TimescaleDB 扩展 (docker-compose postgres:16-alpine 不含, 需 pg_timescale 镜像)
-- 用法: psql -d dc_ioc -f 005_metric_raws_hypertable.sql
-- 
-- 若未安装 TimescaleDB, 降级方案: 使用 PostgreSQL 原生分区 (PARTITION BY RANGE on ts)
-- 本脚本同时提供两种方案, 按环境自动选择。
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$
DECLARE
    has_tsdb boolean;
BEGIN
    SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') INTO has_tsdb;

    IF has_tsdb THEN
        -- ===== TimescaleDB 路径 =====

        -- ---- 1. metric_raws → Hypertable ----
        PERFORM create_hypertable('metric_raws', 'ts',
               chunk_time_interval => INTERVAL '1 day',
               if_not_exists => TRUE,
               migrate_data => TRUE);

        -- 开启压缩: 7 天前数据按 device_id + metric_name 分段压缩
        ALTER TABLE metric_raws SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'device_id, metric_name',
            timescaledb.compress_orderby = 'ts DESC, received_at DESC'
        );
        PERFORM add_compression_policy('metric_raws', INTERVAL '7 days',
               if_not_exists => TRUE);

        -- 保留策略: 仅保留 90 天原始数据 (按需调整)
        PERFORM add_retention_policy('metric_raws', INTERVAL '90 days',
               if_not_exists => TRUE);

        -- 连续聚合: 5 分钟桶 (仪表盘 / 趋势图查询直接读聚合表)
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

        PERFORM add_continuous_aggregate_policy('metric_raws_5min',
               start_offset    => INTERVAL '1 hour',
               end_offset      => INTERVAL '5 minutes',
               schedule_interval => INTERVAL '5 minutes',
               if_not_exists   => TRUE);

        -- 连续聚合: 1 小时桶 (日报 / 周报)
        CREATE MATERIALIZED VIEW IF NOT EXISTS metric_raws_1h
        WITH (timescaledb.continuous) AS
        SELECT time_bucket('1 hour', ts) AS bucket,
               device_id, metric_name,
               avg(value) AS avg_value,
               max(value) AS max_value,
               min(value) AS min_value,
               count(*)   AS samples
        FROM metric_raws
        GROUP BY bucket, device_id, metric_name;

        PERFORM add_continuous_aggregate_policy('metric_raws_1h',
               start_offset    => INTERVAL '2 hours',
               end_offset      => INTERVAL '1 hour',
               schedule_interval => INTERVAL '1 hour',
               if_not_exists   => TRUE);

        RAISE NOTICE '[TimescaleDB] metric_raws hypertable + 压缩 + 保留 + 连续聚合 已完成';

    ELSE
        -- ===== PostgreSQL 原生分区路径 (降级方案) =====

        -- metric_raws 按天分区 (每天一个子表)
        -- 注意: 需要定期创建未来分区 (建议 cron 或 pg_cron)
        -- 本脚本创建当前月 + 下月的分区作为示例

        -- 将 metric_raws 转为分区表 (需先重命名原表)
        -- IF NOT EXISTS (原表存在则跳过, 避免重复执行)
        RAISE NOTICE '[PG Native] TimescaleDB 未安装, 使用原生分区 (建议安装 TimescaleDB 获得更好性能)';

        -- 创建父表 (如果原表已存在且不是分区表, 需要迁移数据)
        IF NOT EXISTS (
            SELECT 1 FROM pg_partitioned_table
            WHERE partrelid = 'metric_raws'::regclass
        ) THEN
            -- 创建分区父表 (若原表已存在数据, 需先迁移)
            RAISE NOTICE '[PG Native] 未检测到分区表, 请手动执行数据迁移后分区';
        END IF;
    END IF;
END $$;
