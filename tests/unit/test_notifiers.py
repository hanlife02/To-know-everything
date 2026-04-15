from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.config.settings import BarkSettings, TelegramSettings
from app.domain.enums import DeliveryMode
from app.domain.models import NotificationMessage
from app.notifications.bark import BarkNotifier
from app.notifications.telegram import TelegramNotifier


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class TelegramNotifierTestCase(unittest.TestCase):
    def test_send_posts_message_to_telegram_api(self) -> None:
        notifier = TelegramNotifier(TelegramSettings(enabled=True, bot_token="token", chat_id="chat"))
        message = NotificationMessage(
            title="信息摘要",
            body="第一条\n第二条",
            mode=DeliveryMode.SUMMARY,
            targets=(),
        )

        with patch("app.notifications.telegram.urlopen", return_value=FakeResponse({"ok": True})) as mocked_urlopen:
            receipt = notifier.send(message)

        self.assertTrue(receipt.delivered)
        self.assertEqual(receipt.detail, "telegram sent 1 segment(s)")
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], "chat")
        self.assertIn("信息摘要", payload["text"])
        self.assertIn("第一条", payload["text"])

    def test_send_returns_failed_receipt_when_telegram_api_rejects_message(self) -> None:
        notifier = TelegramNotifier(TelegramSettings(enabled=True, bot_token="token", chat_id="chat"))
        message = NotificationMessage(
            title="信息摘要",
            body="内容",
            mode=DeliveryMode.SUMMARY,
            targets=(),
        )

        with patch(
            "app.notifications.telegram.urlopen",
            return_value=FakeResponse({"ok": False, "description": "Bad Request"}),
        ):
            receipt = notifier.send(message)

        self.assertFalse(receipt.delivered)
        self.assertIn("Bad Request", receipt.detail)


class BarkNotifierTestCase(unittest.TestCase):
    def test_send_posts_message_to_bark_api(self) -> None:
        notifier = BarkNotifier(BarkSettings(enabled=True, key="key", group="lab"))
        message = NotificationMessage(
            title="信息摘要",
            body="内容",
            mode=DeliveryMode.SUMMARY,
            targets=(),
        )

        with patch("app.notifications.bark.urlopen", return_value=FakeResponse({"code": 200, "message": "success"})) as mocked_urlopen:
            receipt = notifier.send(message)

        self.assertTrue(receipt.delivered)
        self.assertEqual(receipt.detail, "bark sent (group=lab)")
        request = mocked_urlopen.call_args.args[0]
        payload = request.data.decode("utf-8")
        self.assertIn("title=%E4%BF%A1%E6%81%AF%E6%91%98%E8%A6%81", payload)
        self.assertIn("group=lab", payload)

    def test_send_returns_failed_receipt_when_bark_api_rejects_message(self) -> None:
        notifier = BarkNotifier(BarkSettings(enabled=True, key="key"))
        message = NotificationMessage(
            title="信息摘要",
            body="内容",
            mode=DeliveryMode.SUMMARY,
            targets=(),
        )

        with patch(
            "app.notifications.bark.urlopen",
            return_value=FakeResponse({"code": 400, "message": "invalid request"}),
        ):
            receipt = notifier.send(message)

        self.assertFalse(receipt.delivered)
        self.assertIn("invalid request", receipt.detail)


if __name__ == "__main__":
    unittest.main()
