from __future__ import annotations

import argparse
from getpass import getpass
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _env import ensure_project_root_on_path, load_dotenv

ensure_project_root_on_path()
load_dotenv()

from app.automation.jobs import run_delivery_job
from app.automation.scheduler import DailyScheduler
from app.bootstrap import AppController
from app.domain.enums import DeliveryMode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local CLI for To Know Everything")
    subparsers = parser.add_subparsers(dest="command")

    status_parser = subparsers.add_parser("status", help="Show current runtime status")
    status_parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    run_parser = subparsers.add_parser("run", help="Run a single delivery job")
    run_parser.add_argument("mode", nargs="?", default=DeliveryMode.SUMMARY.value, choices=[mode.value for mode in DeliveryMode])
    run_parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    scheduler_parser = subparsers.add_parser("scheduler", help="Run the daily scheduler loop")
    scheduler_parser.add_argument("--poll-interval", type=int, default=30, help="Polling interval in seconds")

    config_parser = subparsers.add_parser("config", help="Read or modify local runtime config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    config_show = config_subparsers.add_parser("show", help="Show config")
    config_show.add_argument(
        "--source",
        choices=("effective", "raw"),
        default="effective",
        help="Show effective config or raw runtime overrides",
    )
    config_show.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    config_path = config_subparsers.add_parser("path", help="Show the runtime config file path")
    config_path.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    config_set = config_subparsers.add_parser("set", help="Set a nested config key")
    config_set.add_argument("key", help="Dotted path, for example automation.enabled")
    config_set.add_argument("value", help="Value to write")
    config_set.add_argument("--json", action="store_true", help="Parse the value as JSON")
    config_set.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    config_unset = config_subparsers.add_parser("unset", help="Remove a nested config key")
    config_unset.add_argument("key", help="Dotted path to remove")
    config_unset.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    config_reset = config_subparsers.add_parser("reset", help="Clear all runtime overrides")
    config_reset.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    config_wizard = config_subparsers.add_parser("wizard", help="Launch the interactive config wizard")
    config_wizard.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    return parser


def main(argv: list[str] | None = None) -> int:
    cli_args = list(sys.argv[1:] if argv is None else argv)
    controller = AppController()
    if not cli_args:
        return run_config_wizard(controller, pretty=True)

    parser = build_parser()
    args = parser.parse_args(cli_args)

    if args.command == "status":
        payload = build_status_payload(controller)
        print_json(payload, pretty=args.pretty)
        return 0

    if args.command == "run":
        context = controller.get_context()
        result = run_delivery_job(context, DeliveryMode.from_value(args.mode))
        print_json(result.as_dict(), pretty=args.pretty)
        return 0

    if args.command == "scheduler":
        context = controller.get_context()
        scheduler = DailyScheduler(controller.get_context)
        print(
            "scheduler started: "
            f"enabled={context.settings.automation.enabled}, "
            f"time={context.settings.automation.daily_time}, "
            f"mode={context.settings.automation.default_mode.value}, "
            f"settings={controller.settings_store_path}"
        )
        scheduler.run_forever(poll_interval_seconds=max(1, args.poll_interval))
        return 0

    if args.command == "config":
        return handle_config_command(controller, args)

    parser.error(f"unsupported command: {args.command}")
    return 2


def handle_config_command(controller: AppController, args: argparse.Namespace) -> int:
    if args.config_command == "show":
        payload = (
            controller.current_settings_payload()
            if args.source == "effective"
            else controller.current_runtime_overrides()
        )
        print_json(redact_sensitive_values(payload), pretty=args.pretty)
        return 0

    if args.config_command == "path":
        print_json({"path": controller.settings_store_path}, pretty=args.pretty)
        return 0

    if args.config_command == "set":
        overrides = controller.current_runtime_overrides()
        set_nested_value(overrides, args.key, parse_cli_value(args.value, parse_json=args.json))
        controller.update_settings(overrides)
        print_json(redact_sensitive_values(overrides), pretty=args.pretty)
        return 0

    if args.config_command == "unset":
        overrides = controller.current_runtime_overrides()
        removed = unset_nested_value(overrides, args.key)
        if not removed:
            raise SystemExit(f"config key not found: {args.key}")
        controller.update_settings(overrides)
        print_json(redact_sensitive_values(overrides), pretty=args.pretty)
        return 0

    if args.config_command == "reset":
        controller.clear_runtime_overrides()
        print_json({}, pretty=args.pretty)
        return 0

    if args.config_command == "wizard":
        return run_config_wizard(controller, pretty=args.pretty)

    raise SystemExit(f"unsupported config command: {args.config_command}")


def run_config_wizard(controller: AppController, *, pretty: bool) -> int:
    defaults = controller.base_settings_payload()

    print("Interactive config wizard")
    print(f"Settings file: {controller.settings_store_path}")
    print("Press Enter to use the value from .env shown in brackets.")

    payload = build_interactive_config_payload(defaults)
    controller.update_settings(payload)

    print("Saved runtime overrides:")
    print_json(redact_sensitive_values(payload), pretty=pretty)
    if not _prompt_bool("Run a delivery job now", default=True):
        return 0

    mode = DeliveryMode.from_value(payload["automation"]["default_mode"])
    print(f"Running delivery job in {mode.value} mode...")
    result = run_delivery_job(controller.get_context(), mode)
    print_json(result.as_dict(), pretty=pretty)
    return 0


def build_status_payload(controller: AppController) -> dict[str, object]:
    context = controller.get_context()
    return {
        "settings_store_path": controller.settings_store_path,
        "dashboard": context.dashboard_service.snapshot(),
        "settings": redact_sensitive_values(context.settings.to_runtime_payload()),
    }


def print_json(payload: Any, *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(json.dumps(payload, ensure_ascii=False))


def build_interactive_config_payload(current: dict[str, object]) -> dict[str, object]:
    automation_current = _mapping_value(current, "automation")
    telegram_current = _mapping_value(current, "telegram")
    bark_current = _mapping_value(current, "bark")
    x_current = _mapping_value(current, "x")
    pku_reagent_current = _mapping_value(current, "pku_reagent")
    sources_current = _mapping_value(current, "sources")

    return {
        "automation": _prompt_automation_settings(automation_current),
        "sources": _prompt_sources_settings(sources_current),
        "telegram": _prompt_telegram_settings(telegram_current),
        "bark": _prompt_bark_settings(bark_current),
        "x": _prompt_x_settings(x_current),
        "pku_reagent": _prompt_pku_reagent_settings(pku_reagent_current),
        "web_api_key": _prompt_secret("Web API key", _string_value(current.get("web_api_key"))),
    }


def parse_cli_value(raw_value: str, *, parse_json: bool) -> Any:
    if parse_json:
        return json.loads(raw_value)

    lowered = raw_value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if lowered and lowered.lstrip("-").isdigit():
        return int(lowered)
    return raw_value


def redact_sensitive_values(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _mask_if_sensitive(key, redact_sensitive_values(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_sensitive_values(item) for item in payload]
    return payload


def set_nested_value(payload: dict[str, object], dotted_key: str, value: Any) -> None:
    parts = _split_dotted_key(dotted_key)
    current: dict[str, object] = payload
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def unset_nested_value(payload: dict[str, object], dotted_key: str) -> bool:
    parts = _split_dotted_key(dotted_key)
    current: dict[str, object] = payload
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            return False
        current = next_value
    removed = current.pop(parts[-1], None) is not None
    _prune_empty_containers(payload, parts[:-1])
    return removed


def _prune_empty_containers(payload: dict[str, object], parents: list[str]) -> None:
    if not parents:
        return
    current = payload
    nodes: list[tuple[dict[str, object], str]] = []
    for part in parents:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            return
        nodes.append((current, part))
        current = next_value
    for parent, key in reversed(nodes):
        value = parent.get(key)
        if isinstance(value, dict) and not value:
            parent.pop(key, None)


def _split_dotted_key(dotted_key: str) -> list[str]:
    parts = [part.strip() for part in dotted_key.split(".") if part.strip()]
    if not parts:
        raise SystemExit("config key must not be empty")
    return parts


def _mask_if_sensitive(key: str, value: Any) -> Any:
    sensitive_keys = {
        "web_api_key",
        "bot_token",
        "key",
        "password",
        "token",
        "cookie_header",
        "captcha_code",
        "sms_code",
        "otp_code",
    }
    if key not in sensitive_keys or not isinstance(value, str):
        return value
    return mask_secret(value)


def mask_secret(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if len(stripped) <= 8:
        return "*" * len(stripped)
    return f"{stripped[:2]}***{stripped[-2:]}"


def _mapping_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_value(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return default


def _int_value(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _string_list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _print_section(title: str) -> None:
    print(f"\n[{title}]")


def _prompt_automation_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("Automation")
    enabled = _prompt_bool("Enable daily automation", _bool_value(current.get("enabled")))
    daily_time = _prompt_text("Daily run time (HH:MM)", _string_value(current.get("daily_time", "09:00")))
    default_mode = _prompt_choice(
        "Default delivery mode",
        choices=[mode.value for mode in DeliveryMode],
        default=_string_value(current.get("default_mode", DeliveryMode.SUMMARY.value)),
    )
    return {
        "enabled": enabled,
        "daily_time": daily_time,
        "default_mode": default_mode,
    }


def _prompt_sources_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("Sources")
    return {
        "mse_notices": _prompt_bool("Enable MSE notices", _bool_value(current.get("mse_notices"))),
        "pku_reagent_orders": _prompt_bool(
            "Enable PKU reagent orders",
            _bool_value(current.get("pku_reagent_orders")),
        ),
        "x_posts": _prompt_bool("Enable X posts", _bool_value(current.get("x_posts"))),
    }


def _prompt_telegram_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("Telegram")
    enabled = _prompt_bool("Enable Telegram notifications", _bool_value(current.get("enabled")))
    if not enabled:
        return {
            "enabled": False,
            "bot_token": _string_value(current.get("bot_token")),
            "chat_id": _string_value(current.get("chat_id")),
            "disable_web_page_preview": _bool_value(
                current.get("disable_web_page_preview"),
                default=True,
            ),
        }
    return {
        "enabled": enabled,
        "bot_token": _prompt_secret("Telegram bot token", _string_value(current.get("bot_token"))),
        "chat_id": _prompt_text("Telegram chat id", _string_value(current.get("chat_id"))),
        "disable_web_page_preview": _prompt_bool(
            "Disable Telegram link previews",
            _bool_value(current.get("disable_web_page_preview"), default=True),
        ),
    }


def _prompt_bark_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("Bark")
    enabled = _prompt_bool("Enable Bark notifications", _bool_value(current.get("enabled")))
    if not enabled:
        return {
            "enabled": False,
            "server_url": _string_value(current.get("server_url", "https://api.day.app")),
            "key": _string_value(current.get("key")),
            "group": _string_value(current.get("group")),
        }
    return {
        "enabled": enabled,
        "server_url": _prompt_text("Bark server URL", _string_value(current.get("server_url", "https://api.day.app"))),
        "key": _prompt_secret("Bark key", _string_value(current.get("key"))),
        "group": _prompt_text("Bark group", _string_value(current.get("group"))),
    }


def _prompt_x_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("X")
    enabled = _prompt_bool("Enable X source", _bool_value(current.get("enabled")))
    if not enabled:
        return {
            "enabled": False,
            "cookie_header": _string_value(current.get("cookie_header")),
            "base_url": _string_value(current.get("base_url", "https://x.com")),
            "usernames": _string_list_value(current.get("usernames")),
            "max_results_per_user": _int_value(current.get("max_results_per_user"), 5),
            "exclude_replies": _bool_value(current.get("exclude_replies"), default=True),
            "exclude_retweets": _bool_value(current.get("exclude_retweets"), default=True),
        }
    base_url = _prompt_text("X base URL", _string_value(current.get("base_url", "https://x.com")))
    usernames = _prompt_csv("X usernames (comma separated)", _string_list_value(current.get("usernames")))
    return {
        "enabled": enabled,
        "base_url": base_url,
        "usernames": usernames,
        "max_results_per_user": _prompt_int(
            "Max posts per user",
            _int_value(current.get("max_results_per_user"), 5),
            minimum=5,
            maximum=100,
        ),
        "exclude_replies": _prompt_bool(
            "Exclude replies",
            _bool_value(current.get("exclude_replies"), default=True),
        ),
        "exclude_retweets": _prompt_bool(
            "Exclude retweets",
            _bool_value(current.get("exclude_retweets"), default=True),
        ),
        "cookie_header": _prompt_secret("X cookie header", _string_value(current.get("cookie_header"))),
    }


def _prompt_pku_reagent_settings(current: dict[str, object]) -> dict[str, object]:
    _print_section("PKU Reagent")
    enabled = _prompt_bool("Enable PKU reagent source", _bool_value(current.get("enabled")))
    if not enabled:
        return {
            "enabled": False,
            "base_url": _string_value(current.get("base_url", "https://reagent.pku.edu.cn")),
            "iaaa_base_url": _string_value(current.get("iaaa_base_url", "https://iaaa.pku.edu.cn/iaaa")),
            "username": _string_value(current.get("username")),
            "password": _string_value(current.get("password")),
            "token": _string_value(current.get("token")),
            "cookie_header": _string_value(current.get("cookie_header")),
            "captcha_code": _string_value(current.get("captcha_code")),
            "sms_code": _string_value(current.get("sms_code")),
            "otp_code": _string_value(current.get("otp_code")),
            "start_date": _string_value(current.get("start_date")),
            "end_date": _string_value(current.get("end_date")),
            "keyword": _string_value(current.get("keyword")),
            "group_code": _string_value(current.get("group_code")),
            "page_size": _int_value(current.get("page_size"), 20),
        }
    return {
        "enabled": enabled,
        "base_url": _prompt_text(
            "PKU reagent base URL",
            _string_value(current.get("base_url", "https://reagent.pku.edu.cn")),
        ),
        "iaaa_base_url": _prompt_text(
            "IAAA base URL",
            _string_value(current.get("iaaa_base_url", "https://iaaa.pku.edu.cn/iaaa")),
        ),
        "username": _prompt_text("PKU username", _string_value(current.get("username"))),
        "password": _prompt_secret("PKU password", _string_value(current.get("password"))),
        "token": _prompt_secret("PKU token", _string_value(current.get("token"))),
        "cookie_header": _prompt_secret("PKU cookie header", _string_value(current.get("cookie_header"))),
        "captcha_code": _prompt_secret("PKU captcha code", _string_value(current.get("captcha_code"))),
        "sms_code": _prompt_secret("PKU SMS code", _string_value(current.get("sms_code"))),
        "otp_code": _prompt_secret("PKU OTP code", _string_value(current.get("otp_code"))),
        "start_date": _prompt_text("Start date (YYYY-MM-DD)", _string_value(current.get("start_date"))),
        "end_date": _prompt_text("End date (YYYY-MM-DD)", _string_value(current.get("end_date"))),
        "keyword": _prompt_text("Keyword filter", _string_value(current.get("keyword"))),
        "group_code": _prompt_text("Group code", _string_value(current.get("group_code"))),
        "page_size": _prompt_int(
            "Page size",
            _int_value(current.get("page_size"), 20),
            minimum=1,
        ),
    }


def _prompt_text(label: str, default: str) -> str:
    prompt = f"{label} [{default}]: " if default else f"{label}: "
    value = input(prompt).strip()
    if value:
        return value
    return default


def _prompt_secret(label: str, default: str) -> str:
    default_hint = mask_secret(default) if default else ""
    prompt = f"{label} [{default_hint}]: " if default_hint else f"{label}: "
    value = getpass(prompt).strip()
    if value:
        return value
    return default


def _prompt_bool(label: str, default: bool) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} ({default_hint}): ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer with y or n.")


def _prompt_choice(label: str, *, choices: list[str], default: str) -> str:
    display_choices = ", ".join(f"{index + 1}:{choice}" for index, choice in enumerate(choices))
    while True:
        value = input(f"{label} [{display_choices}] (default: {default}): ").strip()
        if not value:
            return default
        if value.isdigit():
            index = int(value) - 1
            if 0 <= index < len(choices):
                return choices[index]
        if value in choices:
            return value
        print(f"Please choose one of: {', '.join(choices)}")


def _prompt_csv(label: str, default: list[str]) -> list[str]:
    default_text = ",".join(default)
    value = _prompt_text(label, default_text)
    return [part.strip() for part in value.split(",") if part.strip()]


def _prompt_int(label: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        value = input(f"{label} [{default}]: ").strip()
        if not value:
            return default
        if not value.lstrip("-").isdigit():
            print("Please enter a valid integer.")
            continue
        parsed = int(value)
        if minimum is not None and parsed < minimum:
            print(f"Please enter a value >= {minimum}.")
            continue
        if maximum is not None and parsed > maximum:
            print(f"Please enter a value <= {maximum}.")
            continue
        return parsed


if __name__ == "__main__":
    raise SystemExit(main())
