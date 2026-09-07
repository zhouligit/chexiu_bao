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


class UserInfo(BaseModel):
    id: int
    store_id: int
    username: str
    name: str
    phone: str | None = None
    role: str
    avatar_url: str | None = None
    store: StoreBrief | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo
