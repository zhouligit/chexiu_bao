from fastapi import APIRouter, Depends

from app.api.v1 import auth, customers, inventory, ocr, payments, reports, stores, subscription, suppliers, uploads, users, work_bays, work_orders
from app.dependencies import require_writable_subscription

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_writable_subscription)])
api_router.include_router(auth.router)
api_router.include_router(stores.router)
api_router.include_router(users.router)
api_router.include_router(customers.router)
api_router.include_router(suppliers.router)
api_router.include_router(payments.router)
api_router.include_router(work_bays.router)
api_router.include_router(work_orders.router)
api_router.include_router(work_orders.service_router)
api_router.include_router(inventory.router)
api_router.include_router(reports.router)
api_router.include_router(uploads.router)
api_router.include_router(subscription.router)
api_router.include_router(subscription.admin_router)
