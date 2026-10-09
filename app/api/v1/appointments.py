from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentConvertRequest,
    AppointmentCreate,
    AppointmentUpdate,
)
from app.schemas.common import PageParams
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["预约管理"])


@router.get("")
def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AppointmentService.list_appointments(
        db,
        current_user,
        PageParams(page=page, page_size=page_size, keyword=keyword, status=status),
        date_from=date_from,
        date_to=date_to,
    )
    return success(result.model_dump())


@router.post("")
def create_appointment(
    data: AppointmentCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.create(db, current_user, data)
    return success(item.model_dump())


@router.get("/{appt_id}")
def get_appointment(
    appt_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = AppointmentService.get_detail(db, current_user, appt_id)
    return success(item.model_dump())


@router.put("/{appt_id}")
def update_appointment(
    appt_id: int,
    data: AppointmentUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.update(db, current_user, appt_id, data)
    return success(item.model_dump())


@router.post("/{appt_id}/confirm")
def confirm_appointment(
    appt_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.confirm(db, current_user, appt_id)
    return success(item.model_dump())


@router.post("/{appt_id}/arrive")
def arrive_appointment(
    appt_id: int,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist", "technician")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.arrive(db, current_user, appt_id)
    return success(item.model_dump())


@router.post("/{appt_id}/cancel")
def cancel_appointment(
    appt_id: int,
    data: AppointmentCancelRequest | None = None,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.cancel(db, current_user, appt_id, data)
    return success(item.model_dump())


@router.post("/{appt_id}/convert")
def convert_appointment(
    appt_id: int,
    data: AppointmentConvertRequest | None = None,
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db),
):
    item = AppointmentService.convert(db, current_user, appt_id, data)
    return success(item.model_dump())
