import os
import unittest
from unittest.mock import patch

from app.config.settings import AppSettings


class SettingsTestCase(unittest.TestCase):
    def test_telegram_stays_disabled_without_explicit_flag(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "chat-id",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertFalse(settings.telegram.enabled)
        self.assertFalse(settings.telegram.is_configured())

    def test_telegram_can_be_explicitly_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_ENABLED": "true",
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "chat-id",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertTrue(settings.telegram.enabled)
        self.assertTrue(settings.telegram.is_configured())

    def test_bark_stays_disabled_without_explicit_flag(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BARK_KEY": "bark-key",
                "BARK_GROUP": "lab-orders",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertFalse(settings.bark.enabled)
        self.assertFalse(settings.bark.is_configured())
        self.assertEqual(settings.bark.group, "lab-orders")

    def test_bark_can_be_explicitly_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BARK_ENABLED": "true",
                "BARK_KEY": "bark-key",
                "BARK_GROUP": "lab-orders",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertTrue(settings.bark.enabled)
        self.assertTrue(settings.bark.is_configured())
        self.assertEqual(settings.bark.group, "lab-orders")

    def test_pku_reagent_stays_disabled_without_explicit_flag(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PKU_REAGENT_USERNAME": "CG17288",
                "PKU_REAGENT_PASSWORD": "secret",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertFalse(settings.pku_reagent.enabled)
        self.assertTrue(settings.pku_reagent.has_login_credentials())

    def test_pku_reagent_can_be_explicitly_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PKU_REAGENT_ENABLED": "true",
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

    def test_source_filter_stays_unconfigured_without_explicit_flag(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertEqual(settings.enabled_sources, ())
        self.assertTrue(settings.source_filter_configured)

    def test_source_filter_can_enable_pku_reagent_orders(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "true",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertEqual(settings.enabled_sources, ("pku_reagent_orders",))
        self.assertTrue(settings.source_filter_configured)

    def test_source_filter_can_enable_multiple_sources(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SOURCE_MSE_NOTICES_ENABLED": "true",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "true",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertEqual(settings.enabled_sources, ("mse_notices", "pku_reagent_orders"))
        self.assertTrue(settings.source_filter_configured)

    def test_legacy_enabled_sources_is_still_supported(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ENABLED_SOURCES": "pku_reagent_orders",
            },
            clear=True,
        ):
            settings = AppSettings.from_env()

        self.assertEqual(settings.enabled_sources, ("pku_reagent_orders",))
        self.assertTrue(settings.source_filter_configured)


if __name__ == "__main__":
    unittest.main()
