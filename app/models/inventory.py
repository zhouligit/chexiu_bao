from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin


class Part(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "part"
    __table_args__ = (UniqueConstraint("store_id", "code", name="uq_part_store_code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32))
    brand: Mapped[str | None] = mapped_column(String(50))
    spec: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(10), default="个")
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    sell_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    safe_stock: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("store_id", "part_id", name="uq_inventory_store_part"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    warehouse_location: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    before_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    after_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    remark: Mapped[str | None] = mapped_column(String(255))
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
