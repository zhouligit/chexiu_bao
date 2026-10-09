from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, security
from app.schemas.mp_auth import MpBindRequest, MpLoginRequest
from app.services.mp_auth_service import MpAuthService

router = APIRouter(prefix="/mp/auth", tags=["小程序认证"])


@router.post("/login")
def mp_login(data: MpLoginRequest, db: Session = Depends(get_db)):
    result = MpAuthService.login(db, data)
    return success(result.model_dump())


@router.post("/bind")
def mp_bind(
    data: MpBindRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None or not credentials.credentials:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("请先完成微信登录")
    openid = MpAuthService.resolve_openid_from_token(credentials.credentials)
    result = MpAuthService.bind(db, data, openid)
    return success(result.model_dump())


@router.get("/me")
def mp_me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = MpAuthService.me(db, current_user.id)
    return success(user.model_dump())
