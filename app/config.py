from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Social Pulse Board"
    api_key: str = Field(default="change-me", alias="API_KEY")
    request_timeout: float = Field(default=15.0, alias="REQUEST_TIMEOUT")
    default_limit: int = Field(default=12, alias="DEFAULT_LIMIT")
    cache_ttl_seconds: int = Field(default=120, alias="CACHE_TTL_SECONDS")
    bilibili_cookie: str | None = Field(default=None, alias="BILIBILI_COOKIE")
    weibo_cookie: str | None = Field(default=None, alias="WEIBO_COOKIE")
    zhihu_cookie: str | None = Field(default=None, alias="ZHIHU_COOKIE")
    xiaohongshu_cookie: str | None = Field(default=None, alias="XIAOHONGSHU_COOKIE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def platform_cookies(self) -> dict[str, str]:
        return {
            "bilibili": self.bilibili_cookie or "",
            "weibo": self.weibo_cookie or "",
            "zhihu": self.zhihu_cookie or "",
            "xiaohongshu": self.xiaohongshu_cookie or "",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

