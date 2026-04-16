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
    source_name: str = ""
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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ContentItem":
        published_at_raw = payload.get("published_at")
        published_at = None
        if isinstance(published_at_raw, str) and published_at_raw:
            published_at = datetime.fromisoformat(published_at_raw)
        priority_raw = payload.get("priority", ContentPriority.NORMAL.value)
        priority = ContentPriority(priority_raw)
        tags_raw = payload.get("tags", ())
        metadata_raw = payload.get("metadata", {})
        return cls(
            source_key=str(payload.get("source_key", "")),
            title=str(payload.get("title", "")),
            summary=str(payload.get("summary", "")),
            url=str(payload.get("url", "")),
            source_name=str(payload.get("source_name", "")),
            published_at=published_at,
            external_id=str(payload["external_id"]) if payload.get("external_id") is not None else None,
            priority=priority,
            tags=tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, (list, tuple)) else (),
            metadata={str(key): str(value) for key, value in metadata_raw.items()} if isinstance(metadata_raw, dict) else {},
        )


@dataclass(slots=True)
class SourceFetchResult:
    source_key: str
    items: list[ContentItem]
    source_name: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        return {
            "source_key": self.source_key,
            "source_name": self.source_name,
            "fetched_at": self.fetched_at.isoformat(),
            "items": [item.as_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SourceFetchResult":
        fetched_at_raw = payload.get("fetched_at")
        fetched_at = datetime.now(UTC)
        if isinstance(fetched_at_raw, str) and fetched_at_raw:
            fetched_at = datetime.fromisoformat(fetched_at_raw)
        items_raw = payload.get("items", [])
        return cls(
            source_key=str(payload.get("source_key", "")),
            source_name=str(payload.get("source_name", "")),
            items=[ContentItem.from_dict(item) for item in items_raw if isinstance(item, dict)],
            fetched_at=fetched_at,
        )


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
