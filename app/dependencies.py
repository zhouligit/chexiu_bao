from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.current_user import CurrentUser
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)

SUBSCRIPTION_EXEMPT_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/subscription",
    "/api/v1/admin",
)


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


def require_writable_subscription(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return current_user
    path = request.url.path
    if any(path.startswith(prefix) for prefix in SUBSCRIPTION_EXEMPT_PREFIXES):
        return current_user
    from app.services.subscription_service import SubscriptionService

    SubscriptionService.ensure_can_write(db, current_user.store_id)
    return current_user
