from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings
from app.models import AggregatedResponse, ContentItem, FeedKind, FetchError, Platform
from app.scrapers import BilibiliScraper, WeiboScraper, XiaohongshuScraper, ZhihuScraper
from app.services.classifier import infer_category


@dataclass
class CacheEntry:
    expires_at: datetime
    payload: AggregatedResponse


class AggregatorService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[str, CacheEntry] = {}

    def _cache_key(self, platforms: list[Platform], feed_kinds: list[FeedKind], limit: int) -> str:
        return ":".join(
            [
                ",".join(sorted(platform.value for platform in platforms)),
                ",".join(sorted(feed.value for feed in feed_kinds)),
                str(limit),
            ]
        )

    async def fetch(
        self,
        platforms: list[Platform],
        feed_kinds: list[FeedKind],
        limit: int,
    ) -> AggregatedResponse:
        cache_key = self._cache_key(platforms, feed_kinds, limit)
        now = datetime.now(tz=UTC)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return cached.payload

        timeout = httpx.Timeout(self.settings.request_timeout)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            scrapers = {
                Platform.BILIBILI: BilibiliScraper(client, self.settings),
                Platform.WEIBO: WeiboScraper(client, self.settings),
                Platform.ZHIHU: ZhihuScraper(client, self.settings),
                Platform.XIAOHONGSHU: XiaohongshuScraper(client, self.settings),
            }

            tasks: list[asyncio.Task[list[ContentItem]]] = []
            task_meta: list[tuple[Platform, FeedKind]] = []
            for platform in platforms:
                scraper = scrapers[platform]
                for feed_kind in feed_kinds:
                    tasks.append(asyncio.create_task(scraper.fetch(feed_kind, limit)))
                    task_meta.append((platform, feed_kind))

            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[ContentItem] = []
        errors: list[FetchError] = []

        for (platform, feed_kind), result in zip(task_meta, raw_results, strict=True):
            if isinstance(result, Exception):
                errors.append(FetchError(platform=platform, feed_kind=feed_kind, message=str(result)))
                continue
            for item in result:
                if not item.category or item.category == "general":
                    item.category = infer_category(item.title, item.tags, item.source_category)
                items.append(item)

        items.sort(
            key=lambda item: (
                1 if item.feed_kind == FeedKind.HOT else 0,
                item.popularity_score or 0,
                int(item.published_at.timestamp()) if item.published_at else 0,
            ),
            reverse=True,
        )

        response = AggregatedResponse(
            fetched_at=now,
            platforms=platforms,
            feed_kinds=feed_kinds,
            categories=sorted({item.category for item in items}),
            total=len(items),
            items=items,
            errors=errors,
        )
        self._cache[cache_key] = CacheEntry(
            expires_at=now + timedelta(seconds=self.settings.cache_ttl_seconds),
            payload=response,
        )
        return response

