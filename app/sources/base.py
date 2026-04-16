from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import ContentItem, SourceFetchResult


class SourceAdapter(ABC):
    key: str
    name: str
    enabled: bool = True
    notify_new_only: bool = False
    accumulate_seen_cache: bool = False

    def build_result(self, items: list[ContentItem]) -> SourceFetchResult:
        return SourceFetchResult(source_key=self.key, source_name=self.name, items=items)

    def empty_result(self) -> SourceFetchResult:
        return self.build_result([])

    @abstractmethod
    def fetch(self) -> SourceFetchResult:
        raise NotImplementedError
