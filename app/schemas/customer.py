from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=20)
    gender: int | None = None
    source: str | None = None
    remark: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    gender: int | None = None
    source: str | None = None
    remark: str | None = None


class CustomerResponse(BaseModel):
    id: int
    store_id: int
    name: str
    phone: str
    gender: int | None = None
    source: str | None = None
    remark: str | None = None
    total_spent: float = 0
    visit_count: int = 0
    last_visit_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleCreate(BaseModel):
    customer_id: int
    plate_number: str = Field(min_length=1, max_length=20)
    vin: str | None = Field(default=None, max_length=17)
    brand: str | None = None
    series: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    mileage: int | None = None
    remark: str | None = None


class VehicleUpdate(BaseModel):
    plate_number: str | None = Field(default=None, min_length=1, max_length=20)
    vin: str | None = Field(default=None, max_length=17)
    brand: str | None = None
    series: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    mileage: int | None = None
    remark: str | None = None


class VehicleResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int
    plate_number: str
    vin: str | None = None
    brand: str | None = None
    series: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    mileage: int | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
