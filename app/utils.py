from __future__ import annotations

import re
from datetime import UTC, datetime


def unix_to_datetime(value: int | float | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(float(value), tz=UTC)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_compact_number(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    raw = clean_text(str(value)).replace(",", "")
    if not raw:
        return None

    units = {"亿": 100000000, "万": 10000, "k": 1000, "K": 1000}
    for unit, multiplier in units.items():
        if raw.endswith(unit):
            number = raw.removesuffix(unit)
            try:
                return int(float(number) * multiplier)
            except ValueError:
                return None

    try:
        return int(float(raw))
    except ValueError:
        return None


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result

