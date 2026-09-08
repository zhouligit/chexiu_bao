from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.store import TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    payment_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="paid")
    cashier_id: Mapped[int | None] = mapped_column(BigInteger)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    details = relationship("PaymentDetail", back_populates="payment", lazy="selectin")


class PaymentDetail(Base):
    __tablename__ = "payment_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payment.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_no: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    payment = relationship("Payment", back_populates="details")
