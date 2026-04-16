from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

from app.domain.models import ContentItem
from app.sources.mse_notices.models import MseNotice

NOTICE_PATTERN = re.compile(
    r'<li>\s*<a href="(?P<href>[^"]+)">(?P<title>.*?)</a><i>\[(?P<date>\d{4}年\d{2}月\d{2}日)\]</i>\s*</li>',
    re.DOTALL,
)
LIST_BLOCK_PATTERN = re.compile(r'<div class="list fl">.*?<ul>(?P<content>.*?)</ul>', re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")


def parse_notice_list(html: str, *, base_url: str) -> list[MseNotice]:
    list_block = _extract_list_block(html)
    notices: list[MseNotice] = []
    for match in NOTICE_PATTERN.finditer(list_block):
        title = _clean_text(match.group("title"))
        if not title:
            continue
        notices.append(
            MseNotice(
                title=title,
                url=urljoin(base_url, match.group("href")),
                published_on=match.group("date"),
            )
        )
    return notices


def to_content_item(notice: MseNotice, *, source_key: str, source_name: str) -> ContentItem:
    return ContentItem(
        source_key=source_key,
        source_name=source_name,
        title=notice.title,
        summary="",
        url=notice.url,
        external_id=notice.url,
        metadata={"time": notice.published_on, "include_url": "true"},
    )


def _clean_text(value: str) -> str:
    stripped = TAG_PATTERN.sub("", value)
    return re.sub(r"\s+", " ", unescape(stripped)).strip()


def _extract_list_block(html: str) -> str:
    match = LIST_BLOCK_PATTERN.search(html)
    if not match:
        return html
    return match.group("content")
