from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, NotFoundError
from app.dependencies import CurrentUser
from app.models.customer import Customer, Vehicle
from app.models.payment import Payment, PaymentDetail
from app.models.work_order import WorkOrder
from app.schemas.common import PageParams, PageResult
from app.schemas.payment import PaymentDetailFull, PaymentDetailResponse, PaymentListItem, RefundRequest


METHOD_LABELS = {
    "cash": "现金",
    "wechat": "微信",
    "alipay": "支付宝",
    "bank": "银行卡",
    "card": "刷卡",
}


class PaymentService:
    @staticmethod
    def list_payments(db: Session, current_user: CurrentUser, params: PageParams) -> PageResult:
        query = db.query(Payment).filter(Payment.store_id == current_user.store_id)
        total = query.count()
        payments = (
            query.order_by(Payment.id.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        )

        order_ids = {p.work_order_id for p in payments}
        orders = {
            o.id: o
            for o in db.query(WorkOrder).filter(WorkOrder.id.in_(order_ids)).all()
        } if order_ids else {}

        customer_ids = {o.customer_id for o in orders.values()}
        vehicle_ids = {o.vehicle_id for o in orders.values()}
        customers = {
            c.id: c for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
        } if customer_ids else {}
        vehicles = {
            v.id: v for v in db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
        } if vehicle_ids else {}

        items = []
        for payment in payments:
            order = orders.get(payment.work_order_id)
            customer = customers.get(order.customer_id) if order else None
            vehicle = vehicles.get(order.vehicle_id) if order else None
            items.append(
                PaymentListItem(
                    id=payment.id,
                    payment_no=payment.payment_no,
                    work_order_id=payment.work_order_id,
                    order_no=order.order_no if order else None,
                    customer_name=customer.name if customer else None,
                    plate_number=vehicle.plate_number if vehicle else None,
                    total_amount=float(payment.total_amount),
                    discount_amount=float(payment.discount_amount),
                    payable_amount=float(payment.payable_amount),
                    paid_amount=float(payment.paid_amount),
                    refunded_amount=float(payment.refunded_amount or 0),
                    status=payment.status,
                    settled_at=payment.settled_at,
                    created_at=payment.created_at,
                )
            )
        return PageResult(items=items, total=total, page=params.page, page_size=params.page_size)

    @staticmethod
    def get_payment(db: Session, current_user: CurrentUser, payment_id: int) -> PaymentDetailFull:
        payment = (
            db.query(Payment)
            .options(joinedload(Payment.details))
            .filter(Payment.id == payment_id, Payment.store_id == current_user.store_id)
            .first()
        )
        if payment is None:
            raise NotFoundError("收款记录不存在")

        order = db.query(WorkOrder).filter(WorkOrder.id == payment.work_order_id).first()
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first() if order else None
        vehicle = db.query(Vehicle).filter(Vehicle.id == order.vehicle_id).first() if order else None

        return PaymentDetailFull(
            id=payment.id,
            payment_no=payment.payment_no,
            work_order_id=payment.work_order_id,
            order_no=order.order_no if order else None,
            customer_name=customer.name if customer else None,
            plate_number=vehicle.plate_number if vehicle else None,
            total_amount=float(payment.total_amount),
            discount_amount=float(payment.discount_amount),
            payable_amount=float(payment.payable_amount),
            paid_amount=float(payment.paid_amount),
            refunded_amount=float(payment.refunded_amount or 0),
            status=payment.status,
            settled_at=payment.settled_at,
            details=[PaymentDetailResponse.model_validate(d) for d in payment.details],
            created_at=payment.created_at,
        )

    @staticmethod
    def refund(db: Session, current_user: CurrentUser, payment_id: int, data: RefundRequest) -> PaymentDetailFull:
        payment = (
            db.query(Payment)
            .options(joinedload(Payment.details))
            .filter(Payment.id == payment_id, Payment.store_id == current_user.store_id)
            .first()
        )
        if payment is None:
            raise NotFoundError("收款记录不存在")
        if payment.status == "refunded":
            raise BadRequestError("该收款已全额退款")

        refundable = payment.paid_amount - (payment.refunded_amount or Decimal("0"))
        if data.amount > refundable:
            raise BadRequestError(f"退款金额不能超过可退 ¥{refundable}")

        payment.refunded_amount = (payment.refunded_amount or Decimal("0")) + data.amount
        if payment.refunded_amount >= payment.paid_amount:
            payment.status = "refunded"
        else:
            payment.status = "partial_refund"

        db.add(
            PaymentDetail(
                payment_id=payment.id,
                method="refund",
                amount=-data.amount,
                status="refunded",
                transaction_no=data.reason,
                created_at=datetime.now(timezone.utc),
            )
        )

        order = db.query(WorkOrder).filter(WorkOrder.id == payment.work_order_id).first()
        if order:
            customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
            if customer:
                customer.total_spent = max(Decimal("0"), customer.total_spent - data.amount)

        db.commit()
        return PaymentService.get_payment(db, current_user, payment_id)
