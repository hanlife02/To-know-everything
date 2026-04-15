from __future__ import annotations

from app.bootstrap import AppContext


def get_notification_payload(context: AppContext) -> dict[str, object]:
    return {
        "channels": [channel.value for channel in context.settings.enabled_channels()],
        "telegram_configured": context.settings.telegram.is_configured(),
        "bark_configured": context.settings.bark.is_configured(),
    }

