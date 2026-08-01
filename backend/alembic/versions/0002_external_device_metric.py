"""external device & raw metric tables

Revision ID: 0002_external_device_metric
Revises: 
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_external_device_metric"
down_revision = "0001_init_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_devices",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("sn", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("vendor", sa.String(length=64), nullable=True),
        sa.Column("domain", sa.String(length=32), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("protocol", sa.String(length=32), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_external_devices_device_id", "external_devices", ["device_id"], unique=True)
    op.create_index("ix_external_devices_domain", "external_devices", ["domain"])
    op.create_index("ix_external_devices_category", "external_devices", ["category"])

    op.create_table(
        "metric_raws",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("quality", sa.String(length=16), server_default="good", nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_metric_raws_device_id", "metric_raws", ["device_id"])
    op.create_index("ix_metric_raws_ts", "metric_raws", ["ts"])
    op.create_index("ix_metric_raws_metric_name", "metric_raws", ["metric_name"])
    op.create_index("ix_metric_raw_device_ts", "metric_raws", ["device_id", "ts"])
    op.create_index("ix_metric_raw_device_name", "metric_raws", ["device_id", "metric_name"])


def downgrade() -> None:
    op.drop_index("ix_metric_raw_device_name", table_name="metric_raws")
    op.drop_index("ix_metric_raw_device_ts", table_name="metric_raws")
    op.drop_index("ix_metric_raws_metric_name", table_name="metric_raws")
    op.drop_index("ix_metric_raws_ts", table_name="metric_raws")
    op.drop_index("ix_metric_raws_device_id", table_name="metric_raws")
    op.drop_table("metric_raws")

    op.drop_index("ix_external_devices_category", table_name="external_devices")
    op.drop_index("ix_external_devices_domain", table_name="external_devices")
    op.drop_index("ix_external_devices_device_id", table_name="external_devices")
    op.drop_table("external_devices")
