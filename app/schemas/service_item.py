from decimal import Decimal

from pydantic import BaseModel, Field


class ServiceItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str | None = None
    category_id: int | None = None
    price: Decimal = Field(ge=0)
    labor_hours: Decimal | None = None
    unit: str = "次"
    description: str | None = None


class ServiceItemResponse(BaseModel):
    id: int
    store_id: int
    category_id: int | None = None
    name: str
    code: str | None = None
    price: float
    labor_hours: float | None = None
    unit: str
    description: str | None = None
    status: int

    model_config = {"from_attributes": True}
