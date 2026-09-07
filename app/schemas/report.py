from datetime import date

from pydantic import BaseModel, Field


class DailyReport(BaseModel):
    date: date
    revenue: float = 0
    order_count: int = 0
    avg_ticket: float = 0
    new_orders: int = 0
    in_progress: int = 0
    pending_settle: int = 0
    completed_today: int = 0


class RevenueTrendItem(BaseModel):
    date: date
    revenue: float = 0
    order_count: int = 0


class ServiceAnalysisItem(BaseModel):
    name: str
    amount: float
    count: int
    ratio: float = 0


class OverviewReport(BaseModel):
    today: DailyReport
    month_revenue: float = 0
    month_order_count: int = 0
    total_customers: int = 0
    low_stock_count: int = 0
