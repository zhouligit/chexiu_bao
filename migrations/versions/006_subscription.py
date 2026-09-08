"""subscription orders

Revision ID: 006
Revises: 005
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store",
        sa.Column("subscription_status", sa.String(length=20), server_default="trial", nullable=False),
    )

    op.create_table(
        "subscription_order",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("order_no", sa.String(length=32), nullable=False),
        sa.Column("plan_code", sa.String(length=20), nullable=False),
        sa.Column("billing_cycle", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("transaction_no", sa.String(length=64), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )
    op.create_index("idx_subscription_order_store", "subscription_order", ["store_id"])
    op.create_index("idx_subscription_order_status", "subscription_order", ["status"])


def downgrade() -> None:
    op.drop_index("idx_subscription_order_status", table_name="subscription_order")
    op.drop_index("idx_subscription_order_store", table_name="subscription_order")
    op.drop_table("subscription_order")
    op.drop_column("store", "subscription_status")
