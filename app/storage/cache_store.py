from __future__ import annotations

from app.domain.models import SourceFetchResult
from app.storage.json_store import JsonStore


class CacheStore:
    def __init__(self, root) -> None:
        self._root = root

    def write_source_result(self, result: SourceFetchResult) -> None:
        JsonStore(self._root / f"{result.source_key}.json").save(result.as_dict())

    def read_source_result(self, source_key: str) -> SourceFetchResult | None:
        payload = JsonStore(self._root / f"{source_key}.json").load(default=None)
        if not isinstance(payload, dict):
            return None
        return SourceFetchResult.from_dict(payload)

    def read_seen_dedupe_keys(self, source_key: str) -> set[str]:
        cached = self.read_source_result(source_key)
        if cached is None:
            return set()
        return {item.dedupe_key() for item in cached.items}

    def merge_source_result(self, result: SourceFetchResult) -> None:
        cached = self.read_source_result(result.source_key)
        if cached is None:
            self.write_source_result(result)
            return
        merged_items = list(cached.items)
        seen_keys = {item.dedupe_key() for item in merged_items}
        for item in result.items:
            dedupe_key = item.dedupe_key()
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            merged_items.append(item)
        self.write_source_result(
            SourceFetchResult(
                source_key=result.source_key,
                source_name=result.source_name or cached.source_name,
                items=merged_items,
                fetched_at=result.fetched_at,
            )
        )

    def list_cached_sources(self) -> list[str]:
        return sorted(path.stem for path in self._root.glob("*.json"))
