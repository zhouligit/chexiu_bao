"""store rbac permissions and roles

Revision ID: 009
Revises: 008
Create Date: 2026-10-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permission",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort", sa.SmallInteger(), nullable=True),
        sa.Column("is_sensitive", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "store_role",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("is_system", sa.SmallInteger(), nullable=True),
        sa.Column("data_policy", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "slug", name="uq_store_role_store_slug"),
    )
    op.create_index("idx_store_role_store", "store_role", ["store_id"])

    op.create_table(
        "store_role_permission",
        sa.Column("store_role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_role_id"], ["store_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("store_role_id", "permission_id"),
    )

    op.add_column("user", sa.Column("role_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_user_store_role", "user", "store_role", ["role_id"], ["id"])
    op.create_index("idx_user_role", "user", ["role_id"])

    from sqlalchemy.orm import sessionmaker

    from app.services.role_bootstrap import RoleBootstrap

    bind = op.get_bind()
    Session = sessionmaker(bind=bind)
    db = Session()
    try:
        RoleBootstrap.bootstrap_all_stores(db)
        db.commit()
    finally:
        db.close()


def downgrade() -> None:
    op.drop_index("idx_user_role", table_name="user")
    op.drop_constraint("fk_user_store_role", "user", type_="foreignkey")
    op.drop_column("user", "role_id")
    op.drop_table("store_role_permission")
    op.drop_index("idx_store_role_store", table_name="store_role")
    op.drop_table("store_role")
    op.drop_table("permission")
