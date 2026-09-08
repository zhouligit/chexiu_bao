from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.inventory import InventoryLogResponse, PartCreate, PartUpdate, StockInRequest, StockOutRequest
from app.services.inventory_service import InventoryService

router = APIRouter(tags=["库存管理"])


@router.get("/parts")
def list_parts(
    keyword: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parts = InventoryService.list_parts(db, current_user, keyword)
    return success([p.model_dump() for p in parts])


@router.post("/parts")
def create_part(
    data: PartCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    part = InventoryService.create_part(db, current_user, data)
    return success(part.model_dump())


@router.put("/parts/{part_id}")
def update_part(
    part_id: int,
    data: PartUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    part = InventoryService.update_part(db, current_user, part_id, data)
    return success(part.model_dump())


@router.get("/inventory/alerts")
def inventory_alerts(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = InventoryService.list_alerts(db, current_user)
    return success([a.model_dump() for a in alerts])


@router.post("/inventory/in")
def stock_in(
    data: StockInRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    part = InventoryService.stock_in(db, current_user, data)
    return success(part.model_dump())


@router.post("/inventory/out")
def stock_out(
    data: StockOutRequest,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "warehouse")),
    db: Session = Depends(get_db),
):
    part = InventoryService.stock_out(db, current_user, data)
    return success(part.model_dump())


@router.get("/inventory/logs")
def inventory_logs(
    part_id: int | None = None,
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = InventoryService.list_logs(db, current_user, part_id, limit)
    return success([log.model_dump() for log in logs])
