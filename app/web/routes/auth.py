from __future__ import annotations

from app.bootstrap import AppContext


def get_auth_status(context: AppContext) -> dict[str, bool]:
    return {"api_key_required": bool(context.settings.web_api_key)}

