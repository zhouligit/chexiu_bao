from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_roles
from app.schemas.user_mgmt import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["员工管理"])


@router.get("")
def list_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = UserService.list_users(db, current_user)
    return success([u.model_dump() for u in users])


@router.post("")
def create_user(
    data: UserCreate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    user = UserService.create_user(db, current_user, data)
    return success(user.model_dump())


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: CurrentUser = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db),
):
    user = UserService.update_user(db, current_user, user_id, data)
    return success(user.model_dump())


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    UserService.delete_user(db, current_user, user_id)
    return success()
