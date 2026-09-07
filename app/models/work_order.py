from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.store import SoftDeleteMixin, TimestampMixin

# 工单状态
WO_PENDING_INSPECTION = "pending_inspection"
WO_PENDING_QUOTE = "pending_quote"
WO_PENDING_CONFIRM = "pending_confirm"
WO_IN_PROGRESS = "in_progress"
WO_PENDING_QC = "pending_qc"
WO_PENDING_SETTLE = "pending_settle"
WO_COMPLETED = "completed"
WO_CANCELLED = "cancelled"

WO_TRANSITIONS: dict[str, list[str]] = {
    WO_PENDING_INSPECTION: [WO_PENDING_QUOTE, WO_CANCELLED],
    WO_PENDING_QUOTE: [WO_PENDING_CONFIRM, WO_CANCELLED],
    WO_PENDING_CONFIRM: [WO_IN_PROGRESS, WO_CANCELLED],
    WO_IN_PROGRESS: [WO_PENDING_QC, WO_CANCELLED],
    WO_PENDING_QC: [WO_PENDING_SETTLE, WO_IN_PROGRESS],
    WO_PENDING_SETTLE: [WO_COMPLETED],
}

WO_STATUS_LABELS = {
    WO_PENDING_INSPECTION: "待预检",
    WO_PENDING_QUOTE: "待报价",
    WO_PENDING_CONFIRM: "待确认",
    WO_IN_PROGRESS: "施工中",
    WO_PENDING_QC: "待质检",
    WO_PENDING_SETTLE: "待结算",
    WO_COMPLETED: "已完成",
    WO_CANCELLED: "已取消",
}


class WorkOrder(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "work_order"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=WO_PENDING_INSPECTION)
    mileage_in: Mapped[int | None] = mapped_column(Integer)
    fuel_level: Mapped[str | None] = mapped_column(String(10))
    customer_request: Mapped[str | None] = mapped_column(Text)
    internal_note: Mapped[str | None] = mapped_column(Text)
    receptionist_id: Mapped[int | None] = mapped_column(BigInteger)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    estimated_finish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items = relationship("WorkOrderItem", back_populates="work_order", lazy="selectin")
    parts = relationship("WorkOrderPart", back_populates="work_order", lazy="selectin")
    logs = relationship("WorkOrderLog", back_populates="work_order", lazy="selectin", order_by="WorkOrderLog.created_at")


class WorkOrderItem(Base, TimestampMixin):
    __tablename__ = "work_order_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("work_order.id"), nullable=False, index=True)
    service_item_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    labor_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    type: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    technician_id: Mapped[int | None] = mapped_column(BigInteger)

    work_order = relationship("WorkOrder", back_populates="items")


class WorkOrderPart(Base, TimestampMixin):
    __tablename__ = "work_order_part"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("work_order.id"), nullable=False, index=True)
    part_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    work_order = relationship("WorkOrder", back_populates="parts")


class WorkOrderLog(Base):
    __tablename__ = "work_order_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("work_order.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    remark: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    work_order = relationship("WorkOrder", back_populates="logs")
