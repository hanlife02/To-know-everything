from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.domain.enums import ContentPriority, DeliveryMode, NotificationChannel


@dataclass(slots=True)
class ContentItem:
    source_key: str
    title: str
    summary: str
    url: str
    published_at: datetime | None = None
    external_id: str | None = None
    priority: ContentPriority = ContentPriority.NORMAL
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def dedupe_key(self) -> str:
        if self.url:
            return self.url
        if self.external_id:
            return f"{self.source_key}:{self.external_id}"
        return f"{self.source_key}:{self.title}"

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.published_at is not None:
            payload["published_at"] = self.published_at.isoformat()
        return payload


@dataclass(slots=True)
class SourceFetchResult:
    source_key: str
    items: list[ContentItem]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        return {
            "source_key": self.source_key,
            "fetched_at": self.fetched_at.isoformat(),
            "items": [item.as_dict() for item in self.items],
        }


@dataclass(slots=True)
class NotificationMessage:
    title: str
    body: str
    mode: DeliveryMode
    targets: tuple[NotificationChannel, ...]
    disable_web_page_preview: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "body": self.body,
            "mode": self.mode.value,
            "targets": [target.value for target in self.targets],
            "disable_web_page_preview": self.disable_web_page_preview,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class DeliveryReceipt:
    channel: NotificationChannel
    delivered: bool
    detail: str


@dataclass(slots=True)
class PipelineResult:
    mode: DeliveryMode
    items: list[ContentItem]
    messages: list[NotificationMessage]
    source_results: list[SourceFetchResult]

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "items": [item.as_dict() for item in self.items],
            "messages": [message.as_dict() for message in self.messages],
            "source_results": [result.as_dict() for result in self.source_results],
        }


@dataclass(slots=True)
class JobRunResult:
    mode: DeliveryMode
    fetched_sources: int
    item_count: int
    message_count: int
    receipts: list[DeliveryReceipt]

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "fetched_sources": self.fetched_sources,
            "item_count": self.item_count,
            "message_count": self.message_count,
            "receipts": [asdict(receipt) for receipt in self.receipts],
        }
