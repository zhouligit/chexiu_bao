from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("store_id", "username", name="uq_user_store_username"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("store.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    store = relationship("Store", lazy="joined")
