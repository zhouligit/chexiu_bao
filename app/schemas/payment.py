from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentDetailResponse(BaseModel):
    id: int
    method: str
    amount: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentListItem(BaseModel):
    id: int
    payment_no: str
    work_order_id: int
    order_no: str | None = None
    customer_name: str | None = None
    plate_number: str | None = None
    total_amount: float
    discount_amount: float
    payable_amount: float
    paid_amount: float
    refunded_amount: float
    status: str
    settled_at: datetime | None = None
    created_at: datetime


class PaymentDetailFull(BaseModel):
    id: int
    payment_no: str
    work_order_id: int
    order_no: str | None = None
    customer_name: str | None = None
    plate_number: str | None = None
    total_amount: float
    discount_amount: float
    payable_amount: float
    paid_amount: float
    refunded_amount: float
    status: str
    settled_at: datetime | None = None
    details: list[PaymentDetailResponse] = []
    created_at: datetime


class RefundRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str | None = None
