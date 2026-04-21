from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from app.config.constants import DEFAULT_AUTOMATION_TIME, DEFAULT_DATA_DIR
from app.domain.enums import DeliveryMode, NotificationChannel

KNOWN_SOURCE_KEYS = ("mse_notices", "pku_reagent_orders", "x_posts")


def _parse_bool(value: str | bool | int | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | list[object] | tuple[object, ...] | None) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(part for part in (str(item).strip() for item in value) if part)
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_int(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def _parse_optional_str(value: object, default: str | None = None) -> str | None:
    if value is None:
        return default
    text = str(value).strip()
    return text or None


def _parse_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _parse_enabled_sources_from_env(env: Mapping[str, str]) -> tuple[tuple[str, ...], bool]:
    source_toggles = {
        "mse_notices": env.get("SOURCE_MSE_NOTICES_ENABLED"),
        "pku_reagent_orders": env.get("SOURCE_PKU_REAGENT_ORDERS_ENABLED"),
        "x_posts": env.get("SOURCE_X_POSTS_ENABLED"),
    }
    if any(value is not None for value in source_toggles.values()):
        enabled = tuple(key for key, value in source_toggles.items() if _parse_bool(value))
        return enabled, True
    legacy_enabled_sources = env.get("ENABLED_SOURCES")
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


DEFAULT_X_USERNAMES = ("OpenAI", "AnthropicAI", "GeminiApp", "sama", "elonmusk")


@dataclass(frozen=True, slots=True)
class XSettings:
    enabled: bool = False
    cookie_header: str | None = None
    base_url: str = "https://x.com"
    usernames: tuple[str, ...] = DEFAULT_X_USERNAMES
    max_results_per_user: int = 5
    exclude_replies: bool = True
    exclude_retweets: bool = True

    def is_configured(self) -> bool:
        return self.enabled and bool(self.usernames and self.cookie_header)


@dataclass(frozen=True, slots=True)
class AppSettings:
    env: str = "development"
    log_level: str = "INFO"
    data_dir: Path = DEFAULT_DATA_DIR
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    bark: BarkSettings = field(default_factory=BarkSettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)
    pku_reagent: PkuReagentSettings = field(default_factory=PkuReagentSettings)
    x: XSettings = field(default_factory=XSettings)
    web_api_key: str | None = None
    enabled_sources: tuple[str, ...] = field(default_factory=tuple)
    source_filter_configured: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AppSettings":
        env_data = os.environ if env is None else env
        telegram_bot_token = env_data.get("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = env_data.get("TELEGRAM_CHAT_ID")
        bark_key = env_data.get("BARK_KEY")
        pku_reagent_username = env_data.get("PKU_REAGENT_USERNAME")
        pku_reagent_password = env_data.get("PKU_REAGENT_PASSWORD")
        pku_reagent_token = env_data.get("PKU_REAGENT_TOKEN")
        pku_reagent_cookie = env_data.get("PKU_REAGENT_COOKIE")
        x_usernames = _parse_csv(env_data.get("X_USERNAMES")) or DEFAULT_X_USERNAMES
        enabled_sources, source_filter_configured = _parse_enabled_sources_from_env(env_data)
        telegram = TelegramSettings(
            enabled=_parse_bool(env_data.get("TELEGRAM_ENABLED")),
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
            disable_web_page_preview=_parse_bool(env_data.get("TELEGRAM_DISABLE_WEB_PAGE_PREVIEW"), default=True),
        )
        bark = BarkSettings(
            enabled=_parse_bool(env_data.get("BARK_ENABLED")),
            server_url=env_data.get("BARK_SERVER_URL", "https://api.day.app"),
            key=bark_key,
            group=env_data.get("BARK_GROUP"),
        )
        automation_mode = DeliveryMode.from_value(env_data.get("AUTOMATION_DEFAULT_MODE", DeliveryMode.SUMMARY.value))
        automation = AutomationSettings(
            enabled=_parse_bool(env_data.get("AUTOMATION_ENABLED")),
            daily_time=env_data.get("AUTOMATION_DAILY_TIME", DEFAULT_AUTOMATION_TIME),
            default_mode=automation_mode,
        )
        pku_reagent = PkuReagentSettings(
            enabled=_parse_bool(env_data.get("PKU_REAGENT_ENABLED")),
            base_url=env_data.get("PKU_REAGENT_BASE_URL", "https://reagent.pku.edu.cn"),
            iaaa_base_url=env_data.get("PKU_REAGENT_IAAA_BASE_URL", "https://iaaa.pku.edu.cn/iaaa"),
            username=pku_reagent_username,
            password=pku_reagent_password,
            token=pku_reagent_token,
            cookie_header=pku_reagent_cookie,
            captcha_code=env_data.get("PKU_REAGENT_CAPTCHA_CODE", ""),
            sms_code=env_data.get("PKU_REAGENT_SMS_CODE", ""),
            otp_code=env_data.get("PKU_REAGENT_OTP_CODE", ""),
            start_date=env_data.get("PKU_REAGENT_START_DATE"),
            end_date=env_data.get("PKU_REAGENT_END_DATE"),
            keyword=env_data.get("PKU_REAGENT_KEYWORD", ""),
            group_code=env_data.get("PKU_REAGENT_GROUP_CODE", ""),
            page_size=int(env_data.get("PKU_REAGENT_PAGE_SIZE", "20")),
        )
        x = XSettings(
            enabled=_parse_bool(env_data.get("X_ENABLED")),
            cookie_header=env_data.get("X_COOKIE_HEADER"),
            base_url=env_data.get("X_BASE_URL", "https://x.com"),
            usernames=x_usernames,
            max_results_per_user=_clamp(_parse_int(env_data.get("X_MAX_RESULTS_PER_USER"), 5), 5, 100),
            exclude_replies=_parse_bool(env_data.get("X_EXCLUDE_REPLIES"), default=True),
            exclude_retweets=_parse_bool(env_data.get("X_EXCLUDE_RETWEETS"), default=True),
        )
        return cls(
            env=env_data.get("APP_ENV", "development"),
            log_level=env_data.get("APP_LOG_LEVEL", "INFO"),
            data_dir=Path(env_data.get("APP_DATA_DIR", str(DEFAULT_DATA_DIR))),
            telegram=telegram,
            bark=bark,
            automation=automation,
            pku_reagent=pku_reagent,
            x=x,
            web_api_key=env_data.get("WEB_API_KEY"),
            enabled_sources=enabled_sources,
            source_filter_configured=source_filter_configured,
        )

    def to_runtime_payload(self) -> dict[str, object]:
        return {
            "env": self.env,
            "log_level": self.log_level,
            "data_dir": str(self.data_dir),
            "web_api_key": self.web_api_key or "",
            "automation": {
                "enabled": self.automation.enabled,
                "daily_time": self.automation.daily_time,
                "default_mode": self.automation.default_mode.value,
            },
            "telegram": {
                "enabled": self.telegram.enabled,
                "bot_token": self.telegram.bot_token or "",
                "chat_id": self.telegram.chat_id or "",
                "disable_web_page_preview": self.telegram.disable_web_page_preview,
            },
            "bark": {
                "enabled": self.bark.enabled,
                "server_url": self.bark.server_url,
                "key": self.bark.key or "",
                "group": self.bark.group or "",
            },
            "x": {
                "enabled": self.x.enabled,
                "cookie_header": self.x.cookie_header or "",
                "base_url": self.x.base_url,
                "usernames": list(self.x.usernames),
                "max_results_per_user": self.x.max_results_per_user,
                "exclude_replies": self.x.exclude_replies,
                "exclude_retweets": self.x.exclude_retweets,
            },
            "pku_reagent": {
                "enabled": self.pku_reagent.enabled,
                "base_url": self.pku_reagent.base_url,
                "iaaa_base_url": self.pku_reagent.iaaa_base_url,
                "username": self.pku_reagent.username or "",
                "password": self.pku_reagent.password or "",
                "token": self.pku_reagent.token or "",
                "cookie_header": self.pku_reagent.cookie_header or "",
                "captcha_code": self.pku_reagent.captcha_code,
                "sms_code": self.pku_reagent.sms_code,
                "otp_code": self.pku_reagent.otp_code,
                "start_date": self.pku_reagent.start_date or "",
                "end_date": self.pku_reagent.end_date or "",
                "keyword": self.pku_reagent.keyword,
                "group_code": self.pku_reagent.group_code,
                "page_size": self.pku_reagent.page_size,
            },
            "sources": self.source_enabled_map(),
        }

    def source_enabled_map(self) -> dict[str, bool]:
        enabled = set(self.enabled_sources)
        return {key: key in enabled for key in KNOWN_SOURCE_KEYS}

    def with_runtime_overrides(self, payload: Mapping[str, object] | None) -> "AppSettings":
        if not payload:
            return self
        automation_raw = _as_mapping(payload.get("automation"))
        telegram_raw = _as_mapping(payload.get("telegram"))
        bark_raw = _as_mapping(payload.get("bark"))
        x_raw = _as_mapping(payload.get("x"))
        pku_reagent_raw = _as_mapping(payload.get("pku_reagent"))
        enabled_sources, source_filter_configured = self._resolve_enabled_sources(payload)

        return AppSettings(
            env=self.env,
            log_level=self.log_level,
            data_dir=self.data_dir,
            telegram=TelegramSettings(
                enabled=_parse_bool(telegram_raw.get("enabled"), self.telegram.enabled),
                bot_token=_parse_optional_str(telegram_raw.get("bot_token"), self.telegram.bot_token),
                chat_id=_parse_optional_str(telegram_raw.get("chat_id"), self.telegram.chat_id),
                disable_web_page_preview=_parse_bool(
                    telegram_raw.get("disable_web_page_preview"),
                    self.telegram.disable_web_page_preview,
                ),
            ),
            bark=BarkSettings(
                enabled=_parse_bool(bark_raw.get("enabled"), self.bark.enabled),
                server_url=_parse_text(bark_raw.get("server_url"), self.bark.server_url).strip() or self.bark.server_url,
                key=_parse_optional_str(bark_raw.get("key"), self.bark.key),
                group=_parse_optional_str(bark_raw.get("group"), self.bark.group),
            ),
            automation=AutomationSettings(
                enabled=_parse_bool(automation_raw.get("enabled"), self.automation.enabled),
                daily_time=_parse_text(automation_raw.get("daily_time"), self.automation.daily_time).strip()
                or self.automation.daily_time,
                default_mode=DeliveryMode.from_value(
                    _parse_text(automation_raw.get("default_mode"), self.automation.default_mode.value).strip()
                    or self.automation.default_mode.value
                ),
            ),
            pku_reagent=PkuReagentSettings(
                enabled=_parse_bool(pku_reagent_raw.get("enabled"), self.pku_reagent.enabled),
                base_url=_parse_text(pku_reagent_raw.get("base_url"), self.pku_reagent.base_url).strip()
                or self.pku_reagent.base_url,
                iaaa_base_url=_parse_text(pku_reagent_raw.get("iaaa_base_url"), self.pku_reagent.iaaa_base_url).strip()
                or self.pku_reagent.iaaa_base_url,
                username=_parse_optional_str(pku_reagent_raw.get("username"), self.pku_reagent.username),
                password=_parse_optional_str(pku_reagent_raw.get("password"), self.pku_reagent.password),
                token=_parse_optional_str(pku_reagent_raw.get("token"), self.pku_reagent.token),
                cookie_header=_parse_optional_str(
                    pku_reagent_raw.get("cookie_header"),
                    self.pku_reagent.cookie_header,
                ),
                captcha_code=_parse_text(pku_reagent_raw.get("captcha_code"), self.pku_reagent.captcha_code),
                sms_code=_parse_text(pku_reagent_raw.get("sms_code"), self.pku_reagent.sms_code),
                otp_code=_parse_text(pku_reagent_raw.get("otp_code"), self.pku_reagent.otp_code),
                start_date=_parse_optional_str(pku_reagent_raw.get("start_date"), self.pku_reagent.start_date),
                end_date=_parse_optional_str(pku_reagent_raw.get("end_date"), self.pku_reagent.end_date),
                keyword=_parse_text(pku_reagent_raw.get("keyword"), self.pku_reagent.keyword),
                group_code=_parse_text(pku_reagent_raw.get("group_code"), self.pku_reagent.group_code),
                page_size=max(1, _parse_int(pku_reagent_raw.get("page_size"), self.pku_reagent.page_size)),
            ),
            x=XSettings(
                enabled=_parse_bool(x_raw.get("enabled"), self.x.enabled),
                cookie_header=_parse_optional_str(x_raw.get("cookie_header"), self.x.cookie_header),
                base_url=_parse_text(x_raw.get("base_url"), self.x.base_url).strip() or self.x.base_url,
                usernames=_parse_csv(x_raw.get("usernames")) or self.x.usernames,
                max_results_per_user=_clamp(
                    _parse_int(x_raw.get("max_results_per_user"), self.x.max_results_per_user),
                    5,
                    100,
                ),
                exclude_replies=_parse_bool(x_raw.get("exclude_replies"), self.x.exclude_replies),
                exclude_retweets=_parse_bool(x_raw.get("exclude_retweets"), self.x.exclude_retweets),
            ),
            web_api_key=_parse_optional_str(payload.get("web_api_key"), self.web_api_key),
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

    def _resolve_enabled_sources(self, payload: Mapping[str, object]) -> tuple[tuple[str, ...], bool]:
        sources_raw = _as_mapping(payload.get("sources"))
        if sources_raw:
            defaults = self.source_enabled_map()
            enabled = tuple(
                key
                for key in KNOWN_SOURCE_KEYS
                if _parse_bool(sources_raw.get(key), defaults.get(key, False))
            )
            return enabled, True
        enabled_sources_raw = payload.get("enabled_sources")
        if enabled_sources_raw is not None:
            enabled = tuple(key for key in _parse_csv(enabled_sources_raw) if key in KNOWN_SOURCE_KEYS)
            return enabled, True
        return self.enabled_sources, self.source_filter_configured
