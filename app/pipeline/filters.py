from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.models import ContentItem


def filter_recent_items(items: list[ContentItem], max_age_days: int | None = None) -> list[ContentItem]:
    if max_age_days is None:
        return items
    threshold = datetime.utcnow() - timedelta(days=max_age_days)
    return [item for item in items if item.published_at is None or item.published_at >= threshold]


def deduplicate_items(items: list[ContentItem]) -> list[ContentItem]:
    seen: set[str] = set()
    result: list[ContentItem] = []
    for item in items:
        key = item.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result

