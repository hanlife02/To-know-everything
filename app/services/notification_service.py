from __future__ import annotations

from app.config.settings import AppSettings
from app.domain.enums import DeliveryMode
from app.domain.models import JobRunResult
from app.llm.report_generator import ReportGenerator
from app.notifications.router import NotificationRouter
from app.pipeline.dispatcher import PipelineDispatcher
from app.sources.registry import SourceRegistry
from app.storage.cache_store import CacheStore
from app.storage.state_store import StateStore


class NotificationService:
    def __init__(
        self,
        settings: AppSettings,
        registry: SourceRegistry,
        cache_store: CacheStore,
        state_store: StateStore,
        router: NotificationRouter,
        report_generator: ReportGenerator,
    ) -> None:
        self._registry = registry
        self._cache_store = cache_store
        self._state_store = state_store
        self._dispatcher = PipelineDispatcher(
            settings=settings,
            registry=registry,
            report_generator=report_generator,
            cache_store=cache_store,
        )
        self._router = router

    def run(self, mode: DeliveryMode) -> JobRunResult:
        pipeline_result = self._dispatcher.run(mode)
        for source_result in pipeline_result.source_results:
            source = self._registry.get(source_result.source_key)
            if source is not None and source.accumulate_seen_cache:
                self._cache_store.merge_source_result(source_result)
            else:
                self._cache_store.write_source_result(source_result)
        self._state_store.save_pipeline_snapshot(pipeline_result)
        receipts = self._router.deliver(pipeline_result.messages)
        result = JobRunResult(
            mode=mode,
            fetched_sources=len(pipeline_result.source_results),
            item_count=len(pipeline_result.items),
            message_count=len(pipeline_result.messages),
            receipts=receipts,
        )
        self._state_store.append_run(result)
        return result
