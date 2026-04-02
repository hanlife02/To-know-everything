from __future__ import annotations

from app.models import ContentItem, ContentType, FeedKind, Platform
from app.scrapers.base import PlatformScraper
from app.utils import clean_text, dedupe_keep_order, parse_compact_number, unix_to_datetime


class BilibiliScraper(PlatformScraper):
    platform = Platform.BILIBILI
    hot_url = "https://api.bilibili.com/x/web-interface/popular?ps={limit}&pn=1"
    latest_url = "https://api.bilibili.com/x/web-interface/newlist?rid=0&type=1&ps={limit}&pn=1"

    async def fetch(self, feed_kind: FeedKind, limit: int) -> list[ContentItem]:
        url = self.hot_url if feed_kind == FeedKind.HOT else self.latest_url
        payload = await self.get_json(
            url.format(limit=limit),
            headers={"Referer": "https://www.bilibili.com/"},
        )
        data = payload.get("data", {})
        items = data.get("list") or data.get("archives") or []
        return [self._to_item(feed_kind, entry) for entry in items[:limit]]

    def _to_item(self, feed_kind: FeedKind, entry: dict) -> ContentItem:
        stat = entry.get("stat", {})
        aid = str(entry.get("aid", ""))
        bvid = clean_text(entry.get("bvid"))
        url = f"https://www.bilibili.com/video/{bvid or aid}"
        rcmd_reason = entry.get("rcmd_reason", {})
        reason_text = rcmd_reason.get("content", "") if isinstance(rcmd_reason, dict) else str(rcmd_reason or "")
        tags = dedupe_keep_order([entry.get("tname", ""), reason_text])
        popularity = parse_compact_number(stat.get("view")) or parse_compact_number(entry.get("stat", {}).get("like"))

        return ContentItem(
            id=f"bilibili-{feed_kind.value}-{bvid or aid}",
            platform=self.platform,
            feed_kind=feed_kind,
            title=clean_text(entry.get("title")),
            summary=clean_text(entry.get("desc")),
            author=clean_text(entry.get("owner", {}).get("name")),
            url=url,
            cover_url=clean_text(entry.get("pic")) or None,
            published_at=unix_to_datetime(entry.get("pubdate") or entry.get("ctime")),
            popularity_score=popularity,
            popularity_text=f"{popularity} views" if popularity else None,
            content_type=ContentType.VIDEO,
            source_category=clean_text(entry.get("tname")) or None,
            tags=tags,
            metadata={
                "duration": entry.get("duration"),
                "avid": aid,
                "bvid": bvid or None,
            },
        )
