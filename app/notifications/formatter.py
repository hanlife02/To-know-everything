from __future__ import annotations

from app.config.constants import DEFAULT_MESSAGE_CHUNK_SIZE
from app.domain.models import ContentItem


def build_summary_body(items: list[ContentItem]) -> str:
    sections = [_build_item_section(item) for item in items]
    return "\n".join(section for section in sections if section).strip()


def _build_item_section(item: ContentItem) -> str:
    parts = [item.title]
    content = item.metadata.get("content")
    status = item.metadata.get("status")
    sku = item.metadata.get("sku")
    display_time = item.metadata.get("time") or item.metadata.get("order_time")
    include_url = item.metadata.get("include_url") == "true"
    if content:
        parts.append(content)
    if status:
        parts.append(status)
    if sku:
        parts.append(sku)
    if display_time:
        parts.append(display_time)
    if include_url and item.url:
        parts.append(item.url)
    return " | ".join(part for part in parts if part)


def split_message(body: str, max_length: int = DEFAULT_MESSAGE_CHUNK_SIZE) -> list[str]:
    if len(body) <= max_length:
        return [body]
    segments: list[str] = []
    current = ""
    for line in body.splitlines(keepends=True):
        if len(current) + len(line) > max_length and current:
            segments.append(current.rstrip())
            current = ""
        current += line
    if current:
        segments.append(current.rstrip())
    return segments
