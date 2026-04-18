from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class XPost:
    id: str
    author_id: str
    username: str
    text: str
    created_at: datetime | None = None
    url: str = ""


def parse_x_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    try:
        if normalized.endswith("Z"):
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for pattern in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%d %H:%M:%S%z"):
        try:
            return datetime.strptime(normalized, pattern).astimezone(UTC)
        except ValueError:
            continue
    return None
