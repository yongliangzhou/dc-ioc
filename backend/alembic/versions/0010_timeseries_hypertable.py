"""时序大表 hypertable (数据库设计文档 第八章 8.6: 时序大表专项)

将时序大表 point_data / metric_raws 转为 TimescaleDB hypertable (按 ts 分区),
并启用列存压缩、数据保留策略与连续聚合视图 (加速看板/趋势查询)。

开发/测试库由 app.core.lifespan._ensure_hypertables 自愈创建(无需手动执行);
生产库经本修订补齐。TimescaleDB 要求分区列(ts)必须包含在所有唯一索引/主键中,
故对 metric_raws 原 (id) 主键补 ts 进复合主键 (id, ts)。

前提: 数据库已安装 TimescaleDB 扩展 (docker 镜像 timescale/timescaledb)。
若扩展不可用, 本修订仅打印警告并跳过 (退回普通关系表, 应用仍可运行)。

downgrade: 删除连续聚合视图与压缩/保留策略; hypertable 本身保留
(彻底回退需 DROP EXTENSION timescaledb CASCADE, 属破坏性操作, 不在此自动执行)。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0010_timeseries_hypertable"
down_revision: Union[str, None] = "0009_row_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TARGETS = {
    "point_data": {
        "segmentby": "target_type, target_id, metric",
        "compress_after": "INTERVAL '30 days'",
        "retention": "INTERVAL '1 year'",
        "chunk": "INTERVAL '7 days'",
        "cagg": ("point_data_5min", "target_type, target_id, metric", "5 minutes"),
    },
    "metric_raws": {
        "segmentby": "device_id, metric_name",
        "compress_after": "INTERVAL '7 days'",
        "retention": "INTERVAL '90 days'",
        "chunk": "INTERVAL '1 day'",
        "cagg": ("metric_raws_5min", "device_id, metric_name", "5 minutes"),
    },
}


def _has_timescaledb(bind) -> bool:
    try:
        return bind.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='timescaledb')"
        )).scalar()
    except Exception:  # noqa: BLE001
        return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_timescaledb(bind):
        try:
            bind.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        except Exception as e:  # noqa: BLE001
            print(f"[0010] 未检测到 TimescaleDB 扩展, 跳过时序 hypertable "
                  f"(请用 timescale/timescaledb 镜像): {e}")
            return

    # 所有 DDL 走独立 autocommit 连接: CREATE MATERIALIZED VIEW 不能处于事务块内。
    engine = bind.engine if hasattr(bind, "engine") else bind
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        # metric_raws 复合主键 (id, ts) — 满足 hypertable 分区列约束 (幂等)
        conn.execute(text("""
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
        """))

        for t, cfg in _TARGETS.items():
            try:
                conn.execute(text(
                    f"SELECT create_hypertable('{t}', 'ts', "
                    f"chunk_time_interval => {cfg['chunk']}, "
                    f"if_not_exists => TRUE, migrate_data => TRUE)"
                ))
                conn.execute(text(
                    f"ALTER TABLE {t} SET (timescaledb.compress, "
                    f"timescaledb.compress_segmentby = '{cfg['segmentby']}', "
                    f"timescaledb.compress_orderby = 'ts DESC')"
                ))
                conn.execute(text(
                    f"SELECT add_compression_policy('{t}', {cfg['compress_after']}, if_not_exists => TRUE)"
                ))
                conn.execute(text(
                    f"SELECT add_retention_policy('{t}', {cfg['retention']}, if_not_exists => TRUE)"
                ))
                cname, group_by, bucket = cfg["cagg"]
                conn.execute(text(f"""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS {cname}
                    WITH (timescaledb.continuous) AS
                    SELECT time_bucket('{bucket}', ts) AS bucket,
                           {group_by},
                           avg(value) AS avg_value,
                           max(value) AS max_value,
                           min(value) AS min_value,
                           count(*)   AS samples
                    FROM {t}
                    GROUP BY bucket, {group_by}
                """))
                conn.execute(text(
                    f"SELECT add_continuous_aggregate_policy('{cname}', "
                    f"start_offset => INTERVAL '1 hour', "
                    f"end_offset => INTERVAL '5 minutes', "
                    f"schedule_interval => INTERVAL '5 minutes', if_not_exists => TRUE)"
                ))
                print(f"[0010] 时序超表就绪: {t}")
            except Exception as e:  # noqa: BLE001
                print(f"[0010] 时序超表 {t} 跳过: {e}")
    finally:
        conn.close()


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_timescaledb(bind):
        return
    engine = bind.engine if hasattr(bind, "engine") else bind
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        for t, cfg in _TARGETS.items():
            cname = cfg["cagg"][0]
            try:
                conn.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {cname}"))
                conn.execute(text(f"SELECT remove_compression_policy('{t}')"))
                conn.execute(text(f"SELECT remove_retention_policy('{t}')"))
            except Exception as e:  # noqa: BLE001
                print(f"[0010] downgrade 清理 {t} 跳过: {e}")
    finally:
        conn.close()
    # 注: hypertable 本身保留; 彻底回退需 DROP EXTENSION timescaledb CASCADE。
