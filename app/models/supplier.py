from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    remark: Mapped[str | None] = mapped_column(Text)


class WorkOrderInspection(Base):
    __tablename__ = "work_order_inspection"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("work_order.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    items: Mapped[list | None] = mapped_column(JSON, default=list)
    photos: Mapped[list | None] = mapped_column(JSON, default=list)
    valuables: Mapped[str | None] = mapped_column(Text)
    inspector_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
