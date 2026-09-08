from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import CurrentUser
from app.models.customer import Customer
from app.models.work_order import WO_COMPLETED, WorkOrder, WorkOrderItem
from app.schemas.report import DailyReport, OverviewReport, RevenueTrendItem, ServiceAnalysisItem
from app.services.inventory_service import InventoryService


class ReportService:
    @staticmethod
    def _day_range(target: date) -> tuple[datetime, datetime]:
        start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return start, end

    @staticmethod
    def daily_report(db: Session, current_user: CurrentUser, target: date | None = None) -> DailyReport:
        target = target or date.today()
        start, end = ReportService._day_range(target)
        store_id = current_user.store_id

        revenue = (
            db.query(func.coalesce(func.sum(WorkOrder.paid_amount), 0))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                WorkOrder.settled_at >= start,
                WorkOrder.settled_at < end,
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        order_count = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                WorkOrder.settled_at >= start,
                WorkOrder.settled_at < end,
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        new_orders = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.created_at >= start,
                WorkOrder.created_at < end,
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        in_progress = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == "in_progress",
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        pending_settle = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == "pending_settle",
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )

        revenue_f = float(revenue or 0)
        count = int(order_count or 0)
        avg = round(revenue_f / count, 2) if count else 0

        return DailyReport(
            date=target,
            revenue=revenue_f,
            order_count=count,
            avg_ticket=avg,
            new_orders=int(new_orders or 0),
            in_progress=int(in_progress or 0),
            pending_settle=int(pending_settle or 0),
            completed_today=count,
        )

    @staticmethod
    def revenue_trend(db: Session, current_user: CurrentUser, days: int = 7) -> list[RevenueTrendItem]:
        days = min(max(days, 1), 90)
        store_id = current_user.store_id
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        rows = (
            db.query(
                func.date(WorkOrder.settled_at).label("day"),
                func.coalesce(func.sum(WorkOrder.paid_amount), 0).label("revenue"),
                func.count(WorkOrder.id).label("cnt"),
            )
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                func.date(WorkOrder.settled_at) >= start_date,
                func.date(WorkOrder.settled_at) <= end_date,
                WorkOrder.deleted_at.is_(None),
            )
            .group_by(func.date(WorkOrder.settled_at))
            .all()
        )

        data_map = {str(r.day): (float(r.revenue), int(r.cnt)) for r in rows}
        result = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            rev, cnt = data_map.get(str(d), (0, 0))
            result.append(RevenueTrendItem(date=d, revenue=rev, order_count=cnt))
        return result

    @staticmethod
    def service_analysis(
        db: Session, current_user: CurrentUser, days: int = 30
    ) -> list[ServiceAnalysisItem]:
        days = min(max(days, 1), 365)
        store_id = current_user.store_id
        since = datetime.now(timezone.utc) - timedelta(days=days)

        rows = (
            db.query(
                WorkOrderItem.name,
                func.sum(WorkOrderItem.amount).label("total"),
                func.count(WorkOrderItem.id).label("cnt"),
            )
            .join(WorkOrder, WorkOrder.id == WorkOrderItem.work_order_id)
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                WorkOrder.settled_at >= since,
                WorkOrder.deleted_at.is_(None),
            )
            .group_by(WorkOrderItem.name)
            .order_by(func.sum(WorkOrderItem.amount).desc())
            .limit(10)
            .all()
        )

        total = sum(float(r.total) for r in rows)
        return [
            ServiceAnalysisItem(
                name=r.name,
                amount=float(r.total),
                count=int(r.cnt),
                ratio=round(float(r.total) / total * 100, 1) if total else 0,
            )
            for r in rows
        ]

    @staticmethod
    def overview(db: Session, current_user: CurrentUser) -> OverviewReport:
        today = ReportService.daily_report(db, current_user)
        store_id = current_user.store_id

        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_revenue = (
            db.query(func.coalesce(func.sum(WorkOrder.paid_amount), 0))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                WorkOrder.settled_at >= month_start,
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        month_count = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.store_id == store_id,
                WorkOrder.status == WO_COMPLETED,
                WorkOrder.settled_at >= month_start,
                WorkOrder.deleted_at.is_(None),
            )
            .scalar()
        )
        total_customers = (
            db.query(func.count(Customer.id))
            .filter(Customer.store_id == store_id, Customer.deleted_at.is_(None))
            .scalar()
        )
        alerts = InventoryService.list_alerts(db, current_user)

        return OverviewReport(
            today=today,
            month_revenue=float(month_revenue or 0),
            month_order_count=int(month_count or 0),
            total_customers=int(total_customers or 0),
            low_stock_count=len(alerts),
        )
