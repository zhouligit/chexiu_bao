from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.subscription import ActivateOrderRequest, CreateSubscriptionOrderRequest
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscription", tags=["订阅计费"])


@router.get("/plans")
def list_plans():
    plans = SubscriptionService.list_plans()
    return success([p.model_dump() for p in plans])


@router.get("/status")
def subscription_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.store import Store

    store = db.query(Store).filter(Store.id == current_user.store_id).first()
    status = SubscriptionService.get_store_status(db, store)
    return success(status.model_dump())


@router.get("/orders")
def list_orders(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = SubscriptionService.list_orders(db, current_user)
    return success([o.model_dump() for o in orders])


@router.post("/orders")
def create_order(
    data: CreateSubscriptionOrderRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    order = SubscriptionService.create_order(db, current_user, data)
    return success(order.model_dump())


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    order = SubscriptionService.cancel_order(db, current_user, order_id)
    return success(order.model_dump())


@router.post("/orders/{order_id}/activate")
def activate_order_owner(
    order_id: int,
    data: ActivateOrderRequest,
    current_user: CurrentUser = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    """门店老板确认支付（线下转账后自用，生产环境建议走平台管理员接口或微信支付回调）"""
    status = SubscriptionService.activate_order(
        db,
        order_id,
        payment_method=data.payment_method,
        transaction_no=data.transaction_no,
        remark=data.remark,
        store_id=current_user.store_id,
    )
    return success(status.model_dump())


admin_router = APIRouter(prefix="/admin/subscription", tags=["订阅管理（平台）"])


@admin_router.post("/orders/{order_id}/activate")
def admin_activate_order(
    order_id: int,
    data: ActivateOrderRequest,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("无效的管理员密钥")
    status = SubscriptionService.activate_order(
        db,
        order_id,
        payment_method=data.payment_method,
        transaction_no=data.transaction_no,
        remark=data.remark,
    )
    return success(status.model_dump())
