from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.common import PageParams
from app.schemas.customer import CustomerCreate, CustomerUpdate, VehicleCreate, VehicleUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["客户管理"])


@router.get("")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = CustomerService.list_customers(
        db, current_user, PageParams(page=page, page_size=page_size, keyword=keyword)
    )
    return success(result.model_dump())


@router.post("")
def create_customer(
    data: CustomerCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    customer = CustomerService.create_customer(db, current_user, data)
    return success(customer.model_dump())


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = CustomerService.get_customer(db, current_user, customer_id)
    return success(customer.model_dump())


@router.put("/{customer_id}")
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    customer = CustomerService.update_customer(db, current_user, customer_id, data)
    return success(customer.model_dump())


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    CustomerService.delete_customer(db, current_user, customer_id)
    return success()


@router.get("/{customer_id}/vehicles")
def list_vehicles(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicles = CustomerService.list_vehicles(db, current_user, customer_id)
    return success([v.model_dump() for v in vehicles])


@router.post("/vehicles")
def create_vehicle(
    data: VehicleCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    vehicle = CustomerService.create_vehicle(db, current_user, data)
    return success(vehicle.model_dump())


@router.put("/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    vehicle = CustomerService.update_vehicle(db, current_user, vehicle_id, data)
    return success(vehicle.model_dump())


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    CustomerService.delete_vehicle(db, current_user, vehicle_id)
    return success()


@router.get("/{customer_id}/work-orders")
def list_customer_work_orders(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = CustomerService.list_customer_work_orders(db, current_user, customer_id)
    return success([o.model_dump() for o in orders])
