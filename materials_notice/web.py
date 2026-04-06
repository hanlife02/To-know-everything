from __future__ import annotations

from dataclasses import asdict
import json

from flask import Flask, jsonify, render_template

try:
    from .crawler import (
        DEFAULT_OUTPUT,
        build_notice_summary,
        dump_notices,
        fetch_notices,
        load_cached_notices,
    )
except ImportError:
    from crawler import (
        DEFAULT_OUTPUT,
        build_notice_summary,
        dump_notices,
        fetch_notices,
        load_cached_notices,
    )

app = Flask(__name__)


def enrich_notices(notices: list[dict]) -> list[dict]:
    enriched = []
    for notice in notices:
        item = dict(notice)
        item["summary"] = build_notice_summary(item)
        enriched.append(item)
    return enriched


def build_overview(notices: list[dict]) -> str:
    if not notices:
        return "当前没有可展示的材料学院通知。"
    return (
        f"当前共收录 {len(notices)} 条材料学院通知，"
        "已合并人才培养和学生园地，页面只保留标题、日期和原文链接。"
    )


def load_cached_payload() -> dict:
    if not DEFAULT_OUTPUT.exists():
        return {"updated_at": "", "notices": []}
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    return {
        "updated_at": payload.get("updated_at", ""),
        "notices": payload.get("notices", []),
    }


def load_page_data() -> dict:
    payload = load_cached_payload()
    data = enrich_notices(payload.get("notices", []))
    return {
        "notices": data,
        "overview": build_overview(data),
        "updated_at": payload.get("updated_at") or "暂无缓存",
        "error": "" if data else "当前没有缓存内容，请先点击“更新材料学院通知”。",
    }


def refresh_page_data() -> dict:
    error = ""

    try:
        notices = fetch_notices()
        dump_notices(notices)
        data = [asdict(notice) for notice in notices]
        updated_at = load_cached_payload().get("updated_at") or ""
    except Exception as exc:  # noqa: BLE001
        error = f"更新失败，已回退缓存：{exc}"
        data = load_cached_notices()
        updated_at = load_cached_payload().get("updated_at") or "暂无缓存"

    data = enrich_notices(data)
    return {
        "notices": data,
        "overview": build_overview(data),
        "updated_at": updated_at,
        "error": error,
    }


@app.route("/")
def index():
    return render_template("index.html", **load_page_data())


@app.route("/api/notices")
def notices_api():
    return jsonify(load_page_data())


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8002)
