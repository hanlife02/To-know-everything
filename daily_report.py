from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from content_filters import filter_dashboard_for_reports
from delivery_state import build_xhs_signature
from llm import LLMSettings, generate_text

REPORTS_PATH = Path(__file__).resolve().parent / "data" / "ai_daily_reports.json"

SYSTEM_PROMPT = """
你是一名中文内容运营编辑，负责把平台热门内容摘要整理成可直接发送到 Telegram 的日报。

输出要求：
1. 只使用输入里提供的信息，不要补充未知事实，不要虚构数据。
2. 输出纯文本，不要使用代码块。
3. 语气简洁、信息密度高，适合日报推送。
4. 结构固定为三段：今日观察、重点内容、推送建议。
5. 重点内容最多列 3 条，每条都要包含标题、简短看点、原始链接。
6. 总长度控制在 900 个中文字符以内。
""".strip()


@dataclass(slots=True)
class DailyReport:
    platform_name: str
    title: str
    body: str
    generated_at: str
    content_signature: str = ""


def truncate_text(value: str, limit: int = 180) -> str:
    text = (value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def build_bilibili_items(videos: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for video in videos[:limit]:
        items.append(
            {
                "rank": video.get("rank", "-"),
                "title": str(video.get("title", "")).strip(),
                "author": str(video.get("owner_name", "")).strip(),
                "summary": truncate_text(str(video.get("summary", "")).strip()),
                "url": str(video.get("url", "")).strip(),
                "category": str(video.get("category_v2") or video.get("category") or "").strip(),
                "view": int(video.get("view", 0) or 0),
                "like": int(video.get("like", 0) or 0),
            }
        )
    return items


def build_xhs_items(notes: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for note in notes[:limit]:
        items.append(
            {
                "rank": note.get("rank", "-"),
                "title": str(note.get("title", "")).strip(),
                "author": str(note.get("author_name", "")).strip(),
                "summary": truncate_text(str(note.get("summary", "")).strip()),
                "url": str(note.get("url", "")).strip(),
                "note_type": str(note.get("note_type", "")).strip(),
                "likes": int(note.get("likes", 0) or 0),
            }
        )
    return items


def build_materials_notice_items(
    notices: list[dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for notice in notices[:limit]:
        items.append(
            {
                "rank": notice.get("rank", "-"),
                "title": str(notice.get("title", "")).strip(),
                "summary": truncate_text(str(notice.get("summary", "")).strip()),
                "url": str(notice.get("url", "")).strip(),
                "source": str(notice.get("source", "")).strip(),
                "published_at": str(notice.get("published_at", "")).strip(),
            }
        )
    return items


def build_platform_prompt(
    *,
    platform_name: str,
    updated_at: str,
    overview: str,
    items: list[dict[str, Any]],
) -> str:
    return f"""
请基于下面的 {platform_name} 摘要数据，生成一份适合 Telegram 推送的中文日报正文。

平台：{platform_name}
时间：{updated_at}
总览：{overview.strip()}

候选内容：
{json.dumps(items, ensure_ascii=False, indent=2)}

请严格按下面格式输出：
【今日观察】
用 2 到 3 句话总结今天这个平台的内容风向。

【重点内容】
1. 标题：...
看点：...
链接：...

2. 标题：...
看点：...
链接：...

3. 标题：...
看点：...
链接：...

【推送建议】
- 给出 2 到 3 条可直接用于运营判断的建议。

补充要求：
- 重点内容不足 3 条时，按实际数量输出。
- 看点要基于输入摘要做凝练，不要重复原文大段描述。
- 链接必须保留原始 URL。
""".strip()


def build_report_title(platform_name: str, report_date: str | None = None) -> str:
    date_text = report_date or datetime.now().strftime("%Y-%m-%d")
    return f"{platform_name} 推送日报 | {date_text}"


def generate_platform_daily_report(
    settings: LLMSettings,
    *,
    platform_name: str,
    updated_at: str,
    overview: str,
    items: list[dict[str, Any]],
) -> DailyReport:
    if not items:
        raise ValueError(f"{platform_name} 当前没有可用于生成日报的内容。")

    body = generate_text(
        settings,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_platform_prompt(
            platform_name=platform_name,
            updated_at=updated_at,
            overview=overview,
            items=items,
        ),
    )
    return DailyReport(
        platform_name=platform_name,
        title=build_report_title(platform_name),
        body=body.strip(),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def build_ai_daily_reports(
    settings: LLMSettings,
    dashboard: dict[str, Any],
) -> list[DailyReport]:
    daily_dashboard = filter_dashboard_for_reports(dashboard)
    bilibili = daily_dashboard["bilibili"]
    materials_notices = daily_dashboard["materials_notices"]
    xhs = daily_dashboard["xhs"]

    reports: list[DailyReport] = []

    if bilibili.get("videos"):
        reports.append(generate_platform_daily_report(
            settings,
            platform_name="Bilibili",
            updated_at=str(bilibili.get("updated_at", "")).strip(),
            overview=str(bilibili.get("overview", "")).strip(),
            items=build_bilibili_items(bilibili.get("videos", [])),
        ))
    if materials_notices.get("notices"):
        reports.append(generate_platform_daily_report(
            settings,
            platform_name="材料学院通知",
            updated_at=str(materials_notices.get("updated_at", "")).strip(),
            overview=str(materials_notices.get("overview", "")).strip(),
            items=build_materials_notice_items(materials_notices.get("notices", [])),
        ))
    if xhs.get("notes"):
        report = generate_platform_daily_report(
            settings,
            platform_name="小红书",
            updated_at=str(xhs.get("updated_at", "")).strip(),
            overview=str(xhs.get("overview", "")).strip(),
            items=build_xhs_items(xhs.get("notes", [])),
        )
        report.content_signature = build_xhs_signature(xhs.get("notes", []))
        reports.append(report)

    if not reports:
        raise ValueError("当前没有满足条件的内容可用于生成日报。")

    return reports


def save_ai_daily_reports(
    reports: list[DailyReport],
    path: Path = REPORTS_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(reports),
        "reports": [asdict(report) for report in reports],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_cached_ai_daily_reports(
    path: Path = REPORTS_PATH,
) -> dict[str, Any]:
    if not path.exists():
        return {"generated_at": "", "count": 0, "reports": []}

    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = payload.get("reports", [])
    if not isinstance(reports, list):
        reports = []

    return {
        "generated_at": str(payload.get("generated_at", "")).strip(),
        "count": len(reports),
        "reports": reports,
    }


def serialize_ai_daily_reports(cache: dict[str, Any]) -> dict[str, Any]:
    reports = cache.get("reports", [])
    return {
        "generated_at": str(cache.get("generated_at", "")).strip(),
        "count": len(reports) if isinstance(reports, list) else 0,
        "reports": reports if isinstance(reports, list) else [],
        "available": bool(reports),
    }


def build_ai_daily_report_messages(reports: list[dict[str, Any]]) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []
    for report in reports:
        title = str(report.get("title", "")).strip()
        body = str(report.get("body", "")).strip()
        if title and body:
            messages.append((title, body))
    return messages
