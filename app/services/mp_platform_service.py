"""小程序平台（微信 / 抖音）登录能力路由。"""

from __future__ import annotations

from app.core.exceptions import BadRequestError
from app.services.douyin_mp_service import DouyinMpService
from app.services.wechat_mp_service import WechatMpService

PLATFORMS = frozenset({"weixin", "douyin"})


class MpPlatformService:
    @staticmethod
    def normalize_platform(platform: str | None) -> str:
        p = (platform or "weixin").strip().lower()
        if p not in PLATFORMS:
            raise BadRequestError("不支持的小程序平台")
        return p

    @staticmethod
    def appid(platform: str) -> str:
        p = MpPlatformService.normalize_platform(platform)
        if p == "douyin":
            return DouyinMpService.appid()
        return WechatMpService.appid()

    @staticmethod
    def code2session(platform: str, code: str) -> dict[str, str]:
        p = MpPlatformService.normalize_platform(platform)
        if p == "douyin":
            return DouyinMpService.code2session(code)
        return WechatMpService.code2session(code)

    @staticmethod
    def platform_label(platform: str) -> str:
        return "抖音" if MpPlatformService.normalize_platform(platform) == "douyin" else "微信"
