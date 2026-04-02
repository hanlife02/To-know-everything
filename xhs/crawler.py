from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.xiaohongshu.com"
EXPLORE_URL = f"{BASE_URL}/explore?channel_id=homefeed_recommend"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "recommended.json"
SAMPLE_HTML = Path(__file__).resolve().parent / "fixtures" / "sample_explore.html"
DEFAULT_LIMIT = 20
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "max-age=0",
    "referer": BASE_URL,
    "sec-ch-ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}


@dataclass(slots=True)
class RecommendedNote:
    rank: int
    title: str
    author_name: str
    likes: int
    cover: str
    note_path: str
    url: str
    author_path: str
    author_url: str
    note_type: str


def normalize_count(text: str) -> int:
    raw = (text or "").strip().lower()
    if not raw:
        return 0
    raw = raw.replace(",", "")
    multiplier = 1
    if raw.endswith("w"):
        multiplier = 10000
        raw = raw[:-1]
    elif raw.endswith("k"):
        multiplier = 1000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return 0


def build_summary(note: dict[str, Any]) -> str:
    parts = [
        f"《{note.get('title', '')}》来自创作者 {note.get('author_name', '未知作者')}",
        f"当前点赞约 {note.get('likes', 0)}",
    ]
    note_type = note.get("note_type")
    if note_type == "video":
        parts.append("内容形态为视频笔记")
    elif note_type == "image":
        parts.append("内容形态为图文笔记")
    if note.get("url"):
        parts.append("可直接打开原笔记")
    return "，".join(parts) + "。"


def parse_note_sections(html: str, limit: int = DEFAULT_LIMIT) -> list[RecommendedNote]:
    soup = BeautifulSoup(html, "html.parser")
    notes: list[RecommendedNote] = []

    for index, section in enumerate(soup.select("section.note-item"), start=1):
        title_tag = section.select_one(".footer .title span")
        author_tag = section.select_one(".author-wrapper .author .name")
        like_tag = section.select_one(".author-wrapper .count")
        cover_link = section.select_one("a.cover.mask[href]")
        hidden_link = section.select_one('a[style*="display:none"][href]')
        author_link = section.select_one(".author-wrapper .author[href]")
        image_tag = section.select_one("a.cover.mask img")
        play_icon = section.select_one(".play-icon")

        title = title_tag.get_text(strip=True) if title_tag else ""
        author_name = author_tag.get_text(strip=True) if author_tag else ""
        likes = normalize_count(like_tag.get_text(strip=True) if like_tag else "")
        note_path = ""

        if cover_link and cover_link.get("href"):
            note_path = str(cover_link["href"]).split("?", 1)[0]
        elif hidden_link and hidden_link.get("href"):
            note_path = str(hidden_link["href"]).split("?", 1)[0]

        author_path = ""
        if author_link and author_link.get("href"):
            author_path = str(author_link["href"]).split("?", 1)[0]

        note = RecommendedNote(
            rank=index,
            title=title,
            author_name=author_name,
            likes=likes,
            cover=image_tag.get("src", "").strip() if image_tag else "",
            note_path=note_path,
            url=urljoin(BASE_URL, note_path) if note_path else "",
            author_path=author_path,
            author_url=urljoin(BASE_URL, author_path) if author_path else "",
            note_type="video" if play_icon else "image",
        )

        if note.title or note.author_name:
            notes.append(note)
        if len(notes) >= limit:
            break

    return notes


def fetch_recommended_notes_html(cookie: str | None = None, timeout: int = 20) -> str:
    headers = dict(HEADERS)
    cookie = cookie or os.getenv("XHS_COOKIE", "")
    if cookie:
        headers["cookie"] = cookie
    response = requests.get(EXPLORE_URL, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_recommended_notes(
    limit: int = DEFAULT_LIMIT,
    cookie: str | None = None,
    html: str | None = None,
) -> list[RecommendedNote]:
    content = html if html is not None else fetch_recommended_notes_html(cookie=cookie)
    notes = parse_note_sections(content, limit=limit)
    if not notes:
        raise RuntimeError("No note-item sections were parsed from the XHS response.")
    return notes


def dump_recommended_notes(
    notes: list[RecommendedNote],
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(notes),
        "notes": [asdict(note) for note in notes],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def load_cached_notes(output_path: Path = DEFAULT_OUTPUT) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return payload.get("notes", [])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch latest Xiaohongshu recommended notes.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--cookie",
        default=os.getenv("XHS_COOKIE", ""),
        help="Raw cookie string for xiaohongshu.com. Defaults to XHS_COOKIE env var.",
    )
    parser.add_argument(
        "--html-file",
        type=Path,
        help="Parse from a saved HTML file instead of making a network request.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help=f"Parse the bundled sample HTML: {SAMPLE_HTML.name}",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print simplified notes without writing the cache file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    html = None
    if args.sample:
        html = SAMPLE_HTML.read_text(encoding="utf-8")
    elif args.html_file:
        html = args.html_file.read_text(encoding="utf-8")

    notes = fetch_recommended_notes(
        limit=args.limit,
        cookie=args.cookie or None,
        html=html,
    )
    payload = []
    for note in notes:
        item = asdict(note)
        item["summary"] = build_summary(item)
        payload.append(item)

    if args.no_save:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    output_path = dump_recommended_notes(notes, output_path=args.output)
    print(f"Saved {len(notes)} recommended notes to {output_path}")


if __name__ == "__main__":
    main()
