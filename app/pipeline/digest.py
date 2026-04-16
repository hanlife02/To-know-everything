from __future__ import annotations

from collections import OrderedDict

from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import ContentItem, NotificationMessage
from app.notifications.formatter import build_summary_body


def build_digest_messages(
    items: list[ContentItem],
    targets: tuple[NotificationChannel, ...],
    disable_web_page_preview: bool = True,
) -> list[NotificationMessage]:
    grouped_items: OrderedDict[str, tuple[str, list[ContentItem]]] = OrderedDict()
    for item in items:
        source_name = item.source_name or item.source_key
        if item.source_key not in grouped_items:
            grouped_items[item.source_key] = (source_name, [])
        grouped_items[item.source_key][1].append(item)
    return [
        NotificationMessage(
            title=source_name,
            body=build_summary_body(source_items),
            mode=DeliveryMode.SUMMARY,
            targets=targets,
            disable_web_page_preview=disable_web_page_preview,
            metadata={"source_key": source_key, "source_name": source_name},
        )
        for source_key, (source_name, source_items) in grouped_items.items()
        if source_items
    ]
