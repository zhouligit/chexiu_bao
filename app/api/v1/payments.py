from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.common import PageParams
from app.schemas.payment import RefundRequest
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["收退款"])


@router.get("")
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = PaymentService.list_payments(
        db, current_user, PageParams(page=page, page_size=page_size)
    )
    return success(result.model_dump())


@router.get("/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = PaymentService.get_payment(db, current_user, payment_id)
    return success(payment.model_dump())


@router.post("/{payment_id}/refund")
def refund_payment(
    payment_id: int,
    data: RefundRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "finance")),
    db: Session = Depends(get_db),
):
    payment = PaymentService.refund(db, current_user, payment_id, data)
    return success(payment.model_dump())
