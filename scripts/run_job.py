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

from app.automation.jobs import run_delivery_job
from app.bootstrap import AppController
from app.domain.enums import DeliveryMode


def main() -> int:
    mode = DeliveryMode.SUMMARY
    if len(sys.argv) > 1:
        mode = DeliveryMode.from_value(sys.argv[1])
    controller = AppController()
    context = controller.get_context()
    result = run_delivery_job(context, mode)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
