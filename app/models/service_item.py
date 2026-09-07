from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin


class ServiceCategory(Base, TimestampMixin):
    __tablename__ = "service_category"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)


class ServiceItem(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    labor_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    labor_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(10), default="次")
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
