from __future__ import annotations

from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import ContentItem, NotificationMessage
from app.notifications.formatter import build_summary_body


def build_digest_message(
    items: list[ContentItem],
    targets: tuple[NotificationChannel, ...],
    disable_web_page_preview: bool = True,
) -> NotificationMessage:
    return NotificationMessage(
        title="信息摘要",
        body=build_summary_body(items),
        mode=DeliveryMode.SUMMARY,
        targets=targets,
        disable_web_page_preview=disable_web_page_preview,
    )

