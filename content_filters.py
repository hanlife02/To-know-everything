from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any


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


def filter_items_for_today(
    items: list[dict[str, Any]],
    *,
    date_key: str,
    local_today: date | None = None,
) -> list[dict[str, Any]]:
    today = get_today(local_today)
    return [item for item in items if parse_item_date(item.get(date_key)) == today]


def clone_platform_data(page_data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(page_data)


def filter_platform_for_today(
    page_data: dict[str, Any],
    *,
    items_key: str,
    date_key: str,
    empty_message: str,
    local_today: date | None = None,
) -> dict[str, Any]:
    data = clone_platform_data(page_data)
    items = page_data.get(items_key, [])
    filtered_items = filter_items_for_today(items, date_key=date_key, local_today=local_today)
    data[items_key] = filtered_items
    if filtered_items:
        data["error"] = ""
    else:
        data["error"] = empty_message
    return data


def filter_dashboard_for_today(
    dashboard: dict[str, Any],
    local_today: date | None = None,
) -> dict[str, Any]:
    filtered = {
        "bilibili": filter_platform_for_today(
            dashboard["bilibili"],
            items_key="videos",
            date_key="published_at",
            empty_message="今天没有可推送的哔哩哔哩内容。",
            local_today=local_today,
        ),
        "materials_notices": filter_platform_for_today(
            dashboard["materials_notices"],
            items_key="notices",
            date_key="published_at",
            empty_message="今天没有可推送的材料学院通知。",
            local_today=local_today,
        ),
        "xhs": filter_platform_for_today(
            dashboard["xhs"],
            items_key="notes",
            date_key="published_at",
            empty_message="小红书当前没有可按发布日期筛选的今日内容。",
            local_today=local_today,
        ),
    }
    return filtered
