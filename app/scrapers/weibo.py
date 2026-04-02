from __future__ import annotations

from urllib.parse import quote

from app.models import ContentItem, ContentType, FeedKind, Platform
from app.scrapers.base import PlatformScraper
from app.utils import clean_text, dedupe_keep_order, parse_compact_number


class WeiboScraper(PlatformScraper):
    platform = Platform.WEIBO
    hot_url = "https://weibo.com/ajax/side/hotSearch"

    async def fetch(self, feed_kind: FeedKind, limit: int) -> list[ContentItem]:
        payload = await self.get_json(
            self.hot_url,
            headers={"Referer": "https://weibo.com/"},
        )
        realtime = [item for item in payload.get("data", {}).get("realtime", []) if not item.get("is_ad")]

        if feed_kind == FeedKind.HOT:
            selected = realtime[:limit]
        else:
            selected = [
                item for item in realtime
                if clean_text(item.get("label_name") or item.get("icon_desc") or item.get("small_icon_desc")) in {"新", "沸"}
            ]
            if len(selected) < limit:
                existing = {item.get("word") for item in selected}
                selected.extend([item for item in realtime if item.get("word") not in existing])
            selected = selected[:limit]

        return [self._to_item(feed_kind, entry) for entry in selected]

    def _to_item(self, feed_kind: FeedKind, entry: dict) -> ContentItem:
        word = clean_text(entry.get("word") or entry.get("note"))
        query = entry.get("word_scheme") or word
        popularity = parse_compact_number(entry.get("num"))
        label = clean_text(entry.get("label_name") or entry.get("icon_desc") or entry.get("small_icon_desc"))
        tags = dedupe_keep_order([label, "热搜"])

        return ContentItem(
            id=f"weibo-{feed_kind.value}-{word}",
            platform=self.platform,
            feed_kind=feed_kind,
            title=word,
            summary=clean_text(entry.get("note")) or None,
            author="微博热搜",
            url=f"https://s.weibo.com/weibo?q={quote(query)}",
            popularity_score=popularity,
            popularity_text=f"{popularity} heat" if popularity else None,
            content_type=ContentType.TOPIC,
            source_category="热搜榜",
            tags=tags,
            metadata={
                "rank": entry.get("realpos") or entry.get("rank"),
                "label": label or None,
            },
        )

