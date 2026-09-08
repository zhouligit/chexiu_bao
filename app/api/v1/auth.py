from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.auth import LoginRequest, RefreshRequest, UserInfo
from app.schemas.store import RegisterRequest
from app.services.auth_service import AuthService
from app.services.store_service import StoreService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    result = StoreService.register(db, data)
    return success(result.model_dump())


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = AuthService.login(db, data)
    return success(result.model_dump())


@router.post("/refresh")
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    result = AuthService.refresh(db, data.refresh_token)
    return success(result.model_dump())


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = AuthService.get_me(db, current_user.id)
    return success(user.model_dump())
