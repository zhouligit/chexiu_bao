"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=True),
        sa.Column("plan", sa.String(length=20), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "username", name="uq_user_store_username"),
    )
    op.create_index("idx_user_store", "user", ["store_id"])

    op.create_table(
        "customer",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("gender", sa.SmallInteger(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("total_spent", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=True),
        sa.Column("last_visit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "phone", name="uq_customer_store_phone"),
    )
    op.create_index("idx_customer_store", "customer", ["store_id"])

    op.create_table(
        "vehicle",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("plate_number", sa.String(length=20), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=True),
        sa.Column("brand", sa.String(length=50), nullable=True),
        sa.Column("series", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("engine_no", sa.String(length=50), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "plate_number", name="uq_vehicle_store_plate"),
    )
    op.create_index("idx_vehicle_customer", "vehicle", ["customer_id"])


def downgrade() -> None:
    op.drop_index("idx_vehicle_customer", table_name="vehicle")
    op.drop_table("vehicle")
    op.drop_index("idx_customer_store", table_name="customer")
    op.drop_table("customer")
    op.drop_index("idx_user_store", table_name="user")
    op.drop_table("user")
    op.drop_table("store")
