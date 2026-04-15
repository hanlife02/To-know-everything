from __future__ import annotations

from typing import NotRequired, TypedDict


class SourceDefinition(TypedDict):
    source_key: str
    label: str
    description: NotRequired[str]


class NotificationPayload(TypedDict):
    title: str
    body: str
    mode: str


class AutomationPayload(TypedDict):
    enabled: bool
    daily_time: str
    default_mode: str

