from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin

APPT_PENDING = "pending"
APPT_CONFIRMED = "confirmed"
APPT_ARRIVED = "arrived"
APPT_CANCELLED = "cancelled"
APPT_EXPIRED = "expired"
APPT_CONVERTED = "converted"

APPT_STATUS_LABELS = {
    APPT_PENDING: "待确认",
    APPT_CONFIRMED: "已确认",
    APPT_ARRIVED: "已到店",
    APPT_CANCELLED: "已取消",
    APPT_EXPIRED: "已过期",
    APPT_CONVERTED: "已转工单",
}

# 允许的状态流转（门店操作）
APPT_TRANSITIONS: dict[str, list[str]] = {
    APPT_PENDING: [APPT_CONFIRMED, APPT_CANCELLED, APPT_ARRIVED, APPT_CONVERTED],
    APPT_CONFIRMED: [APPT_ARRIVED, APPT_CANCELLED, APPT_CONVERTED, APPT_EXPIRED],
    APPT_ARRIVED: [APPT_CONVERTED, APPT_CANCELLED],
}


class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "appointment"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    contact_name: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    plate_number: Mapped[str | None] = mapped_column(String(20))
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=APPT_PENDING, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="mp_store")
    work_order_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("work_order.id"), index=True)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    pay_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    service_item_ids: Mapped[str | None] = mapped_column(String(500))  # 逗号分隔 id
    remark: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
