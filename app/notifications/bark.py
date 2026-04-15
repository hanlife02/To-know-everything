from __future__ import annotations

import logging

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
        logger.info("bark message prepared: %s", message.title)
        return DeliveryReceipt(channel=self.channel, delivered=True, detail="bark send stub executed")

