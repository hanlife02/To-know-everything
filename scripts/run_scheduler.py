from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _env import ensure_project_root_on_path, load_dotenv

ensure_project_root_on_path()
load_dotenv()

from app.automation.scheduler import DailyScheduler
from app.bootstrap import create_app_context


def main() -> int:
    context = create_app_context()
    scheduler = DailyScheduler(context)
    print(
        "scheduler started: "
        f"enabled={context.settings.automation.enabled}, "
        f"time={context.settings.automation.daily_time}, "
        f"mode={context.settings.automation.default_mode.value}"
    )
    scheduler.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
