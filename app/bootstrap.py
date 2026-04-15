from __future__ import annotations

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


def create_app_context() -> AppContext:
    settings = AppSettings.from_env()
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
