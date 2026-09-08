from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.dependencies import CurrentUser
from app.models.user import User
from app.schemas.user_mgmt import ALLOWED_ROLES, UserCreate, UserListItem, UserUpdate


class UserService:
    @staticmethod
    def list_users(db: Session, current_user: CurrentUser) -> list[UserListItem]:
        users = (
            db.query(User)
            .filter(User.store_id == current_user.store_id, User.deleted_at.is_(None))
            .order_by(User.id)
            .all()
        )
        return [UserListItem.model_validate(u) for u in users]

    @staticmethod
    def create_user(db: Session, current_user: CurrentUser, data: UserCreate) -> UserListItem:
        if data.role not in ALLOWED_ROLES:
            raise BadRequestError("无效的角色")
        if data.role == "owner":
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
            role=data.role,
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
            if data.status == 0:
                raise ForbiddenError("不能禁用老板账号")

        update_data = data.model_dump(exclude_unset=True)
        if "role" in update_data:
            if update_data["role"] not in ALLOWED_ROLES:
                raise BadRequestError("无效的角色")
            if update_data["role"] == "owner" and user.role != "owner":
                raise BadRequestError("不能将员工提升为老板")

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
