import os
import tempfile
import unittest
from unittest.mock import patch

from app.bootstrap import create_app_context
from app.web import get_dashboard_payload, get_settings_payload


class WebPayloadsTestCase(unittest.TestCase):
    def test_settings_and_dashboard_include_x_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    "APP_DATA_DIR": tmpdir,
                    "X_ENABLED": "true",
                    "X_BEARER_TOKEN": "token",
                    "X_USERNAMES": "OpenAI,AnthropicAI,sama",
                    "X_MAX_RESULTS_PER_USER": "7",
                    "X_EXCLUDE_REPLIES": "false",
                    "X_EXCLUDE_RETWEETS": "true",
                    "SOURCE_X_POSTS_ENABLED": "true",
                },
                clear=True,
            ):
                context = create_app_context()

            settings_payload = get_settings_payload(context)
            dashboard_payload = get_dashboard_payload(context)

        self.assertEqual(
            settings_payload["x"],
            {
                "enabled": True,
                "configured": True,
                "usernames": ["OpenAI", "AnthropicAI", "sama"],
                "max_results_per_user": 7,
                "exclude_replies": False,
                "exclude_retweets": True,
            },
        )
        self.assertEqual(dashboard_payload["x"], settings_payload["x"])
        self.assertIn("x_posts", dashboard_payload["enabled_sources"])
        registered_sources = {item["key"]: item for item in dashboard_payload["registered_sources"]}
        self.assertTrue(registered_sources["x_posts"]["enabled"])


if __name__ == "__main__":
    unittest.main()
