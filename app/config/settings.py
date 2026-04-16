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


def _parse_enabled_sources_from_env() -> tuple[tuple[str, ...], bool]:
    source_toggles = {
        "mse_notices": os.getenv("SOURCE_MSE_NOTICES_ENABLED"),
        "pku_reagent_orders": os.getenv("SOURCE_PKU_REAGENT_ORDERS_ENABLED"),
    }
    if any(value is not None for value in source_toggles.values()):
        enabled = tuple(key for key, value in source_toggles.items() if _parse_bool(value))
        return enabled, True
    legacy_enabled_sources = os.getenv("ENABLED_SOURCES")
    if legacy_enabled_sources is not None:
        return _parse_csv(legacy_enabled_sources), True
    return (), False


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
    group: str | None = None

    def is_configured(self) -> bool:
        return self.enabled and bool(self.key)


@dataclass(frozen=True, slots=True)
class AutomationSettings:
    enabled: bool = False
    daily_time: str = DEFAULT_AUTOMATION_TIME
    default_mode: DeliveryMode = DeliveryMode.SUMMARY


@dataclass(frozen=True, slots=True)
class PkuReagentSettings:
    enabled: bool = False
    base_url: str = "https://reagent.pku.edu.cn"
    iaaa_base_url: str = "https://iaaa.pku.edu.cn/iaaa"
    username: str | None = None
    password: str | None = None
    token: str | None = None
    cookie_header: str | None = None
    captcha_code: str = ""
    sms_code: str = ""
    otp_code: str = ""
    start_date: str | None = None
    end_date: str | None = None
    keyword: str = ""
    group_code: str = ""
    page_size: int = 20

    def has_static_session(self) -> bool:
        return bool(self.username and self.token and self.cookie_header)

    def has_login_credentials(self) -> bool:
        return bool(self.username and self.password)

    def is_configured(self) -> bool:
        return self.enabled and (self.has_static_session() or self.has_login_credentials())


@dataclass(frozen=True, slots=True)
class AppSettings:
    env: str = "development"
    log_level: str = "INFO"
    data_dir: Path = DEFAULT_DATA_DIR
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    bark: BarkSettings = field(default_factory=BarkSettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)
    pku_reagent: PkuReagentSettings = field(default_factory=PkuReagentSettings)
    web_api_key: str | None = None
    enabled_sources: tuple[str, ...] = field(default_factory=tuple)
    source_filter_configured: bool = False

    @classmethod
    def from_env(cls) -> "AppSettings":
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        bark_key = os.getenv("BARK_KEY")
        pku_reagent_username = os.getenv("PKU_REAGENT_USERNAME")
        pku_reagent_password = os.getenv("PKU_REAGENT_PASSWORD")
        pku_reagent_token = os.getenv("PKU_REAGENT_TOKEN")
        pku_reagent_cookie = os.getenv("PKU_REAGENT_COOKIE")
        enabled_sources, source_filter_configured = _parse_enabled_sources_from_env()
        telegram = TelegramSettings(
            enabled=_parse_bool(os.getenv("TELEGRAM_ENABLED")),
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
            disable_web_page_preview=_parse_bool(os.getenv("TELEGRAM_DISABLE_WEB_PAGE_PREVIEW"), default=True),
        )
        bark = BarkSettings(
            enabled=_parse_bool(os.getenv("BARK_ENABLED")),
            server_url=os.getenv("BARK_SERVER_URL", "https://api.day.app"),
            key=bark_key,
            group=os.getenv("BARK_GROUP"),
        )
        automation_mode = DeliveryMode.from_value(os.getenv("AUTOMATION_DEFAULT_MODE", DeliveryMode.SUMMARY.value))
        automation = AutomationSettings(
            enabled=_parse_bool(os.getenv("AUTOMATION_ENABLED")),
            daily_time=os.getenv("AUTOMATION_DAILY_TIME", DEFAULT_AUTOMATION_TIME),
            default_mode=automation_mode,
        )
        pku_reagent = PkuReagentSettings(
            enabled=_parse_bool(os.getenv("PKU_REAGENT_ENABLED")),
            base_url=os.getenv("PKU_REAGENT_BASE_URL", "https://reagent.pku.edu.cn"),
            iaaa_base_url=os.getenv("PKU_REAGENT_IAAA_BASE_URL", "https://iaaa.pku.edu.cn/iaaa"),
            username=pku_reagent_username,
            password=pku_reagent_password,
            token=pku_reagent_token,
            cookie_header=pku_reagent_cookie,
            captcha_code=os.getenv("PKU_REAGENT_CAPTCHA_CODE", ""),
            sms_code=os.getenv("PKU_REAGENT_SMS_CODE", ""),
            otp_code=os.getenv("PKU_REAGENT_OTP_CODE", ""),
            start_date=os.getenv("PKU_REAGENT_START_DATE"),
            end_date=os.getenv("PKU_REAGENT_END_DATE"),
            keyword=os.getenv("PKU_REAGENT_KEYWORD", ""),
            group_code=os.getenv("PKU_REAGENT_GROUP_CODE", ""),
            page_size=int(os.getenv("PKU_REAGENT_PAGE_SIZE", "20")),
        )
        return cls(
            env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
            data_dir=Path(os.getenv("APP_DATA_DIR", str(DEFAULT_DATA_DIR))),
            telegram=telegram,
            bark=bark,
            automation=automation,
            pku_reagent=pku_reagent,
            web_api_key=os.getenv("WEB_API_KEY"),
            enabled_sources=enabled_sources,
            source_filter_configured=source_filter_configured,
        )

    def enabled_channels(self) -> tuple[NotificationChannel, ...]:
        channels: list[NotificationChannel] = []
        if self.telegram.enabled:
            channels.append(NotificationChannel.TELEGRAM)
        if self.bark.enabled:
            channels.append(NotificationChannel.BARK)
        return tuple(channels)
