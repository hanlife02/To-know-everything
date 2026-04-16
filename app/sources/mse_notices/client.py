from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.request import Request, urlopen


class MseNoticesClient(ABC):
    @abstractmethod
    def fetch_page(self, url: str) -> str:
        raise NotImplementedError


class HttpMseNoticesClient(MseNoticesClient):
    def fetch_page(self, url: str) -> str:
        request = Request(
            url=url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=15) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
