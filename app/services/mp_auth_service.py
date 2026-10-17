from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User
from app.models.wechat_identity import WechatIdentity
from app.schemas.auth import UserInfo
from app.schemas.mp_auth import MpBindRequest, MpLoginRequest, MpLoginResponse
from app.services.auth_service import AuthService
from app.services.mp_platform_service import MpPlatformService


class MpAuthService:
    @staticmethod
    def _user_info(db: Session, user: User) -> UserInfo:
        return AuthService.build_user_info(db, user)

    @staticmethod
    def _access_token(user: User, platform: str) -> str:
        extra = {
            "user_id": user.id,
            "store_id": user.store_id,
            "role": user.role,
            "client": "mp",
            "platform": MpPlatformService.normalize_platform(platform),
        }
        return create_access_token(str(user.id), extra)

    @staticmethod
    def _bind_token(openid: str, *, client: str, platform: str, appid: str) -> str:
        """未绑定员工时签发，仅用于 /mp/auth/bind。"""
        plat = MpPlatformService.normalize_platform(platform)
        return create_access_token(
            f"openid:{openid}",
            {
                "type": "mp_bind",
                "openid": openid,
                "client": client,
                "platform": plat,
                "appid": appid,
            },
        )

    @staticmethod
    def _get_or_create_identity(
        db: Session,
        *,
        openid: str,
        unionid: str,
        client: str,
        appid: str,
    ) -> WechatIdentity:
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
        platform = MpPlatformService.normalize_platform(data.platform)
        session = MpPlatformService.code2session(platform, data.code)
        openid = session["openid"]
        unionid = session.get("unionid") or ""
        appid = MpPlatformService.appid(platform)

        identity = MpAuthService._get_or_create_identity(
            db, openid=openid, unionid=unionid, client=data.client, appid=appid
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
                    token=MpAuthService._access_token(user, platform),
                    bound=True,
                    user=MpAuthService._user_info(db, user),
                    openid=openid,
                )

        return MpLoginResponse(
            token=MpAuthService._bind_token(
                openid, client=data.client, platform=platform, appid=appid
            ),
            bound=False,
            user=None,
            openid=openid,
        )

    @staticmethod
    def bind(db: Session, data: MpBindRequest, openid: str, appid: str) -> MpLoginResponse:
        platform = MpPlatformService.normalize_platform(data.platform)
        plat_label = MpPlatformService.platform_label(platform)
        if not openid:
            raise UnauthorizedError(f"缺少{plat_label}身份，请重新登录")
        if not appid:
            appid = MpPlatformService.appid(platform)

        user = (
            db.query(User)
            .filter(User.username == data.username, User.deleted_at.is_(None))
            .first()
        )
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("用户名或密码错误")
        if user.status != 1:
            raise UnauthorizedError("账号已禁用")

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
            raise BadRequestError(
                f"该账号已绑定其他{plat_label}，请先在 PC 端解绑或联系管理员"
            )

        if identity.user_id and identity.user_id != user.id:
            raise BadRequestError(f"当前{plat_label}已绑定其他账号")

        identity.user_id = user.id
        identity.store_id = user.store_id
        identity.client = data.client
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        return MpLoginResponse(
            token=MpAuthService._access_token(user, platform),
            bound=True,
            user=MpAuthService._user_info(db, user),
            openid=openid,
        )

    @staticmethod
    def resolve_bind_context(token: str) -> tuple[str, str, str]:
        """bind 阶段从 token 解析 openid、appid、platform。"""
        payload = decode_token(token)
        if payload.get("type") == "mp_bind" and payload.get("openid"):
            openid = str(payload["openid"])
            platform = MpPlatformService.normalize_platform(str(payload.get("platform") or "weixin"))
            appid = str(payload.get("appid") or "") or MpPlatformService.appid(platform)
            return openid, appid, platform
        openid = payload.get("openid")
        if openid:
            platform = MpPlatformService.normalize_platform(str(payload.get("platform") or "weixin"))
            appid = str(payload.get("appid") or "") or MpPlatformService.appid(platform)
            return str(openid), appid, platform
        sub = str(payload.get("sub") or "")
        if sub.startswith("openid:"):
            openid = sub[len("openid:") :]
            platform = MpPlatformService.normalize_platform(str(payload.get("platform") or "weixin"))
            appid = str(payload.get("appid") or "") or MpPlatformService.appid(platform)
            return openid, appid, platform
        raise UnauthorizedError("请先完成小程序登录")

    @staticmethod
    def resolve_openid_from_token(token: str) -> str:
        openid, _, _ = MpAuthService.resolve_bind_context(token)
        return openid

    @staticmethod
    def me(db: Session, user_id: int) -> UserInfo:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if user is None:
            raise UnauthorizedError("用户不存在或已禁用")
        return MpAuthService._user_info(db, user)
