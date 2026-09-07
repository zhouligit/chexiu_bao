from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.common import PageParams
from app.schemas.service_item import ServiceItemCreate
from app.schemas.work_order import (
    SettleRequest,
    StatusTransition,
    WorkOrderCreate,
    WorkOrderItemCreate,
    WorkOrderPartCreate,
)
from app.services.work_order_service import ServiceItemService, WorkOrderService

router = APIRouter(prefix="/work-orders", tags=["工单管理"])


@router.get("")
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = WorkOrderService.list_orders(
        db, current_user, PageParams(page=page, page_size=page_size, keyword=keyword, status=status)
    )
    return success(result.model_dump())


@router.post("")
def create_work_order(
    data: WorkOrderCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.create_order(db, current_user, data)
    return success(detail.model_dump())


@router.get("/{order_id}")
def get_work_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.get_detail(db, current_user, order_id)
    return success(detail.model_dump())


@router.put("/{order_id}/status")
def transition_status(
    order_id: int,
    data: StatusTransition,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.transition(db, current_user, order_id, data.to_status, data.remark)
    return success(detail.model_dump())


@router.post("/{order_id}/items")
def add_item(
    order_id: int,
    data: WorkOrderItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.add_item(db, current_user, order_id, data)
    return success(detail.model_dump())


@router.post("/{order_id}/parts")
def add_part(
    order_id: int,
    data: WorkOrderPartCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.add_part(db, current_user, order_id, data)
    return success(detail.model_dump())


@router.post("/{order_id}/settle")
def settle_order(
    order_id: int,
    data: SettleRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist", "finance")),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.settle(db, current_user, order_id, data)
    return success(detail.model_dump())


service_router = APIRouter(prefix="/service-items", tags=["服务项目"])


@service_router.get("")
def list_service_items(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = ServiceItemService.list_items(db, current_user)
    return success([i.model_dump() for i in items])


@service_router.post("")
def create_service_item(
    data: ServiceItemCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    item = ServiceItemService.create_item(db, current_user, data)
    return success(item.model_dump())
