from pydantic import BaseModel, Field

from app.schemas.auth import UserInfo


class MpLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    client: str = Field(default="store", pattern="^(store|owner)$")


class MpBindRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)
    client: str = Field(default="store", pattern="^(store|owner)$")


class MpLoginResponse(BaseModel):
    token: str
    bound: bool
    user: UserInfo | None = None
    openid: str | None = None
