from __future__ import annotations

from app.bootstrap import AppContext


def get_dashboard_payload(context: AppContext) -> dict[str, object]:
    return context.dashboard_service.snapshot()

