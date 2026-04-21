import os
import tempfile
import unittest
from unittest.mock import patch

from app.bootstrap import AppController


class AppControllerTestCase(unittest.TestCase):
    def test_controller_persists_settings_and_other_controllers_can_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    "APP_DATA_DIR": tmpdir,
                    "AUTOMATION_ENABLED": "false",
                    "AUTOMATION_DAILY_TIME": "09:00",
                    "SOURCE_MSE_NOTICES_ENABLED": "true",
                    "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                    "SOURCE_X_POSTS_ENABLED": "false",
                },
                clear=True,
            ):
                first = AppController()
                second = AppController()

                first.update_settings(
                    {
                        "automation": {
                            "enabled": True,
                            "daily_time": "08:15",
                            "default_mode": "report",
                        },
                        "sources": {
                            "mse_notices": True,
                            "pku_reagent_orders": True,
                            "x_posts": True,
                        },
                        "x": {
                            "enabled": True,
                            "cookie_header": "auth_token=test; ct0=csrf",
                            "usernames": ["OpenAI", "sama"],
                        },
                    }
                )

                synced = second.get_context().settings

                self.assertTrue(synced.automation.enabled)
                self.assertEqual(synced.automation.daily_time, "08:15")
                self.assertEqual(synced.automation.default_mode.value, "report")
                self.assertEqual(synced.enabled_sources, ("mse_notices", "pku_reagent_orders", "x_posts"))
                self.assertTrue(synced.x.enabled)
                self.assertEqual(synced.x.usernames, ("OpenAI", "sama"))
                self.assertTrue((synced.data_dir / "settings" / "runtime_settings.json").exists())


if __name__ == "__main__":
    unittest.main()
