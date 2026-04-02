from __future__ import annotations

from app.models import ContentItem, ContentType, FeedKind, Platform
from app.scrapers.base import PlatformScraper
from app.utils import clean_text, dedupe_keep_order, parse_compact_number


class XiaohongshuScraper(PlatformScraper):
    platform = Platform.XIAOHONGSHU
    explore_url = "https://www.xiaohongshu.com/explore"

    async def fetch(self, feed_kind: FeedKind, limit: int) -> list[ContentItem]:
        html = await self.get_text(self.explore_url, headers={"Referer": "https://www.xiaohongshu.com/"})
        state = self.parse_embedded_json(html, '"currentChannel":"homefeed_recommend"')
        feed_entries = [entry for entry in state.get("feed", {}).get("feeds", []) if entry.get("modelType") == "note"]

        if feed_kind == FeedKind.HOT:
            feed_entries.sort(
                key=lambda entry: parse_compact_number(entry.get("noteCard", {}).get("interactInfo", {}).get("likedCount")) or 0,
                reverse=True,
            )

        return [self._to_item(feed_kind, entry) for entry in feed_entries[:limit]]

    def _to_item(self, feed_kind: FeedKind, entry: dict) -> ContentItem:
        note_card = entry.get("noteCard", {})
        note_id = clean_text(entry.get("id"))
        xsec_token = clean_text(entry.get("xsecToken"))
        like_count = parse_compact_number(note_card.get("interactInfo", {}).get("likedCount"))
        note_type = clean_text(note_card.get("type")) or "note"
        cover = note_card.get("cover", {})
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        if xsec_token:
            url = f"{url}?xsec_token={xsec_token}&xsec_source=pc_feed"

        return ContentItem(
            id=f"xiaohongshu-{feed_kind.value}-{note_id}",
            platform=self.platform,
            feed_kind=feed_kind,
            title=clean_text(note_card.get("displayTitle")) or "小红书内容",
            summary=clean_text(note_card.get("desc")) or None,
            author=clean_text(note_card.get("user", {}).get("nickname") or note_card.get("user", {}).get("nickName")),
            url=url,
            cover_url=clean_text(cover.get("urlDefault") or cover.get("urlPre")) or None,
            popularity_score=like_count,
            popularity_text=f"{like_count} likes" if like_count else None,
            content_type=ContentType.VIDEO if note_type == "video" else ContentType.NOTE,
            source_category="推荐流",
            tags=dedupe_keep_order([note_type, "推荐"]),
            metadata={
                "note_id": note_id,
                "xsec_token": xsec_token or None,
                "duration": note_card.get("video", {}).get("capa", {}).get("duration"),
            },
        )
