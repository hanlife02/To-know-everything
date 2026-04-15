import os
import unittest
from unittest.mock import patch

from app.config.settings import AppSettings


class SettingsTestCase(unittest.TestCase):
    def test_telegram_auto_enables_with_bot_token_and_chat_id(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "chat-id",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertTrue(settings.telegram.enabled)
        self.assertTrue(settings.telegram.is_configured())

    def test_bark_auto_enables_with_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BARK_KEY": "bark-key",
                "BARK_GROUP": "lab-orders",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertTrue(settings.bark.enabled)
        self.assertTrue(settings.bark.is_configured())
        self.assertEqual(settings.bark.group, "lab-orders")

    def test_pku_reagent_auto_enables_with_username_and_password(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PKU_REAGENT_USERNAME": "CG17288",
                "PKU_REAGENT_PASSWORD": "secret",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertTrue(settings.pku_reagent.enabled)
        self.assertTrue(settings.pku_reagent.has_login_credentials())

    def test_pku_reagent_can_be_explicitly_disabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PKU_REAGENT_ENABLED": "false",
                "PKU_REAGENT_USERNAME": "CG17288",
                "PKU_REAGENT_PASSWORD": "secret",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertFalse(settings.pku_reagent.enabled)


if __name__ == "__main__":
    unittest.main()
