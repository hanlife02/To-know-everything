from __future__ import annotations

from enum import StrEnum


class DeliveryMode(StrEnum):
    SUMMARY = "summary"
    REPORT = "report"

    @classmethod
    def from_value(cls, value: str) -> "DeliveryMode":
        try:
            return cls(value)
        except ValueError:
            return cls.SUMMARY


class NotificationChannel(StrEnum):
    TELEGRAM = "telegram"
    BARK = "bark"


class ContentPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

