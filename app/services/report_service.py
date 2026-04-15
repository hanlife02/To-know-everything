from __future__ import annotations

from app.domain.models import ContentItem
from app.llm.report_generator import ReportGenerator


class ReportService:
    def __init__(self, report_generator: ReportGenerator) -> None:
        self._report_generator = report_generator

    def preview(self, items: list[ContentItem]) -> str:
        return self._report_generator.generate(items)

