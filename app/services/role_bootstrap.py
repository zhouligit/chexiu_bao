from sqlalchemy.orm import Session

from app.models.rbac import Permission, StoreRole, StoreRolePermission
from app.models.store import Store
from app.models.user import User
from app.permissions.catalog import (
    PERMISSIONS,
    ROLE_LABELS,
    SYSTEM_ROLE_SLUGS,
    default_data_policy_for_slug,
    permissions_for_role_slug,
)


class RoleBootstrap:
    @staticmethod
    def ensure_global_permissions(db: Session) -> None:
        existing = {row.code: row for row in db.query(Permission).all()}
        sensitive = {
            "payment:refund",
            "customer:delete",
            "user:delete",
            "subscription:activate",
            "role:manage",
        }
        for code, module, name, sort in PERMISSIONS:
            if code in existing:
                continue
            db.add(
                Permission(
                    code=code,
                    module=module,
                    name=name,
                    sort=sort,
                    is_sensitive=1 if code in sensitive else 0,
                )
            )
        db.flush()

    @staticmethod
    def ensure_store_roles(db: Session, store_id: int) -> dict[str, StoreRole]:
        RoleBootstrap.ensure_global_permissions(db)
        code_to_perm = {p.code: p for p in db.query(Permission).all()}
        roles_by_slug: dict[str, StoreRole] = {}
        for slug in SYSTEM_ROLE_SLUGS:
            role = (
                db.query(StoreRole)
                .filter(StoreRole.store_id == store_id, StoreRole.slug == slug)
                .first()
            )
            if role is None:
                role = StoreRole(
                    store_id=store_id,
                    slug=slug,
                    name=ROLE_LABELS.get(slug, slug),
                    is_system=1,
                    data_policy=default_data_policy_for_slug(slug),
                )
                db.add(role)
                db.flush()
            roles_by_slug[slug] = role

            desired_codes = permissions_for_role_slug(slug)
            existing_ids = {
                pid
                for (pid,) in db.query(StoreRolePermission.permission_id)
                .filter(StoreRolePermission.store_role_id == role.id)
                .all()
            }
            for code in desired_codes:
                perm = code_to_perm.get(code)
                if perm is None or perm.id in existing_ids:
                    continue
                db.add(StoreRolePermission(store_role_id=role.id, permission_id=perm.id))
        db.flush()
        return roles_by_slug

    @staticmethod
    def backfill_user_role_ids(db: Session, store_id: int) -> None:
        roles = RoleBootstrap.ensure_store_roles(db, store_id)
        users = db.query(User).filter(User.store_id == store_id, User.deleted_at.is_(None)).all()
        for user in users:
            role = None
            if user.role_id:
                role = (
                    db.query(StoreRole)
                    .filter(StoreRole.id == user.role_id, StoreRole.store_id == store_id)
                    .first()
                )
            if role is None:
                role = roles.get(user.role)
                if role:
                    user.role_id = role.id
            if role and user.role != role.slug:
                user.role = role.slug

    @staticmethod
    def bootstrap_all_stores(db: Session) -> None:
        RoleBootstrap.ensure_global_permissions(db)
        store_ids = [row.id for row in db.query(Store.id).filter(Store.deleted_at.is_(None)).all()]
        for store_id in store_ids:
            RoleBootstrap.backfill_user_role_ids(db, store_id)
