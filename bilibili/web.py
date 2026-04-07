from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json

from flask import Flask, jsonify, render_template

try:
    from .crawler import (
        DEFAULT_OUTPUT,
        DEFAULT_PAGE,
        DEFAULT_PAGE_SIZE,
        dump_hot_videos,
        fetch_hot_videos,
        load_cached_hot_videos,
    )
except ImportError:
    from crawler import (
        DEFAULT_OUTPUT,
        DEFAULT_PAGE,
        DEFAULT_PAGE_SIZE,
        dump_hot_videos,
        fetch_hot_videos,
        load_cached_hot_videos,
    )

app = Flask(__name__)


def format_count(value: int) -> str:
    if value >= 100000000:
        return f"{value / 100000000:.1f}亿"
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(value)


def build_video_summary(video: dict) -> str:
    category = video.get("category_v2") or video.get("category") or "未分类"
    published_at = video.get("published_at") or "发布时间未知"
    location = video.get("location")
    reason = video.get("reason")
    description = (video.get("description") or "").replace("\n", " ").strip()

    parts = [
        f"《{video.get('title', '')}》来自 UP 主 {video.get('owner_name', '未知')}",
        f"分区是 {category}",
        f"发布时间为 {published_at}",
        f"时长 {video.get('duration', '00:00')}",
        (
            f"目前播放 {format_count(int(video.get('view', 0)))}"
            f"、点赞 {format_count(int(video.get('like', 0)))}"
            f"、评论 {format_count(int(video.get('reply', 0)))}"
            f"、收藏 {format_count(int(video.get('favorite', 0)))}"
        ),
    ]

    if location:
        parts.append(f"发布地为 {location}")
    if reason:
        parts.append(f"推荐标签是“{reason}”")
    if description:
        parts.append(f"简介要点：{description[:80]}{'...' if len(description) > 80 else ''}")

    return "，".join(parts) + "。"


def enrich_videos(videos: list[dict]) -> list[dict]:
    enriched = []
    for video in videos:
        item = dict(video)
        item["summary"] = build_video_summary(item)
        enriched.append(item)
    return enriched


def build_overview(videos: list[dict]) -> str:
    if not videos:
        return "当前没有可展示的热门视频摘要。"

    categories = [
        video.get("category_v2") or video.get("category")
        for video in videos
        if video.get("category_v2") or video.get("category")
    ]
    top_categories = [name for name, _ in Counter(categories).most_common(3)]
    category_text = "、".join(top_categories) if top_categories else "多种内容类型"
    total_views = sum(int(video.get("view", 0)) for video in videos)
    total_likes = sum(int(video.get("like", 0)) for video in videos)

    return (
        f"当前页面共收录 {len(videos)} 条 Bilibili 热门内容，"
        f"主题主要集中在 {category_text}。"
        f"这些视频合计约 {format_count(total_views)} 播放、"
        f"{format_count(total_likes)} 点赞，适合直接按摘要快速浏览。"
    )


def load_cached_payload() -> dict:
    if not DEFAULT_OUTPUT.exists():
        return {"updated_at": "", "videos": []}
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    return {
        "updated_at": payload.get("updated_at", ""),
        "videos": payload.get("videos", []),
    }


def load_page_data() -> dict:
    payload = load_cached_payload()
    data = enrich_videos(payload.get("videos", []))

    return {
        "videos": data,
        "overview": build_overview(data),
        "updated_at": payload.get("updated_at") or "暂无缓存",
        "error": "" if data else "当前没有缓存内容，请先点击“更新 Bilibili”。",
    }


def refresh_page_data() -> dict:
    error = ""

    try:
        videos = fetch_hot_videos(page_size=DEFAULT_PAGE_SIZE, page=DEFAULT_PAGE)
        dump_hot_videos(videos, page_size=DEFAULT_PAGE_SIZE, page=DEFAULT_PAGE)
        data = [asdict(video) for video in videos]
        updated_at = load_cached_payload().get("updated_at") or ""
    except Exception as exc:  # noqa: BLE001
        error = f"更新失败，已回退缓存：{exc}"
        data = load_cached_hot_videos()
        updated_at = load_cached_payload().get("updated_at") or "暂无缓存"

    data = enrich_videos(data)

    return {
        "videos": data,
        "overview": build_overview(data),
        "updated_at": updated_at,
        "error": error,
    }


@app.route("/")
def index():
    page_data = load_page_data()
    return render_template("index.html", **page_data)


@app.route("/api/hot")
def hot_api():
    return jsonify(load_page_data())
