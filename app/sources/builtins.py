from __future__ import annotations

from app.config.settings import AppSettings
from app.sources.mse_notices.service import MseNoticesSource
from app.sources.pku_reagent.service import PkuReagentNotificationSource
from app.sources.registry import SourceRegistry
from app.storage.paths import StoragePaths


def register_builtin_sources(registry: SourceRegistry, settings: AppSettings, paths: StoragePaths) -> None:
    registry.register(MseNoticesSource())
    registry.register(
        PkuReagentNotificationSource.from_settings(
            settings.pku_reagent,
            session_cache_path=paths.settings / "pku_reagent_session.json",
        )
    )
