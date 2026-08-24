"""init core tables: idc / cabinet / server / point_data

Revision ID: 0001_init_core_tables
Revises:
Create Date: 2026-07-23

说明:
- point_data 为时序大表, 建议在迁移后执行 TimescaleDB hypertable 转换
  (见 deploy/sql/003_point_data_hypertable.sql)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_init_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- 数据中心 ----------
    op.create_table(
        "idc",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("address", sa.String(255), server_default=""),
        sa.Column("power_capacity_mw", sa.Numeric(10, 3), server_default="0"),
        sa.Column("cooling_capacity_mw", sa.Numeric(10, 3), server_default="0"),
        sa.Column("rack_capacity", sa.Integer, server_default="0"),
        sa.Column("rooms", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(16), server_default="运营"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_idc_code"),
        comment="数据中心",
    )
    op.create_index("ix_idc_code", "idc", ["code"], unique=True)
    op.create_index("ix_idc_region", "idc", ["region"])
    op.create_index("ix_idc_status", "idc", ["status"])

    # ---------- 机柜 ----------
    op.create_table(
        "cabinet",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("idc_id", sa.Integer, sa.ForeignKey("idc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("room", sa.String(32), nullable=False),
        sa.Column("row", sa.String(16), server_default=""),
        sa.Column("u_total", sa.Integer, server_default="42"),
        sa.Column("u_used", sa.Integer, server_default="0"),
        sa.Column("rated_power_kw", sa.Numeric(8, 2), server_default="10.0"),
        sa.Column("current_power_kw", sa.Numeric(8, 2), server_default="0"),
        sa.Column("status", sa.String(16), server_default="在用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="机柜",
    )
    op.create_index("ix_cabinet_code", "cabinet", ["code"])
    op.create_index("ix_cabinet_room", "cabinet", ["room"])
    op.create_index("ix_cabinet_status", "cabinet", ["status"])
    # 同 IDC 内编号唯一 + IDC+包间 组合索引
    op.create_index("uq_cabinet_idc_code", "cabinet", ["idc_id", "code"], unique=True)
    op.create_index("ix_cabinet_idc_room", "cabinet", ["idc_id", "room"])

    # ---------- 物理服务器 ----------
    op.create_table(
        "server",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cabinet_id", sa.Integer, sa.ForeignKey("cabinet.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_no", sa.String(64), nullable=False),
        sa.Column("hostname", sa.String(128), server_default=""),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("brand", sa.String(64), server_default=""),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column("u_start", sa.Integer, nullable=False),
        sa.Column("u_end", sa.Integer, nullable=False),
        sa.Column("cpu_model", sa.String(128), server_default=""),
        sa.Column("cpu_count", sa.Integer, server_default="2"),
        sa.Column("cpu_cores", sa.Integer, server_default="0"),
        sa.Column("memory_gb", sa.Integer, server_default="0"),
        sa.Column("disk_desc", sa.String(255), server_default=""),
        sa.Column("business", sa.String(128), server_default=""),
        sa.Column("status", sa.String(16), server_default="在线"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("u_end >= u_start", name="ck_server_u_range"),
        sa.CheckConstraint("u_start >= 1", name="ck_server_u_start_pos"),
        sa.UniqueConstraint("asset_no", name="uq_server_asset_no"),
        comment="物理服务器",
    )
    op.create_index("ix_server_asset_no", "server", ["asset_no"], unique=True)
    op.create_index("ix_server_ip", "server", ["ip"])
    op.create_index("ix_server_business", "server", ["business"])
    op.create_index("ix_server_status", "server", ["status"])
    op.create_index("ix_server_cabinet_u", "server", ["cabinet_id", "u_start", "u_end"])
    op.create_index("ix_server_ip_status", "server", ["ip", "status"])

    # ---------- 实时测点时序 ----------
    op.create_table(
        "point_data",
        sa.Column("id", sa.BigInteger, autoincrement=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", sa.BigInteger, nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(16), server_default=""),
        sa.Column("quality", sa.SmallInteger, server_default="100"),
        sa.PrimaryKeyConstraint("id", "ts", name="pk_point_data"),
        comment="实时测点时序数据",
    )
    op.create_index("ix_pd_target_metric_ts", "point_data", ["target_type", "target_id", "metric", "ts"])
    op.create_index("ix_pd_metric_ts", "point_data", ["metric", "ts"])
    # BRIN 时间索引: 顺序写时序表大范围扫描极省空间
    op.create_index("ix_pd_ts_brin", "point_data", ["ts"], postgresql_using="brin")


def downgrade() -> None:
    op.drop_table("point_data")
    op.drop_table("server")
    op.drop_table("cabinet")
    op.drop_table("idc")
