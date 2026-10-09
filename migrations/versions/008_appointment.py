"""appointment table for mini program

Revision ID: 008
Revises: 007
Create Date: 2026-10-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("vehicle_id", sa.BigInteger(), nullable=True),
        sa.Column("contact_name", sa.String(length=50), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=False),
        sa.Column("plate_number", sa.String(length=20), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="mp_store", nullable=False),
        sa.Column("work_order_id", sa.BigInteger(), nullable=True),
        sa.Column("deposit_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("pay_status", sa.String(length=20), server_default="unpaid", nullable=False),
        sa.Column("service_item_ids", sa.String(length=500), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_appointment_store", "appointment", ["store_id"])
    op.create_index("idx_appointment_status", "appointment", ["status"])
    op.create_index("idx_appointment_start", "appointment", ["scheduled_start"])
    op.create_index("idx_appointment_customer", "appointment", ["customer_id"])
    op.create_index("idx_appointment_work_order", "appointment", ["work_order_id"])


def downgrade() -> None:
    op.drop_index("idx_appointment_work_order", table_name="appointment")
    op.drop_index("idx_appointment_customer", table_name="appointment")
    op.drop_index("idx_appointment_start", table_name="appointment")
    op.drop_index("idx_appointment_status", table_name="appointment")
    op.drop_index("idx_appointment_store", table_name="appointment")
    op.drop_table("appointment")
