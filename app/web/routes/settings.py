from __future__ import annotations

from app.bootstrap import AppContext


def get_settings_payload(context: AppContext) -> dict[str, object]:
    return {
        "env": context.settings.env,
        "log_level": context.settings.log_level,
        "data_dir": str(context.settings.data_dir),
        "automation_enabled": context.settings.automation.enabled,
        "automation_daily_time": context.settings.automation.daily_time,
        "default_mode": context.settings.automation.default_mode.value,
        "x": {
            "enabled": context.settings.x.enabled,
            "configured": context.settings.x.is_configured(),
            "usernames": list(context.settings.x.usernames),
            "base_url": context.settings.x.base_url,
            "max_results_per_user": context.settings.x.max_results_per_user,
            "exclude_replies": context.settings.x.exclude_replies,
            "exclude_retweets": context.settings.x.exclude_retweets,
        },
    }
