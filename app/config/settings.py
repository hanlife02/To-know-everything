from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.config.constants import DEFAULT_AUTOMATION_TIME, DEFAULT_DATA_DIR
from app.domain.enums import DeliveryMode, NotificationChannel


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True, slots=True)
class TelegramSettings:
    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None
    disable_web_page_preview: bool = True

    def is_configured(self) -> bool:
        return self.enabled and bool(self.bot_token and self.chat_id)


@dataclass(frozen=True, slots=True)
class BarkSettings:
    enabled: bool = False
    server_url: str = "https://api.day.app"
    key: str | None = None

    def is_configured(self) -> bool:
        return self.enabled and bool(self.key)


@dataclass(frozen=True, slots=True)
class AutomationSettings:
    enabled: bool = False
    daily_time: str = DEFAULT_AUTOMATION_TIME
    default_mode: DeliveryMode = DeliveryMode.SUMMARY


@dataclass(frozen=True, slots=True)
class AppSettings:
    env: str = "development"
    log_level: str = "INFO"
    data_dir: Path = DEFAULT_DATA_DIR
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    bark: BarkSettings = field(default_factory=BarkSettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)
    web_api_key: str | None = None
    enabled_sources: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_env(cls) -> "AppSettings":
        telegram = TelegramSettings(
            enabled=_parse_bool(os.getenv("TELEGRAM_ENABLED")),
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            disable_web_page_preview=_parse_bool(os.getenv("TELEGRAM_DISABLE_WEB_PAGE_PREVIEW"), default=True),
        )
        bark = BarkSettings(
            enabled=_parse_bool(os.getenv("BARK_ENABLED")),
            server_url=os.getenv("BARK_SERVER_URL", "https://api.day.app"),
            key=os.getenv("BARK_KEY"),
        )
        automation_mode = DeliveryMode.from_value(os.getenv("AUTOMATION_DEFAULT_MODE", DeliveryMode.SUMMARY.value))
        automation = AutomationSettings(
            enabled=_parse_bool(os.getenv("AUTOMATION_ENABLED")),
            daily_time=os.getenv("AUTOMATION_DAILY_TIME", DEFAULT_AUTOMATION_TIME),
            default_mode=automation_mode,
        )
        return cls(
            env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
            data_dir=Path(os.getenv("APP_DATA_DIR", str(DEFAULT_DATA_DIR))),
            telegram=telegram,
            bark=bark,
            automation=automation,
            web_api_key=os.getenv("WEB_API_KEY"),
            enabled_sources=_parse_csv(os.getenv("ENABLED_SOURCES")),
        )

    def enabled_channels(self) -> tuple[NotificationChannel, ...]:
        channels: list[NotificationChannel] = []
        if self.telegram.enabled:
            channels.append(NotificationChannel.TELEGRAM)
        if self.bark.enabled:
            channels.append(NotificationChannel.BARK)
        return tuple(channels)

