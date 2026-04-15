from __future__ import annotations

from app.domain.models import SourceFetchResult
from app.storage.json_store import JsonStore


class CacheStore:
    def __init__(self, root) -> None:
        self._root = root

    def write_source_result(self, result: SourceFetchResult) -> None:
        JsonStore(self._root / f"{result.source_key}.json").save(result.as_dict())

    def list_cached_sources(self) -> list[str]:
        return sorted(path.stem for path in self._root.glob("*.json"))

