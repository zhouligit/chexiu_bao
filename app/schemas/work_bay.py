from datetime import datetime

from pydantic import BaseModel, Field


class WorkBayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: str | None = Field(default="repair", pattern="^(repair|wash|beauty)$")
    status: int = Field(default=1, ge=0, le=2)
    sort_order: int = Field(default=0, ge=0)


class WorkBayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    type: str | None = Field(default=None, pattern="^(repair|wash|beauty)$")
    status: int | None = Field(default=None, ge=0, le=2)
    sort_order: int | None = Field(default=None, ge=0)


class WorkBayResponse(BaseModel):
    id: int
    store_id: int
    name: str
    type: str | None = None
    status: int
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
