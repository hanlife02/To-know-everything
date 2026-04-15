from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import SourceFetchResult


class SourceAdapter(ABC):
    key: str
    name: str
    enabled: bool = True

    @abstractmethod
    def fetch(self) -> SourceFetchResult:
        raise NotImplementedError

