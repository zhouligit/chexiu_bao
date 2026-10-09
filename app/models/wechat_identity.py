from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.store import TimestampMixin


class WechatIdentity(Base, TimestampMixin):
    """微信 openid 与门店员工 / 车主客户的绑定关系。"""

    __tablename__ = "wechat_identity"
    __table_args__ = (
        UniqueConstraint("appid", "openid", name="uq_wechat_identity_appid_openid"),
    )

    # SQLite 仅 INTEGER PK 支持自增；生产 MySQL/PG 仍用 BIGINT
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    store_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("store.id"), index=True)
    openid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unionid: Mapped[str | None] = mapped_column(String(64))
    appid: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer.id"), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    client: Mapped[str] = mapped_column(String(20), default="store")  # store | owner
