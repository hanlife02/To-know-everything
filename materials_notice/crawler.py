from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.mse.pku.edu.cn"
LIST_URLS = (
    ("人才培养", f"{BASE_URL}/jxzs/tzgg.htm"),
    ("学生园地", f"{BASE_URL}/xsyd/tzgg.htm"),
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "notices.json"
DEFAULT_LIMIT = 50
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "max-age=0",
    "referer": f"{BASE_URL}/",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}
TITLE_SUFFIX = "-北京大学材料科学与工程学院"


@dataclass(slots=True)
class MaterialNotice:
    rank: int
    title: str
    published_at: str
    url: str
    source: str


def normalize_text(value: str) -> str:
    return " ".join((value or "").replace("\xa0", " ").split())


def needs_full_title(title: str) -> bool:
    text = normalize_text(title)
    return text.endswith("...") or text.endswith("…")


def extract_full_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for selector in (".content-title h3", 'meta[name="pageTitle"]', "title"):
        node = soup.select_one(selector)
        if not node:
            continue

        if getattr(node, "name", "") == "meta":
            title = normalize_text(node.get("content", ""))
        else:
            title = normalize_text(node.get_text(strip=True))

        if not title:
            continue
        if selector == "title" and title.endswith(TITLE_SUFFIX):
            title = title[: -len(TITLE_SUFFIX)].rstrip("-").strip()
        if title:
            return title

    return ""


def resolve_full_title(title: str, url: str, timeout: int = 20) -> str:
    if not needs_full_title(title) or not url:
        return title

    try:
        html = fetch_notice_html(url, timeout=timeout)
        full_title = extract_full_title(html)
    except Exception:  # noqa: BLE001
        return title

    return full_title or title


def build_notice_summary(notice: dict[str, str]) -> str:
    parts = []
    published_at = str(notice.get("published_at", "")).strip()
    source = str(notice.get("source", "")).strip()
    if source:
        parts.append(f"来源：{source}")
    if published_at:
        parts.append(f"发布时间：{published_at}")
    if notice.get("url"):
        parts.append("可直接打开原通知")
    return "，".join(parts) + "。" if parts else ""


def parse_chinese_date(value: str) -> datetime:
    text = normalize_text(value)
    try:
        return datetime.strptime(text, "%Y年%m月%d日")
    except ValueError:
        return datetime.min


def parse_notice_list(
    html: str,
    *,
    source_name: str,
    source_url: str,
    limit: int = DEFAULT_LIMIT,
) -> list[MaterialNotice]:
    soup = BeautifulSoup(html, "html.parser")
    notices: list[MaterialNotice] = []

    for index, item in enumerate(soup.select(".list > ul > li"), start=1):
        link = item.select_one("a[href]")
        date_tag = item.select_one("i")
        if not link:
            continue

        title = normalize_text(link.get_text(strip=True))
        href = str(link.get("href", "")).strip()
        published_at = normalize_text(date_tag.get_text(strip=True).strip("[]")) if date_tag else ""
        url = urljoin(source_url, href) if href else ""

        if not title or not url:
            continue

        title = resolve_full_title(title, url)

        notices.append(
            MaterialNotice(
                rank=index,
                title=title,
                published_at=published_at,
                url=url,
                source=source_name,
            )
        )
        if len(notices) >= limit:
            break

    if not notices:
        raise RuntimeError("未解析到材料学院通知列表。")
    return notices


def fetch_notice_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response.text


def merge_notices(notice_groups: list[list[MaterialNotice]], limit: int = DEFAULT_LIMIT) -> list[MaterialNotice]:
    seen: set[tuple[str, str]] = set()
    merged: list[MaterialNotice] = []

    for notice in sorted(
        [item for group in notice_groups for item in group],
        key=lambda item: (parse_chinese_date(item.published_at), item.title),
        reverse=True,
    ):
        key = (notice.url, notice.title)
        if key in seen:
            continue
        seen.add(key)
        merged.append(notice)
        if len(merged) >= limit:
            break

    return [
        MaterialNotice(
            rank=index,
            title=notice.title,
            published_at=notice.published_at,
            url=notice.url,
            source=notice.source,
        )
        for index, notice in enumerate(merged, start=1)
    ]


def fetch_notices(limit: int = DEFAULT_LIMIT) -> list[MaterialNotice]:
    notice_groups: list[list[MaterialNotice]] = []

    for source_name, source_url in LIST_URLS:
        content = fetch_notice_html(source_url)
        notice_groups.append(
            parse_notice_list(
                content,
                source_name=source_name,
                source_url=source_url,
                limit=limit,
            )
        )

    notices = merge_notices(notice_groups, limit=limit)
    if not notices:
        raise RuntimeError("未抓取到材料学院通知。")
    return notices


def dump_notices(
    notices: list[MaterialNotice],
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(notices),
        "notices": [asdict(notice) for notice in notices],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def load_cached_notices(output_path: Path = DEFAULT_OUTPUT) -> list[dict[str, str]]:
    if not output_path.exists():
        return []
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    notices = payload.get("notices", [])
    return notices if isinstance(notices, list) else []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch latest PKU MSE notices.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print simplified notices without writing the cache file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    notices = fetch_notices(limit=args.limit)
    payload = []
    for notice in notices:
        item = asdict(notice)
        item["summary"] = build_notice_summary(item)
        payload.append(item)

    if args.no_save:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    output_path = dump_notices(notices, output_path=args.output)
    print(f"Saved {len(notices)} notices to {output_path}")


if __name__ == "__main__":
    main()
