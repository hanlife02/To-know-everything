import unittest
from dataclasses import dataclass
from datetime import UTC, datetime

from app.automation.scheduler import DailyScheduler, _parse_daily_time


class StubStateStore:
    def __init__(self, history: list[dict[str, object]] | None = None) -> None:
        self._history = history or []

    def get_run_history(self) -> list[dict[str, object]]:
        return list(self._history)


@dataclass
class StubAutomationSettings:
    enabled: bool = True
    daily_time: str = "09:00"
    default_mode: object = "summary"


@dataclass
class StubSettings:
    automation: StubAutomationSettings


@dataclass
class StubContext:
    settings: StubSettings
    state_store: StubStateStore


class SchedulerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tzinfo = datetime.now().astimezone().tzinfo

    def test_parse_daily_time(self) -> None:
        parsed = _parse_daily_time("09:30")

        self.assertEqual(parsed.hour, 9)
        self.assertEqual(parsed.minute, 30)

    def test_is_due_false_before_scheduled_time(self) -> None:
        scheduler = DailyScheduler(
            StubContext(
                settings=StubSettings(automation=StubAutomationSettings(enabled=True, daily_time="09:00")),
                state_store=StubStateStore(),
            )
        )

        due = scheduler.is_due(datetime(2026, 4, 16, 8, 59, tzinfo=self._tzinfo))

        self.assertFalse(due)

    def test_is_due_true_after_scheduled_time_when_not_run(self) -> None:
        scheduler = DailyScheduler(
            StubContext(
                settings=StubSettings(automation=StubAutomationSettings(enabled=True, daily_time="09:00")),
                state_store=StubStateStore(),
            )
        )

        due = scheduler.is_due(datetime(2026, 4, 16, 9, 1, tzinfo=self._tzinfo))

        self.assertTrue(due)

    def test_is_due_false_after_run_for_same_schedule_window(self) -> None:
        scheduler = DailyScheduler(
            StubContext(
                settings=StubSettings(automation=StubAutomationSettings(enabled=True, daily_time="09:00")),
                state_store=StubStateStore(
                    [
                        {
                            "timestamp": datetime(2026, 4, 16, 9, 5, tzinfo=self._tzinfo).astimezone(UTC).isoformat(),
                        }
                    ]
                ),
            )
        )

        due = scheduler.is_due(datetime(2026, 4, 16, 9, 6, tzinfo=self._tzinfo))

        self.assertFalse(due)

    def test_is_due_true_if_only_run_was_before_today_schedule(self) -> None:
        scheduler = DailyScheduler(
            StubContext(
                settings=StubSettings(automation=StubAutomationSettings(enabled=True, daily_time="09:00")),
                state_store=StubStateStore(
                    [
                        {
                            "timestamp": datetime(2026, 4, 16, 8, 30, tzinfo=self._tzinfo).astimezone(UTC).isoformat(),
                        }
                    ]
                ),
            )
        )

        due = scheduler.is_due(datetime(2026, 4, 16, 9, 1, tzinfo=self._tzinfo))

        self.assertTrue(due)


if __name__ == "__main__":
    unittest.main()
