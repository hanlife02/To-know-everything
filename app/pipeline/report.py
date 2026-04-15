from __future__ import annotations

from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import ContentItem, NotificationMessage
from app.llm.report_generator import ReportGenerator


def build_report_message(
    items: list[ContentItem],
    report_generator: ReportGenerator,
    targets: tuple[NotificationChannel, ...],
    disable_web_page_preview: bool = True,
) -> NotificationMessage:
    return NotificationMessage(
        title="AI 日报",
        body=report_generator.generate(items),
        mode=DeliveryMode.REPORT,
        targets=targets,
        disable_web_page_preview=disable_web_page_preview,
    )

