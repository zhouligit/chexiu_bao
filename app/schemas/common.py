from pydantic import BaseModel, Field


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    keyword: str | None = None
    status: str | None = None


class PageResult(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
