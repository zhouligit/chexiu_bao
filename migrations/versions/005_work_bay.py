"""work bay

Revision ID: 005
Revises: 004
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_bay",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=True),
        sa.Column("status", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_work_bay_store", "work_bay", ["store_id"])

    op.add_column("work_order", sa.Column("work_bay_id", sa.BigInteger(), nullable=True))
    op.create_index("idx_work_order_work_bay", "work_order", ["work_bay_id"])


def downgrade() -> None:
    op.drop_index("idx_work_order_work_bay", table_name="work_order")
    op.drop_column("work_order", "work_bay_id")
    op.drop_index("idx_work_bay_store", table_name="work_bay")
    op.drop_table("work_bay")
