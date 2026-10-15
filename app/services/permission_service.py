from sqlalchemy.orm import Session

from app.models.rbac import Permission, StoreRole, StoreRolePermission
from app.models.user import User
from app.permissions.catalog import ALL_PERMISSION_CODES


class PermissionService:
    @staticmethod
    def is_owner(user: User) -> bool:
        return user.role == "owner"

    @staticmethod
    def get_store_role(db: Session, user: User) -> StoreRole | None:
        if user.role_id is None:
            return None
        return (
            db.query(StoreRole)
            .filter(StoreRole.id == user.role_id, StoreRole.store_id == user.store_id)
            .first()
        )

    @staticmethod
    def effective_permission_codes(db: Session, user: User) -> set[str]:
        if PermissionService.is_owner(user):
            return set(ALL_PERMISSION_CODES)
        role = PermissionService.get_store_role(db, user)
        if role is None:
            return set()
        codes = {p.code for p in role.permissions}
        return codes

    @staticmethod
    def has_permission(db: Session, user: User, code: str) -> bool:
        if PermissionService.is_owner(user):
            return True
        return code in PermissionService.effective_permission_codes(db, user)

    @staticmethod
    def get_data_policy(db: Session, user: User) -> dict:
        if PermissionService.is_owner(user):
            return {
                "work_order": {"visibility": "store"},
                "appointment": {"visibility": "store"},
            }
        role = PermissionService.get_store_role(db, user)
        if role is None or not role.data_policy:
            return {
                "work_order": {"visibility": "store"},
                "appointment": {"visibility": "store"},
            }
        return role.data_policy

    @staticmethod
    def work_order_visibility(db: Session, user: User) -> str:
        policy = PermissionService.get_data_policy(db, user)
        wo = policy.get("work_order") or {}
        return wo.get("visibility", "store")

    @staticmethod
    def list_catalog(db: Session) -> list[dict]:
        rows = db.query(Permission).order_by(Permission.sort, Permission.id).all()
        return [
            {
                "id": p.id,
                "code": p.code,
                "module": p.module,
                "name": p.name,
                "sort": p.sort,
                "is_sensitive": bool(p.is_sensitive),
            }
            for p in rows
        ]

    @staticmethod
    def sync_role_permissions(db: Session, role: StoreRole, permission_codes: set[str]) -> None:
        code_to_id = {p.code: p.id for p in db.query(Permission).all()}
        desired_ids = {code_to_id[c] for c in permission_codes if c in code_to_id}
        existing = (
            db.query(StoreRolePermission)
            .filter(StoreRolePermission.store_role_id == role.id)
            .all()
        )
        existing_ids = {row.permission_id for row in existing}
        for row in existing:
            if row.permission_id not in desired_ids:
                db.delete(row)
        for pid in desired_ids - existing_ids:
            db.add(StoreRolePermission(store_role_id=role.id, permission_id=pid))
