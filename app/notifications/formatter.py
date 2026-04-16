from __future__ import annotations

from app.config.constants import DEFAULT_MESSAGE_CHUNK_SIZE
from app.domain.models import ContentItem


def build_summary_body(items: list[ContentItem]) -> str:
    sections = [_build_item_section(item) for item in items]
    return "\n\n".join(section for section in sections if section).strip()


def _build_item_section(item: ContentItem) -> str:
    lines = [f"title: {item.title}"]
    status = item.metadata.get("status")
    sku = item.metadata.get("sku")
    order_time = item.metadata.get("order_time")
    if status:
        lines.append(f"status: {status}")
    if sku:
        lines.append(f"sku: {sku}")
    if order_time:
        lines.append(f"time: {order_time}")
    return "\n".join(lines)


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
