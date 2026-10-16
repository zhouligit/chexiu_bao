from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User
from app.models.wechat_identity import WechatIdentity
from app.schemas.auth import UserInfo
from app.schemas.mp_auth import MpBindRequest, MpLoginRequest, MpLoginResponse
from app.services.auth_service import AuthService
from app.services.wechat_mp_service import WechatMpService


class MpAuthService:
    @staticmethod
    def _user_info(db: Session, user: User) -> UserInfo:
        return AuthService.build_user_info(db, user)

    @staticmethod
    def _access_token(user: User) -> str:
        extra = {
            "user_id": user.id,
            "store_id": user.store_id,
            "role": user.role,
            "client": "mp",
        }
        return create_access_token(str(user.id), extra)

    @staticmethod
    def _bind_token(openid: str, client: str) -> str:
        """未绑定员工时签发，仅用于 /mp/auth/bind。"""
        return create_access_token(
            f"openid:{openid}",
            {"type": "mp_bind", "openid": openid, "client": client},
        )

    @staticmethod
    def _get_or_create_identity(
        db: Session,
        *,
        openid: str,
        unionid: str,
        client: str,
    ) -> WechatIdentity:
        appid = WechatMpService.appid()
        identity = (
            db.query(WechatIdentity)
            .filter(WechatIdentity.appid == appid, WechatIdentity.openid == openid)
            .first()
        )
        if identity is None:
            identity = WechatIdentity(
                openid=openid,
                unionid=unionid or None,
                appid=appid,
                client=client,
            )
            db.add(identity)
            db.flush()
        else:
            if unionid and not identity.unionid:
                identity.unionid = unionid
            if client and identity.client != client:
                identity.client = client
        return identity

    @staticmethod
    def login(db: Session, data: MpLoginRequest) -> MpLoginResponse:
        session = WechatMpService.code2session(data.code)
        openid = session["openid"]
        unionid = session.get("unionid") or ""

        identity = MpAuthService._get_or_create_identity(
            db, openid=openid, unionid=unionid, client=data.client
        )
        db.commit()
        db.refresh(identity)

        if identity.user_id:
            user = (
                db.query(User)
                .filter(User.id == identity.user_id, User.deleted_at.is_(None))
                .first()
            )
            if user and user.status == 1:
                user.last_login_at = datetime.now(timezone.utc)
                db.commit()
                return MpLoginResponse(
                    token=MpAuthService._access_token(user),
                    bound=True,
                    user=MpAuthService._user_info(db, user),
                    openid=openid,
                )

        return MpLoginResponse(
            token=MpAuthService._bind_token(openid, data.client),
            bound=False,
            user=None,
            openid=openid,
        )

    @staticmethod
    def bind(db: Session, data: MpBindRequest, openid: str) -> MpLoginResponse:
        if not openid:
            raise UnauthorizedError("缺少微信身份，请重新登录")

        user = (
            db.query(User)
            .filter(User.username == data.username, User.deleted_at.is_(None))
            .first()
        )
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("用户名或密码错误")
        if user.status != 1:
            raise UnauthorizedError("账号已禁用")

        appid = WechatMpService.appid()
        identity = (
            db.query(WechatIdentity)
            .filter(WechatIdentity.appid == appid, WechatIdentity.openid == openid)
            .first()
        )
        if identity is None:
            identity = WechatIdentity(
                openid=openid,
                appid=appid,
                client=data.client,
            )
            db.add(identity)
            db.flush()

        # 同一员工仅允许绑定一个 openid（同 appid）
        existing_user_bind = (
            db.query(WechatIdentity)
            .filter(
                WechatIdentity.appid == appid,
                WechatIdentity.user_id == user.id,
                WechatIdentity.id != identity.id,
            )
            .first()
        )
        if existing_user_bind is not None:
            raise BadRequestError("该账号已绑定其他微信，请先在 PC 端解绑或联系管理员")

        if identity.user_id and identity.user_id != user.id:
            raise BadRequestError("当前微信已绑定其他账号")

        identity.user_id = user.id
        identity.store_id = user.store_id
        identity.client = data.client
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        return MpLoginResponse(
            token=MpAuthService._access_token(user),
            bound=True,
            user=MpAuthService._user_info(db, user),
            openid=openid,
        )

    @staticmethod
    def resolve_openid_from_token(token: str) -> str:
        payload = decode_token(token)
        # bind token: create_access_token extra 会把 type 覆盖为 mp_bind
        if payload.get("type") == "mp_bind" and payload.get("openid"):
            return str(payload["openid"])
        openid = payload.get("openid")
        if openid:
            return str(openid)
        sub = str(payload.get("sub") or "")
        if sub.startswith("openid:"):
            return sub[len("openid:") :]
        raise UnauthorizedError("请先完成微信登录")


    @staticmethod
    def me(db: Session, user_id: int) -> UserInfo:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if user is None:
            raise UnauthorizedError("用户不存在或已禁用")
        return MpAuthService._user_info(db, user)
