from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.store import StoreUpdate
from app.services.store_service import StoreService

router = APIRouter(prefix="/store", tags=["门店管理"])


@router.get("")
def get_store(
    current_user: CurrentUser = Depends(require_permission("settings:store")),
    db: Session = Depends(get_db),
):
    store = StoreService.get_current_store(db, current_user)
    return success(store.model_dump())


@router.put("")
def update_store(
    data: StoreUpdate,
    current_user: CurrentUser = Depends(require_permission("settings:store")),
    db: Session = Depends(get_db),
):
    store = StoreService.update_store(db, current_user, data)
    return success(store.model_dump())
