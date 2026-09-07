"""inventory schema

Revision ID: 003
Revises: 002
Create Date: 2026-09-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "part",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("brand", sa.String(length=50), nullable=True),
        sa.Column("spec", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=10), nullable=True),
        sa.Column("purchase_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("sell_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("safe_stock", sa.Integer(), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "code", name="uq_part_store_code"),
    )
    op.create_index("idx_part_store", "part", ["store_id"])

    op.create_table(
        "inventory",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("part_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("locked_quantity", sa.Integer(), nullable=True),
        sa.Column("avg_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("warehouse_location", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "part_id", name="uq_inventory_store_part"),
    )
    op.create_index("idx_inventory_store", "inventory", ["store_id"])

    op.create_table(
        "inventory_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("part_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("before_qty", sa.Integer(), nullable=False),
        sa.Column("after_qty", sa.Integer(), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_inv_log_part", "inventory_log", ["store_id", "part_id"])


def downgrade() -> None:
    op.drop_index("idx_inv_log_part", table_name="inventory_log")
    op.drop_table("inventory_log")
    op.drop_index("idx_inventory_store", table_name="inventory")
    op.drop_table("inventory")
    op.drop_index("idx_part_store", table_name="part")
    op.drop_table("part")
