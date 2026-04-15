from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap import AppContext
from app.automation.jobs import run_delivery_job


@dataclass(slots=True)
class DailyScheduler:
    context: AppContext

    def run_pending(self) -> None:
        if not self.context.settings.automation.enabled:
            return
        run_delivery_job(self.context, self.context.settings.automation.default_mode)

