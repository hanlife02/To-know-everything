from __future__ import annotations

from app.domain.models import SourceFetchResult
from app.sources.registry import SourceRegistry


def refresh_sources(registry: SourceRegistry, enabled_sources: tuple[str, ...] = ()) -> list[SourceFetchResult]:
    return [source.fetch() for source in registry.enabled(enabled_sources)]

