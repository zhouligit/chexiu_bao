from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PlanPriceOption(BaseModel):
    billing_cycle: str
    label: str
    amount: float
    unit_price_hint: str | None = None


class SubscriptionPlanResponse(BaseModel):
    code: str
    name: str
    description: str
    max_users: int
    features: list[str]
    prices: list[PlanPriceOption]


class SubscriptionStatusResponse(BaseModel):
    status: str
    status_label: str
    plan: str
    plan_name: str
    expired_at: datetime | None = None
    days_remaining: int | None = None
    is_active: bool
    is_trial: bool
    is_lifetime: bool
    grace_days: int = 0
    max_users: int
    can_write: bool
    message: str | None = None


class CreateSubscriptionOrderRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=20)
    billing_cycle: str = Field(pattern="^(monthly|yearly|lifetime)$")


class SubscriptionOrderResponse(BaseModel):
    id: int
    order_no: str
    plan_code: str
    plan_name: str
    billing_cycle: str
    billing_cycle_label: str
    amount: float
    status: str
    payment_method: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    paid_at: datetime | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivateOrderRequest(BaseModel):
    payment_method: str = Field(default="manual", pattern="^(manual|wechat|alipay|bank)$")
    transaction_no: str | None = None
    remark: str | None = None
