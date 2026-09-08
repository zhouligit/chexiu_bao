"""supplier and inspection

Revision ID: 004
Revises: 003
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("contact", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_supplier_store", "supplier", ["store_id"])

    op.create_table(
        "work_order_inspection",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("photos", sa.JSON(), nullable=True),
        sa.Column("valuables", sa.Text(), nullable=True),
        sa.Column("inspector_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wo_inspection", "work_order_inspection", ["work_order_id"])

    op.add_column(
        "payment",
        sa.Column("refunded_amount", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("payment", "refunded_amount")
    op.drop_index("idx_wo_inspection", table_name="work_order_inspection")
    op.drop_table("work_order_inspection")
    op.drop_index("idx_supplier_store", table_name="supplier")
    op.drop_table("supplier")
