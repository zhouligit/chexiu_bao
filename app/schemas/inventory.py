from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PartCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=32)
    brand: str | None = None
    spec: str | None = None
    unit: str = "个"
    purchase_price: Decimal | None = Field(default=None, ge=0)
    sell_price: Decimal | None = Field(default=None, ge=0)
    safe_stock: int = Field(default=0, ge=0)
    initial_stock: int = Field(default=0, ge=0)


class StockInRequest(BaseModel):
    part_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    remark: str | None = None


class StockOutRequest(BaseModel):
    part_id: int
    quantity: int = Field(gt=0)
    remark: str | None = None


class PartUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=32)
    brand: str | None = None
    spec: str | None = None
    unit: str | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)
    sell_price: Decimal | None = Field(default=None, ge=0)
    safe_stock: int | None = Field(default=None, ge=0)


class PartWithStock(BaseModel):
    id: int
    store_id: int
    name: str
    code: str | None = None
    brand: str | None = None
    spec: str | None = None
    unit: str
    purchase_price: float | None = None
    sell_price: float | None = None
    safe_stock: int
    status: int
    quantity: int = 0
    locked_quantity: int = 0
    available_quantity: int = 0
    avg_cost: float | None = None
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


class InventoryLogResponse(BaseModel):
    id: int
    part_id: int
    part_name: str | None = None
    type: str
    quantity: int
    before_qty: int
    after_qty: int
    ref_type: str | None = None
    ref_id: int | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


LOG_TYPE_LABELS = {
    "in": "入库",
    "out": "出库",
    "lock": "锁定",
    "unlock": "释放",
}
