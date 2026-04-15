from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import TelegramSettings
from app.domain.enums import NotificationChannel
from app.domain.models import DeliveryReceipt, NotificationMessage
from app.notifications.base import NotificationClient
from app.notifications.formatter import split_message

logger = logging.getLogger(__name__)


class TelegramNotifier(NotificationClient):
    channel = NotificationChannel.TELEGRAM

    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if not self._settings.is_configured():
            return DeliveryReceipt(channel=self.channel, delivered=False, detail="telegram not configured")
        segments = self._build_segments(message)
        logger.info("sending telegram message: %s (%s segment(s))", message.title, len(segments))
        try:
            for index, segment in enumerate(segments, start=1):
                payload = {
                    "chat_id": self._settings.chat_id,
                    "text": segment,
                    "disable_web_page_preview": message.disable_web_page_preview,
                }
                response = self._post_json(
                    f"https://api.telegram.org/bot{self._settings.bot_token}/sendMessage",
                    payload,
                )
                if not response.get("ok", False):
                    detail = str(response.get("description", "telegram send failed"))
                    return DeliveryReceipt(
                        channel=self.channel,
                        delivered=False,
                        detail=f"telegram send failed on segment {index}: {detail}",
                    )
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            return DeliveryReceipt(channel=self.channel, delivered=False, detail=f"telegram send failed: {exc}")
        return DeliveryReceipt(channel=self.channel, delivered=True, detail=f"telegram sent {len(segments)} segment(s)")

    def _build_segments(self, message: NotificationMessage) -> list[str]:
        body_segments = split_message(message.body)
        if len(body_segments) == 1:
            return [f"{message.title}\n\n{body_segments[0]}".strip()]
        return [
            f"{message.title} ({index}/{len(body_segments)})\n\n{segment}".strip()
            for index, segment in enumerate(body_segments, start=1)
        ]

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
