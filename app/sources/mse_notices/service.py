from __future__ import annotations

from urllib.error import HTTPError, URLError

from app.domain.models import SourceFetchResult
from app.sources.base import SourceAdapter
from app.sources.mse_notices.client import HttpMseNoticesClient, MseNoticesClient
from app.sources.mse_notices.parser import parse_notice_list, to_content_item

MSE_NOTICES_SOURCE_KEY = "mse_notices"
MSE_NOTICES_SOURCE_NAME = "材料学院通知"
MSE_NOTICES_URL = "https://www.mse.pku.edu.cn/tzgg.htm"


class MseNoticesSource(SourceAdapter):
    notify_new_only = True
    accumulate_seen_cache = True

    def __init__(
        self,
        *,
        key: str = MSE_NOTICES_SOURCE_KEY,
        name: str = MSE_NOTICES_SOURCE_NAME,
        enabled: bool = True,
        client: MseNoticesClient | None = None,
        list_url: str = MSE_NOTICES_URL,
    ) -> None:
        self.key = key
        self.name = name
        self.enabled = enabled
        self.client = client or HttpMseNoticesClient()
        self.list_url = list_url

    def fetch(self) -> SourceFetchResult:
        if not self.enabled:
            return self.empty_result()
        try:
            html = self.client.fetch_page(self.list_url)
        except (HTTPError, URLError, TimeoutError, ValueError):
            return self.empty_result()
        notices = parse_notice_list(html, base_url=self.list_url)
        items = [to_content_item(notice, source_key=self.key, source_name=self.name) for notice in notices]
        return self.build_result(items)
