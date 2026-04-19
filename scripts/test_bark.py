from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _env import ensure_project_root_on_path, load_dotenv

ensure_project_root_on_path()
load_dotenv()

from app.config.settings import AppSettings
from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import NotificationMessage
from app.notifications.bark import BarkNotifier


def main() -> int:
    settings = AppSettings.from_env()
    notifier = BarkNotifier(settings.bark)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    title = sys.argv[1] if len(sys.argv) > 1 else "To know everything test"
    body = sys.argv[2] if len(sys.argv) > 2 else f"Bark test message sent at {timestamp}"
    message = NotificationMessage(
        title=title,
        body=body,
        mode=DeliveryMode.SUMMARY,
        targets=(NotificationChannel.BARK,),
    )
    receipt = notifier.send(message)
    print(
        json.dumps(
            {
                "channel": receipt.channel.value,
                "delivered": receipt.delivered,
                "detail": receipt.detail,
                "configured": settings.bark.is_configured(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if receipt.delivered else 1


if __name__ == "__main__":
    raise SystemExit(main())
