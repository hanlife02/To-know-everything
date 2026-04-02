from __future__ import annotations

from app.models import ContentItem, ContentType, FeedKind, Platform
from app.scrapers.base import PlatformScraper
from app.utils import clean_text, dedupe_keep_order, parse_compact_number, unix_to_datetime


class ZhihuScraper(PlatformScraper):
    platform = Platform.ZHIHU
    explore_url = "https://www.zhihu.com/explore"

    async def fetch(self, feed_kind: FeedKind, limit: int) -> list[ContentItem]:
        html = await self.get_text(self.explore_url, headers={"Referer": "https://www.zhihu.com/"})
        state = self.parse_embedded_json(html, '"square":{"hotQuestionList"')
        square = state.get("initialState", {}).get("explore", {}).get("square", {})
        entries = [*square.get("hotQuestionList", []), *square.get("potentialList", [])]

        if feed_kind == FeedKind.HOT:
            entries.sort(
                key=lambda item: (
                    item.get("reaction", {}).get("upvoteNum", 0),
                    item.get("reaction", {}).get("pv", 0),
                ),
                reverse=True,
            )
        else:
            entries.sort(
                key=lambda item: (
                    item.get("question", {}).get("created", 0),
                    item.get("question", {}).get("updatedTime", 0),
                ),
                reverse=True,
            )

        return [self._to_item(feed_kind, entry) for entry in entries[:limit]]

    def _to_item(self, feed_kind: FeedKind, entry: dict) -> ContentItem:
        question = entry.get("question", {})
        reaction = entry.get("reaction", {})
        title = clean_text(question.get("title"))
        topics = [topic.get("name", "") for topic in question.get("topics", [])]
        popularity = parse_compact_number(reaction.get("upvoteNum")) or parse_compact_number(reaction.get("pv"))
        summary = clean_text(reaction.get("text")) or f"关注 {reaction.get('followNum', 0)} / 回答 {reaction.get('answerNum', 0)}"

        return ContentItem(
            id=f"zhihu-{feed_kind.value}-{question.get('id')}",
            platform=self.platform,
            feed_kind=feed_kind,
            title=title,
            summary=summary,
            author=clean_text(question.get("creator", {}).get("name")) or "知乎",
            url=clean_text(question.get("url")),
            published_at=unix_to_datetime(question.get("created")),
            popularity_score=popularity,
            popularity_text=f"{popularity} engagements" if popularity else None,
            content_type=ContentType.QUESTION,
            source_category=clean_text(topics[0]) or None,
            tags=dedupe_keep_order(topics + [question.get("label", "")]),
            metadata={
                "answer_count": reaction.get("answerNum"),
                "follow_count": reaction.get("followNum"),
                "pv": reaction.get("pv"),
            },
        )
