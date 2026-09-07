from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.store import Store
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo


class AuthService:
    @staticmethod
    def login(db: Session, data: LoginRequest) -> TokenResponse:
        user = (
            db.query(User)
            .filter(User.username == data.username, User.deleted_at.is_(None))
            .first()
        )
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("用户名或密码错误")
        if user.status != 1:
            raise UnauthorizedError("账号已禁用")

        user.last_login_at = datetime.now(UTC)
        db.commit()
        db.refresh(user)

        token_extra = {"user_id": user.id, "store_id": user.store_id, "role": user.role}
        access_token = create_access_token(str(user.id), token_extra)
        refresh_token = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserInfo.model_validate(user),
        )

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = int(payload["sub"])
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if user is None or user.status != 1:
            raise UnauthorizedError("用户不存在或已禁用")

        token_extra = {"user_id": user.id, "store_id": user.store_id, "role": user.role}
        access_token = create_access_token(str(user.id), token_extra)
        new_refresh_token = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user=UserInfo.model_validate(user),
        )

    @staticmethod
    def get_me(db: Session, user_id: int) -> UserInfo:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if user is None:
            raise NotFoundError("用户不存在")
        return UserInfo.model_validate(user)


class SeedService:
    @staticmethod
    def ensure_demo_data(db: Session) -> None:
        from app.core.security import hash_password

        store = db.query(Store).filter(Store.code == "demo").first()
        if store is None:
            store = Store(name="演示汽修店", code="demo", phone="400-000-0000", address="演示地址")
            db.add(store)
            db.flush()

        user = (
            db.query(User)
            .filter(User.store_id == store.id, User.username == "admin")
            .first()
        )
        if user is None:
            user = User(
                store_id=store.id,
                username="admin",
                password_hash=hash_password("admin123"),
                name="管理员",
                role="owner",
            )
            db.add(user)
            db.flush()

        from decimal import Decimal

        from app.models.service_item import ServiceItem

        default_services = [
            ("小保养", Decimal("299")),
            ("大保养", Decimal("599")),
            ("更换机油", Decimal("150")),
            ("四轮定位", Decimal("200")),
            ("洗车", Decimal("30")),
            ("补胎", Decimal("50")),
        ]
        for name, price in default_services:
            exists = (
                db.query(ServiceItem)
                .filter(ServiceItem.store_id == store.id, ServiceItem.name == name)
                .first()
            )
            if not exists:
                db.add(ServiceItem(store_id=store.id, name=name, price=price))

        from app.models.inventory import Part
        from app.dependencies import CurrentUser
        from app.schemas.inventory import StockInRequest
        from app.services.inventory_service import InventoryService

        default_parts = [
            ("机油滤清器", "OF-001", Decimal("35"), Decimal("60"), 20, 5),
            ("空气滤清器", "AF-001", Decimal("45"), Decimal("80"), 15, 5),
            ("全合成机油 4L", "OIL-001", Decimal("180"), Decimal("280"), 30, 10),
            ("刹车片前", "BP-F", Decimal("120"), Decimal("200"), 10, 3),
        ]
        seed_user = CurrentUser(
            id=user.id,
            store_id=store.id,
            username="admin",
            name="管理员",
            role="owner",
        )
        for name, code, purchase, sell, stock, safe in default_parts:
            exists = (
                db.query(Part)
                .filter(Part.store_id == store.id, Part.code == code)
                .first()
            )
            if not exists:
                part = Part(
                    store_id=store.id,
                    name=name,
                    code=code,
                    purchase_price=purchase,
                    sell_price=sell,
                    safe_stock=safe,
                )
                db.add(part)
                db.flush()
                InventoryService.stock_in(
                    db,
                    seed_user,
                    StockInRequest(part_id=part.id, quantity=stock, unit_cost=purchase, remark="初始入库"),
                )

        db.commit()
