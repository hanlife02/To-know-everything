from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.bilibili.com/x/web-interface/popular"
DEFAULT_PAGE_SIZE = 20
DEFAULT_PAGE = 1
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_OUTPUT = DATA_DIR / "hot.json"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.bilibili.com",
    "referer": "https://www.bilibili.com/v/popular/all",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}


@dataclass(slots=True)
class HotVideo:
    rank: int
    title: str
    owner_name: str
    category: str
    category_v2: str
    reason: str
    published_at: str
    duration: str
    view: int
    like: int
    reply: int
    favorite: int
    coin: int
    share: int
    description: str
    location: str
    cover: str
    bvid: str
    url: str


def format_unix_timestamp(timestamp: int | None) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: int | None) -> str:
    total_seconds = seconds or 0
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def simplify_video(item: dict[str, Any], rank: int) -> HotVideo:
    stat = item.get("stat", {})
    reason = item.get("rcmd_reason", {}).get("content", "")
    description = (item.get("desc") or item.get("dynamic") or "").strip()
    return HotVideo(
        rank=rank,
        title=item.get("title", "").strip(),
        owner_name=item.get("owner", {}).get("name", "").strip(),
        category=item.get("tname", "").strip(),
        category_v2=item.get("tnamev2", "").strip(),
        reason=reason.strip(),
        published_at=format_unix_timestamp(item.get("pubdate")),
        duration=format_duration(item.get("duration")),
        view=int(stat.get("view", 0) or 0),
        like=int(stat.get("like", 0) or 0),
        reply=int(stat.get("reply", 0) or 0),
        favorite=int(stat.get("favorite", 0) or 0),
        coin=int(stat.get("coin", 0) or 0),
        share=int(stat.get("share", 0) or 0),
        description=description,
        location=(item.get("pub_location") or "").strip(),
        cover=(item.get("pic") or "").replace("http://", "https://"),
        bvid=item.get("bvid", "").strip(),
        url=f"https://www.bilibili.com/video/{item.get('bvid', '').strip()}",
    )


def fetch_hot_videos(
    page_size: int = DEFAULT_PAGE_SIZE,
    page: int = DEFAULT_PAGE,
    timeout: int = 15,
) -> list[HotVideo]:
    params = {
        "ps": page_size,
        "pn": page,
        "web_location": "333.934",
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    if payload.get("code") != 0:
        raise RuntimeError(
            f"Bilibili API returned code={payload.get('code')}, message={payload.get('message')}"
        )

    items = payload.get("data", {}).get("list", [])
    base_rank = (page - 1) * page_size
    return [
        simplify_video(item, rank=base_rank + index)
        for index, item in enumerate(items, start=1)
    ]


def dump_hot_videos(
    videos: list[HotVideo],
    output_path: Path = DEFAULT_OUTPUT,
    page_size: int = DEFAULT_PAGE_SIZE,
    page: int = DEFAULT_PAGE,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "page": page,
        "page_size": page_size,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "videos": [asdict(video) for video in videos],
    }
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def load_cached_hot_videos(output_path: Path = DEFAULT_OUTPUT) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return payload.get("videos", [])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch latest Bilibili hot videos.")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to save the simplified hot list JSON.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the simplified payload only, without writing a cache file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    videos = fetch_hot_videos(page_size=args.page_size, page=args.page)
    if args.no_save:
        print(json.dumps([asdict(video) for video in videos], ensure_ascii=False, indent=2))
        return

    output_path = dump_hot_videos(
        videos=videos,
        output_path=args.output,
        page_size=args.page_size,
        page=args.page,
    )
    print(f"Saved {len(videos)} hot videos to {output_path}")


if __name__ == "__main__":
    main()
