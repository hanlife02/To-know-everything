from __future__ import annotations

import os
from threading import RLock
from dataclasses import dataclass

from app.config.settings import AppSettings
from app.llm.report_generator import ReportGenerator
from app.notifications.router import NotificationRouter, build_notification_router
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.sources.builtins import register_builtin_sources
from app.sources.registry import SourceRegistry
from app.storage.cache_store import CacheStore
from app.storage.paths import StoragePaths
from app.storage.settings_store import SettingsStore
from app.storage.state_store import StateStore


@dataclass(slots=True)
class AppContext:
    settings: AppSettings
    paths: StoragePaths
    registry: SourceRegistry
    cache_store: CacheStore
    state_store: StateStore
    router: NotificationRouter
    report_generator: ReportGenerator
    dashboard_service: DashboardService
    notification_service: NotificationService
    report_service: ReportService


def build_app_context(settings: AppSettings) -> AppContext:
    paths = StoragePaths.ensure(settings.data_dir)
    registry = SourceRegistry()
    register_builtin_sources(registry, settings, paths)
    cache_store = CacheStore(paths.cache)
    state_store = StateStore(paths.state)
    report_generator = ReportGenerator()
    router = build_notification_router(settings)
    dashboard_service = DashboardService(settings=settings, registry=registry, paths=paths, state_store=state_store)
    notification_service = NotificationService(
        settings=settings,
        registry=registry,
        cache_store=cache_store,
        state_store=state_store,
        router=router,
        report_generator=report_generator,
    )
    report_service = ReportService(report_generator=report_generator)
    return AppContext(
        settings=settings,
        paths=paths,
        registry=registry,
        cache_store=cache_store,
        state_store=state_store,
        router=router,
        report_generator=report_generator,
        dashboard_service=dashboard_service,
        notification_service=notification_service,
        report_service=report_service,
    )


def create_app_context() -> AppContext:
    return build_app_context(AppSettings.from_env())


class AppController:
    def __init__(self) -> None:
        self._lock = RLock()
        self._env = dict(os.environ)
        base_settings = AppSettings.from_env(self._env)
        self._paths = StoragePaths.ensure(base_settings.data_dir)
        self._settings_store = SettingsStore(self._paths.settings)
        self._settings_fingerprint: int | None = None
        self._context = self._build_context()

    @property
    def settings_store_path(self) -> str:
        return str(self._settings_store.path)

    def get_context(self) -> AppContext:
        self.sync()
        with self._lock:
            return self._context

    def current_settings_payload(self) -> dict[str, object]:
        return self.get_context().settings.to_runtime_payload()

    def base_settings_payload(self) -> dict[str, object]:
        with self._lock:
            return AppSettings.from_env(self._env).to_runtime_payload()

    def current_runtime_overrides(self) -> dict[str, object]:
        with self._lock:
            return self._settings_store.load()

    def update_settings(self, payload: dict[str, object]) -> AppContext:
        with self._lock:
            self._settings_store.save(payload)
            self._settings_fingerprint = self._settings_store.fingerprint()
            self._context = self._build_context()
            return self._context

    def clear_runtime_overrides(self) -> AppContext:
        return self.update_settings({})

    def sync(self) -> None:
        fingerprint = self._settings_store.fingerprint()
        with self._lock:
            if fingerprint == self._settings_fingerprint:
                return
            self._settings_fingerprint = fingerprint
            self._context = self._build_context()

    def _build_context(self) -> AppContext:
        base_settings = AppSettings.from_env(self._env)
        overrides = self._settings_store.load()
        settings = base_settings.with_runtime_overrides(overrides)
        return build_app_context(settings)
