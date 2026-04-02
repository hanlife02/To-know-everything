from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from flask import Flask, jsonify, render_template

try:
    from .crawler import build_summary, dump_recommended_notes, fetch_recommended_notes, load_cached_notes
except ImportError:
    from crawler import build_summary, dump_recommended_notes, fetch_recommended_notes, load_cached_notes

app = Flask(__name__)


def format_count(value: int) -> str:
    if value >= 100000000:
        return f"{value / 100000000:.1f}亿"
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(value)


def enrich_notes(notes: list[dict]) -> list[dict]:
    enriched = []
    for note in notes:
        item = dict(note)
        item["summary"] = build_summary(item)
        enriched.append(item)
    return enriched


def build_overview(notes: list[dict]) -> str:
    if not notes:
        return "当前没有可展示的小红书推荐笔记摘要。"

    video_count = sum(1 for note in notes if note.get("note_type") == "video")
    image_count = sum(1 for note in notes if note.get("note_type") == "image")
    total_likes = sum(int(note.get("likes", 0)) for note in notes)

    return (
        f"当前页面共收录 {len(notes)} 条小红书推荐笔记，"
        f"其中图文 {image_count} 条、视频 {video_count} 条，"
        f"已解析点赞总量约 {format_count(total_likes)}。"
        f"页面只保留标题、作者、点赞和可用链接这些关键字段。"
    )


def load_page_data() -> dict:
    error = ""
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        notes = fetch_recommended_notes()
        dump_recommended_notes(notes)
        data = [asdict(note) for note in notes]
    except Exception as exc:  # noqa: BLE001
        error = f"实时抓取失败，已尝试回退缓存：{exc}"
        data = load_cached_notes()

    data = enrich_notes(data)

    return {
        "notes": data,
        "overview": build_overview(data),
        "updated_at": updated_at,
        "error": error,
    }


@app.route("/")
def index():
    return render_template("index.html", **load_page_data())


@app.route("/api/notes")
def notes_api():
    return jsonify(load_page_data())


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8001)
