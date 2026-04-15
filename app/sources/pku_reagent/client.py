from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.sources.pku_reagent.auth import PkuReagentSessionExpiredError
from app.sources.pku_reagent.models import PkuReagentOrderQuery
from app.sources.pku_reagent.models import PkuReagentSession


class PkuReagentClient(Protocol):
    def fetch_order_rows(self, session: PkuReagentSession, query: PkuReagentOrderQuery) -> list[dict[str, object]]:
        ...


@dataclass(slots=True)
class HttpPkuReagentClient:
    base_url: str
    timeout_seconds: int = 30

    def fetch_order_rows(self, session: PkuReagentSession, query: PkuReagentOrderQuery) -> list[dict[str, object]]:
        payload = query.to_payload(username=session.username, token=session.token)
        request = Request(
            url=f"{self.base_url.rstrip('/')}/Jpost",
            data=urlencode(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Cookie": session.cookie_header,
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "to-know-everything/0.1",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        if str(data.get("flag", "")) != "1":
            message = str(data.get("message", "pku reagent source request failed"))
            if "token过期" in message:
                raise PkuReagentSessionExpiredError(message)
            raise RuntimeError(message)
        rows = data.get("data", [])
        if isinstance(rows, str) and "|||" in rows:
            return []
        if not isinstance(rows, list):
            raise RuntimeError("pku reagent source returned unexpected payload shape")
        return rows
