from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["经营报表"])


@router.get("/overview")
def overview(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = ReportService.overview(db, current_user)
    return success(data.model_dump())


@router.get("/daily")
def daily_report(
    target_date: date | None = Query(default=None, alias="date"),
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "finance", "receptionist")),
    db: Session = Depends(get_db),
):
    data = ReportService.daily_report(db, current_user, target_date)
    return success(data.model_dump())


@router.get("/revenue-trend")
def revenue_trend(
    days: int = Query(default=7, ge=1, le=90),
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "finance")),
    db: Session = Depends(get_db),
):
    data = ReportService.revenue_trend(db, current_user, days)
    return success([d.model_dump() for d in data])


@router.get("/service-analysis")
def service_analysis(
    days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_roles("owner", "manager", "finance")),
    db: Session = Depends(get_db),
):
    data = ReportService.service_analysis(db, current_user, days)
    return success([d.model_dump() for d in data])
