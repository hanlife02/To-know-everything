from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.enums import NotificationChannel
from app.domain.models import DeliveryReceipt, NotificationMessage


class NotificationClient(ABC):
    channel: NotificationChannel

    @abstractmethod
    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        raise NotImplementedError

