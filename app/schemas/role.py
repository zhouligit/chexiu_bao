from pydantic import BaseModel, Field


class PermissionItem(BaseModel):
    id: int
    code: str
    module: str
    name: str
    sort: int
    is_sensitive: bool


class StoreRoleListItem(BaseModel):
    id: int
    store_id: int
    slug: str
    name: str
    is_system: bool
    user_count: int = 0
    permission_count: int = 0

    model_config = {"from_attributes": True}


class StoreRoleDetail(BaseModel):
    id: int
    store_id: int
    slug: str
    name: str
    is_system: bool
    data_policy: dict
    permission_codes: list[str]


class StoreRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str | None = Field(default=None, max_length=32)
    copy_from_id: int | None = None
    permission_codes: list[str] = Field(default_factory=list)
    data_policy: dict | None = None


class StoreRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    permission_codes: list[str] | None = None
    data_policy: dict | None = None
