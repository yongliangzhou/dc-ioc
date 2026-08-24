-- B4: 容量/能耗「分析型长期时序」表。与 metric_raws 解耦, 由每日 rollup 写入,
--     不受 P0-1 retention 清理影响, 使容量/能耗历史长期留存 (不再依赖快照逆推)。
-- 用法 (在目标库执行): psql -d <db> -f 008_capacity_energy_history.sql

CREATE TABLE IF NOT EXISTS capacity_energy_history (
    id          BIGSERIAL PRIMARY KEY,
    idc_code    VARCHAR(32) NOT NULL DEFAULT 'DC1',
    metric_key  VARCHAR(64) NOT NULL,
    bucket      TIMESTAMPTZ NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(16),
    source      VARCHAR(16) NOT NULL DEFAULT 'real',
    meta        JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 幂等 upsert 键: 同 (园区, 指标, 日桶) 唯一
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_ceh_scope_key_bucket'
    ) THEN
        ALTER TABLE capacity_energy_history
            ADD CONSTRAINT uq_ceh_scope_key_bucket
            UNIQUE (idc_code, metric_key, bucket);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_ceh_key_bucket
    ON capacity_energy_history (metric_key, bucket);
