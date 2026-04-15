from __future__ import annotations

from app.config.settings import AppSettings
from app.sources.registry import SourceRegistry
from app.storage.paths import StoragePaths
from app.storage.state_store import StateStore


class DashboardService:
    def __init__(
        self,
        settings: AppSettings,
        registry: SourceRegistry,
        paths: StoragePaths,
        state_store: StateStore,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._paths = paths
        self._state_store = state_store

    def snapshot(self) -> dict[str, object]:
        return {
            "env": self._settings.env,
            "enabled_channels": [channel.value for channel in self._settings.enabled_channels()],
            "enabled_sources": list(self._settings.enabled_sources),
            "registered_sources": self._registry.snapshot(),
            "automation_enabled": self._settings.automation.enabled,
            "automation_daily_time": self._settings.automation.daily_time,
            "data_paths": {
                "cache": str(self._paths.cache),
                "state": str(self._paths.state),
                "settings": str(self._paths.settings),
                "logs": str(self._paths.logs),
            },
            "recent_runs": self._state_store.get_run_history()[-5:],
        }

