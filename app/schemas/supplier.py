from datetime import datetime

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    remark: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    remark: str | None = None


class SupplierResponse(BaseModel):
    id: int
    store_id: int
    name: str
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
