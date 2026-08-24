-- P1-4: 测点幂等去重 — 为 metric_raws 增加 (device_id, metric_name, ts) 唯一键
-- 避免 Kafka at-least-once 重投产生重复落库。
-- 用法 (在目标库执行, 需以超级用户/表属主运行):
--   psql -d <db> -f 007_metric_raw_unique.sql
--
-- 说明: 本脚本使用 CREATE UNIQUE INDEX CONCURRENTLY, 不阻塞线上读写,
--       适合对已上线的大表在线加唯一约束 (会在建索引期间短暂占用 2 个连接)。
--       若表为空或很小, alembic 迁移 0003 的普通建索引即可。

-- 1) 清理历史重复行: 同 (device_id, metric_name, ts) 仅保留 id 最大一条
DELETE FROM metric_raws a
USING metric_raws b
WHERE a.device_id = b.device_id
  AND a.metric_name = b.metric_name
  AND a.ts = b.ts
  AND a.id < b.id;

-- 2) 并发建立唯一索引 (不阻塞读写; TimescaleDB hypertable 同样支持,
--    因唯一约束已包含分区时间列 ts)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_metric_raw_device_name_ts
  ON metric_raws (device_id, metric_name, ts);
