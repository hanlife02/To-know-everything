from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MseNotice:
    title: str
    url: str
    published_on: str
