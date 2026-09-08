from datetime import datetime

from pydantic import BaseModel, Field


class InspectionItem(BaseModel):
    name: str
    status: str = "normal"
    note: str | None = None


class InspectionSubmit(BaseModel):
    type: str = "pre_check"
    items: list[InspectionItem]
    photos: list[str] = []
    valuables: str | None = None
    finish: bool = False


class InspectionResponse(BaseModel):
    id: int
    work_order_id: int
    type: str
    items: list[InspectionItem] | None = None
    photos: list[str] | None = None
    valuables: str | None = None
    inspector_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


DEFAULT_PRE_CHECK_ITEMS = [
    {"name": "左前轮胎", "status": "normal", "note": ""},
    {"name": "右前轮胎", "status": "normal", "note": ""},
    {"name": "左后轮胎", "status": "normal", "note": ""},
    {"name": "右后轮胎", "status": "normal", "note": ""},
    {"name": "外观漆面", "status": "normal", "note": ""},
    {"name": "灯光", "status": "normal", "note": ""},
    {"name": "内饰", "status": "normal", "note": ""},
    {"name": "随车物品", "status": "normal", "note": ""},
]
