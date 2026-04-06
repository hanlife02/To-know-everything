from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any

from bilibili.web import load_page_data as load_bilibili_page_data
from bilibili.web import refresh_page_data as refresh_bilibili_page_data
from content_filters import filter_dashboard_for_summary, get_today, parse_item_date
from daily_report import (
    build_ai_daily_report_messages,
    build_ai_daily_reports,
    load_cached_ai_daily_reports,
    save_ai_daily_reports,
)
from delivery_state import set_delivery_signature
from llm import load_llm_settings
from notifications import (
    build_combined_digest,
    build_platform_digest,
    load_notification_settings,
    send_bark_notification,
    send_notification,
    send_telegram_messages,
)
from materials_notice.web import load_page_data as load_materials_notices_page_data
from materials_notice.web import refresh_page_data as refresh_materials_notices_page_data
from xhs.web import load_page_data as load_xhs_page_data
from xhs.web import refresh_page_data as refresh_xhs_page_data


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_dashboard_data() -> dict[str, Any]:
    return {
        "bilibili": load_bilibili_page_data(),
        "materials_notices": load_materials_notices_page_data(),
        "xhs": load_xhs_page_data(),
    }


def validate_page_data(platform_name: str, page_data: dict[str, Any], items_key: str) -> None:
    error = str(page_data.get("error", "")).strip()
    items = page_data.get(items_key, [])

    if error:
        log(f"{platform_name}: {error}")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"{platform_name} 没有可用内容，无法继续执行。")


def refresh_dashboard_data() -> dict[str, Any]:
    bilibili = refresh_bilibili_page_data()
    materials_notices = refresh_materials_notices_page_data()
    xhs = refresh_xhs_page_data()

    validate_page_data("Bilibili", bilibili, "videos")
    validate_page_data("材料学院通知", materials_notices, "notices")
    validate_page_data("小红书", xhs, "notes")

    log(f"Bilibili 已准备好，当前 {len(bilibili['videos'])} 条内容。")
    log(f"材料学院通知已准备好，当前 {len(materials_notices['notices'])} 条内容。")
    log(f"小红书已准备好，当前 {len(xhs['notes'])} 条内容。")

    return {
        "bilibili": bilibili,
        "materials_notices": materials_notices,
        "xhs": xhs,
    }


def load_cached_dashboard_data() -> dict[str, Any]:
    dashboard = load_dashboard_data()
    validate_page_data("Bilibili", dashboard["bilibili"], "videos")
    validate_page_data("材料学院通知", dashboard["materials_notices"], "notices")
    validate_page_data("小红书", dashboard["xhs"], "notes")
    return dashboard


def build_summary_payload(
    target: str,
    dashboard: dict[str, Any],
) -> tuple[str, str, dict[str, str]]:
    filtered_dashboard = filter_dashboard_for_summary(dashboard)
    state_updates: dict[str, str] = {}

    if target == "bilibili":
        bilibili = filtered_dashboard["bilibili"]
        return (*build_platform_digest("Bilibili", bilibili["overview"], bilibili["videos"]), state_updates)
    if target == "materials_notices":
        materials_notices = filtered_dashboard["materials_notices"]
        return (*build_platform_digest(
            "材料学院通知",
            materials_notices["overview"],
            materials_notices["notices"],
        ), state_updates)
    if target == "xhs":
        xhs = filtered_dashboard["xhs"]
        if xhs.get("notes") and xhs.get("content_signature"):
            state_updates["xhs"] = str(xhs["content_signature"]).strip()
        return (*build_platform_digest("小红书", xhs["overview"], xhs["notes"]), state_updates)
    if target == "all":
        xhs = filtered_dashboard["xhs"]
        if xhs.get("notes") and xhs.get("content_signature"):
            state_updates["xhs"] = str(xhs["content_signature"]).strip()
        return (
            *build_combined_digest(
                filtered_dashboard["bilibili"],
                filtered_dashboard["materials_notices"],
                filtered_dashboard["xhs"],
            ),
            state_updates,
        )
    raise ValueError(f"Unsupported summary target: {target}")


def generate_reports(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    settings = load_llm_settings()
    if not settings.base_url or not settings.api_key or not settings.model:
        raise ValueError("LLM base URL、API key 或 model 未配置完整。")

    reports = build_ai_daily_reports(settings, dashboard)
    save_ai_daily_reports(reports)
    log(f"AI 日报已生成并缓存，共 {len(reports)} 份。")
    return [
        {
            "platform_name": report.platform_name,
            "title": report.title,
            "body": report.body,
            "generated_at": report.generated_at,
            "content_signature": report.content_signature,
        }
        for report in reports
    ]


def push_summary(channel: str, target: str, dashboard: dict[str, Any]) -> None:
    settings = load_notification_settings()
    title, body, state_updates = build_summary_payload(target, dashboard)
    results = send_notification(settings, channel, title, body)
    for platform, signature in state_updates.items():
        if signature:
            set_delivery_signature("summary", platform, signature)
    for result in results:
        log(result)


def load_cached_report_messages() -> list[tuple[str, str]]:
    cache = load_cached_ai_daily_reports()
    if parse_item_date(cache.get("generated_at")) != get_today():
        raise RuntimeError("缓存的 AI 日报不是今天生成的，请先重新生成。")
    messages = build_ai_daily_report_messages(cache.get("reports", []))
    if not messages:
        raise RuntimeError("没有可推送的 AI 日报缓存，请先执行 generate-report 或 run-all。")
    return messages


def push_reports(
    reports: list[dict[str, Any]] | None = None,
    *,
    bark_completion: bool = True,
) -> int:
    settings = load_notification_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise ValueError("Telegram bot token 或 chat id 未配置。")

    cached_reports = None
    if reports is not None:
        messages = build_ai_daily_report_messages(reports)
    else:
        cache = load_cached_ai_daily_reports()
        cached_reports = cache.get("reports", [])
        messages = load_cached_report_messages()
    results = send_telegram_messages(settings, messages)
    for result in results:
        log(result)
    source_reports = reports if reports is not None else cached_reports or []
    for report in source_reports:
        if report.get("platform_name") == "小红书" and str(report.get("content_signature", "")).strip():
            set_delivery_signature("report", "xhs", str(report["content_signature"]).strip())

    if not bark_completion:
        return len(messages)
    if not settings.bark_key:
        log("未配置 Bark key，跳过日报完成通知。")
        return len(messages)

    try:
        bark_result = send_bark_notification(
            settings,
            "AI 日报推送完成",
            (
                f"已通过 Telegram 推送 {len(messages)} 份日报，"
                f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        log(f"Bark 完成通知发送失败：{exc}")
    else:
        log(bark_result)
    return len(messages)


def run_all(
    *,
    push_summary_too: bool = False,
    summary_channel: str = "all",
    summary_target: str = "all",
    bark_completion: bool = True,
) -> dict[str, int]:
    dashboard = refresh_dashboard_data()
    reports = generate_reports(dashboard)
    if push_summary_too:
        push_summary(summary_channel, summary_target, dashboard)
    pushed_reports = push_reports(reports, bark_completion=bark_completion)
    return {
        "bilibili_count": len(dashboard["bilibili"]["videos"]),
        "materials_count": len(dashboard["materials_notices"]["notices"]),
        "xhs_count": len(dashboard["xhs"]["notes"]),
        "report_count": len(reports),
        "pushed_report_count": pushed_reports,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the daily content pipeline.")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("run-all", "refresh", "generate-report", "push-summary", "push-report"),
        default="run-all",
        help="Which pipeline action to run. Defaults to run-all.",
    )
    parser.add_argument(
        "--summary-channel",
        choices=("bark", "telegram", "all"),
        default="all",
        help="Notification channel for summary push.",
    )
    parser.add_argument(
        "--summary-target",
        choices=("bilibili", "materials_notices", "xhs", "all"),
        default="all",
        help="Which summary to push when using push-summary.",
    )
    parser.add_argument(
        "--push-summary-too",
        action="store_true",
        help="Also push the combined summary during run-all.",
    )
    parser.add_argument(
        "--no-bark-completion",
        action="store_true",
        help="Do not send the Bark completion ping after AI report delivery.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "refresh":
        refresh_dashboard_data()
        log("刷新完成。")
        return

    if args.mode == "generate-report":
        dashboard = load_cached_dashboard_data()
        generate_reports(dashboard)
        return

    if args.mode == "push-summary":
        dashboard = load_cached_dashboard_data()
        push_summary(args.summary_channel, args.summary_target, dashboard)
        return

    if args.mode == "push-report":
        push_reports(bark_completion=not args.no_bark_completion)
        return

    run_all(
        push_summary_too=args.push_summary_too,
        summary_channel=args.summary_channel,
        summary_target=args.summary_target,
        bark_completion=not args.no_bark_completion,
    )


if __name__ == "__main__":
    main()
