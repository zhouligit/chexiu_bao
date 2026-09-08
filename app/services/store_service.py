import secrets
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.dependencies import CurrentUser
from app.models.inventory import Part
from app.models.service_item import ServiceItem
from app.models.store import Store
from app.models.user import User
from app.schemas.auth import TokenResponse, UserInfo
from app.schemas.inventory import StockInRequest
from app.schemas.store import RegisterRequest, StoreResponse, StoreUpdate
from app.services.auth_service import AuthService
from app.services.inventory_service import InventoryService


class StoreService:
    @staticmethod
    def get_current_store(db: Session, current_user: CurrentUser) -> StoreResponse:
        store = StoreService._get_store_or_404(db, current_user.store_id)
        return StoreResponse.model_validate(store)

    @staticmethod
    def update_store(db: Session, current_user: CurrentUser, data: StoreUpdate) -> StoreResponse:
        store = StoreService._get_store_or_404(db, current_user.store_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(store, key, value)
        db.commit()
        db.refresh(store)
        return StoreResponse.model_validate(store)

    @staticmethod
    def register(db: Session, data: RegisterRequest) -> TokenResponse:
        exists = (
            db.query(User)
            .filter(User.username == data.username, User.deleted_at.is_(None))
            .first()
        )
        if exists:
            raise ConflictError("用户名已被占用")

        code = f"s{secrets.token_hex(4)}"
        store = Store(
            name=data.store_name,
            code=code,
            phone=data.store_phone,
            address=data.store_address,
        )
        from app.services.subscription_service import SubscriptionService

        SubscriptionService.init_trial_store(store)
        db.add(store)
        db.flush()

        user = User(
            store_id=store.id,
            username=data.username,
            password_hash=hash_password(data.password),
            name=data.name,
            phone=data.phone,
            role="owner",
        )
        db.add(user)
        db.flush()

        StoreService._seed_store_defaults(db, store.id, user)
        db.commit()
        db.refresh(user)

        from app.schemas.auth import LoginRequest

        return AuthService.login(db, LoginRequest(username=data.username, password=data.password))

    @staticmethod
    def _seed_store_defaults(db: Session, store_id: int, user: User) -> None:
        default_services = [
            ("小保养", Decimal("299")),
            ("大保养", Decimal("599")),
            ("更换机油", Decimal("150")),
            ("四轮定位", Decimal("200")),
            ("洗车", Decimal("30")),
            ("补胎", Decimal("50")),
        ]
        for name, price in default_services:
            db.add(ServiceItem(store_id=store_id, name=name, price=price))

        default_parts = [
            ("机油滤清器", "OF-001", Decimal("35"), Decimal("60"), 20, 5),
            ("空气滤清器", "AF-001", Decimal("45"), Decimal("80"), 15, 5),
            ("全合成机油 4L", "OIL-001", Decimal("180"), Decimal("280"), 30, 10),
            ("刹车片前", "BP-F", Decimal("120"), Decimal("200"), 10, 3),
        ]
        seed_user = CurrentUser(
            id=user.id,
            store_id=store_id,
            username=user.username,
            name=user.name,
            role=user.role,
        )
        for name, code, purchase, sell, stock, safe in default_parts:
            part = Part(
                store_id=store_id,
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

    @staticmethod
    def _get_store_or_404(db: Session, store_id: int) -> Store:
        store = db.query(Store).filter(Store.id == store_id, Store.deleted_at.is_(None)).first()
        if store is None:
            raise NotFoundError("门店不存在")
        return store
