from __future__ import annotations

from app.config.settings import AppSettings
from app.domain.enums import NotificationChannel
from app.domain.models import DeliveryReceipt, NotificationMessage
from app.notifications.bark import BarkNotifier
from app.notifications.telegram import TelegramNotifier


class NotificationRouter:
    def __init__(self, clients: dict[NotificationChannel, object]) -> None:
        self._clients = clients

    def deliver(self, messages: list[NotificationMessage]) -> list[DeliveryReceipt]:
        receipts: list[DeliveryReceipt] = []
        for message in messages:
            for channel in message.targets:
                client = self._clients.get(channel)
                if client is None:
                    receipts.append(DeliveryReceipt(channel=channel, delivered=False, detail="channel client missing"))
                    continue
                receipts.append(client.send(message))
        return receipts


def build_notification_router(settings: AppSettings) -> NotificationRouter:
    clients = {
        NotificationChannel.TELEGRAM: TelegramNotifier(settings.telegram),
        NotificationChannel.BARK: BarkNotifier(settings.bark),
    }
    return NotificationRouter(clients=clients)

