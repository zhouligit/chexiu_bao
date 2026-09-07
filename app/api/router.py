from fastapi import APIRouter

from app.api.v1 import auth, customers, inventory, reports, work_orders

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(work_orders.router)
api_router.include_router(work_orders.service_router)
api_router.include_router(inventory.router)
api_router.include_router(reports.router)
