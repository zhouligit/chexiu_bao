from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, JSON, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin


class Customer(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customer"
    __table_args__ = (UniqueConstraint("store_id", "phone", name="uq_customer_store_phone"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[int | None] = mapped_column(SmallInteger)
    source: Mapped[str | None] = mapped_column(String(30))
    remark: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    visit_count: Mapped[int] = mapped_column(default=0)
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicle"
    __table_args__ = (UniqueConstraint("store_id", "plate_number", name="uq_vehicle_store_plate"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17))
    brand: Mapped[str | None] = mapped_column(String(50))
    series: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(SmallInteger)
    color: Mapped[str | None] = mapped_column(String(20))
    mileage: Mapped[int | None] = mapped_column()
    engine_no: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(Text)
