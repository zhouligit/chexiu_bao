from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.dependencies import CurrentUser
from app.models.rbac import StoreRole
from app.models.user import User
from app.permissions.catalog import ROLE_LABELS
from app.schemas.user_mgmt import ALLOWED_ROLES, UserCreate, UserListItem, UserManagementAccess, UserUpdate
from app.services.permission_service import PermissionService


class UserService:
    @staticmethod
    def management_access(db: Session, current_user: CurrentUser) -> UserManagementAccess:
        user = (
            db.query(User)
            .filter(User.id == current_user.id, User.deleted_at.is_(None))
            .first()
        )
        if user is None:
            raise NotFoundError("用户不存在")
        store_role = PermissionService.get_store_role(db, user)
        from app.permissions.catalog import ROLE_LABELS

        slug = store_role.slug if store_role else user.role
        name = store_role.name if store_role else ROLE_LABELS.get(user.role, user.role)
        perms = PermissionService.effective_permission_codes(db, user)
        can_open = "settings:users" in perms
        can_list = can_open or "user:read" in perms
        return UserManagementAccess(
            role_slug=slug,
            role_name=name,
            can_open_management=can_open,
            can_list=can_list,
            can_create="user:create" in perms,
            can_update="user:update" in perms,
            can_delete="user:delete" in perms,
        )

    @staticmethod
    def list_users(db: Session, current_user: CurrentUser) -> list[UserListItem]:
        users = (
            db.query(User)
            .filter(User.store_id == current_user.store_id, User.deleted_at.is_(None))
            .order_by(User.id)
            .all()
        )
        role_ids = {u.role_id for u in users if u.role_id}
        roles = {}
        if role_ids:
            roles = {
                r.id: r
                for r in db.query(StoreRole).filter(StoreRole.id.in_(role_ids)).all()
            }
        result: list[UserListItem] = []
        for u in users:
            item = UserListItem.model_validate(u)
            if u.role_id and u.role_id in roles:
                item.role_name = roles[u.role_id].name
            elif u.role:
                item.role_name = ROLE_LABELS.get(u.role, u.role)
            result.append(item)
        return result

    @staticmethod
    def create_user(db: Session, current_user: CurrentUser, data: UserCreate) -> UserListItem:
        role, role_id = UserService._resolve_role(
            db, current_user.store_id, data.role_id, data.role or "receptionist"
        )
        if role == "owner":
            raise BadRequestError("不能创建老板角色")

        exists = (
            db.query(User)
            .filter(User.username == data.username, User.deleted_at.is_(None))
            .first()
        )
        if exists:
            raise ConflictError("用户名已被占用")

        store_exists = (
            db.query(User)
            .filter(
                User.store_id == current_user.store_id,
                User.username == data.username,
                User.deleted_at.is_(None),
            )
            .first()
        )
        if store_exists:
            raise ConflictError("本店已有同名账号")

        user = User(
            store_id=current_user.store_id,
            username=data.username,
            password_hash=hash_password(data.password),
            name=data.name,
            phone=data.phone,
            role=role,
            role_id=role_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserListItem.model_validate(user)

    @staticmethod
    def update_user(
        db: Session, current_user: CurrentUser, user_id: int, data: UserUpdate
    ) -> UserListItem:
        user = UserService._get_user_or_404(db, current_user, user_id)

        if user.id == current_user.id and data.status == 0:
            raise BadRequestError("不能禁用自己")
        if user.role == "owner" and current_user.id != user.id:
            if data.role and data.role != "owner":
                raise ForbiddenError("不能修改老板角色")
            if data.role_id is not None:
                raise ForbiddenError("不能修改老板角色")
            if data.status == 0:
                raise ForbiddenError("不能禁用老板账号")

        update_data = data.model_dump(exclude_unset=True)
        if "role_id" in update_data or "role" in update_data:
            role, role_id = UserService._resolve_role(
                db,
                current_user.store_id,
                update_data.get("role_id"),
                update_data.get("role"),
            )
            if role == "owner" and user.role != "owner":
                raise BadRequestError("不能将员工提升为老板")
            user.role = role
            user.role_id = role_id
            update_data.pop("role", None)
            update_data.pop("role_id", None)

        password = update_data.pop("password", None)
        if password:
            user.password_hash = hash_password(password)

        for key, value in update_data.items():
            setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return UserListItem.model_validate(user)

    @staticmethod
    def delete_user(db: Session, current_user: CurrentUser, user_id: int) -> None:
        user = UserService._get_user_or_404(db, current_user, user_id)
        if user.id == current_user.id:
            raise BadRequestError("不能删除自己")
        if user.role == "owner":
            raise ForbiddenError("不能删除老板账号")
        user.deleted_at = datetime.now(timezone.utc)
        user.status = 0
        db.commit()

    @staticmethod
    def _resolve_role(
        db: Session, store_id: int, role_id: int | None, role_slug: str | None
    ) -> tuple[str, int]:
        if role_id is not None:
            store_role = (
                db.query(StoreRole)
                .filter(StoreRole.id == role_id, StoreRole.store_id == store_id)
                .first()
            )
            if store_role is None:
                raise BadRequestError("无效的角色")
            if store_role.slug == "owner":
                raise BadRequestError("不能分配老板角色")
            return store_role.slug, store_role.id
        slug = role_slug or "receptionist"
        if slug not in ALLOWED_ROLES:
            raise BadRequestError("无效的角色")
        if slug == "owner":
            raise BadRequestError("不能分配老板角色")
        store_role = (
            db.query(StoreRole)
            .filter(StoreRole.store_id == store_id, StoreRole.slug == slug)
            .first()
        )
        if store_role is None:
            raise BadRequestError("门店角色未初始化，请联系管理员")
        return store_role.slug, store_role.id

    @staticmethod
    def _get_user_or_404(db: Session, current_user: CurrentUser, user_id: int) -> User:
        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.store_id == current_user.store_id,
                User.deleted_at.is_(None),
            )
            .first()
        )
        if user is None:
            raise NotFoundError("员工不存在")
        return user
