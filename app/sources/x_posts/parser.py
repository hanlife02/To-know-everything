from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.sources.x_posts.models import XPost, parse_x_created_at

MAIN_SCRIPT_PATTERN = re.compile(r'https://abs\.twimg\.com/responsive-web/client-web/main\.[^"]+\.js')
BEARER_TOKEN_PATTERN = re.compile(r"AAAAAAAAAAAAAAAAAAAAA[^\"']+")
GRAPHQL_OPERATION_PATTERN = re.compile(
    r'queryId:"(?P<query_id>[^"]+)",operationName:"(?P<name>UserByScreenName|UserTweets)"'
)


@dataclass(frozen=True, slots=True)
class XWebGraphqlConfig:
    main_script_url: str
    bearer_token: str
    user_by_screen_name_query_id: str
    user_tweets_query_id: str


def extract_main_script_url(html: str) -> str:
    match = MAIN_SCRIPT_PATTERN.search(html)
    if not match:
        raise ValueError("x web main script URL not found")
    return match.group(0)


def extract_graphql_config(main_script: str, *, main_script_url: str) -> XWebGraphqlConfig:
    bearer_match = BEARER_TOKEN_PATTERN.search(main_script)
    if not bearer_match:
        raise ValueError("x web bearer token not found")
    query_ids: dict[str, str] = {}
    for match in GRAPHQL_OPERATION_PATTERN.finditer(main_script):
        query_ids[match.group("name")] = match.group("query_id")
    if "UserByScreenName" not in query_ids or "UserTweets" not in query_ids:
        raise ValueError("x web graphql query ids not found")
    return XWebGraphqlConfig(
        main_script_url=main_script_url,
        bearer_token=bearer_match.group(0),
        user_by_screen_name_query_id=query_ids["UserByScreenName"],
        user_tweets_query_id=query_ids["UserTweets"],
    )


def extract_ct0(cookie_header: str) -> str:
    for part in cookie_header.split(";"):
        segment = part.strip()
        if not segment or "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        if key.strip() == "ct0":
            return value.strip()
    raise ValueError("ct0 cookie is required in X_COOKIE_HEADER")


def parse_user_rest_id(payload: dict[str, Any]) -> str | None:
    result = (
        payload.get("data", {})
        .get("user", {})
        .get("result")
    )
    if not isinstance(result, dict):
        return None
    rest_id = result.get("rest_id")
    if isinstance(rest_id, str) and rest_id.strip():
        return rest_id.strip()
    return None


def parse_timeline_posts(payload: dict[str, Any], *, username: str) -> list[XPost]:
    instructions = (
        payload.get("data", {})
        .get("user", {})
        .get("result", {})
        .get("timeline", {})
        .get("timeline", {})
        .get("instructions", [])
    )
    if not isinstance(instructions, list):
        return []
    posts: list[XPost] = []
    seen_ids: set[str] = set()
    for instruction in instructions:
        if not isinstance(instruction, dict):
            continue
        for tweet_result in _iter_primary_tweet_results(instruction):
            post = _tweet_result_to_post(tweet_result, username=username)
            if post is None or post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            posts.append(post)
    return posts


def _iter_primary_tweet_results(instruction: dict[str, Any]):
    entry = instruction.get("entry")
    if isinstance(entry, dict):
        yield from _iter_entry_tweet_results(entry)
    entries = instruction.get("entries")
    if isinstance(entries, list):
        for entry_item in entries:
            if isinstance(entry_item, dict):
                yield from _iter_entry_tweet_results(entry_item)


def _iter_entry_tweet_results(entry: dict[str, Any]):
    content = entry.get("content")
    if not isinstance(content, dict):
        return
    if content.get("type") == "TimelinePinEntry":
        return
    item_content = content.get("itemContent")
    if isinstance(item_content, dict):
        tweet_results = item_content.get("tweet_results")
        if isinstance(tweet_results, dict):
            result = tweet_results.get("result")
            if isinstance(result, dict):
                yield result
    items = content.get("items")
    if isinstance(items, list):
        for module_item in items:
            if not isinstance(module_item, dict):
                continue
            item = module_item.get("item")
            if not isinstance(item, dict):
                continue
            item_content = item.get("itemContent")
            if not isinstance(item_content, dict):
                continue
            tweet_results = item_content.get("tweet_results")
            if isinstance(tweet_results, dict):
                result = tweet_results.get("result")
                if isinstance(result, dict):
                    yield result


def _tweet_result_to_post(result: dict[str, Any], *, username: str) -> XPost | None:
    typename = result.get("__typename")
    if typename in {"TweetWithVisibilityResults", "TweetTombstone"}:
        result = result.get("tweet", result)
    if not isinstance(result, dict):
        return None
    rest_id = result.get("rest_id")
    legacy = result.get("legacy")
    if not isinstance(rest_id, str) or not rest_id.strip() or not isinstance(legacy, dict):
        return None
    full_text = ""
    note_tweet = result.get("note_tweet")
    if isinstance(note_tweet, dict):
        note_result = note_tweet.get("note_tweet_results", {}).get("result")
        if isinstance(note_result, dict):
            note_text = note_result.get("text")
            if isinstance(note_text, str) and note_text.strip():
                full_text = note_text.strip()
    if not full_text:
        raw_text = legacy.get("full_text")
        if isinstance(raw_text, str) and raw_text.strip():
            full_text = raw_text.strip()
    if not full_text:
        return None
    author_result = (
        result.get("core", {})
        .get("user_results", {})
        .get("result", {})
    )
    author_rest_id = ""
    if isinstance(author_result, dict):
        author_rest_id_raw = author_result.get("rest_id")
        if isinstance(author_rest_id_raw, str):
            author_rest_id = author_rest_id_raw.strip()
    created_at_raw = legacy.get("created_at")
    created_at = parse_x_created_at(created_at_raw) if isinstance(created_at_raw, str) else None
    return XPost(
        id=rest_id.strip(),
        author_id=author_rest_id or username,
        username=username,
        text=full_text,
        created_at=created_at,
        url=f"https://x.com/{username}/status/{rest_id.strip()}",
    )


def compact_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
