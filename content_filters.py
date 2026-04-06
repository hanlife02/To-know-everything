from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any

from delivery_state import build_xhs_signature, get_delivery_signature


def get_today(local_today: date | None = None) -> date:
    return local_today or datetime.now().date()


def parse_item_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def filter_items_for_recent_days(
    items: list[dict[str, Any]],
    *,
    date_key: str,
    include_days: int,
    local_today: date | None = None,
) -> list[dict[str, Any]]:
    today = get_today(local_today)
    results: list[dict[str, Any]] = []
    for item in items:
        item_date = parse_item_date(item.get(date_key))
        if item_date is None:
            continue
        delta = (today - item_date).days
        if 0 <= delta < include_days:
            results.append(item)
    return results


def clone_platform_data(page_data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(page_data)


def filter_platform_for_recent_days(
    page_data: dict[str, Any],
    *,
    items_key: str,
    date_key: str,
    include_days: int,
    empty_message: str,
    local_today: date | None = None,
) -> dict[str, Any]:
    data = clone_platform_data(page_data)
    items = page_data.get(items_key, [])
    filtered_items = filter_items_for_recent_days(
        items,
        date_key=date_key,
        include_days=include_days,
        local_today=local_today,
    )
    data[items_key] = filtered_items
    if filtered_items:
        data["error"] = ""
    else:
        data["error"] = empty_message
    return data


def filter_xhs_for_change(
    page_data: dict[str, Any],
    *,
    mode: str,
    unchanged_message: str,
) -> dict[str, Any]:
    data = clone_platform_data(page_data)
    notes = data.get("notes", [])
    signature = build_xhs_signature(notes)
    data["content_signature"] = signature

    if not notes:
        data["error"] = "当前没有可推送的小红书内容。"
        return data

    previous_signature = get_delivery_signature(mode, "xhs")
    if previous_signature and previous_signature == signature:
        data["notes"] = []
        data["error"] = unchanged_message
    else:
        data["error"] = ""
    return data


def filter_dashboard_for_summary(
    dashboard: dict[str, Any],
    local_today: date | None = None,
) -> dict[str, Any]:
    return {
        "bilibili": clone_platform_data(dashboard["bilibili"]),
        "materials_notices": filter_platform_for_recent_days(
            dashboard["materials_notices"],
            items_key="notices",
            date_key="published_at",
            include_days=2,
            empty_message="最近两天没有可推送的材料学院通知。",
            local_today=local_today,
        ),
        "xhs": filter_xhs_for_change(
            dashboard["xhs"],
            mode="summary",
            unchanged_message="小红书内容和上次摘要推送相同，已跳过。",
        ),
    }


def filter_dashboard_for_reports(
    dashboard: dict[str, Any],
    local_today: date | None = None,
) -> dict[str, Any]:
    return {
        "bilibili": clone_platform_data(dashboard["bilibili"]),
        "materials_notices": filter_platform_for_recent_days(
            dashboard["materials_notices"],
            items_key="notices",
            date_key="published_at",
            include_days=2,
            empty_message="最近两天没有可用于生成日报的材料学院通知。",
            local_today=local_today,
        ),
        "xhs": filter_xhs_for_change(
            dashboard["xhs"],
            mode="report",
            unchanged_message="小红书内容和上次 AI 日报相同，已跳过。",
        ),
    }
