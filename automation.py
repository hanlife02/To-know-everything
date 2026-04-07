from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from daily_job import push_summary, refresh_dashboard_data, run_all

SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "automation_settings.json"
SUPPORTED_DELIVERY_MODES = {"summary", "report"}
SUPPORTED_SUMMARY_CHANNELS = {"bark", "telegram", "all"}
SUPPORTED_SUMMARY_TARGETS = {"bilibili", "materials_notices", "xhs", "all"}
_SETTINGS_LOCK = threading.RLock()


@dataclass(slots=True)
class AutomationSettings:
    enabled: bool = False
    hour: int = 9
    minute: int = 0
    delivery_mode: str = "report"
    summary_channel: str = "all"
    summary_target: str = "all"
    bark_completion: bool = True
    last_attempt_at: str = ""
    last_success_at: str = ""
    last_status: str = "idle"
    last_error: str = ""


def parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def clamp_int(value: Any, *, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def normalize_settings(settings: AutomationSettings) -> AutomationSettings:
    settings.hour = clamp_int(settings.hour, minimum=0, maximum=23, default=9)
    settings.minute = clamp_int(settings.minute, minimum=0, maximum=59, default=0)
    if settings.delivery_mode not in SUPPORTED_DELIVERY_MODES:
        settings.delivery_mode = "report"
    if settings.summary_channel not in SUPPORTED_SUMMARY_CHANNELS:
        settings.summary_channel = "all"
    if settings.summary_target not in SUPPORTED_SUMMARY_TARGETS:
        settings.summary_target = "all"
    if settings.last_status not in {"idle", "running", "success", "error"}:
        settings.last_status = "idle"
    settings.last_attempt_at = str(settings.last_attempt_at or "").strip()
    settings.last_success_at = str(settings.last_success_at or "").strip()
    settings.last_error = str(settings.last_error or "").strip()
    return settings


def load_automation_settings(path: Path = SETTINGS_PATH) -> AutomationSettings:
    settings = AutomationSettings()
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        delivery_mode = str(payload.get("delivery_mode", "")).strip()
        if delivery_mode not in SUPPORTED_DELIVERY_MODES:
            if parse_bool(payload.get("generate_ai_reports"), True):
                delivery_mode = "report"
            else:
                delivery_mode = "summary"
        settings = AutomationSettings(
            enabled=parse_bool(payload.get("enabled"), False),
            hour=clamp_int(payload.get("hour"), minimum=0, maximum=23, default=9),
            minute=clamp_int(payload.get("minute"), minimum=0, maximum=59, default=0),
            delivery_mode=delivery_mode,
            summary_channel=str(payload.get("summary_channel", "all")).strip(),
            summary_target=str(payload.get("summary_target", "all")).strip(),
            bark_completion=parse_bool(payload.get("bark_completion"), True),
            last_attempt_at=str(payload.get("last_attempt_at", "")).strip(),
            last_success_at=str(payload.get("last_success_at", "")).strip(),
            last_status=str(payload.get("last_status", "idle")).strip(),
            last_error=str(payload.get("last_error", "")).strip(),
        )
    return normalize_settings(settings)


def save_automation_settings(
    settings: AutomationSettings,
    path: Path = SETTINGS_PATH,
) -> Path:
    normalized = normalize_settings(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _SETTINGS_LOCK:
        path.write_text(
            json.dumps(asdict(normalized), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return path


def serialize_automation_settings(settings: AutomationSettings) -> dict[str, Any]:
    return {
        "enabled": settings.enabled,
        "hour": settings.hour,
        "minute": settings.minute,
        "time_text": f"{settings.hour:02d}:{settings.minute:02d}",
        "delivery_mode": settings.delivery_mode,
        "summary_channel": settings.summary_channel,
        "summary_target": settings.summary_target,
        "bark_completion": settings.bark_completion,
        "last_attempt_at": settings.last_attempt_at,
        "last_success_at": settings.last_success_at,
        "last_status": settings.last_status,
        "last_error": settings.last_error,
    }


def get_automation_status(settings: AutomationSettings) -> dict[str, Any]:
    return {
        "enabled": settings.enabled,
        "schedule": f"{settings.hour:02d}:{settings.minute:02d}",
        "delivery_mode": settings.delivery_mode,
        "delivery_mode_text": "摘要" if settings.delivery_mode == "summary" else "日报",
        "last_attempt_at": settings.last_attempt_at or "暂无",
        "last_success_at": settings.last_success_at or "暂无",
        "last_status": settings.last_status,
        "last_error": settings.last_error,
        "summary_channel": settings.summary_channel,
        "summary_target": settings.summary_target,
        "bark_completion": settings.bark_completion,
    }


def should_run_now(settings: AutomationSettings, now: datetime | None = None) -> bool:
    if not settings.enabled:
        return False

    current = now or datetime.now()
    if (current.hour, current.minute) < (settings.hour, settings.minute):
        return False

    if not settings.last_attempt_at:
        return True

    try:
        last_attempt = datetime.strptime(settings.last_attempt_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True

    return last_attempt.date() < current.date()


def update_automation_run_state(
    *,
    status: str,
    attempt_at: str | None = None,
    success_at: str | None = None,
    error: str | None = None,
    path: Path = SETTINGS_PATH,
) -> AutomationSettings:
    with _SETTINGS_LOCK:
        settings = load_automation_settings(path)
        settings.last_status = status
        if attempt_at is not None:
            settings.last_attempt_at = attempt_at
        if success_at is not None:
            settings.last_success_at = success_at
        if error is not None:
            settings.last_error = error
        save_automation_settings(settings, path)
    return settings


def run_automation_job(path: Path = SETTINGS_PATH) -> dict[str, int]:
    settings = load_automation_settings(path)
    attempt_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_automation_run_state(status="running", attempt_at=attempt_at, error="")

    try:
        if settings.delivery_mode == "summary":
            dashboard = refresh_dashboard_data()
            push_summary(settings.summary_channel, settings.summary_target, dashboard)
            result = {
                "bilibili_count": len(dashboard["bilibili"]["videos"]),
                "materials_count": len(dashboard["materials_notices"]["notices"]),
                "xhs_count": len(dashboard["xhs"]["notes"]),
                "report_count": 0,
                "pushed_report_count": 0,
            }
        else:
            result = run_all(
                generate_ai_reports=True,
                push_summary_too=False,
                summary_channel=settings.summary_channel,
                summary_target=settings.summary_target,
                bark_completion=settings.bark_completion,
            )
    except Exception as exc:  # noqa: BLE001
        update_automation_run_state(
            status="error",
            attempt_at=attempt_at,
            error=str(exc).strip(),
            path=path,
        )
        raise

    success_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_automation_run_state(
        status="success",
        attempt_at=attempt_at,
        success_at=success_at,
        error="",
        path=path,
    )
    return result


class AutomationScheduler:
    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="automation-scheduler",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        while not self._stop_event.wait(30):
            settings = load_automation_settings(self.path)
            if not should_run_now(settings):
                continue

            try:
                run_automation_job(self.path)
            except Exception as exc:  # noqa: BLE001
                print(f"[automation] scheduled run failed: {exc}")


automation_scheduler = AutomationScheduler()
