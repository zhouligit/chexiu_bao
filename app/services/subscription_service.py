from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.constants.subscription_plans import (
    BILLING_CYCLES,
    DEFAULT_PLAN_CODE,
    GRACE_DAYS,
    SUBSCRIPTION_PLANS,
    TRIAL_DAYS,
)
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.current_user import CurrentUser
from app.models.store import Store
from app.models.subscription import (
    BILLING_LIFETIME,
    BILLING_MONTHLY,
    BILLING_YEARLY,
    ORDER_CANCELLED,
    ORDER_PAID,
    ORDER_PENDING,
    SUB_STATUS_ACTIVE,
    SUB_STATUS_EXPIRED,
    SUB_STATUS_LIFETIME,
    SUB_STATUS_TRIAL,
    SubscriptionOrder,
)
from app.schemas.subscription import (
    CreateSubscriptionOrderRequest,
    PlanPriceOption,
    SubscriptionOrderResponse,
    SubscriptionPlanResponse,
    SubscriptionStatusResponse,
)
from app.utils.datetime_utils import as_utc, utc_now
from app.utils.order_no import generate_serial_no

STATUS_LABELS = {
    SUB_STATUS_TRIAL: "试用中",
    SUB_STATUS_ACTIVE: "已订阅",
    SUB_STATUS_EXPIRED: "已过期",
    SUB_STATUS_LIFETIME: "终身版",
}


class SubscriptionService:
    @staticmethod
    def list_plans() -> list[SubscriptionPlanResponse]:
        result = []
        for plan in SUBSCRIPTION_PLANS.values():
            prices: list[PlanPriceOption] = []
            if plan.prices.monthly is not None:
                prices.append(
                    PlanPriceOption(
                        billing_cycle="monthly",
                        label=BILLING_CYCLES["monthly"]["label"],
                        amount=float(plan.prices.monthly),
                    )
                )
            if plan.prices.yearly is not None:
                monthly_equiv = (plan.prices.yearly / Decimal("12")).quantize(Decimal("0.01"))
                prices.append(
                    PlanPriceOption(
                        billing_cycle="yearly",
                        label=BILLING_CYCLES["yearly"]["label"],
                        amount=float(plan.prices.yearly),
                        unit_price_hint=f"约 ¥{monthly_equiv}/月，省 15%+",
                    )
                )
            if plan.prices.lifetime is not None:
                prices.append(
                    PlanPriceOption(
                        billing_cycle="lifetime",
                        label=BILLING_CYCLES["lifetime"]["label"],
                        amount=float(plan.prices.lifetime),
                        unit_price_hint="一次付费，永久使用",
                    )
                )
            result.append(
                SubscriptionPlanResponse(
                    code=plan.code,
                    name=plan.name,
                    description=plan.description,
                    max_users=plan.max_users,
                    features=list(plan.features),
                    prices=prices,
                )
            )
        return result

    @staticmethod
    def get_store_status(db: Session, store: Store) -> SubscriptionStatusResponse:
        now = utc_now()
        SubscriptionService._sync_expired_status(db, store, now)
        plan_def = SUBSCRIPTION_PLANS.get(store.plan, SUBSCRIPTION_PLANS[DEFAULT_PLAN_CODE])

        expired_at = as_utc(store.expired_at)
        days_remaining = None
        if expired_at is not None:
            days_remaining = (expired_at.date() - now.date()).days

        is_lifetime = store.subscription_status == SUB_STATUS_LIFETIME
        is_trial = store.subscription_status == SUB_STATUS_TRIAL
        is_active = SubscriptionService._is_active(store, now)
        can_write = SubscriptionService._can_write(store, now)

        message = None
        if is_lifetime:
            message = "您已开通终身版，感谢支持！"
        elif is_trial and days_remaining is not None:
            message = f"试用剩余 {max(days_remaining, 0)} 天，请及时订阅"
        elif store.subscription_status == SUB_STATUS_EXPIRED:
            if days_remaining is not None and days_remaining >= -GRACE_DAYS:
                message = f"订阅已过期，宽限期剩余 {GRACE_DAYS + days_remaining} 天（只读）"
            else:
                message = "订阅已过期，请续费后继续使用"
        elif days_remaining is not None and days_remaining <= 7:
            message = f"订阅将于 {days_remaining} 天后到期，建议提前续费"

        return SubscriptionStatusResponse(
            status=store.subscription_status,
            status_label=STATUS_LABELS.get(store.subscription_status, store.subscription_status),
            plan=store.plan,
            plan_name=plan_def.name,
            expired_at=expired_at,
            days_remaining=days_remaining,
            is_active=is_active,
            is_trial=is_trial,
            is_lifetime=is_lifetime,
            grace_days=GRACE_DAYS,
            max_users=plan_def.max_users,
            can_write=can_write,
            message=message,
        )

    @staticmethod
    def ensure_can_write(db: Session, store_id: int) -> None:
        store = SubscriptionService._get_store(db, store_id)
        now = utc_now()
        SubscriptionService._sync_expired_status(db, store, now)
        if not SubscriptionService._can_write(store, now):
            status = SubscriptionService.get_store_status(db, store)
            raise ForbiddenError(status.message or "订阅已过期，请续费后继续使用")

    @staticmethod
    def init_trial_store(store: Store) -> None:
        store.plan = DEFAULT_PLAN_CODE
        store.subscription_status = SUB_STATUS_TRIAL
        store.expired_at = utc_now() + timedelta(days=TRIAL_DAYS)

    @staticmethod
    def create_order(
        db: Session, current_user: CurrentUser, data: CreateSubscriptionOrderRequest
    ) -> SubscriptionOrderResponse:
        plan = SUBSCRIPTION_PLANS.get(data.plan_code)
        if plan is None:
            raise BadRequestError("套餐不存在")

        amount = SubscriptionService._price_for_cycle(plan, data.billing_cycle)
        if amount is None:
            raise BadRequestError("该套餐不支持所选计费周期")

        order_no = generate_serial_no(db, SubscriptionOrder, "order_no", "SUB")
        order = SubscriptionOrder(
            store_id=current_user.store_id,
            order_no=order_no,
            plan_code=data.plan_code,
            billing_cycle=data.billing_cycle,
            amount=amount,
            status=ORDER_PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return SubscriptionService._order_response(order)

    @staticmethod
    def list_orders(db: Session, current_user: CurrentUser) -> list[SubscriptionOrderResponse]:
        orders = (
            db.query(SubscriptionOrder)
            .filter(SubscriptionOrder.store_id == current_user.store_id)
            .order_by(SubscriptionOrder.id.desc())
            .limit(50)
            .all()
        )
        return [SubscriptionService._order_response(o) for o in orders]

    @staticmethod
    def activate_order(
        db: Session,
        order_id: int,
        payment_method: str = "manual",
        transaction_no: str | None = None,
        remark: str | None = None,
        store_id: int | None = None,
    ) -> SubscriptionStatusResponse:
        query = db.query(SubscriptionOrder).filter(SubscriptionOrder.id == order_id)
        if store_id is not None:
            query = query.filter(SubscriptionOrder.store_id == store_id)
        order = query.first()
        if order is None:
            raise NotFoundError("订阅订单不存在")
        if order.status == ORDER_PAID:
            raise BadRequestError("订单已支付")
        if order.status == ORDER_CANCELLED:
            raise BadRequestError("订单已取消")

        store = SubscriptionService._get_store(db, order.store_id)
        now = utc_now()
        period_start, period_end = SubscriptionService._calc_period(store, order.billing_cycle, now)

        order.status = ORDER_PAID
        order.payment_method = payment_method
        order.transaction_no = transaction_no
        order.remark = remark
        order.paid_at = now
        order.period_start = period_start
        order.period_end = period_end

        store.plan = order.plan_code
        if order.billing_cycle == BILLING_LIFETIME:
            store.subscription_status = SUB_STATUS_LIFETIME
            store.expired_at = None
        else:
            store.subscription_status = SUB_STATUS_ACTIVE
            store.expired_at = period_end

        db.commit()
        db.refresh(store)
        return SubscriptionService.get_store_status(db, store)

    @staticmethod
    def cancel_order(db: Session, current_user: CurrentUser, order_id: int) -> SubscriptionOrderResponse:
        order = (
            db.query(SubscriptionOrder)
            .filter(
                SubscriptionOrder.id == order_id,
                SubscriptionOrder.store_id == current_user.store_id,
            )
            .first()
        )
        if order is None:
            raise NotFoundError("订阅订单不存在")
        if order.status != ORDER_PENDING:
            raise BadRequestError("只能取消待支付订单")
        order.status = ORDER_CANCELLED
        db.commit()
        db.refresh(order)
        return SubscriptionService._order_response(order)

    @staticmethod
    def _calc_period(store: Store, billing_cycle: str, now: datetime) -> tuple[datetime, datetime | None]:
        if billing_cycle == BILLING_LIFETIME:
            return now, None

        expired_at = as_utc(store.expired_at)
        base = now
        if expired_at and expired_at > now and store.subscription_status in (
            SUB_STATUS_ACTIVE,
            SUB_STATUS_TRIAL,
        ):
            base = expired_at

        days = BILLING_CYCLES[billing_cycle]["days"]
        return base, base + timedelta(days=days)

    @staticmethod
    def _price_for_cycle(plan, billing_cycle: str) -> Decimal | None:
        mapping = {
            "monthly": plan.prices.monthly,
            "yearly": plan.prices.yearly,
            "lifetime": plan.prices.lifetime,
        }
        return mapping.get(billing_cycle)

    @staticmethod
    def _sync_expired_status(db: Session, store: Store, now: datetime) -> None:
        if store.subscription_status in (SUB_STATUS_LIFETIME, SUB_STATUS_EXPIRED):
            return
        expired_at = as_utc(store.expired_at)
        if expired_at is not None and expired_at < now:
            if store.subscription_status != SUB_STATUS_EXPIRED:
                store.subscription_status = SUB_STATUS_EXPIRED
                db.commit()

    @staticmethod
    def _is_active(store: Store, now: datetime) -> bool:
        if store.subscription_status == SUB_STATUS_LIFETIME:
            return True
        expired_at = as_utc(store.expired_at)
        if expired_at is None:
            return store.subscription_status in (SUB_STATUS_ACTIVE, SUB_STATUS_TRIAL)
        return expired_at >= now

    @staticmethod
    def _can_write(store: Store, now: datetime) -> bool:
        if store.subscription_status == SUB_STATUS_LIFETIME:
            return True
        expired_at = as_utc(store.expired_at)
        if expired_at is None:
            return store.subscription_status in (SUB_STATUS_ACTIVE, SUB_STATUS_TRIAL)
        grace_end = expired_at + timedelta(days=GRACE_DAYS)
        return grace_end >= now

    @staticmethod
    def _get_store(db: Session, store_id: int) -> Store:
        store = db.query(Store).filter(Store.id == store_id, Store.deleted_at.is_(None)).first()
        if store is None:
            raise NotFoundError("门店不存在")
        return store

    @staticmethod
    def _order_response(order: SubscriptionOrder) -> SubscriptionOrderResponse:
        plan = SUBSCRIPTION_PLANS.get(order.plan_code)
        return SubscriptionOrderResponse(
            id=order.id,
            order_no=order.order_no,
            plan_code=order.plan_code,
            plan_name=plan.name if plan else order.plan_code,
            billing_cycle=order.billing_cycle,
            billing_cycle_label=BILLING_CYCLES.get(order.billing_cycle, {}).get("label", order.billing_cycle),
            amount=float(order.amount),
            status=order.status,
            payment_method=order.payment_method,
            period_start=order.period_start,
            period_end=order.period_end,
            paid_at=order.paid_at,
            remark=order.remark,
            created_at=order.created_at,
        )
