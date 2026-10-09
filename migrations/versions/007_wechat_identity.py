"""wechat identity for mini program

Revision ID: 007
Revises: 006
Create Date: 2026-10-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wechat_identity",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=True),
        sa.Column("openid", sa.String(length=64), nullable=False),
        sa.Column("unionid", sa.String(length=64), nullable=True),
        sa.Column("appid", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("client", sa.String(length=20), server_default="store", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appid", "openid", name="uq_wechat_identity_appid_openid"),
    )
    op.create_index("idx_wechat_identity_openid", "wechat_identity", ["openid"])
    op.create_index("idx_wechat_identity_user", "wechat_identity", ["user_id"])
    op.create_index("idx_wechat_identity_customer", "wechat_identity", ["customer_id"])
    op.create_index("idx_wechat_identity_store", "wechat_identity", ["store_id"])


def downgrade() -> None:
    op.drop_index("idx_wechat_identity_store", table_name="wechat_identity")
    op.drop_index("idx_wechat_identity_customer", table_name="wechat_identity")
    op.drop_index("idx_wechat_identity_user", table_name="wechat_identity")
    op.drop_index("idx_wechat_identity_openid", table_name="wechat_identity")
    op.drop_table("wechat_identity")
