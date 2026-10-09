from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class AppointmentCreate(BaseModel):
    contact_name: str = Field(min_length=1, max_length=50)
    contact_phone: str = Field(min_length=5, max_length=20)
    plate_number: str | None = Field(default=None, max_length=20)
    scheduled_start: datetime
    scheduled_end: datetime | None = None
    customer_id: int | None = None
    vehicle_id: int | None = None
    service_item_ids: list[int] | None = None
    remark: str | None = None
    source: str = Field(default="mp_store", pattern="^(mp_owner|mp_store|phone)$")
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0)


class AppointmentUpdate(BaseModel):
    contact_name: str | None = Field(default=None, min_length=1, max_length=50)
    contact_phone: str | None = Field(default=None, min_length=5, max_length=20)
    plate_number: str | None = Field(default=None, max_length=20)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    customer_id: int | None = None
    vehicle_id: int | None = None
    service_item_ids: list[int] | None = None
    remark: str | None = None


class AppointmentCancelRequest(BaseModel):
    remark: str | None = None


class AppointmentConvertRequest(BaseModel):
    mileage_in: int | None = None
    fuel_level: str | None = None
    customer_request: str | None = None


class AppointmentItem(BaseModel):
    id: int
    status: str
    status_label: str
    contact_name: str
    contact_phone: str
    plate_number: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime | None = None
    source: str
    source_label: str
    customer_id: int | None = None
    vehicle_id: int | None = None
    work_order_id: int | None = None
    deposit_amount: float = 0
    pay_status: str = "unpaid"
    service_item_ids: list[int] = Field(default_factory=list)
    remark: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("service_item_ids", mode="before")
    @classmethod
    def parse_ids(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip().isdigit()]
        return []
