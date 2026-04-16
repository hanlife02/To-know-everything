from __future__ import annotations

from app.sources.base import SourceAdapter


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceAdapter] = {}

    def register(self, source: SourceAdapter) -> None:
        self._sources[source.key] = source

    def get(self, source_key: str) -> SourceAdapter | None:
        return self._sources.get(source_key)

    def all(self) -> list[SourceAdapter]:
        return list(self._sources.values())

    def enabled(self, allowed_keys: tuple[str, ...] | None = None) -> list[SourceAdapter]:
        if allowed_keys is None:
            return [source for source in self._sources.values() if source.enabled]
        allowed = set(allowed_keys)
        return [source for source in self._sources.values() if source.enabled and source.key in allowed]

    def snapshot(self) -> list[dict[str, object]]:
        return [
            {"key": source.key, "name": source.name, "enabled": source.enabled}
            for source in self._sources.values()
        ]
