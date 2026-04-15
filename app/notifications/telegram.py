from __future__ import annotations

import logging

from app.config.settings import TelegramSettings
from app.domain.enums import NotificationChannel
from app.domain.models import DeliveryReceipt, NotificationMessage
from app.notifications.base import NotificationClient

logger = logging.getLogger(__name__)


class TelegramNotifier(NotificationClient):
    channel = NotificationChannel.TELEGRAM

    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if not self._settings.is_configured():
            return DeliveryReceipt(channel=self.channel, delivered=False, detail="telegram not configured")
        logger.info("telegram message prepared: %s", message.title)
        return DeliveryReceipt(channel=self.channel, delivered=True, detail="telegram send stub executed")

