from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import TimestampMixin

WORK_BAY_IDLE = 1
WORK_BAY_BUSY = 2
WORK_BAY_DISABLED = 0

WORK_BAY_TYPE_LABELS = {
    "repair": "机修",
    "wash": "洗车",
    "beauty": "美容",
}


class WorkBay(Base, TimestampMixin):
    __tablename__ = "work_bay"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[int] = mapped_column(SmallInteger, default=WORK_BAY_IDLE)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
