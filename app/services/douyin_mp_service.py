"""抖音小程序：code2session。未配置 AppID 时走本地 mock。"""

from __future__ import annotations

import hashlib
import logging

import httpx

from app.config import get_settings
from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

CODE2SESSION_URL = "https://developer.toutiao.com/api/apps/v2/jscode2session"
CODE2SESSION_SANDBOX_URL = "https://open-sandbox.douyin.com/api/apps/v2/jscode2session"


class DouyinMpService:
    @staticmethod
    def appid() -> str:
        settings = get_settings()
        return settings.douyin_mp_app_id or "dev-mock-tt-appid"

    @staticmethod
    def is_mock() -> bool:
        settings = get_settings()
        return not (settings.douyin_mp_app_id and settings.douyin_mp_app_secret)

    @staticmethod
    def code2session(code: str) -> dict[str, str]:
        if not code or not code.strip():
            raise BadRequestError("缺少抖音登录 code")

        settings = get_settings()
        if DouyinMpService.is_mock():
            digest = hashlib.sha256(f"tt:{code.strip()}".encode()).hexdigest()[:28]
            openid = f"mock_tt_{digest}"
            logger.warning("DOUYIN_MP mock code2session → openid=%s", openid)
            return {"openid": openid, "session_key": "mock_session_key", "unionid": ""}

        url = CODE2SESSION_SANDBOX_URL if settings.douyin_mp_sandbox else CODE2SESSION_URL
        body = {
            "appid": settings.douyin_mp_app_id,
            "secret": settings.douyin_mp_app_secret,
            "code": code.strip(),
            "anonymous_code": "",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.exception("douyin code2session network error")
            raise BadRequestError("抖音登录服务暂不可用") from exc

        err_no = payload.get("err_no", payload.get("error"))
        if err_no not in (0, None, "0"):
            tips = payload.get("err_tips") or payload.get("message") or str(err_no)
            extra = ""
            tips_l = str(tips).lower()
            if "bad code" in tips_l or "40018" in tips_l or "code错误" in str(tips):
                extra = "；请确认服务器 DOUYIN_MP_APP_ID/SECRET 与开发者工具 AppID 一致并已重启 API"
            raise BadRequestError(f"抖音登录失败: {tips}{extra}")

        data = payload.get("data") or {}
        openid = data.get("openid")
        if not openid:
            raise BadRequestError("抖音未返回 openid")

        return {
            "openid": openid,
            "session_key": data.get("session_key") or "",
            "unionid": data.get("unionid") or "",
        }
