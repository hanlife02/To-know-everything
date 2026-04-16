from __future__ import annotations

from app.config.settings import AppSettings
from app.domain.enums import DeliveryMode
from app.domain.models import ContentItem, PipelineResult
from app.llm.report_generator import ReportGenerator
from app.pipeline.digest import build_digest_message
from app.pipeline.filters import deduplicate_items, filter_recent_items
from app.pipeline.refresh import refresh_sources
from app.pipeline.report import build_report_message
from app.sources.registry import SourceRegistry


class PipelineDispatcher:
    def __init__(self, settings: AppSettings, registry: SourceRegistry, report_generator: ReportGenerator) -> None:
        self._settings = settings
        self._registry = registry
        self._report_generator = report_generator

    def run(self, mode: DeliveryMode) -> PipelineResult:
        enabled_sources = self._settings.enabled_sources if self._settings.source_filter_configured else None
        source_results = refresh_sources(self._registry, enabled_sources)
        items: list[ContentItem] = []
        for result in source_results:
            items.extend(result.items)
        items = deduplicate_items(filter_recent_items(items))
        messages = []
        targets = self._settings.enabled_channels()
        if items and targets:
            if mode is DeliveryMode.REPORT:
                messages.append(
                    build_report_message(
                        items=items,
                        report_generator=self._report_generator,
                        targets=targets,
                        disable_web_page_preview=self._settings.telegram.disable_web_page_preview,
                    )
                )
            else:
                messages.append(
                    build_digest_message(
                        items=items,
                        targets=targets,
                        disable_web_page_preview=self._settings.telegram.disable_web_page_preview,
                    )
                )
        return PipelineResult(mode=mode, items=items, messages=messages, source_results=source_results)
