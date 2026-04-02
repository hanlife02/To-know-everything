from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Platform(str, Enum):
    BILIBILI = "bilibili"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    XIAOHONGSHU = "xiaohongshu"


class FeedKind(str, Enum):
    HOT = "hot"
    LATEST = "latest"


class ContentType(str, Enum):
    VIDEO = "video"
    TOPIC = "topic"
    QUESTION = "question"
    NOTE = "note"
    ARTICLE = "article"
    MIXED = "mixed"


class ContentItem(BaseModel):
    id: str
    platform: Platform
    feed_kind: FeedKind
    title: str
    summary: str | None = None
    author: str | None = None
    url: str
    cover_url: str | None = None
    published_at: datetime | None = None
    popularity_score: int | None = None
    popularity_text: str | None = None
    content_type: ContentType = ContentType.MIXED
    source_category: str | None = None
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class FetchError(BaseModel):
    platform: Platform
    feed_kind: FeedKind
    message: str


class AggregatedResponse(BaseModel):
    fetched_at: datetime
    platforms: list[Platform]
    feed_kinds: list[FeedKind]
    categories: list[str]
    total: int
    items: list[ContentItem]
    errors: list[FetchError]

