from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _env import ensure_project_root_on_path, load_dotenv

ensure_project_root_on_path()
load_dotenv()

from app.bootstrap import create_app_context


def main() -> int:
    context = create_app_context()
    defaults = {
        "notification_settings.json": {
            "telegram_enabled": context.settings.telegram.enabled,
            "bark_enabled": context.settings.bark.enabled,
        },
        "automation_settings.json": {
            "enabled": context.settings.automation.enabled,
            "daily_time": context.settings.automation.daily_time,
            "mode": context.settings.automation.default_mode.value,
        },
        "llm_settings.json": {"report_enabled": True},
    }
    for filename, payload in defaults.items():
        path = context.paths.settings / filename
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("runtime settings bootstrapped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
