from pydantic import BaseModel, Field


class MpLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    client: str = Field(default="store", pattern="^(store|owner)$")


class MpBindRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)
    client: str = Field(default="store", pattern="^(store|owner)$")


class MpUserBrief(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: str | None = None
    store_id: int | None = None
    store_name: str | None = None


class MpLoginResponse(BaseModel):
    token: str
    bound: bool
    user: MpUserBrief | None = None
    openid: str | None = None
