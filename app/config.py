from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "车修宝"
    debug: bool = False
    secret_key: str = "dev-secret-key"
    database_url: str = "postgresql://localhost:5432/chexiu_bao"
    redis_url: str | None = None
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 7
    storage_type: str = "local"
    storage_local_path: str = "./uploads"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    baidu_ocr_api_key: str | None = None
    baidu_ocr_secret_key: str | None = None
    admin_api_key: str | None = None

    # 微信小程序（未配置时 code2session 走本地 mock，便于联调）
    wechat_mp_app_id: str | None = None
    wechat_mp_app_secret: str | None = None

    # 抖音小程序（未配置 SECRET 时走 mock openid）
    douyin_mp_app_id: str | None = None
    douyin_mp_app_secret: str | None = None
    douyin_mp_sandbox: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]



@lru_cache
def get_settings() -> Settings:
    return Settings()
