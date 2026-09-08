from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.common import PageParams
from app.schemas.payment import RefundRequest
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.payment_service import PaymentService
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["供应商"])


@router.get("")
def list_suppliers(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = SupplierService.list_suppliers(db, current_user)
    return success([i.model_dump() for i in items])


@router.post("")
def create_supplier(
    data: SupplierCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    item = SupplierService.create_supplier(db, current_user, data)
    return success(item.model_dump())


@router.put("/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    item = SupplierService.update_supplier(db, current_user, supplier_id, data)
    return success(item.model_dump())


@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    SupplierService.delete_supplier(db, current_user, supplier_id)
    return success()
