from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from time import sleep
from typing import Callable

from app.bootstrap import AppContext
from app.automation.jobs import run_delivery_job


@dataclass(slots=True)
class DailyScheduler:
    context: AppContext | Callable[[], AppContext]

    def run_pending(self, now: datetime | None = None) -> bool:
        context = self._current_context()
        if not self.is_due(now, context=context):
            return False
        run_delivery_job(context, context.settings.automation.default_mode)
        return True

    def is_due(self, now: datetime | None = None, context: AppContext | None = None) -> bool:
        active_context = context or self._current_context()
        if not active_context.settings.automation.enabled:
            return False
        current = (now or datetime.now().astimezone()).astimezone()
        scheduled_at = self._scheduled_datetime_for_day(current, active_context=active_context)
        if current < scheduled_at:
            return False
        return not self._has_run_since(scheduled_at, active_context=active_context)

    def run_forever(self, poll_interval_seconds: int = 30) -> None:
        while True:
            self.run_pending()
            sleep(poll_interval_seconds)

    def _scheduled_datetime_for_day(self, now: datetime, *, active_context: AppContext) -> datetime:
        scheduled_time = _parse_daily_time(active_context.settings.automation.daily_time)
        return now.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )

    def _has_run_since(self, threshold: datetime, *, active_context: AppContext) -> bool:
        for run in reversed(active_context.state_store.get_run_history()):
            raw_timestamp = run.get("timestamp")
            if not isinstance(raw_timestamp, str):
                continue
            try:
                timestamp = datetime.fromisoformat(raw_timestamp)
            except ValueError:
                continue
            localized = timestamp.astimezone(threshold.tzinfo)
            if localized >= threshold:
                return True
            if localized < threshold - timedelta(days=1):
                break
        return False

    def _current_context(self) -> AppContext:
        if callable(self.context):
            return self.context()
        return self.context


def _parse_daily_time(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour not in range(24) or minute not in range(60):
        raise ValueError(f"invalid automation daily time: {value}")
    return time(hour=hour, minute=minute)
