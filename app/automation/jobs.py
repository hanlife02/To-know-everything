from __future__ import annotations

from app.bootstrap import AppContext
from app.domain.enums import DeliveryMode
from app.domain.models import JobRunResult


def run_delivery_job(context: AppContext, mode: DeliveryMode | None = None) -> JobRunResult:
    selected_mode = mode or context.settings.automation.default_mode
    return context.notification_service.run(selected_mode)

