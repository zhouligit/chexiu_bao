from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.role import StoreRoleCreate, StoreRoleUpdate
from app.services.permission_service import PermissionService
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["角色权限"])


@router.get("/permissions-catalog")
def permissions_catalog(
    _: CurrentUser = Depends(require_permission("role:read", "role:manage")),
    db: Session = Depends(get_db),
):
    return success(PermissionService.list_catalog(db))


@router.get("")
def list_roles(
    current_user: CurrentUser = Depends(require_permission("role:read", "role:manage")),
    db: Session = Depends(get_db),
):
    roles = RoleService.list_roles(db, current_user)
    return success([r.model_dump() for r in roles])


@router.get("/{role_id}")
def get_role(
    role_id: int,
    current_user: CurrentUser = Depends(require_permission("role:read", "role:manage")),
    db: Session = Depends(get_db),
):
    role = RoleService.get_role(db, current_user, role_id)
    return success(role.model_dump())


@router.post("")
def create_role(
    data: StoreRoleCreate,
    current_user: CurrentUser = Depends(require_permission("role:manage")),
    db: Session = Depends(get_db),
):
    role = RoleService.create_role(db, current_user, data)
    return success(role.model_dump())


@router.put("/{role_id}")
def update_role(
    role_id: int,
    data: StoreRoleUpdate,
    current_user: CurrentUser = Depends(require_permission("role:manage")),
    db: Session = Depends(get_db),
):
    role = RoleService.update_role(db, current_user, role_id, data)
    return success(role.model_dump())


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    current_user: CurrentUser = Depends(require_permission("role:manage")),
    db: Session = Depends(get_db),
):
    RoleService.delete_role(db, current_user, role_id)
    return success()
