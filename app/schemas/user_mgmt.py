from datetime import datetime

from pydantic import BaseModel, Field

ALLOWED_ROLES = ("owner", "manager", "receptionist", "technician", "warehouse", "finance")

ROLE_LABELS = {
    "owner": "老板",
    "manager": "店长",
    "receptionist": "前台",
    "technician": "技师",
    "warehouse": "仓管",
    "finance": "财务",
}


class UserListItem(BaseModel):
    id: int
    store_id: int
    username: str
    name: str
    phone: str | None = None
    role: str
    status: int
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    role: str = Field(default="receptionist")


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    role: str | None = None
    status: int | None = None
    password: str | None = Field(default=None, min_length=6, max_length=100)
