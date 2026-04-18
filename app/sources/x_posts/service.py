from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError

from app.config.settings import XSettings
from app.domain.models import ContentItem, SourceFetchResult
from app.sources.base import SourceAdapter
from app.sources.x_posts.client import HttpXPostsClient, XPostsClient
from app.sources.x_posts.models import XPost

X_POSTS_SOURCE_KEY = "x_posts"
X_POSTS_SOURCE_NAME = "X 关注"


class XPostsSource(SourceAdapter):
    notify_new_only = True
    accumulate_seen_cache = True

    def __init__(
        self,
        *,
        key: str = X_POSTS_SOURCE_KEY,
        name: str = X_POSTS_SOURCE_NAME,
        enabled: bool = True,
        client: XPostsClient | None = None,
        usernames: tuple[str, ...] = (),
        max_results_per_user: int = 5,
        exclude_replies: bool = True,
        exclude_retweets: bool = True,
    ) -> None:
        self.key = key
        self.name = name
        self.enabled = enabled
        self.client = client
        self.usernames = usernames
        self.max_results_per_user = max_results_per_user
        self.exclude_replies = exclude_replies
        self.exclude_retweets = exclude_retweets

    @classmethod
    def from_settings(cls, settings: XSettings) -> "XPostsSource":
        client: XPostsClient | None = None
        if settings.bearer_token:
            client = HttpXPostsClient(
                bearer_token=settings.bearer_token,
                api_base_url=settings.api_base_url,
            )
        return cls(
            enabled=settings.enabled,
            client=client,
            usernames=settings.usernames,
            max_results_per_user=settings.max_results_per_user,
            exclude_replies=settings.exclude_replies,
            exclude_retweets=settings.exclude_retweets,
        )

    def fetch(self) -> SourceFetchResult:
        if not self.enabled or self.client is None or not self.usernames:
            return self.empty_result()
        items: list[ContentItem] = []
        try:
            for username in self.usernames:
                user = self.client.lookup_user_by_username(username)
                if user is None:
                    continue
                posts = self.client.fetch_user_posts(
                    user,
                    max_results=self.max_results_per_user,
                    exclude_replies=self.exclude_replies,
                    exclude_retweets=self.exclude_retweets,
                )
                items.extend(self._to_content_item(post) for post in posts)
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError):
            return self.empty_result()
        items.sort(
            key=lambda item: (
                item.published_at or datetime.min.replace(tzinfo=UTC),
                item.title,
            ),
            reverse=True,
        )
        return self.build_result(items)

    def _to_content_item(self, post: XPost) -> ContentItem:
        normalized_text = re.sub(r"\s+", " ", post.text).strip()
        display_time = ""
        if post.created_at is not None:
            display_time = post.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        url = f"https://x.com/{post.username}/status/{post.id}"
        return ContentItem(
            source_key=self.key,
            source_name=self.name,
            title=f"@{post.username}",
            summary=normalized_text,
            url=url,
            published_at=post.created_at,
            external_id=post.id,
            metadata={
                "content": normalized_text,
                "time": display_time,
                "include_url": "true",
            },
        )
