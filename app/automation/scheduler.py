from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from time import sleep

from app.bootstrap import AppContext
from app.automation.jobs import run_delivery_job


@dataclass(slots=True)
class DailyScheduler:
    context: AppContext

    def run_pending(self, now: datetime | None = None) -> bool:
        if not self.is_due(now):
            return False
        run_delivery_job(self.context, self.context.settings.automation.default_mode)
        return True

    def is_due(self, now: datetime | None = None) -> bool:
        if not self.context.settings.automation.enabled:
            return False
        current = (now or datetime.now().astimezone()).astimezone()
        scheduled_at = self._scheduled_datetime_for_day(current)
        if current < scheduled_at:
            return False
        return not self._has_run_since(scheduled_at)

    def run_forever(self, poll_interval_seconds: int = 30) -> None:
        while True:
            self.run_pending()
            sleep(poll_interval_seconds)

    def _scheduled_datetime_for_day(self, now: datetime) -> datetime:
        scheduled_time = _parse_daily_time(self.context.settings.automation.daily_time)
        return now.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )

    def _has_run_since(self, threshold: datetime) -> bool:
        for run in reversed(self.context.state_store.get_run_history()):
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


def _parse_daily_time(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour not in range(24) or minute not in range(60):
        raise ValueError(f"invalid automation daily time: {value}")
    return time(hour=hour, minute=minute)
