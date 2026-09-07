from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    store_id: int
    username: str
    name: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError()

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("user_id")
    if user_id is None:
        raise UnauthorizedError()

    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if user is None or user.status != 1:
        raise UnauthorizedError("用户不存在或已禁用")

    return CurrentUser(
        id=user.id,
        store_id=user.store_id,
        username=user.username,
        name=user.name,
        role=user.role,
    )


def require_roles(*roles: str):
    def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles and current_user.role != "owner":
            raise ForbiddenError()
        return current_user

    return checker
