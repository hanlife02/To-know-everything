import os
import unittest
from unittest.mock import patch

from app.config.settings import AppSettings


class RuntimeSettingsTestCase(unittest.TestCase):
    def test_runtime_overrides_can_replace_env_backed_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AUTOMATION_ENABLED": "false",
                "SOURCE_MSE_NOTICES_ENABLED": "true",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                "SOURCE_X_POSTS_ENABLED": "false",
                "X_ENABLED": "false",
                "X_USERNAMES": "OpenAI",
            },
            clear=True,
        ):
            base = AppSettings.from_env()

        overridden = base.with_runtime_overrides(
            {
                "automation": {
                    "enabled": True,
                    "daily_time": "07:30",
                    "default_mode": "report",
                },
                "sources": {
                    "mse_notices": False,
                    "pku_reagent_orders": True,
                    "x_posts": True,
                },
                "x": {
                    "enabled": True,
                    "cookie_header": "auth_token=test; ct0=csrf",
                    "usernames": ["OpenAI", "AnthropicAI"],
                    "exclude_replies": False,
                },
            }
        )

        self.assertTrue(overridden.automation.enabled)
        self.assertEqual(overridden.automation.daily_time, "07:30")
        self.assertEqual(overridden.automation.default_mode.value, "report")
        self.assertEqual(overridden.enabled_sources, ("pku_reagent_orders", "x_posts"))
        self.assertTrue(overridden.x.enabled)
        self.assertEqual(overridden.x.usernames, ("OpenAI", "AnthropicAI"))
        self.assertFalse(overridden.x.exclude_replies)

    def test_runtime_payload_contains_nested_settings_and_sources(self) -> None:
        settings = AppSettings().with_runtime_overrides(
            {
                "sources": {
                    "mse_notices": True,
                    "pku_reagent_orders": True,
                    "x_posts": False,
                }
            }
        )

        payload = settings.to_runtime_payload()

        self.assertIn("automation", payload)
        self.assertIn("telegram", payload)
        self.assertIn("pku_reagent", payload)
        self.assertEqual(
            payload["sources"],
            {
                "mse_notices": True,
                "pku_reagent_orders": True,
                "x_posts": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
