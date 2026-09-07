"""work orders schema

Revision ID: 002
Revises: 001
Create Date: 2026-09-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_category",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_service_category_store", "service_category", ["store_id"])

    op.create_table(
        "service_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cost_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("labor_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("labor_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("unit", sa.String(length=10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_service_item_store", "service_item", ["store_id"])

    op.create_table(
        "work_order",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("order_no", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("vehicle_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mileage_in", sa.Integer(), nullable=True),
        sa.Column("fuel_level", sa.String(length=10), nullable=True),
        sa.Column("customer_request", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("receptionist_id", sa.BigInteger(), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("payable_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("estimated_finish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )
    op.create_index("idx_wo_store", "work_order", ["store_id"])
    op.create_index("idx_wo_status", "work_order", ["store_id", "status"])

    op.create_table(
        "work_order_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=False),
        sa.Column("service_item_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("discount", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("labor_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("technician_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wo_item", "work_order_item", ["work_order_id"])

    op.create_table(
        "work_order_part",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=False),
        sa.Column("part_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cost_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wo_part", "work_order_part", ["work_order_id"])

    op.create_table(
        "work_order_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wo_log", "work_order_log", ["work_order_id"])

    op.create_table(
        "payment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_no", sa.String(length=32), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("payable_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("cashier_id", sa.BigInteger(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_no"),
    )
    op.create_index("idx_payment_wo", "payment", ["work_order_id"])

    op.create_table(
        "payment_detail",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("transaction_no", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_payment_detail", "payment_detail", ["payment_id"])


def downgrade() -> None:
    op.drop_index("idx_payment_detail", table_name="payment_detail")
    op.drop_table("payment_detail")
    op.drop_index("idx_payment_wo", table_name="payment")
    op.drop_table("payment")
    op.drop_index("idx_wo_log", table_name="work_order_log")
    op.drop_table("work_order_log")
    op.drop_index("idx_wo_part", table_name="work_order_part")
    op.drop_table("work_order_part")
    op.drop_index("idx_wo_item", table_name="work_order_item")
    op.drop_table("work_order_item")
    op.drop_index("idx_wo_status", table_name="work_order")
    op.drop_index("idx_wo_store", table_name="work_order")
    op.drop_table("work_order")
    op.drop_index("idx_service_item_store", table_name="service_item")
    op.drop_table("service_item")
    op.drop_index("idx_service_category_store", table_name="service_category")
    op.drop_table("service_category")
