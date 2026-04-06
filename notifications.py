from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "notification_settings.json"
TELEGRAM_TEXT_LIMIT = 4000


@dataclass(slots=True)
class NotificationSettings:
    bark_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def get_response_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:300] if text else f"HTTP {response.status_code}"

    description = str(payload.get("description", "")).strip()
    if description:
        return description
    return json.dumps(payload, ensure_ascii=False)


def load_notification_settings(path: Path = SETTINGS_PATH) -> NotificationSettings:
    settings = NotificationSettings(
        bark_key=os.getenv("BARK_KEY", "").strip(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        settings = NotificationSettings(
            bark_key=str(payload.get("bark_key", settings.bark_key)).strip(),
            telegram_bot_token=str(
                payload.get("telegram_bot_token", settings.telegram_bot_token)
            ).strip(),
            telegram_chat_id=str(payload.get("telegram_chat_id", settings.telegram_chat_id)).strip(),
        )

    return settings


def save_notification_settings(
    settings: NotificationSettings,
    path: Path = SETTINGS_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def serialize_notification_settings(settings: NotificationSettings) -> dict[str, str]:
    return asdict(settings)


def mask_secret(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * (len(value) - keep * 2)}{value[-keep:]}"


def get_notification_status(settings: NotificationSettings) -> dict[str, Any]:
    return {
        "bark_configured": bool(settings.bark_key),
        "telegram_configured": bool(
            settings.telegram_bot_token and settings.telegram_chat_id
        ),
        "masked_bark_key": mask_secret(settings.bark_key),
        "masked_telegram_bot_token": mask_secret(settings.telegram_bot_token),
        "masked_telegram_chat_id": mask_secret(settings.telegram_chat_id, keep=2),
    }


def send_bark_notification(
    settings: NotificationSettings,
    title: str,
    body: str,
) -> str:
    if not settings.bark_key:
        raise ValueError("Bark key is not configured.")

    response = requests.post(
        "https://api.day.app/push",
        json={
            "device_key": settings.bark_key,
            "title": title,
            "body": body,
            "automaticallyCopy": "1",
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Bark push failed: {get_response_error_message(response)}")

    payload = response.json()
    if payload.get("code") != 200:
        raise RuntimeError(f"Bark push failed: {get_response_error_message(response)}")
    return "Bark 通知发送成功。"


def send_telegram_notification(
    settings: NotificationSettings,
    title: str,
    body: str,
) -> str:
    return send_telegram_text(settings, build_telegram_text(title, body))


def build_telegram_text(title: str, body: str) -> str:
    return f"{title.strip()}\n\n{body.strip()}".strip()


def send_telegram_text(
    settings: NotificationSettings,
    text: str,
) -> str:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise ValueError("Telegram bot token or chat id is not configured.")

    if len(text) > TELEGRAM_TEXT_LIMIT:
        raise ValueError(
            f"Telegram text is too long ({len(text)} chars), limit is {TELEGRAM_TEXT_LIMIT}."
        )

    response = requests.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(
            f"Telegram push failed: {get_response_error_message(response)}"
        )

    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(
            f"Telegram push failed: {get_response_error_message(response)}"
        )
    return "Telegram 通知发送成功。"


def send_telegram_messages(
    settings: NotificationSettings,
    messages: list[tuple[str, str]],
) -> list[str]:
    results: list[str] = []
    for index, (title, body) in enumerate(messages, start=1):
        try:
            send_telegram_text(settings, build_telegram_text(title, body))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Telegram 第 {index} 条消息发送失败：{exc}") from exc
        results.append(f"Telegram 第 {index} 条消息发送成功。")
    return results


def send_notification(
    settings: NotificationSettings,
    channel: str,
    title: str,
    body: str,
) -> list[str]:
    results: list[str] = []

    if channel in {"bark", "all"}:
        results.append(send_bark_notification(settings, title, body))
    if channel in {"telegram", "all"}:
        results.append(send_telegram_notification(settings, title, body))

    if not results:
        raise ValueError(f"Unsupported notification channel: {channel}")

    return results


def build_platform_digest(
    platform_name: str,
    overview: str,
    items: list[dict[str, Any]],
    *,
    item_title_key: str = "title",
    limit: int = 5,
) -> tuple[str, str]:
    if not items:
        raise ValueError(f"{platform_name} 当前没有可推送的内容。")

    lines = [overview.strip()]
    for item in items[:limit]:
        title = item.get(item_title_key, "").strip()
        summary = item.get("summary", "").strip()
        lines.append(f"{item.get('rank', '-')}. {title}")
        if summary:
            lines.append(summary)
        if item.get("url"):
            lines.append(f"链接：{item['url']}")
        lines.append("")

    body = "\n".join(line for line in lines if line is not None).strip()
    title = f"{platform_name} 最新摘要"
    return title, body


def build_combined_digest(
    bilibili: dict[str, Any],
    materials_notices: dict[str, Any],
    xhs: dict[str, Any],
) -> tuple[str, str]:
    title = "内容摘要看板更新"
    body_parts: list[str] = []

    sections = [
        ("【Bilibili】", bilibili.get("overview", "").strip(), bilibili.get("videos", [])),
        (
            "【材料学院通知】",
            materials_notices.get("overview", "").strip(),
            materials_notices.get("notices", []),
        ),
        ("【小红书】", xhs.get("overview", "").strip(), xhs.get("notes", [])),
    ]

    for section_title, overview, items in sections:
        if not items:
            continue
        body_parts.extend([section_title, overview, ""])
        for item in items[:3]:
            body_parts.append(f"{item.get('rank', '-')}. {item.get('title', '')}")
            body_parts.append(item.get("summary", "").strip())
            if item.get("url"):
                body_parts.append(f"链接：{item['url']}")
            body_parts.append("")

    if not body_parts:
        raise ValueError("当前没有满足推送条件的内容。")

    body = "\n".join(part for part in body_parts if part is not None).strip()
    return title, body
