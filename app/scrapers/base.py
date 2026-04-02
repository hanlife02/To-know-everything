from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import httpx
from selectolax.parser import HTMLParser

from app.config import Settings
from app.models import ContentItem, FeedKind, Platform


class PlatformScraper(ABC):
    platform: Platform

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    @property
    def default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def cookie_header(self) -> str | None:
        cookie = self.settings.platform_cookies.get(self.platform.value, "")
        return cookie or None

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict:
        merged_headers = {**self.default_headers, **(headers or {})}
        if self.cookie_header():
            merged_headers["Cookie"] = self.cookie_header() or ""
        response = await self.client.get(url, headers=merged_headers)
        response.raise_for_status()
        return response.json()

    async def get_text(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> str:
        merged_headers = {**self.default_headers, **(headers or {})}
        if self.cookie_header():
            merged_headers["Cookie"] = self.cookie_header() or ""
        response = await self.client.get(url, headers=merged_headers)
        response.raise_for_status()
        return response.text

    def parse_embedded_json(self, html: str, marker: str) -> dict:
        parser = HTMLParser(html)
        for node in parser.css("script"):
            content = (node.text() or "").strip()
            if marker not in content:
                continue
            if content.startswith("{") and content.endswith("}"):
                return self._loads_relaxed_json(content)
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return self._loads_relaxed_json(content[start : end + 1])
        raise ValueError(f"Could not locate embedded JSON for marker: {marker}")

    def _loads_relaxed_json(self, payload: str) -> dict:
        candidate = re.sub(r"(?<=[:\[,])\s*undefined(?=[,\]}])", " null", payload)
        return json.loads(candidate)

    @abstractmethod
    async def fetch(self, feed_kind: FeedKind, limit: int) -> list[ContentItem]:
        raise NotImplementedError
