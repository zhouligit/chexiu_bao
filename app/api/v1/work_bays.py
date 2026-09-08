from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.work_bay import WorkBayCreate, WorkBayUpdate
from app.services.work_bay_service import WorkBayService

router = APIRouter(prefix="/work-bays", tags=["工位管理"])


@router.get("")
def list_work_bays(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bays = WorkBayService.list_bays(db, current_user)
    return success([b.model_dump() for b in bays])


@router.post("")
def create_work_bay(
    data: WorkBayCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    bay = WorkBayService.create_bay(db, current_user, data)
    return success(bay.model_dump())


@router.put("/{bay_id}")
def update_work_bay(
    bay_id: int,
    data: WorkBayUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    bay = WorkBayService.update_bay(db, current_user, bay_id, data)
    return success(bay.model_dump())


@router.delete("/{bay_id}")
def delete_work_bay(
    bay_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    WorkBayService.delete_bay(db, current_user, bay_id)
    return success()
