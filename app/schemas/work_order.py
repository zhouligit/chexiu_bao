from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WorkOrderCreate(BaseModel):
    customer_id: int
    vehicle_id: int
    mileage_in: int | None = None
    fuel_level: str | None = None
    customer_request: str | None = None
    internal_note: str | None = None


class WorkOrderItemCreate(BaseModel):
    service_item_id: int | None = None
    name: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    labor_hours: Decimal | None = None
    type: str = "normal"


class WorkOrderPartCreate(BaseModel):
    part_id: int | None = None
    name: str | None = Field(default=None, max_length=100)
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class StatusTransition(BaseModel):
    to_status: str
    remark: str | None = None


class AssignRequest(BaseModel):
    technician_id: int
    item_ids: list[int] | None = None


class SettleRequest(BaseModel):
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    payments: list["PaymentMethodInput"] = Field(min_length=1)


class PaymentMethodInput(BaseModel):
    method: str = Field(pattern="^(cash|wechat|alipay|bank|card)$")
    amount: Decimal = Field(gt=0)


class WorkOrderItemResponse(BaseModel):
    id: int
    name: str
    quantity: float
    unit_price: float
    discount: float
    amount: float
    labor_hours: float | None = None
    type: str
    status: str
    technician_id: int | None = None

    model_config = {"from_attributes": True}


class WorkOrderPartResponse(BaseModel):
    id: int
    name: str
    quantity: int
    unit_price: float
    amount: float
    status: str

    model_config = {"from_attributes": True}


class WorkOrderLogResponse(BaseModel):
    id: int
    from_status: str | None
    to_status: str
    operator_id: int | None
    remark: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerBrief(BaseModel):
    id: int
    name: str
    phone: str

    model_config = {"from_attributes": True}


class VehicleBrief(BaseModel):
    id: int
    plate_number: str
    brand: str | None = None
    model: str | None = None

    model_config = {"from_attributes": True}


class WorkOrderListItem(BaseModel):
    id: int
    order_no: str
    status: str
    status_label: str
    customer_id: int
    vehicle_id: int
    customer_name: str | None = None
    plate_number: str | None = None
    total_amount: float
    payable_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderDetail(BaseModel):
    id: int
    order_no: str
    status: str
    status_label: str = ""
    customer_id: int
    vehicle_id: int
    customer: CustomerBrief | None = None
    vehicle: VehicleBrief | None = None
    mileage_in: int | None = None
    fuel_level: str | None = None
    customer_request: str | None = None
    internal_note: str | None = None
    receptionist_id: int | None = None
    total_amount: float
    discount_amount: float
    payable_amount: float
    paid_amount: float
    items: list[WorkOrderItemResponse] = []
    parts: list[WorkOrderPartResponse] = []
    logs: list[WorkOrderLogResponse] = []
    created_at: datetime
    finished_at: datetime | None = None
    settled_at: datetime | None = None

    model_config = {"from_attributes": True}
