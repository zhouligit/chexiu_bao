from sqlalchemy import BigInteger, ForeignKey, Integer, JSON, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.store import TimestampMixin

_PK = BigInteger().with_variant(Integer, "sqlite")


class Permission(Base, TimestampMixin):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_sensitive: Mapped[int] = mapped_column(SmallInteger, default=0)


class StoreRole(Base, TimestampMixin):
    __tablename__ = "store_role"
    __table_args__ = (UniqueConstraint("store_id", "slug", name="uq_store_role_store_slug"),)

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("store.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_system: Mapped[int] = mapped_column(SmallInteger, default=1)
    data_policy: Mapped[dict] = mapped_column(JSON, default=dict)

    permissions = relationship(
        "Permission",
        secondary="store_role_permission",
        lazy="selectin",
    )


class StoreRolePermission(Base):
    __tablename__ = "store_role_permission"

    store_role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("store_role.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True
    )
