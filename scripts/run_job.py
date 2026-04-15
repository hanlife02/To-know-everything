from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.automation.jobs import run_delivery_job
from app.bootstrap import create_app_context
from app.domain.enums import DeliveryMode


def main() -> int:
    mode = DeliveryMode.SUMMARY
    if len(sys.argv) > 1:
        mode = DeliveryMode.from_value(sys.argv[1])
    context = create_app_context()
    result = run_delivery_job(context, mode)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

