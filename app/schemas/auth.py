from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str


class StoreBrief(BaseModel):
    id: int
    name: str
    code: str | None = None

    model_config = {"from_attributes": True}


class SubscriptionBrief(BaseModel):
    status: str
    status_label: str
    plan: str
    plan_name: str
    expired_at: datetime | None = None
    days_remaining: int | None = None
    is_active: bool
    can_write: bool
    message: str | None = None


class UserInfo(BaseModel):
    id: int
    store_id: int
    username: str
    name: str
    phone: str | None = None
    role: str
    avatar_url: str | None = None
    store: StoreBrief | None = None
    subscription: SubscriptionBrief | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo
