from __future__ import annotations

from app.config.settings import AppSettings
from app.domain.enums import DeliveryMode
from app.domain.models import ContentItem, PipelineResult, SourceFetchResult
from app.llm.report_generator import ReportGenerator
from app.pipeline.digest import build_digest_messages
from app.pipeline.filters import deduplicate_items, filter_recent_items
from app.pipeline.refresh import refresh_sources
from app.pipeline.report import build_report_messages
from app.sources.registry import SourceRegistry
from app.storage.cache_store import CacheStore


class PipelineDispatcher:
    def __init__(
        self,
        settings: AppSettings,
        registry: SourceRegistry,
        report_generator: ReportGenerator,
        cache_store: CacheStore,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._report_generator = report_generator
        self._cache_store = cache_store

    def run(self, mode: DeliveryMode) -> PipelineResult:
        enabled_sources = self._settings.enabled_sources if self._settings.source_filter_configured else None
        source_results = self._filter_incremental_results(refresh_sources(self._registry, enabled_sources))
        items: list[ContentItem] = []
        for result in source_results:
            items.extend(result.items)
        items = deduplicate_items(filter_recent_items(items))
        messages = []
        targets = self._settings.enabled_channels()
        if items and targets:
            if mode is DeliveryMode.REPORT:
                messages.extend(
                    build_report_messages(
                        items=items,
                        report_generator=self._report_generator,
                        targets=targets,
                        disable_web_page_preview=self._settings.telegram.disable_web_page_preview,
                    )
                )
            else:
                messages.extend(
                    build_digest_messages(
                        items=items,
                        targets=targets,
                        disable_web_page_preview=self._settings.telegram.disable_web_page_preview,
                    )
                )
        return PipelineResult(mode=mode, items=items, messages=messages, source_results=source_results)

    def _filter_incremental_results(self, source_results: list[SourceFetchResult]) -> list[SourceFetchResult]:
        filtered_results: list[SourceFetchResult] = []
        for result in source_results:
            source = self._registry.get(result.source_key)
            if source is None or not source.notify_new_only:
                filtered_results.append(result)
                continue
            seen_keys = self._cache_store.read_seen_dedupe_keys(result.source_key)
            filtered_items = [item for item in result.items if item.dedupe_key() not in seen_keys]
            filtered_results.append(
                SourceFetchResult(
                    source_key=result.source_key,
                    source_name=result.source_name,
                    items=filtered_items,
                    fetched_at=result.fetched_at,
                )
            )
        return filtered_results
