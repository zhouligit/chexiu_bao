import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.dependencies import CurrentUser
from app.models.rbac import Permission, StoreRole
from app.models.user import User
from app.permissions.catalog import ALL_PERMISSION_CODES, ROLE_LABELS, default_data_policy_for_slug
from app.schemas.role import StoreRoleCreate, StoreRoleDetail, StoreRoleListItem, StoreRoleUpdate
from app.services.permission_service import PermissionService


class RoleService:
    @staticmethod
    def list_roles(db: Session, current_user: CurrentUser) -> list[StoreRoleListItem]:
        roles = (
            db.query(StoreRole)
            .filter(StoreRole.store_id == current_user.store_id)
            .order_by(StoreRole.id)
            .all()
        )
        user_counts = dict(
            db.query(User.role_id, func.count(User.id))
            .filter(User.store_id == current_user.store_id, User.deleted_at.is_(None))
            .group_by(User.role_id)
            .all()
        )
        result: list[StoreRoleListItem] = []
        for role in roles:
            result.append(
                StoreRoleListItem(
                    id=role.id,
                    store_id=role.store_id,
                    slug=role.slug,
                    name=role.name,
                    is_system=bool(role.is_system),
                    user_count=user_counts.get(role.id, 0),
                    permission_count=len(role.permissions),
                )
            )
        return result

    @staticmethod
    def get_role(db: Session, current_user: CurrentUser, role_id: int) -> StoreRoleDetail:
        role = RoleService._get_role_or_404(db, current_user, role_id)
        return StoreRoleDetail(
            id=role.id,
            store_id=role.store_id,
            slug=role.slug,
            name=role.name,
            is_system=bool(role.is_system),
            data_policy=role.data_policy or default_data_policy_for_slug(role.slug),
            permission_codes=[p.code for p in role.permissions],
        )

    @staticmethod
    def create_role(db: Session, current_user: CurrentUser, data: StoreRoleCreate) -> StoreRoleDetail:
        slug = data.slug or RoleService._slugify(data.name)
        if slug in ROLE_LABELS and slug != "custom":
            raise BadRequestError("请使用其他角色标识，系统预留名称不可用于自定义角色")
        exists = (
            db.query(StoreRole)
            .filter(StoreRole.store_id == current_user.store_id, StoreRole.slug == slug)
            .first()
        )
        if exists:
            raise BadRequestError("角色标识已存在")

        permission_codes: set[str] = set()
        data_policy = data.data_policy or default_data_policy_for_slug("receptionist")
        if data.copy_from_id:
            src = RoleService._get_role_or_404(db, current_user, data.copy_from_id)
            permission_codes = {p.code for p in src.permissions}
            data_policy = src.data_policy or data_policy
        if data.permission_codes:
            permission_codes = RoleService._validate_codes(set(data.permission_codes))

        role = StoreRole(
            store_id=current_user.store_id,
            slug=slug,
            name=data.name,
            is_system=0,
            data_policy=data_policy,
        )
        db.add(role)
        db.flush()
        PermissionService.sync_role_permissions(db, role, permission_codes)
        db.commit()
        db.refresh(role)
        return RoleService.get_role(db, current_user, role.id)

    @staticmethod
    def update_role(
        db: Session, current_user: CurrentUser, role_id: int, data: StoreRoleUpdate
    ) -> StoreRoleDetail:
        role = RoleService._get_role_or_404(db, current_user, role_id)
        if role.slug == "owner":
            raise ForbiddenError("老板角色不可修改权限")

        if data.name is not None:
            role.name = data.name
        if data.data_policy is not None:
            role.data_policy = data.data_policy
        if data.permission_codes is not None:
            codes = RoleService._validate_codes(set(data.permission_codes))
            PermissionService.sync_role_permissions(db, role, codes)

        db.commit()
        db.refresh(role)
        return RoleService.get_role(db, current_user, role.id)

    @staticmethod
    def delete_role(db: Session, current_user: CurrentUser, role_id: int) -> None:
        role = RoleService._get_role_or_404(db, current_user, role_id)
        if role.is_system:
            raise BadRequestError("系统预设角色不可删除")
        in_use = (
            db.query(User.id)
            .filter(User.role_id == role.id, User.deleted_at.is_(None))
            .first()
        )
        if in_use:
            raise BadRequestError("仍有员工使用该角色，请先调整员工角色")
        db.delete(role)
        db.commit()

    @staticmethod
    def _validate_codes(codes: set[str]) -> set[str]:
        invalid = codes - set(ALL_PERMISSION_CODES)
        if invalid:
            raise BadRequestError(f"无效权限: {', '.join(sorted(invalid))}")
        return codes

    @staticmethod
    def _slugify(name: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
        return (base or "custom")[:32]

    @staticmethod
    def _get_role_or_404(db: Session, current_user: CurrentUser, role_id: int) -> StoreRole:
        role = (
            db.query(StoreRole)
            .filter(StoreRole.id == role_id, StoreRole.store_id == current_user.store_id)
            .first()
        )
        if role is None:
            raise NotFoundError("角色不存在")
        return role
