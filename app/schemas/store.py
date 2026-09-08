from datetime import datetime

from pydantic import BaseModel, Field


class StoreResponse(BaseModel):
    id: int
    name: str
    code: str | None = None
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    status: int
    plan: str
    expired_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)


class RegisterRequest(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    store_phone: str | None = Field(default=None, max_length=20)
    store_address: str | None = Field(default=None, max_length=255)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
