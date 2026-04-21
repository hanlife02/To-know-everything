import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts.run_cli import main, parse_cli_value, set_nested_value, unset_nested_value


class CliHelpersTestCase(unittest.TestCase):
    def test_parse_cli_value_infers_common_scalars(self) -> None:
        self.assertIs(parse_cli_value("true", parse_json=False), True)
        self.assertIs(parse_cli_value("false", parse_json=False), False)
        self.assertIsNone(parse_cli_value("null", parse_json=False))
        self.assertEqual(parse_cli_value("12", parse_json=False), 12)
        self.assertEqual(parse_cli_value("09:00", parse_json=False), "09:00")
        self.assertEqual(parse_cli_value('["a", "b"]', parse_json=True), ["a", "b"])

    def test_set_and_unset_nested_value(self) -> None:
        payload: dict[str, object] = {}

        set_nested_value(payload, "automation.enabled", True)
        set_nested_value(payload, "x.usernames", ["OpenAI", "sama"])

        self.assertEqual(
            payload,
            {
                "automation": {"enabled": True},
                "x": {"usernames": ["OpenAI", "sama"]},
            },
        )

        self.assertTrue(unset_nested_value(payload, "x.usernames"))
        self.assertEqual(payload, {"automation": {"enabled": True}})
        self.assertFalse(unset_nested_value(payload, "x.usernames"))


class CliCommandTestCase(unittest.TestCase):
    def test_config_commands_and_status_use_local_runtime_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "APP_DATA_DIR": tmpdir,
                "AUTOMATION_ENABLED": "false",
                "AUTOMATION_DAILY_TIME": "09:00",
                "AUTOMATION_DEFAULT_MODE": "summary",
                "SOURCE_MSE_NOTICES_ENABLED": "false",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                "SOURCE_X_POSTS_ENABLED": "false",
                "TELEGRAM_ENABLED": "false",
                "BARK_ENABLED": "false",
                "PKU_REAGENT_ENABLED": "false",
                "X_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=True):
                set_output = self._run_main(
                    ["config", "set", "automation.enabled", "true", "--pretty"],
                )
                set_payload = json.loads(set_output)
                self.assertTrue(set_payload["automation"]["enabled"])

                usernames_output = self._run_main(
                    ["config", "set", "x.usernames", '["OpenAI","AnthropicAI"]', "--json"],
                )
                usernames_payload = json.loads(usernames_output)
                self.assertEqual(usernames_payload["x"]["usernames"], ["OpenAI", "AnthropicAI"])

                raw_output = self._run_main(["config", "show", "--source", "raw"])
                raw_payload = json.loads(raw_output)
                self.assertTrue(raw_payload["automation"]["enabled"])
                self.assertEqual(raw_payload["x"]["usernames"], ["OpenAI", "AnthropicAI"])

                effective_output = self._run_main(["config", "show", "--source", "effective"])
                effective_payload = json.loads(effective_output)
                self.assertTrue(effective_payload["automation"]["enabled"])
                self.assertEqual(effective_payload["x"]["usernames"], ["OpenAI", "AnthropicAI"])

                status_output = self._run_main(["status"])
                status_payload = json.loads(status_output)
                self.assertEqual(status_payload["settings"]["automation"]["enabled"], True)
                self.assertIn("dashboard", status_payload)

                unset_output = self._run_main(["config", "unset", "x.usernames"])
                unset_payload = json.loads(unset_output)
                self.assertNotIn("x", unset_payload)

                reset_output = self._run_main(["config", "reset"])
                self.assertEqual(json.loads(reset_output), {})

    def test_running_cli_without_args_launches_wizard_and_saves_runtime_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "APP_DATA_DIR": tmpdir,
                "AUTOMATION_ENABLED": "false",
                "AUTOMATION_DAILY_TIME": "09:00",
                "AUTOMATION_DEFAULT_MODE": "summary",
                "SOURCE_MSE_NOTICES_ENABLED": "false",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                "SOURCE_X_POSTS_ENABLED": "false",
                "TELEGRAM_ENABLED": "false",
                "BARK_ENABLED": "false",
                "PKU_REAGENT_ENABLED": "false",
                "X_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=True):
                with patch(
                    "builtins.input",
                    side_effect=[
                        "y",
                        "08:30",
                        "2",
                        "y",
                        "n",
                        "y",
                        "y",
                        "chat-123",
                        "n",
                        "n",
                        "y",
                        "https://x.com",
                        "OpenAI,AnthropicAI",
                        "8",
                        "y",
                        "n",
                        "n",
                        "",
                    ],
                ), patch(
                    "scripts.run_cli.getpass",
                    side_effect=[
                        "telegram-token",
                        "x-cookie=value",
                        "web-api-key",
                    ],
                ), patch(
                    "scripts.run_cli.run_delivery_job",
                ) as run_delivery_job_mock:
                    run_delivery_job_mock.return_value.as_dict.return_value = {"status": "ok"}
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        exit_code = main([])
                    self.assertEqual(exit_code, 0)
                    run_delivery_job_mock.assert_called_once()

                runtime_config_path = os.path.join(tmpdir, "settings", "runtime_settings.json")
                with open(runtime_config_path, encoding="utf-8") as handle:
                    raw_payload = json.load(handle)
                self.assertEqual(
                    raw_payload["automation"],
                    {
                        "enabled": True,
                        "daily_time": "08:30",
                        "default_mode": "report",
                    },
                )
                self.assertEqual(
                    raw_payload["sources"],
                    {
                        "mse_notices": True,
                        "pku_reagent_orders": False,
                        "x_posts": True,
                    },
                )
                self.assertTrue(raw_payload["telegram"]["enabled"])
                self.assertEqual(raw_payload["telegram"]["chat_id"], "chat-123")
                self.assertEqual(raw_payload["telegram"]["bot_token"], "telegram-token")
                self.assertTrue(raw_payload["x"]["enabled"])
                self.assertEqual(raw_payload["x"]["base_url"], "https://x.com")
                self.assertEqual(raw_payload["x"]["usernames"], ["OpenAI", "AnthropicAI"])
                self.assertEqual(raw_payload["x"]["max_results_per_user"], 8)
                self.assertFalse(raw_payload["x"]["exclude_retweets"])
                self.assertEqual(raw_payload["x"]["cookie_header"], "x-cookie=value")
                self.assertFalse(raw_payload["pku_reagent"]["enabled"])
                self.assertEqual(raw_payload["web_api_key"], "web-api-key")

    def test_wizard_can_save_without_running_delivery_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "APP_DATA_DIR": tmpdir,
                "AUTOMATION_ENABLED": "false",
                "AUTOMATION_DAILY_TIME": "09:00",
                "AUTOMATION_DEFAULT_MODE": "summary",
                "SOURCE_MSE_NOTICES_ENABLED": "false",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                "SOURCE_X_POSTS_ENABLED": "false",
                "TELEGRAM_ENABLED": "false",
                "BARK_ENABLED": "false",
                "PKU_REAGENT_ENABLED": "false",
                "X_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=True):
                with patch(
                    "builtins.input",
                    side_effect=[""] * 10 + ["n"],
                ), patch(
                    "scripts.run_cli.getpass",
                    side_effect=["", "", ""],
                ), patch(
                    "scripts.run_cli.run_delivery_job",
                ) as run_delivery_job_mock:
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        exit_code = main([])
                    self.assertEqual(exit_code, 0)
                    run_delivery_job_mock.assert_not_called()

    def test_wizard_uses_env_defaults_when_user_presses_enter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "APP_DATA_DIR": tmpdir,
                "AUTOMATION_ENABLED": "true",
                "AUTOMATION_DAILY_TIME": "07:15",
                "AUTOMATION_DEFAULT_MODE": "report",
                "SOURCE_MSE_NOTICES_ENABLED": "true",
                "SOURCE_PKU_REAGENT_ORDERS_ENABLED": "false",
                "SOURCE_X_POSTS_ENABLED": "true",
                "TELEGRAM_ENABLED": "true",
                "TELEGRAM_CHAT_ID": "env-chat-id",
                "TELEGRAM_BOT_TOKEN": "env-telegram-token",
                "TELEGRAM_DISABLE_WEB_PAGE_PREVIEW": "false",
                "BARK_ENABLED": "false",
                "PKU_REAGENT_ENABLED": "false",
                "X_ENABLED": "true",
                "X_BASE_URL": "https://x.example.com",
                "X_USERNAMES": "OpenAI,sama",
                "X_MAX_RESULTS_PER_USER": "9",
                "X_EXCLUDE_REPLIES": "false",
                "X_EXCLUDE_RETWEETS": "true",
                "X_COOKIE_HEADER": "env-x-cookie",
                "WEB_API_KEY": "env-web-api-key",
            }
            with patch.dict(os.environ, env, clear=True):
                self._run_main(["config", "set", "automation.daily_time", "22:45"])
                self._run_main(["config", "set", "telegram.chat_id", "runtime-chat-id"])
                self._run_main(["config", "set", "x.usernames", '["AnthropicAI"]', "--json"])

                with patch(
                    "builtins.input",
                    side_effect=[""] * 18,
                ), patch(
                    "scripts.run_cli.getpass",
                    side_effect=["", "", ""],
                ), patch(
                    "scripts.run_cli.run_delivery_job",
                ) as run_delivery_job_mock:
                    run_delivery_job_mock.return_value.as_dict.return_value = {"status": "ok"}
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        exit_code = main([])
                    self.assertEqual(exit_code, 0)
                    run_delivery_job_mock.assert_called_once()

                runtime_config_path = os.path.join(tmpdir, "settings", "runtime_settings.json")
                with open(runtime_config_path, encoding="utf-8") as handle:
                    raw_payload = json.load(handle)

                self.assertEqual(
                    raw_payload["automation"],
                    {
                        "enabled": True,
                        "daily_time": "07:15",
                        "default_mode": "report",
                    },
                )
                self.assertEqual(
                    raw_payload["sources"],
                    {
                        "mse_notices": True,
                        "pku_reagent_orders": False,
                        "x_posts": True,
                    },
                )
                self.assertEqual(raw_payload["telegram"]["chat_id"], "env-chat-id")
                self.assertEqual(raw_payload["telegram"]["bot_token"], "env-telegram-token")
                self.assertEqual(raw_payload["x"]["base_url"], "https://x.example.com")
                self.assertEqual(raw_payload["x"]["usernames"], ["OpenAI", "sama"])
                self.assertEqual(raw_payload["x"]["max_results_per_user"], 9)
                self.assertFalse(raw_payload["x"]["exclude_replies"])
                self.assertTrue(raw_payload["x"]["exclude_retweets"])
                self.assertEqual(raw_payload["x"]["cookie_header"], "env-x-cookie")
                self.assertEqual(raw_payload["web_api_key"], "env-web-api-key")

    def _run_main(self, argv: list[str]) -> str:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(argv)
        self.assertEqual(exit_code, 0)
        return buffer.getvalue().strip()


if __name__ == "__main__":
    unittest.main()
