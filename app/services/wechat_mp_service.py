"""微信小程序基础能力：code2session 等。未配置 AppID 时走开发 mock。"""

from __future__ import annotations

import hashlib
import logging

import httpx

from app.config import get_settings
from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WechatMpService:
    @staticmethod
    def appid() -> str:
        settings = get_settings()
        return settings.wechat_mp_app_id or "dev-mock-appid"

    @staticmethod
    def is_mock() -> bool:
        settings = get_settings()
        return not (settings.wechat_mp_app_id and settings.wechat_mp_app_secret)

    @staticmethod
    def code2session(code: str) -> dict[str, str]:
        """用 wx.login code 换 openid/session_key。

        返回: {"openid": ..., "session_key": ..., "unionid": ...?}
        """
        if not code or not code.strip():
            raise BadRequestError("缺少微信登录 code")

        settings = get_settings()
        if WechatMpService.is_mock():
            # 开发态：同一 code 稳定映射到同一 openid，便于本地联调
            digest = hashlib.sha256(code.strip().encode()).hexdigest()[:28]
            openid = f"mock_{digest}"
            logger.warning("WECHAT_MP mock code2session → openid=%s", openid)
            return {"openid": openid, "session_key": "mock_session_key", "unionid": ""}

        params = {
            "appid": settings.wechat_mp_app_id,
            "secret": settings.wechat_mp_app_secret,
            "js_code": code.strip(),
            "grant_type": "authorization_code",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(CODE2SESSION_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.exception("code2session network error")
            raise BadRequestError("微信登录服务暂不可用") from exc

        if data.get("errcode"):
            msg = data.get("errmsg") or data.get("errcode")
            hint = ""
            if str(msg).lower().find("invalid code") >= 0:
                hint = "（若在抖音端出现，请确认请求带 platform=douyin 且勿用微信 code2session）"
            raise BadRequestError(f"微信登录失败: {msg}{hint}")

        openid = data.get("openid")
        if not openid:
            raise BadRequestError("微信未返回 openid")

        return {
            "openid": openid,
            "session_key": data.get("session_key") or "",
            "unionid": data.get("unionid") or "",
        }
