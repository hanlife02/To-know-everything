from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.settings import BarkSettings
from app.domain.enums import NotificationChannel
from app.domain.models import DeliveryReceipt, NotificationMessage
from app.notifications.base import NotificationClient

logger = logging.getLogger(__name__)


class BarkNotifier(NotificationClient):
    channel = NotificationChannel.BARK

    def __init__(self, settings: BarkSettings) -> None:
        self._settings = settings

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if not self._settings.is_configured():
            return DeliveryReceipt(channel=self.channel, delivered=False, detail="bark not configured")
        logger.info("sending bark notification: %s", message.title)
        payload = {
            "title": message.title,
            "body": message.body,
        }
        if self._settings.group:
            payload["group"] = self._settings.group
        try:
            response = self._post_form(f"{self._settings.server_url.rstrip('/')}/{self._settings.key}", payload)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            return DeliveryReceipt(channel=self.channel, delivered=False, detail=f"bark send failed: {exc}")
        code = response.get("code")
        if code not in (None, 200):
            detail = str(response.get("message", "bark send failed"))
            return DeliveryReceipt(channel=self.channel, delivered=False, detail=f"bark send failed: {detail}")
        detail = "bark sent"
        if self._settings.group:
            detail = f"{detail} (group={self._settings.group})"
        return DeliveryReceipt(channel=self.channel, delivered=True, detail=detail)

    def _post_form(self, url: str, payload: dict[str, str]) -> dict[str, object]:
        request = Request(
            url=url,
            data=urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            data = response.read().decode("utf-8")
        if not data:
            return {}
        return json.loads(data)
