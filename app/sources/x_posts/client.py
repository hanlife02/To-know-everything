from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from app.sources.x_posts.models import XPost, XUser, parse_x_created_at


class XPostsClient(Protocol):
    def lookup_user_by_username(self, username: str) -> XUser | None:
        ...

    def fetch_user_posts(
        self,
        user: XUser,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        ...


@dataclass(slots=True)
class HttpXPostsClient:
    bearer_token: str
    api_base_url: str = "https://api.x.com"
    timeout_seconds: int = 20

    def lookup_user_by_username(self, username: str) -> XUser | None:
        payload = self._request_json(f"/2/users/by/username/{quote(username)}")
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        user_id = str(data.get("id", "")).strip()
        resolved_username = str(data.get("username", username)).strip()
        if not user_id or not resolved_username:
            return None
        return XUser(
            id=user_id,
            username=resolved_username,
            name=str(data.get("name", "")).strip(),
        )

    def fetch_user_posts(
        self,
        user: XUser,
        *,
        max_results: int,
        exclude_replies: bool,
        exclude_retweets: bool,
    ) -> list[XPost]:
        exclude: list[str] = []
        if exclude_replies:
            exclude.append("replies")
        if exclude_retweets:
            exclude.append("retweets")
        params = {
            "max_results": str(max_results),
            "tweet.fields": "created_at",
        }
        if exclude:
            params["exclude"] = ",".join(exclude)
        payload = self._request_json(f"/2/users/{quote(user.id)}/tweets?{urlencode(params)}")
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return []
        return [
            XPost(
                id=str(row.get("id", "")).strip(),
                author_id=str(row.get("author_id", user.id)).strip(),
                username=user.username,
                text=str(row.get("text", "")).strip(),
                created_at=parse_x_created_at(str(row.get("created_at", "")).strip()),
            )
            for row in rows
            if isinstance(row, dict) and str(row.get("id", "")).strip() and str(row.get("text", "")).strip()
        ]

    def _request_json(self, path: str) -> dict[str, object]:
        request = Request(
            url=f"{self.api_base_url.rstrip('/')}{path}",
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
                "User-Agent": "to-know-everything/0.1",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("x posts source returned unexpected payload shape")
        return data
