from __future__ import annotations

from app.config.constants import DEFAULT_MESSAGE_CHUNK_SIZE
from app.domain.models import ContentItem


def build_summary_body(items: list[ContentItem]) -> str:
    lines = ["今日摘要", ""]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.title}")
        if item.summary:
            lines.append(f"   {item.summary}")
        lines.append(f"   来源: {item.source_key}")
        if item.url:
            lines.append(f"   链接: {item.url}")
        lines.append("")
    return "\n".join(lines).strip()


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

