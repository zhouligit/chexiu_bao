from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.common import PageParams
from app.schemas.inspection import InspectionSubmit
from app.schemas.service_item import ServiceItemCreate, ServiceItemUpdate
from app.schemas.work_order import (
    AssignRequest,
    SettleRequest,
    StatusTransition,
    WorkOrderCreate,
    WorkOrderItemCreate,
    WorkOrderItemStatusUpdate,
    WorkOrderPartCreate,
)
from app.services.inspection_service import InspectionService
from app.services.print_service import PrintService
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


@router.post("/{order_id}/items/{item_id}/confirm")
def confirm_addon_item(
    order_id: int,
    item_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.confirm_addon_item(db, current_user, order_id, item_id)
    return success(detail.model_dump())


@router.put("/{order_id}/items/{item_id}/status")
def update_item_status(
    order_id: int,
    item_id: int,
    data: WorkOrderItemStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.update_item_status(db, current_user, order_id, item_id, data.status)
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


@router.post("/{order_id}/assign")
def assign_technician(
    order_id: int,
    data: AssignRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.assign_technician(db, current_user, order_id, data)
    return success(detail.model_dump())


@router.get("/{order_id}/inspection")
def get_inspection(
    order_id: int,
    type: str = Query("pre_check", alias="type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = InspectionService.get_inspection(db, current_user, order_id, type)
    if record is None:
        if type == "pre_check":
            return success({"items": InspectionService.get_default_items(), "photos": []})
        return success({"items": [], "photos": []})
    return success(record.model_dump())


@router.post("/{order_id}/inspection")
def submit_inspection(
    order_id: int,
    data: InspectionSubmit,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    record = InspectionService.submit_inspection(db, current_user, order_id, data)
    return success(record.model_dump())


@router.get("/{order_id}/print", response_class=HTMLResponse)
def print_work_order(
    order_id: int,
    type: str = Query("quote", alias="type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    html = PrintService.render_html(db, current_user, order_id, type)
    return HTMLResponse(content=html)


@router.get("/{order_id}/print/pdf")
def print_work_order_pdf(
    order_id: int,
    type: str = Query("quote", alias="type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = WorkOrderService.get_detail(db, current_user, order_id)
    try:
        pdf_bytes = PrintService.render_pdf(db, current_user, order_id, type)
    except RuntimeError as exc:
        from app.core.exceptions import BadRequestError

        raise BadRequestError(str(exc)) from exc
    filename = PrintService.pdf_filename(detail.order_no, type)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


service_router = APIRouter(prefix="/service-items", tags=["服务项目"])


@service_router.get("")
def list_service_items(
    all: bool = Query(False, alias="all"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = ServiceItemService.list_items(db, current_user, include_disabled=all)
    return success([i.model_dump() for i in items])


@service_router.post("")
def create_service_item(
    data: ServiceItemCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    item = ServiceItemService.create_item(db, current_user, data)
    return success(item.model_dump())


@service_router.put("/{item_id}")
def update_service_item(
    item_id: int,
    data: ServiceItemUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    item = ServiceItemService.update_item(db, current_user, item_id, data)
    return success(item.model_dump())


@service_router.delete("/{item_id}")
def delete_service_item(
    item_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    ServiceItemService.delete_item(db, current_user, item_id)
    return success()
